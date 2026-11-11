"""Explicit-role frozen final models and outcome-blind prediction; no score-join API."""

import argparse
from pathlib import Path
import subprocess
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from . import baseline as base
from . import session_anxiety_regression as reg
from .baseline_preprocessing import FoldPreprocessor
from .features import finite, read_jsonl, write_jsonl
from .pilot_state import atomic, digest, inventory, now, read
from .validate_sample import require_ignored

ROOT=Path(__file__).resolve().parents[2]
CONFIG=ROOT/'configs/independent-anxiety-evaluation-v2.json'
CONFIG_ID='c395c8052d582e83c5f24ad8e9cd75e68fd33d94752c3f8caea1567ba591a8d5'
VERSION='explicit-final-support-v2'


def load_config():
    cfg=read(CONFIG);old=reg.load_config()
    if digest(cfg)!=CONFIG_ID or any(cfg[k]!=old[k] for k in ('models','targets','regression','preprocessing','summaries','mean_strategy')):
        raise ValueError('Locked final design/settings changed')
    return cfg


def load_design(path):
    require_ignored(path);cfg=load_config();plan=read(path)
    if digest(plan)!=cfg['allocation_manifest_sha256']:
        raise ValueError('Locked acquisition/allocation manifest changed')
    train=plan['training_participants'];final=plan['locked_final']
    if (train!=[f's{i}' for i in range(1,7)] or len(final)!=10 or len(set(final))!=10
            or set(train+['s25'])&set(final) or plan['engineering_only']!=['s25']
            or [e['id'] for e in plan['participants']]!=final
            or any(e['role']!='locked_final' for e in plan['participants'])):
        raise ValueError('Training/final/engineering role separation violated')
    return cfg,plan


