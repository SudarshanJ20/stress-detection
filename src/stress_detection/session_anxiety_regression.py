"""Frozen LOPO regression of released author-computed post-session means."""

import argparse
import json
from pathlib import Path
import subprocess
import time
import warnings

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from . import baseline as base
from . import session_anxiety_audit as audit
from .baseline_preprocessing import FoldPreprocessor
from .features import finite, read_jsonl, write_jsonl
from .pilot_state import atomic, digest, inventory, now, read
from .validate_sample import require_ignored

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'configs/session-anxiety-regression-v1.json'
REGISTERED = 'e9639dc37673a2ff5122c98858ece38a14284b93fd36f3defb88a03e789b471f'


def load_config():
    cfg = read(CONFIG)
    expected = {'mean': [], **{k:v for k,v in audit.load_config()['models'].items() if k != 'dummy'}}
    if digest(cfg) != REGISTERED or cfg['models'] != expected:
        raise ValueError('Modified/unregistered regression design or predictor allowlist')
    return cfg


def load_sessions(folder, cfg):
    """Preserve the old no-fit audit and explicitly accept its computed-score payload."""
    require_ignored(folder)
    receipt = read(folder/'receipt.json')
    files = inventory(folder); files.pop('receipt.json', None)
    current = base.code_hashes()
    if (receipt['status'] != 'completed' or receipt['output_files'] != files
            or receipt['configuration_id'] != cfg['source_audit_configuration_id']
            or receipt['configuration'] != audit.load_config() or receipt['software'] != base.versions()
            or any(current.get(k) != v for k,v in receipt['code'].items())):
        raise ValueError('Incomplete/changed source session audit')
    tables, proof = audit.derive(Path(receipt['feature_run']), Path(receipt['selection_path']), audit.load_config())
    if proof != receipt['source_proof']:
        raise ValueError('Source questionnaire/features changed')
    for name, expected in tables.items():
        if read_jsonl(folder/name) != expected:
            raise ValueError('Session data/outcome alignment changed')
    index, x, outcomes = (tables[k] for k in ('index.jsonl','X.jsonl','outcomes.jsonl'))
    if ([r['participant'] for r in index] != cfg['participants']
            or any(r['role'] != cfg['role'] for r in index)):
        raise ValueError('Participant role/inventory leakage')
    ys = {}
    for target, spec in cfg['targets'].items():
        # Read documented dimension/occasion directly; never infer it from task or assignment.
        values = [r['dimensions'][spec['dimension']][spec['occasion']] for r in outcomes]
        if any(not finite(v) or not cfg['score_range'][0] <= v <= cfg['score_range'][1] for v in values):
            raise ValueError('Missing/nonfinite/out-of-range released target')
        ys[target] = np.asarray(values, dtype=float)
    return index, x, ys, {'source_files':inventory(folder), 'inputs':proof}


def folds(index):
    result = audit.fold_inventory(index)
    for f in result:
        p = f['held_out_participant']
        f['train'] = [i for i,r in enumerate(index) if r['participant'] != p]
        f['test'] = [i for i,r in enumerate(index) if r['participant'] == p]
    return result


def estimator_parameters(cfg):
    return {k:v for k,v in cfg['regression'].items() if k != 'class'}


def fit_fold(x, y, columns, cfg):
    if len(y) != len(x) or not np.isfinite(y).all():
        raise ValueError('Missing/unaligned training target')
    pre = FoldPreprocessor().fit(x) if columns else None
    model = {'preprocessor':pre, 'estimator':None, 'columns':columns, 'mean':float(np.mean(y)),
             'fallback':bool(columns and not pre.keep_.any()), 'warnings':[]}
    if columns and pre.keep_.any():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model['estimator'] = Ridge(**estimator_parameters(cfg)).fit(pre.transform(x), y)
        model['warnings'] = [str(w.message) for w in caught]
    return model


def predict(model, x):
    if model['estimator'] is None:
        return np.full(len(x), model['mean'])
    return model['estimator'].predict(model['preprocessor'].transform(x))


def support(row, columns, empty):
    n = sum(row[c] is not None for c in columns)
    return {'requested':len(columns), 'observed':n, 'missing':len(columns)-n,
            'fully_observed':n == len(columns) and not empty, 'training_empty_columns':empty}


