"""Frozen facial-family ablations and added feature-missingness stress tests."""

import argparse
import json
from pathlib import Path
import subprocess
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from . import baseline as base
from .features import read_jsonl, write_jsonl
from .pilot_state import atomic, digest, inventory, now, read
from .validate_sample import require_ignored

ROOT=Path(__file__).resolve().parents[2]
CONFIG=ROOT/'configs/confound-ablation-v1.json'
REGISTERED={'confound-ablation-v1':'3c80cf92a6b5b2973b03f1002fc92ef621e95eaa5b6b083c9e1a91ca74b55873'}


def expected_ablations(baseline):
    mouth=baseline['models']['facial'][:3];motion=baseline['models']['facial'][-2:]
    result={}
    for suffix,removed in (('no_mouth',mouth),('no_motion',motion),('no_mouth_no_motion',mouth+motion)):
        columns=[c for c in baseline['models']['facial'] if c not in removed]
        result['facial_'+suffix]=columns
        result['facial_'+suffix+'_plus_bpm']=columns+baseline['models']['camera_bpm']
    return result


def availability(models):
    return {name:{'available':bool(columns),'column_count':len(columns),
                  'reason':None if columns else 'empty feature allowlist'} for name,columns in models.items()}


def load_config():
    cfg=read(CONFIG);original=base.load_config()
    if (REGISTERED.get(cfg['version'])!=digest(cfg) or cfg['baseline_configuration_id']!=digest(original)
            or cfg['ablation_models']!=expected_ablations(original)
            or cfg['saved_baseline_models']!=original['models']
            or any(cfg[k]!=original[k] for k in ('logistic_regression','decision_threshold','decision_rule','preprocessing'))):
        raise ValueError('Modified/unregistered ablation design or changed baseline settings')
    union=sorted({c for columns in [*cfg['ablation_models'].values(),*original['models'].values()] for c in columns})
    if cfg['masking']['columns']!=union or any(c.startswith(('id_','label_','ref_')) for c in union):
        raise ValueError('Mask/predictor allowlist mismatch')
    return cfg,original


def analysis_config(original,models,cfg):
    return {**original,'models':models,'interpretation':cfg['interpretation']}


def source_baseline(folder,original):
    """Explicit compatibility import: recorded source modules unchanged; additions allowed."""
    require_ignored(folder)
    status=read(folder/'status.json');plan=read(folder/'plan.json')
    if (status['status']!='completed' or status['plan_sha256']!=digest(plan)
            or plan['configuration']!=original or plan['configuration_id']!=digest(original)
            or plan['software']!=base.versions()):
        raise ValueError('Incomplete/incompatible saved baseline')
    current=base.code_hashes()
    if any(current.get(name)!=checksum for name,checksum in plan['code'].items()):
        raise ValueError('Saved baseline computation changed')
    files=inventory(folder);without_status={k:v for k,v in files.items() if k!='status.json'}
    if without_status!=status['output_files']:
        raise ValueError('Saved baseline output hashes changed')
    data,inputs=base.load_features(Path(plan['feature_run']),original)
    if inputs!=plan['input_provenance']:
        raise ValueError('Saved baseline feature inputs changed')
    predictions=read_jsonl(folder/'predictions.jsonl')
    validation=base.validate_models(folder,plan,original,data,predictions)
    return plan,data,predictions,{'files':files,'feature_inputs':inputs,'validation':validation}


def scores(n_rows,n_columns,seed):
    """RNG receives shape/seed only: no labels, IDs, tasks or participant strata."""
    return np.random.Generator(np.random.PCG64(seed)).random((n_rows,n_columns))


def mask_row(row,draws,columns,level):
    if len(draws)!=len(columns) or not 0<=level<=1:
        raise ValueError('Invalid mask dimensions/level')
    result=dict(row)
    for c,u in zip(columns,draws):
        if row[c] is not None and u<level:
            result[c]=None
    return result


def masked_data(data,ordered_keys,draws,columns,level):
    positions={key:i for i,key in enumerate(ordered_keys)}
    return {contrast:{'index':d['index'],'x':[mask_row(row,draws[positions[m['id_window_key']]],columns,level)
        for row,m in zip(d['x'],d['index'])]} for contrast,d in data.items()}