def context(cfg,plan):
    return {'version':VERSION,'configuration':cfg,'configuration_id':digest(cfg),'allocation':plan,
            'code':base.code_hashes(),'software':base.versions(),
            'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),'created_at':now()}


def check_context(receipt,cfg,plan):
    if (receipt['version']!=VERSION or receipt['configuration']!=cfg or receipt['configuration_id']!=digest(cfg)
            or receipt['allocation']!=plan or receipt['code']!=base.code_hashes() or receipt['software']!=base.versions()):
        raise ValueError('Incompatible model/export computation context')


def artifact_inventory(folder):
    # Reject misplaced outcome payloads before hashing/reading any artifact tree.
    for path in folder.rglob('*'):
        if ('selfreportedanx' in path.name.lower() or path.name.lower()=='outcomes.jsonl'
                or any('sealed-outcome' in part.lower() for part in path.parts)):
            raise ValueError('Questionnaire payload forbidden in model/export/prediction artifacts')
    return inventory(folder)


def complete_files(folder,receipt):
    files=artifact_inventory(folder);files.pop('receipt.json',None)
    if receipt['status']!='completed' or files!=receipt['output_files']:
        raise ValueError('Incomplete or changed artifacts')


def train(plan_path,source_audit,output):
    cfg,plan=load_design(plan_path)
    # Only the old six-development importer has questionnaire access. No final path is passed.
    index,x,ys,proof=reg.load_sessions(source_audit,reg.load_config())
    if [r['participant'] for r in index]!=plan['training_participants'] or any(r['role']!='development_only' for r in index):
        raise ValueError('Final/engineering participants in training')
    require_ignored(output);output.mkdir(parents=True,exist_ok=False)
    receipt={**context(cfg,plan),'status':'running','kind':'frozen_training_bundle','source_audit':str(source_audit.resolve()),
             'source_proof':proof,'training_participants':plan['training_participants'],'final_outcomes_read':False}
    atomic(output/'receipt.json',receipt);start=time.perf_counter()
    try:
        with threadpool_limits(limits=1):
            for target,y in ys.items():
                for name,cols in cfg['models'].items():
                    model=reg.fit_fold(base.matrix(x,cols),y,cols,cfg)
                    folder=output/'models'/target/name;folder.mkdir(parents=True)
                    joblib.dump(model,folder/'model.joblib')
                    state=model['preprocessor'].snapshot(cols) if cols else None
                    atomic(folder/'fit.json',{'target':target,'model':name,'training_participants':plan['training_participants'],
                        'training_sessions':[r['session_key'] for r in index],'preprocessing':state,'training_mean':model['mean'],
                        'fallback_to_mean':model['fallback'],'warnings':model['warnings'],
                        'parameters':model['estimator'].get_params() if model['estimator'] is not None else None})
        feature_run=Path(read(source_audit/'receipt.json')['feature_run'])
        cameras={r['id_recording']:r['id_video_sha256'] for r in read_jsonl(feature_run/'windows.jsonl')}
        atomic(output/'training-camera-hashes.json',cameras)
        atomic(output/'feature-lists.json',cfg['models'])
        (output/'pip-freeze.txt').write_text(subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
        receipt.update(status='completed',ended=now(),elapsed_seconds=time.perf_counter()-start,output_files=artifact_inventory(output))
        receipt['output_files'].pop('receipt.json',None)
    except BaseException as exc:
        receipt.update(status='failed',failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:atomic(output/'receipt.json',receipt)
    return validate_models(output,plan_path,deep=True)


def validate_models(folder,plan_path,deep=False):
    """Shallow inference validation reads artifacts only, never training/final questionnaire files."""
    cfg,plan=load_design(plan_path);require_ignored(folder);receipt=read(folder/'receipt.json')
    check_context(receipt,cfg,plan);complete_files(folder,receipt)
    if (receipt['kind']!='frozen_training_bundle' or receipt['training_participants']!=plan['training_participants']
            or receipt['final_outcomes_read'] or read(folder/'feature-lists.json')!=cfg['models']):
        raise ValueError('Wrong model bundle/roles')
    cameras=read(folder/'training-camera-hashes.json')
    if (set(cameras)!={p+'/'+t for p in plan['training_participants'] for t in ('T1','T2','T3')}
            or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in cameras.values())):
        raise ValueError('Training video identity inventory mismatch')
    expected={str(Path('models')/t/m/'model.joblib') for t in cfg['targets'] for m in cfg['models']}
    if {str(p.relative_to(folder)) for p in folder.rglob('*.joblib')}!=expected:
        raise ValueError('Incomplete/extra frozen model inventory')
    data=None
    if deep:
        index,x,ys,proof=reg.load_sessions(Path(receipt['source_audit']),reg.load_config())
        if proof!=receipt['source_proof'] or [r['participant'] for r in index]!=plan['training_participants']:
            raise ValueError('Training source changed')
        feature_run=Path(read(Path(receipt['source_audit'])/'receipt.json')['feature_run'])
        if cameras!={r['id_recording']:r['id_video_sha256'] for r in read_jsonl(feature_run/'windows.jsonl')}:
            raise ValueError('Training video identities changed')
        data=(index,x,ys)
    for target in cfg['targets']:
        for name,cols in cfg['models'].items():
            loc=folder/'models'/target/name;model=joblib.load(loc/'model.joblib');fit=read(loc/'fit.json')
            pre=model['preprocessor'];snapshot=pre.snapshot(cols) if pre else None
            expected_fit=bool(cols and not model['fallback'])
            params=reg.Ridge(**reg.estimator_parameters(cfg)).get_params() if expected_fit else None
            if (model['columns']!=cols or fit['training_participants']!=plan['training_participants']
                    or fit['training_sessions']!=[p+'/session-1' for p in plan['training_participants']]
                    or fit['target']!=target or fit['model']!=name or fit['preprocessing']!=snapshot
                    or fit['parameters']!=params or (model['estimator'] is not None)!=expected_fit
                    or (expected_fit and model['estimator'].get_params()!=params)
                    or fit['training_mean']!=model['mean'] or fit['fallback_to_mean']!=model['fallback']):
                raise ValueError('Model settings/preprocessing/role mismatch')
            if data:
                _,x,ys=data;y=ys[target];values=base.matrix(x,cols)
                fresh=FoldPreprocessor().fit(values) if cols else None
                if ((fresh.snapshot(cols) if fresh else None)!=snapshot or model['mean']!=float(y.mean())
                        or model['fallback']!=bool(cols and not fresh.keep_.any())):
                    raise ValueError('Training-only preprocessing/mean mismatch')
                if expected_fit:
                    z=fresh.transform(values);zm=z.mean(axis=0);center=z-zm;coef=model['estimator'].coef_
                    if (not np.allclose((center.T@center+cfg['regression']['alpha']*np.eye(z.shape[1]))@coef,
                                        center.T@(y-y.mean()),atol=1e-9,rtol=1e-9)
                            or not np.isclose(model['estimator'].intercept_,y.mean()-zm@coef,atol=1e-10,rtol=1e-10)):
                        raise ValueError('Training-only Ridge objective mismatch')
    return {'status':'passed','models':12,'training_participants':plan['training_participants'],
            'deep_training_check':deep,'final_outcomes_read':False}


def prediction_inventory(rows,people,cfg,plan):
    keys={(p,t,m) for p in people for t in cfg['targets'] for m in cfg['models']}
    seen=set()
    if not people or len(set(people))!=len(people) or not set(people)<=set(plan['locked_final']):
        raise ValueError('Wrong/duplicate final participant inventory')
    for row in rows:
        key=(row['participant'],row['target'],row['model'])
        if (key not in keys or key in seen or row['role']!='locked_final'
                or row['session_key']!=row['participant']+'/session-1' or not finite(row['prediction'])
                or row['configuration_id']!=digest(cfg) or row['training_participants']!=plan['training_participants']
                or set(row)!={'participant','role','session_key','target','model','prediction','configuration_id','training_participants','support'}):
            raise ValueError('Prediction role/leakage/inventory mismatch')
        seen.add(key)
    if seen!=keys:raise ValueError('Incomplete prediction inventory')


def predict_batches(plan_path,models_run,exports,output,require_all=True):
    from .final_camera_features import load_export
    cfg,plan=load_design(plan_path);validate_models(models_run,plan_path)
    index=[];values=[];sources={};video_hashes=set()
    for path in exports:
        ix,x,export_receipt=load_export(path,plan_path,models_run)
        incoming=list(export_receipt['source_recordings'].values())
        if video_hashes & set(incoming):raise ValueError('Duplicate video content across final batches')
        video_hashes.update(incoming)
        index+=ix;values+=x;sources[str(path.resolve())]=artifact_inventory(path)
    people=[r['participant'] for r in index]
    if not people or len(set(people))!=len(people) or not set(people)<=set(plan['locked_final']):
        raise ValueError('Overlapping/non-final export batches')
    if require_all and set(people)!=set(plan['locked_final']):raise ValueError('All ten scheduled final sessions required')
    order=sorted(range(len(index)),key=lambda i:plan['locked_final'].index(people[i]))
    index=[index[i] for i in order];values=[values[i] for i in order];people=[r['participant'] for r in index]
    require_ignored(output);output.mkdir(parents=True,exist_ok=False)
    receipt={**context(cfg,plan),'status':'running','kind':'unlabeled_final_predictions','complete_cohort':require_all,
             'models_run':str(models_run.resolve()),'model_files':artifact_inventory(models_run),'exports':sources,
             'participants':people,'outcomes_read':False}
    atomic(output/'receipt.json',receipt)
    try:
        rows=[]
        with threadpool_limits(limits=1):
            for target in cfg['targets']:
                for name,cols in cfg['models'].items():
                    model=joblib.load(models_run/'models'/target/name/'model.joblib')
                    state=model['preprocessor'].snapshot(cols) if cols else None
                    empty=state['training_all_missing_columns'] if state else []
                    for meta,raw,p in zip(index,values,reg.predict(model,base.matrix(values,cols))):
                        rows.append({'participant':meta['participant'],'role':'locked_final','session_key':meta['session_key'],
                            'target':target,'model':name,'prediction':float(p),'configuration_id':digest(cfg),
                            'training_participants':plan['training_participants'],'support':reg.support(raw,cols,empty)})
        prediction_inventory(rows,people,cfg,plan);write_jsonl(output/'predictions.jsonl',rows)
        receipt.update(status='completed',ended=now(),output_files=artifact_inventory(output));receipt['output_files'].pop('receipt.json',None)
    except BaseException as exc:
        receipt.update(status='failed',failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:atomic(output/'receipt.json',receipt)
    return validate_predictions(output,plan_path)


def validate_predictions(folder,plan_path):
    from .final_camera_features import load_export
    cfg,plan=load_design(plan_path);r=read(folder/'receipt.json');check_context(r,cfg,plan);complete_files(folder,r)
    if r['kind']!='unlabeled_final_predictions' or r['outcomes_read']:raise ValueError('Unblinded/wrong prediction bundle')
    models=Path(r['models_run']);validate_models(models,plan_path)
    if artifact_inventory(models)!=r['model_files']:raise ValueError('Frozen models changed')
    raw={}
    for path,proof in r['exports'].items():
        path=Path(path)
        if artifact_inventory(path)!=proof:raise ValueError('Export changed')
        ix,x,_=load_export(path,plan_path,models)
        for meta,value in zip(ix,x):
            if meta['participant'] in raw:raise ValueError('Overlapping batches')
            raw[meta['participant']]=value
    people=r['participants'];rows=read_jsonl(folder/'predictions.jsonl');prediction_inventory(rows,people,cfg,plan)
    if set(people)!=set(raw) or (r['complete_cohort'] and set(people)!=set(plan['locked_final'])):
        raise ValueError('Missing scheduled prediction sessions')
    for row in rows:
        model=joblib.load(models/'models'/row['target']/row['model']/'model.joblib');cols=cfg['models'][row['model']]
        empty=model['preprocessor'].snapshot(cols)['training_all_missing_columns'] if cols else []
        value=raw[row['participant']]
        if (not np.isclose(row['prediction'],float(reg.predict(model,base.matrix([value],cols))[0]),atol=1e-12,rtol=1e-12)
                or row['support']!=reg.support(value,cols,empty)):
            raise ValueError('Predictions/support not reproducible from frozen models')
    return {'status':'passed','predictions':len(rows),'sessions':len(people),'complete_cohort':r['complete_cohort'],
            'model_artifacts_hashed':True,'prediction_artifacts_hashed':True,'outcomes_read':False,
            'all_scheduled_predictions_locked':bool(r['complete_cohort'] and len(rows)==cfg['expected_final_predictions'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('train','validate-models','predict','validate-predictions'):mode.add_argument('--'+name,action='store_true')
    parser.add_argument('--source-audit',type=Path);parser.add_argument('--models-run',type=Path)
    parser.add_argument('--export',type=Path,action='append',default=[])
    parser.add_argument('--allow-partial-batch',action='store_true');parser.add_argument('--deep-training-check',action='store_true')
    a=parser.parse_args()
    if a.train:
        if not a.source_audit:parser.error('--source-audit required')
        result=train(a.plan,a.source_audit,a.output)
    elif a.validate_models:result=validate_models(a.output,a.plan,a.deep_training_check)
    elif a.predict:
        if not a.models_run or not a.export:parser.error('--models-run and --export required')
        result=predict_batches(a.plan,a.models_run,a.export,a.output,not a.allow_partial_batch)
    else:result=validate_predictions(a.output,a.plan)
    print(result)


if __name__=='__main__':main()