def metrics(rows):
    y = np.asarray([r['truth'] for r in rows]); pred = np.asarray([r['prediction'] for r in rows])
    n = len(rows)
    sst = float(np.sum((y-y.mean())**2)) if n else 0.
    return {'n':n, 'mae':float(np.mean(np.abs(pred-y))) if n else None,
            'rmse':float(np.sqrt(np.mean((pred-y)**2))) if n else None,
            'r2':float(1-np.sum((pred-y)**2)/sst) if n >= 2 and sst > 0 else None,
            'r2_undefined_reason':None if n >= 2 and sst > 0 else 'fewer than two observations or constant outcome'}


def validate_inventory(predictions, index, ys, cfg):
    expected = {(t,m,r['session_key']) for t in cfg['targets'] for m in cfg['models'] for r in index}
    seen = set(); lookup = {r['session_key']:i for i,r in enumerate(index)}
    for r in predictions:
        key = (r['target'],r['model'],r['session_key'])
        if key not in expected or key in seen:
            raise ValueError('Duplicate/missing/unexpected prediction key')
        seen.add(key); i = lookup[r['session_key']]; person = index[i]['participant']
        if (r['participant'] != person or set(r['training_participants']) != set(cfg['participants'])-{person}
                or len(r['training_participants']) != 5 or r['configuration_id'] != digest(cfg)
                or r['truth'] != ys[r['target']][i] or not finite(r['prediction'])):
            raise ValueError('Participant leakage, target alignment or invalid prediction')
    if seen != expected or len(predictions) != cfg['expected_predictions']:
        raise ValueError('Incomplete prediction inventory')


def report(predictions, cfg):
    result = {}
    for target in cfg['targets']:
        result[target] = {}
        baseline = {r['participant']:r for r in predictions if r['target'] == target and r['model'] == 'mean'}
        for name in cfg['models']:
            selected = [r for r in predictions if r['target'] == target and r['model'] == name]
            result[target][name] = {'all':metrics(selected),
                'per_participant':{r['participant']:metrics([r]) for r in selected},
                'supported':metrics([r for r in selected if r['support']['fully_observed']]),
                'paired_absolute_error_minus_mean':{r['participant']:float(abs(r['prediction']-r['truth'])-
                    abs(baseline[r['participant']]['prediction']-r['truth'])) for r in selected}}
    return result