def mask_records(rows,draws,columns,levels):
    result=[]
    for level in levels:
        for row,u in zip(rows,draws):
            result.append({'window_key':row['id_window_key'],'level':level,
                'natural_missing_columns':[c for c in columns if row[c] is None],
                'eligible_count':sum(row[c] is not None for c in columns),
                'added_missing_columns':[c for c,value in zip(columns,u) if row[c] is not None and value<level]})
    return result


def fold_description(data,original):
    return {contrast:[{**{k:v for k,v in f.items() if k not in ('train','test')},
        'training_row_keys':[d['index'][i]['id_window_key'] for i in f['train']],
        'evaluation_row_keys':[d['index'][i]['id_window_key'] for i in f['test']]} for f in base.folds(d['index'],original)] for contrast,d in data.items()}


def prepare(baseline_run,output):
    cfg,original=load_config();baseline_plan,data,_,proof=source_baseline(baseline_run,original)
    if fold_description(data,original)!=baseline_plan['folds']:
        raise ValueError('Ablation folds differ from completed baseline')
    feature_run=Path(baseline_plan['feature_run']);rows=read_jsonl(feature_run/'windows.jsonl')
    require_ignored(output);output.mkdir(parents=True,exist_ok=False)
    plan={'prepared_at':now(),'configuration':cfg,'configuration_id':digest(cfg),
        'baseline_run':str(baseline_run.resolve()),'baseline_plan_sha256':digest(baseline_plan),
        'feature_run':str(feature_run),'source_proof':proof,'folds':baseline_plan['folds'],
        'ordered_window_keys':[r['id_window_key'] for r in rows],
        'availability':availability(cfg['ablation_models']),'software':base.versions(),'code':base.code_hashes(),
        'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'git_status_at_prepare':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)}
    atomic(output/'plan.json',plan);atomic(output/'configuration.json',cfg)
    atomic(output/'feature-lists.json',{'ablations':cfg['ablation_models'],'saved_baselines':original['models']})
    atomic(output/'status.json',{'status':'prepared','plan_sha256':digest(plan),'prepared_at':plan['prepared_at']})
    return plan


def load_plan(output):
    plan=read(output/'plan.json');cfg,original=load_config()
    if (plan['configuration']!=cfg or plan['configuration_id']!=digest(cfg)
            or plan['software']!=base.versions() or plan['code']!=base.code_hashes()
            or read(output/'configuration.json')!=cfg
            or read(output/'feature-lists.json')!={'ablations':cfg['ablation_models'],'saved_baselines':original['models']}):
        raise ValueError('Frozen ablation settings/code/runtime changed')
    return plan,cfg,original


def prediction(contrast,name,meta,fold,probability,raw,columns,empty,plan,original):
    return {'contrast':contrast,'model':name,'window_key':meta['id_window_key'],
        'participant':fold['participant'],'fold_id':fold['fold_id'],
        'training_participants':fold['training_participants'],'configuration_id':plan['configuration_id'],
        'truth':meta['target'],'condition':meta['label_condition'],'probability_active':float(probability),
        'prediction':int(probability>original['decision_threshold']),
        'support':base.feature_support(raw,columns,empty)}


def fit_ablations(output,plan,cfg,original,data):
    models={name:cols for name,cols in cfg['ablation_models'].items() if cols}
    predictions=[]
    with base.threadpool_limits(limits=cfg['thread_limit']):
        for contrast,d in data.items():
            y=np.asarray([m['target'] for m in d['index']])
            for name,columns in models.items():
                x=base.matrix(d['x'],columns)
                for f in base.folds(d['index'],original):
                    print('Fit clean ablation',contrast,name,f['participant'],flush=True)
                    model=base.fit_fold(x[f['train']],y[f['train']],columns,original)
                    location=output/'models'/contrast/name/f['participant'];location.mkdir(parents=True)
                    joblib.dump(model,location/'model.joblib')
                    state=model['preprocessor'].snapshot(columns)
                    state.update(fallback_to_prior=model['fallback'],warnings=model['warnings'],estimator_parameters=model['estimator'].get_params(),
                        training_participants=f['training_participants'],evaluation_participants=f['evaluation_participants'],
                        training_row_keys=[d['index'][i]['id_window_key'] for i in f['train']],
                        evaluation_row_keys=[d['index'][i]['id_window_key'] for i in f['test']],configuration_id=plan['configuration_id'])
                    atomic(location/'fit.json',state)
                    probs=base.probabilities(model,x[f['test']])
                    predictions.extend(prediction(contrast,name,d['index'][i],f,p,d['x'][i],columns,
                        state['training_all_missing_columns'],plan,original) for i,p in zip(f['test'],probs))
    write_jsonl(output/'predictions.jsonl',predictions)
    saved=read_jsonl(output/'predictions.jsonl');acfg=analysis_config(original,models,cfg)
    base.prediction_inventory(saved,data,acfg,plan['configuration_id'])
    atomic(output/'metrics.json',base.report_from_predictions(saved,acfg))
    return base.validate_models(output,plan,acfg,data,saved)


def stress_predictions(output,plan,cfg,original,data,draws):
    available={k:v for k,v in cfg['ablation_models'].items() if v}
    all_models={**original['models'],**available}
    keys=plan['ordered_window_keys'];columns=cfg['masking']['columns']
    with threadpool_limits(limits=cfg['thread_limit']), (output/'stress-predictions.jsonl').open('x') as target:
        for contrast,d in data.items():
            for name,model_columns in all_models.items():
                for f in base.folds(d['index'],original):
                    source=Path(plan['baseline_run']) if name in original['models'] else output
                    location=source/'models'/contrast/name/f['participant']
                    model=joblib.load(location/'model.joblib');state=read(location/'fit.json')
                    # No model/preprocessor fitting under any mask level.
                    for level in cfg['masking']['levels']:
                        masked=masked_data({contrast:d},keys,draws,columns,level)[contrast]
                        x=base.matrix(masked['x'],model_columns)
                        probs=base.probabilities(model,x[f['test']])
                        for i,p in zip(f['test'],probs):
                            row=prediction(contrast,name,d['index'][i],f,p,masked['x'][i],model_columns,
                                state['training_all_missing_columns'],plan,original)
                            natural=base.feature_support(d['x'][i],model_columns,state['training_all_missing_columns'])
                            row.update(mask_level=level,natural_support=natural,
                                added_missing_count=row['support']['missing_count']-natural['missing_count'],
                                model_source='saved_baseline' if name in original['models'] else 'clean_ablation_fit',
                                source_model_configuration_id=cfg['baseline_configuration_id'] if name in original['models'] else plan['configuration_id'])
                            target.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')


def reports(output,plan,cfg,original,data,baseline_predictions):
    available={k:v for k,v in cfg['ablation_models'].items() if v}
    all_models={**original['models'],**available};full_cfg=analysis_config(original,all_models,cfg)
    baseline_rows=[{**r,'configuration_id':plan['configuration_id']} for r in baseline_predictions]
    clean=baseline_rows+read_jsonl(output/'predictions.jsonl')
    base.prediction_inventory(clean,data,full_cfg,plan['configuration_id'])
    atomic(output/'clean-comparison.json',base.report_from_predictions(clean,full_cfg))
    stress=read_jsonl(output/'stress-predictions.jsonl')
    summaries={}
    draws=np.load(output/'mask-scores.npy',allow_pickle=False)
    for level in cfg['masking']['levels']:
        selected=[r for r in stress if r['mask_level']==level]
        masked=masked_data(data,plan['ordered_window_keys'],draws,cfg['masking']['columns'],level)
        base.prediction_inventory(selected,masked,full_cfg,plan['configuration_id'])
        summaries[str(level)]=base.report_from_predictions(selected,full_cfg)
    atomic(output/'stress-metrics.json',summaries)
    # Realized added rates are descriptive strata, never inputs to generation.
    rates=[]
    for level in cfg['masking']['levels']:
        for contrast,d in data.items():
            positions={k:i for i,k in enumerate(plan['ordered_window_keys'])}
            for person in cfg['participants']:
                for truth in (0,1):
                    selected=[(r,m) for r,m in zip(d['x'],d['index']) if m['id_participant']==person and m['target']==truth]
                    eligible=added=0
                    for row,m in selected:
                        for c,u in zip(cfg['masking']['columns'],draws[positions[m['id_window_key']]]):
                            if row[c] is not None:
                                eligible+=1;added+=int(u<level)
                    rates.append({'level':level,'contrast':contrast,'participant':person,'truth':truth,
                        'eligible_cells':eligible,'added_missing_cells':added,'realized_added_fraction':added/eligible if eligible else None})
    atomic(output/'mask-rates.json',rates)
    render_report(output,cfg)


def validate(output,completed=True):
    plan,cfg,original=load_plan(output);status=read(output/'status.json')
    if status.get('plan_sha256')!=digest(plan) or (completed and status['status']!='completed'):
        raise ValueError('Incomplete/changed ablation plan')
    if completed:
        actual=inventory(output);actual.pop('status.json',None)
        if actual!=status['output_files']:raise ValueError('Ablation outputs changed')
    baseline_plan,data,baseline_predictions,proof=source_baseline(Path(plan['baseline_run']),original)
    if proof!=plan['source_proof'] or digest(baseline_plan)!=plan['baseline_plan_sha256']:
        raise ValueError('Original baseline changed')
    if fold_description(data,original)!=plan['folds']:
        raise ValueError('Fold split changed')
    rows=read_jsonl(Path(plan['feature_run'])/'windows.jsonl')
    keys=[r['id_window_key'] for r in rows]
    if keys!=plan['ordered_window_keys']:raise ValueError('Mask row alignment changed')
    draws=np.load(output/'mask-scores.npy',allow_pickle=False)
    expected=scores(len(rows),len(cfg['masking']['columns']),cfg['masking']['seed'])
    if not np.array_equal(draws,expected):raise ValueError('Seeded mask scores do not reproduce')
    expected_masks=mask_records(rows,draws,cfg['masking']['columns'],cfg['masking']['levels'])
    if read_jsonl(output/'masks.jsonl')!=expected_masks:raise ValueError('Masks/natural missingness do not reproduce')
    available={k:v for k,v in cfg['ablation_models'].items() if v}
    acfg=analysis_config(original,available,cfg)
    clean=read_jsonl(output/'predictions.jsonl')
    clean_validation=base.validate_models(output,plan,acfg,data,clean)
    clean_lookup={(r['contrast'],r['model'],r['window_key']):r for r in baseline_predictions+clean}
    all_models={**original['models'],**available};full_cfg=analysis_config(original,all_models,cfg)
    stress=read_jsonl(output/'stress-predictions.jsonl')
    expected_total=len(cfg['masking']['levels'])*len(all_models)*len(cfg['contrasts'])*72
    if len(stress)!=expected_total:raise ValueError('Incomplete stress inventory')
    summaries={}
    for level in cfg['masking']['levels']:
        selected=[r for r in stress if r['mask_level']==level]
        masked=masked_data(data,keys,draws,cfg['masking']['columns'],level)
        base.prediction_inventory(selected,masked,full_cfg,plan['configuration_id'])
        for contrast,d in data.items():
            for name,columns in all_models.items():
                x=base.matrix(masked[contrast]['x'],columns)
                for f in base.folds(d['index'],original):
                    source=Path(plan['baseline_run']) if name in original['models'] else output
                    loc=source/'models'/contrast/name/f['participant'];model=joblib.load(loc/'model.joblib');state=read(loc/'fit.json')
                    observed=[r for r in selected if r['contrast']==contrast and r['model']==name and r['participant']==f['participant']]
                    expected_probs=base.probabilities(model,x[f['test']])
                    if ([r['window_key'] for r in observed]!=[d['index'][i]['id_window_key'] for i in f['test']]
                            or not np.array_equal(expected_probs,[r['probability_active'] for r in observed])):
                        raise ValueError('Masked predictions differ from frozen models')
                    for p,i in zip(observed,f['test']):
                        raw=base.feature_support(d['x'][i],columns,state['training_all_missing_columns'])
                        expected_support=base.feature_support(masked[contrast]['x'][i],columns,state['training_all_missing_columns'])
                        source_id=cfg['baseline_configuration_id'] if name in original['models'] else plan['configuration_id']
                        source_kind='saved_baseline' if name in original['models'] else 'clean_ablation_fit'
                        if (p['natural_support']!=raw or p['support']!=expected_support
                                or p['added_missing_count']!=expected_support['missing_count']-raw['missing_count']
                                or p['source_model_configuration_id']!=source_id or p['model_source']!=source_kind):
                            raise ValueError('Added versus natural support/model provenance mismatch')
                        if level==0:
                            old=clean_lookup[contrast,name,p['window_key']]
                            if p['probability_active']!=old['probability_active'] or p['prediction']!=old['prediction']:
                                raise ValueError('Clean results differ from saved baseline/ablation')
        summaries[str(level)]=base.report_from_predictions(selected,full_cfg)
    if read(output/'stress-metrics.json')!=summaries:
        raise ValueError('Stress metrics not derived from saved predictions')
    comparison=[{**r,'configuration_id':plan['configuration_id']} for r in baseline_predictions]+clean
    if read(output/'clean-comparison.json')!=base.report_from_predictions(comparison,full_cfg):
        raise ValueError('Baseline comparison metrics mismatch')
    return {'status':'passed','clean_ablation_predictions':len(clean),'new_fold_models':clean_validation['fold_models'],
        'stress_predictions':len(stress),'mask_rows':len(expected_masks),'mask_shape':list(draws.shape),
        'baseline_files_unchanged':True,'feature_tables_unchanged':True,'same_participant_folds':True,
        'all_levels_reproduce_from_frozen_models':True,'clean_matches_saved_baseline':True,
        'natural_nulls_preserved':True,'shared_nested_masks':True,'rng_uses_shape_seed_only':True,
        'classifiers_refit_for_masking':False}


def execute(output):
    plan,cfg,original=load_plan(output);status=read(output/'status.json')
    if status['status']!='prepared' or status['plan_sha256']!=digest(plan):
        raise ValueError('Refuse changed plan or overwrite; use a fresh root')
    baseline_plan,data,baseline_predictions,proof=source_baseline(Path(plan['baseline_run']),original)
    if proof!=plan['source_proof'] or digest(baseline_plan)!=plan['baseline_plan_sha256']:
        raise ValueError('Saved baseline changed since preparation')
    start=time.perf_counter();atomic(output/'status.json',{'status':'running','started':now(),'plan_sha256':digest(plan)})
    try:
        rows=read_jsonl(Path(plan['feature_run'])/'windows.jsonl')
        draws=scores(len(rows),len(cfg['masking']['columns']),cfg['masking']['seed'])
        np.save(output/'mask-scores.npy',draws,allow_pickle=False)
        write_jsonl(output/'masks.jsonl',mask_records(rows,draws,cfg['masking']['columns'],cfg['masking']['levels']))
        atomic(output/'availability.json',availability(cfg['ablation_models']))
        fit_ablations(output,plan,cfg,original,data)
        stress_predictions(output,plan,cfg,original,data,draws)
        reports(output,plan,cfg,original,data,baseline_predictions)
        checks=validate(output,completed=False);atomic(output/'validation.json',checks)
        files=inventory(output);files.pop('status.json',None)
        atomic(output/'status.json',{'status':'completed','ended':now(),'elapsed_seconds':time.perf_counter()-start,
            'plan_sha256':digest(plan),'output_files':files})
    except BaseException as exc:
        atomic(output/'status.json',{'status':'failed','ended':now(),'plan_sha256':digest(plan),'failure':f'{type(exc).__name__}: {exc}'})
        raise
    return checks


def render_report(output,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    clean=read(output/'clean-comparison.json');stress=read(output/'stress-metrics.json')
    lines=['# Bounded exploratory confound ablation','',cfg['interpretation'],
        'Primary results retain all 72 rows per model/contrast. Accuracy equals balanced accuracy for this balanced inventory. Macro-F1 below is pooled; detailed per-participant and participant-macro metrics are in JSON.',
        'No calibration, rejection tuning, hyperparameter search or participant acquisition. Empty ablation allowlists are unavailable, never replaced by dummy.','']
    def fmt(value):return 'undefined' if value is None else f'{value:.4f}'
    labels={'dummy':'Dummy','facial':'Face','camera_bpm':'BPM','facial_camera_bpm':'Face+BPM',
        'quality_values':'Quality','missingness':'Missingness','facial_no_mouth':'Eyes+motion',
        'facial_no_mouth_plus_bpm':'Eyes+motion+BPM','facial_no_motion':'Mouth+eyes',
        'facial_no_motion_plus_bpm':'Mouth+eyes+BPM','facial_no_mouth_no_motion':'Eyes',
        'facial_no_mouth_no_motion_plus_bpm':'Eyes+BPM'}
    for contrast,models in clean['contrasts'].items():
        lines+=['## '+contrast,'','| Model | N | Accuracy | Macro-F1 | Brier | Confusion [[TN,FP],[FN,TP]] | Supported (rest/active) |',
                '|---|---:|---:|---:|---:|---|---|']
        for name,entry in models.items():
            m=entry['all']['pooled'];s=entry['supported']['pooled']
            lines.append(f"| {name} | {m['n']} | {fmt(m['accuracy'])} | {fmt(m['macro_f1'])} | {fmt(m['brier'])} | {m['confusion_matrix']} | {s['n']} ({s['class_counts']['rest']}/{s['class_counts']['active']}) |")
        lines+=['','### Added feature-missingness: all scheduled rows','',
            '| Model | Level | N | Accuracy | Macro-F1 | Brier | Confusion | Supported (rest/active) |',
            '|---|---:|---:|---:|---:|---:|---|---|']
        for name in models:
            for level in cfg['masking']['levels']:
                e=stress[str(level)]['contrasts'][contrast][name];m=e['all']['pooled'];s=e['supported']['pooled']
                lines.append(f"| {name} | {level:.0%} | {m['n']} | {fmt(m['accuracy'])} | {fmt(m['macro_f1'])} | {fmt(m['brier'])} | {m['confusion_matrix']} | {s['n']} ({s['class_counts']['rest']}/{s['class_counts']['active']}) |")
        lines+=['','### Clean per-participant accuracy','', '| Model | '+' | '.join(cfg['participants'])+' |','|---|'+'---:|'*6]
        for name,e in models.items():
            lines.append('| '+name+' | '+' | '.join(fmt(e['all']['per_participant'][p]['accuracy']) for p in cfg['participants'])+' |')
        names=list(models);x=np.arange(len(names))
        fig,axes=plt.subplots(1,2,figsize=(15,6),layout='constrained')
        for axis,metric in zip(axes,('accuracy','brier')):
            axis.bar(x,[models[n]['all']['pooled'][metric] for n in names]);axis.set_ylim(0,1)
            axis.set_xticks(x,[labels[n] for n in names],rotation=60,ha='right',fontsize=8);axis.set_title(contrast+' — clean '+metric)
        fig.savefig(output/(contrast+'-clean-comparison.png'),dpi=150);plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(15,6),layout='constrained')
        for axis,metric in zip(axes,('accuracy','brier')):
            for name in names:
                axis.plot(cfg['masking']['levels'],[stress[str(level)]['contrasts'][contrast][name]['all']['pooled'][metric] for level in cfg['masking']['levels']],marker='o',label=labels[name])
            axis.set_ylim(0,1);axis.set_xticks(cfg['masking']['levels']);axis.set_xlabel('Added-null probability per observed feature cell');axis.set_title(contrast+' — '+metric)
        axes[1].legend(fontsize=8,loc='center left',bbox_to_anchor=(1,0.5))
        fig.savefig(output/(contrast+'-added-missingness.png'),dpi=150);plt.close(fig)
    lines+=['','## Interpretation and limits','',
        'Ablated models are fitted on the same clean training participants with unchanged baseline settings; all stress predictions use their frozen models/preprocessors. Saved baseline models are loaded, never refitted. The 0% arm must exactly reproduce saved clean predictions.',
        'Masks use one PCG64 seed, iid scores per original row/feature, with nested thresholds. RNG inputs are shape/seed only. Shared row/feature cells get identical masks across models and contrasts; naturally null values remain null. Eligibility depends on existing data, so realized rates differ by class/person; masks are not forced balanced.',
        'Masking covers value, quality and missingness-control features. Derived indicators are not recomputed; this is an unstructured feature-drop test, not a physically consistent video/sensor simulation. It adds missingness, does not remove the dataset’s natural missingness confound, and one realization does not establish general robustness.',
        'Speech, facial/eye/head behaviour, pose, exposure, ROI geometry and recording conditions/order can identify task. Removing mouth and motion summaries does not remove all behaviour or conditions. Training-median patterns can still encode availability even without explicit flags. Arithmetic has pre-existing unsupported facial rows; primary metrics keep them.',
        'All six participants have informed pipeline development. These results are exploratory task classification, not psychological stress measurement or final independent evaluation. No model/feature set is selected or tuned from these held-out results. A separately planned untouched participant evaluation is next; calibration, rejection tuning and acquisition remain outside this study.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-run',type=Path);parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--execute',action='store_true');mode.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        if not args.baseline_run:parser.error('--baseline-run required')
        print('Prepared without fitting',prepare(args.baseline_run,args.output)['configuration_id'])
    elif args.execute:print(json.dumps(execute(args.output),indent=2))
    else:print(json.dumps(validate(args.output),indent=2))


if __name__=='__main__':main()