def prepare(source, output):
    cfg = load_config(); index, _, _, proof = load_sessions(source, cfg)
    require_ignored(output); output.mkdir(parents=True, exist_ok=False)
    plan = {'configuration':cfg, 'configuration_id':digest(cfg), 'source_audit':str(source.resolve()),
            'source_proof':proof, 'folds':folds(index), 'code':base.code_hashes(), 'software':base.versions(),
            'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True), 'prepared_at':now()}
    atomic(output/'plan.json',plan); atomic(output/'configuration.json',cfg)
    atomic(output/'feature-lists.json',cfg['models'])
    (output/'pip-freeze.txt').write_text(subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
    atomic(output/'status.json',{'status':'prepared','plan_sha256':digest(plan)})
    return plan


def load_plan(output):
    require_ignored(output); plan = read(output/'plan.json'); cfg = load_config()
    if (plan['configuration'] != cfg or plan['configuration_id'] != digest(cfg)
            or plan['code'] != base.code_hashes() or plan['software'] != base.versions()
            or read(output/'configuration.json') != cfg or read(output/'feature-lists.json') != cfg['models']):
        raise ValueError('Frozen regression plan/code/software changed')
    index, x, ys, proof = load_sessions(Path(plan['source_audit']),cfg)
    if proof != plan['source_proof'] or folds(index) != plan['folds']:
        raise ValueError('Inputs/fold identities changed')
    return plan, cfg, index, x, ys


def execute(output):
    plan,cfg,index,x,ys = load_plan(output); status = read(output/'status.json')
    if status != {'status':'prepared','plan_sha256':digest(plan)}:
        raise ValueError('Refuse overwrite/incomplete/changed plan; use fresh output')
    start = time.perf_counter()
    atomic(output/'status.json',{'status':'running','plan_sha256':digest(plan)})
    try:
        predictions = []
        with threadpool_limits(limits=cfg['thread_limit']):
            for target,y in ys.items():
                for name,columns in cfg['models'].items():
                    values = base.matrix(x,columns)
                    for f in plan['folds']:
                        train, test = f['train'],f['test']; person = f['held_out_participant']
                        model = fit_fold(values[train],y[train],columns,cfg)
                        loc = output/'models'/target/name/person; loc.mkdir(parents=True)
                        joblib.dump(model,loc/'model.joblib')
                        snapshot = model['preprocessor'].snapshot(columns) if columns else None
                        state = {'preprocessing':snapshot, 'training_participants':f['training_participants'],
                            'evaluation_participants':f['evaluation_participants'], 'training_sessions':f['training_sessions'],
                            'evaluation_sessions':f['evaluation_sessions'], 'fallback_to_mean':model['fallback'],
                            'training_mean':model['mean'], 'warnings':model['warnings'],
                            'estimator_parameters':model['estimator'].get_params() if model['estimator'] is not None else None}
                        atomic(loc/'fit.json',state)
                        empty = snapshot['training_all_missing_columns'] if snapshot else []
                        for i,p in zip(test,predict(model,values[test])):
                            predictions.append({'target':target,'model':name,'session_key':index[i]['session_key'],
                                'participant':person,'training_participants':f['training_participants'],
                                'configuration_id':digest(cfg),'truth':float(y[i]),'prediction':float(p),
                                'support':support(x[i],columns,empty)})
        write_jsonl(output/'predictions.jsonl',predictions)
        saved = read_jsonl(output/'predictions.jsonl'); validate_inventory(saved,index,ys,cfg)
        atomic(output/'metrics.json',report(saved,cfg)); render(output,cfg)
        checks = validate(output,completed=False); atomic(output/'validation.json',checks)
        files = inventory(output); files.pop('status.json')
        atomic(output/'status.json',{'status':'completed','plan_sha256':digest(plan),'output_files':files,
                                     'elapsed_seconds':time.perf_counter()-start,'ended':now()})
        return checks
    except BaseException as exc:
        atomic(output/'status.json',{'status':'failed','plan_sha256':digest(plan),'failure':f'{type(exc).__name__}: {exc}'})
        raise


def validate(output, completed=True):
    plan,cfg,index,x,ys = load_plan(output); status = read(output/'status.json')
    if status['plan_sha256'] != digest(plan) or (completed and status['status'] != 'completed'):
        raise ValueError('Incomplete/changed plan')
    if completed:
        files = inventory(output); files.pop('status.json')
        if files != status['output_files']: raise ValueError('Regression output hashes changed')
    predictions = read_jsonl(output/'predictions.jsonl'); validate_inventory(predictions,index,ys,cfg)
    for target,y in ys.items():
        for name,columns in cfg['models'].items():
            values = base.matrix(x,columns)
            for f in plan['folds']:
                person = f['held_out_participant']; loc = output/'models'/target/name/person
                model = joblib.load(loc/'model.joblib'); state = read(loc/'fit.json')
                train,test = f['train'],f['test']
                expected_pre = FoldPreprocessor().fit(values[train]) if columns else None
                snapshot = expected_pre.snapshot(columns) if expected_pre else None
                actual_snapshot = model['preprocessor'].snapshot(columns) if model['preprocessor'] else None
                mean = float(np.mean(y[train])); fallback = bool(columns and not expected_pre.keep_.any())
                if (snapshot != actual_snapshot or snapshot != state['preprocessing']
                        or model['columns'] != columns or model['mean'] != mean or state['training_mean'] != mean
                        or model['fallback'] != fallback or state['fallback_to_mean'] != fallback
                        or state['training_participants'] != f['training_participants']
                        or state['evaluation_participants'] != f['evaluation_participants']
                        or state['training_sessions'] != f['training_sessions'] or state['evaluation_sessions'] != f['evaluation_sessions']):
                    raise ValueError('Fold-local preprocessing/identity mismatch')
                should_fit = bool(columns and not fallback)
                params = Ridge(**estimator_parameters(cfg)).get_params() if should_fit else None
                if ((model['estimator'] is not None) != should_fit or state['estimator_parameters'] != params
                        or (should_fit and model['estimator'].get_params() != params)):
                    raise ValueError('Changed regression parameters/fallback')
                if should_fit:
                    # Verify the fitted L2 normal equations using training rows only;
                    # no classifier/regressor is refitted during validation.
                    z = expected_pre.transform(values[train]); zmean = z.mean(axis=0)
                    centered = z-zmean; coef = model['estimator'].coef_
                    lhs = (centered.T@centered + cfg['regression']['alpha']*np.eye(z.shape[1]))@coef
                    rhs = centered.T@(y[train]-mean)
                    if (not np.allclose(lhs,rhs,atol=1e-9,rtol=1e-9)
                            or not np.isclose(model['estimator'].intercept_,mean-zmean@coef,atol=1e-10,rtol=1e-10)):
                        raise ValueError('Ridge coefficients do not solve the training-only objective')
                selected = [r for r in predictions if r['target']==target and r['model']==name and r['participant']==person]
                empty = snapshot['training_all_missing_columns'] if snapshot else []
                if ([r['session_key'] for r in selected] != [index[i]['session_key'] for i in test]
                        or not np.array_equal(predict(model,values[test]),[r['prediction'] for r in selected])
                        or any(r['support'] != support(x[i],columns,empty) for r,i in zip(selected,test))):
                    raise ValueError('Saved prediction/support does not reproduce')
    if read(output/'metrics.json') != report(predictions,cfg):
        raise ValueError('Metrics differ from saved predictions')
    return {'status':'passed','predictions':len(predictions),'fold_models':72,'sessions':6,
            'per_model_target':6,'participant_separation':True,'fold_local_preprocessing':True,
            'targets':'direct author-computed post-session means','source_audit_unchanged':True,
            'classification':'unavailable; no categories or accuracy'}


def render(output,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    predictions = read_jsonl(output/'predictions.jsonl'); results = read(output/'metrics.json')
    lines = ['# Exploratory released-score session regression','',
        'Raw post-session means on the released1–4 scale; cognitive primary, somatic secondary. Six development-informed people, one row each. No categories or accuracy. No clinical/live or independent validation claim.','']
    for target,models in results.items():
        lines += ['## '+target,'','| Model | N | MAE | RMSE | R² | Fully observed aggregate inputs N |','|---|---:|---:|---:|---:|---:|']
        for name,e in models.items():
            m=e['all']; r='undefined' if m['r2'] is None else f"{m['r2']:.4f}"
            lines.append(f"| {name} | {m['n']} | {m['mae']:.4f} | {m['rmse']:.4f} | {r} | {e['supported']['n']} |")
        lines += ['', '| Participant | Released post score | '+' | '.join(cfg['models'])+' |', '|---|'+'---:|'*(1+len(cfg['models']))]
        for p in cfg['participants']:
            rows={r['model']:r for r in predictions if r['participant']==p and r['target']==target}
            lines.append('| '+p+f" | {rows['mean']['truth']:.4f} | "+' | '.join(f"{rows[m]['prediction']:.4f}" for m in cfg['models'])+' |')
        fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
        names=list(models)
        for ax,metric in zip(axes,('mae','rmse')):
            ax.bar(names,[models[n]['all'][metric] for n in names]);ax.set_ylabel('Released score units');ax.set_title(target+' '+metric)
            ax.tick_params(axis='x',rotation=45)
        fig.savefig(output/(target+'-errors.png'),dpi=140);plt.close(fig)
    lines += ['', 'All72 held-out predictions retained. Per-person R² is undefined (one session). Pooled R² uses all six predictions and can be negative; it is not an accuracy percentage.',
        'Value models omit explicit indicators, but medians/imputation and natural support can encode condition. Pooled observed windows are not complete recording support; raw per-task counts remain in the source audit.',
        'Six participants already informed pipeline development. Dimensions exceed five training rows in several arms; fixed Ridge is a feasibility calculation, not evidence of adequacy. No model/target/ROI selected from outcomes.',
        'Pre scores, questionnaire reconstruction, wrist values, task identity and test/ctrl are not predictors. No score normalization, clipping, new participant, calibration or rejection tuning. Independent controlled use-case validation remains necessary.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-audit',type=Path);parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare','execute','validate'):mode.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.prepare:
        if not args.source_audit:parser.error('--source-audit required')
        print('Prepared without fitting',prepare(args.source_audit,args.output)['configuration_id'])
    elif args.execute:print(execute(args.output))
    else:print(validate(args.output))


if __name__=='__main__':main()
