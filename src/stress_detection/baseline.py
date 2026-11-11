"""Frozen exploratory task-classification LOPO experiment; private artifacts only."""

import argparse
from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import time
import warnings

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_info, threadpool_limits

from .baseline_preprocessing import FoldPreprocessor
from .features import (BEHAVIOUR, PULSE, IDENTIFIERS, finite, read_jsonl, schema,
                       validate_rows, validate_selection, write_jsonl)
from .manifest import fingerprint
from .pilot_state import atomic, digest, inventory, now, read
from .policy import load_policy
from .validate_sample import require_ignored

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'configs/exploratory-lopo-v1.json'
REGISTERED = {'exploratory-lopo-v1': '9f83f5a31141a6ceecbc9a0179d3777bb35518ae0f7d2d367fb9e9ff5f2934b6'}
QUALITY = ['q_brightness_mean', 'q_brightness_std', 'q_dark_fraction_mean',
    'q_saturated_fraction_mean', 'q_laplacian_variance_mean', 'q_face_area_mean',
    'q_brightness_change_abs_median', *[f'q_region_{r}_area_mean' for r in
                                     ('forehead','cheek_image_left','cheek_image_right')]]
METRICS = ('accuracy','balanced_accuracy','macro_f1','active_recall','rest_false_positive_rate','brier')
PACKAGES = ('numpy','scikit-learn','scipy','joblib','narwhals','threadpoolctl','cloudpickle','matplotlib')


def versions():
    return {'python':platform.python_version(), **{p:version(p) for p in PACKAGES}}


def code_hashes():
    return {p.name:fingerprint(p,p.name)['sha256'] for p in sorted(Path(__file__).parent.glob('*.py'))}


def validate_allowlists(cfg):
    expected = {'dummy':[], 'facial':BEHAVIOUR, 'camera_bpm':PULSE,
        'facial_camera_bpm':BEHAVIOUR+PULSE, 'quality_values':QUALITY,
        'missingness':schema()['model_feature_lists']['missingness_only']}
    if cfg['models'] != expected:
        raise ValueError('Changed/forbidden predictor allowlist; freeze a new experiment')
    for name in cfg['value_models']:
        if any(c.startswith(('id_','label_','ref_')) or c.endswith(('_missing','_valid_fraction')) for c in cfg['models'][name]):
            raise ValueError('Metadata or explicit missingness predictor in value model')


def load_config(path=CONFIG):
    cfg = read(path)
    validate_allowlists(cfg)
    if REGISTERED.get(cfg['version']) != digest(cfg) or cfg['feature_schema_sha256'] != digest(schema()):
        raise ValueError('Unknown/modified experiment or incompatible feature schema')
    return cfg


def load_features(folder, cfg):
    """Verify saved artifacts without invalidating them for an added experiment module.

    Every module recorded by the feature receipt must remain byte-identical.
    New unrelated module names are allowed. No reference payload is parsed.
    """
    require_ignored(folder)
    receipt=read(folder/'receipt.json')
    if (receipt['status']!='completed' or receipt['policy']!=load_policy()[1]
            or receipt['feature_schema_sha256']!=cfg['feature_schema_sha256']
            or receipt['software']!={'numpy':np.__version__,'python':platform.python_version()}):
        raise ValueError('Incomplete/incompatible saved feature run')
    for name,checksum in receipt['code'].items():
        if fingerprint(Path(__file__).parent/name,name)['sha256']!=checksum:
            raise ValueError('Feature computation changed: '+name)
    files=inventory(folder);files.pop('receipt.json',None)
    if files!=receipt['output_files'] or read(folder/'schema.json')!=schema():
        raise ValueError('Feature artifact/schema hash mismatch')
    selection=validate_selection(receipt['selection'])
    roles={e['id']:e['role'] for e in selection['participants']}
    if (selection['cohort']!='pilot' or set(roles)!=set(cfg['participants'])
            or set(roles.values())!={cfg['participant_role']} or 's25' in roles):
        raise ValueError('Pilot/development participant-role leakage')
    rows=read_jsonl(folder/'windows.jsonl');report=read(folder/'validation.json')
    validate_rows(rows,108,roles,report['schedules'])
    by_key={r['id_window_key']:r for r in rows}
    data={}
    for contrast,positive in cfg['contrasts'].items():
        x=read_jsonl(folder/contrast/'X.jsonl');index=read_jsonl(folder/contrast/'index.jsonl')
        if len(x)!=cfg['expected_rows_per_contrast'] or len(index)!=len(x):
            raise ValueError('Wrong contrast inventory')
        seen=set()
        for values,meta in zip(x,index):
            key=meta['id_window_key']
            if key in seen or key not in by_key:
                raise ValueError('Duplicate/unmatched feature index')
            seen.add(key);source=by_key[key]
            if (source['label_condition'] not in ('rest',positive)
                    or meta!={**{c:source[c] for c in IDENTIFIERS},'label_condition':source['label_condition'],
                               'target':int(source['label_condition']==positive)}
                    or values!={c:source[c] for c in schema()['model_columns']}
                    or any(v is not None and not finite(v) for v in values.values())):
                raise ValueError('Contrast labels, predictors or row alignment invalid')
        expected={r['id_window_key'] for r in rows if r['label_condition'] in ('rest',positive)}
        if seen!=expected:
            raise ValueError('Missing scheduled contrast rows')
        data[contrast]={'x':x,'index':index}
        folds(index,cfg)  # Validate grouping and class support before any fit.
    return data, {'feature_receipt':fingerprint(folder/'receipt.json','receipt.json'),
                  'feature_files':files, 'role':'pilot_development','rows':108}


def folds(index,cfg):
    groups=np.asarray([r['id_participant'] for r in index])
    keys=[r['id_window_key'] for r in index]
    if len(set(keys))!=len(keys) or set(groups)!=set(cfg['participants']):
        raise ValueError('Duplicate keys or unexpected participant groups')
    result=[]
    for participant in cfg['participants']:
        train=np.flatnonzero(groups!=participant);test=np.flatnonzero(groups==participant)
        training=sorted(set(groups[train]));evaluation=sorted(set(groups[test]))
        if (len(training)!=5 or evaluation!=[participant] or set(training)&set(evaluation)
                or len(train)!=60 or len(test)!=12
                or Counter(index[i]['target'] for i in test)!={0:6,1:6}
                or Counter(index[i]['target'] for i in train)!={0:30,1:30}):
            raise ValueError('Participant leakage or incomplete/class-imbalanced scheduled fold')
        result.append({'participant':participant,'fold_id':'held-out-'+participant,
            'training_participants':training,'evaluation_participants':evaluation,
            'train':train,'test':test})
    return result



def matrix(x,columns):
    return np.asarray([[np.nan if row[c] is None else row[c] for c in columns] for row in x],dtype=float).reshape(len(x),len(columns))


def fit_fold(x,y,columns,cfg):
    pre=FoldPreprocessor().fit(x) if columns else None
    fallback=bool(columns and not pre.keep_.any())
    if not columns or fallback:
        estimator=DummyClassifier(strategy=cfg['dummy_strategy'],random_state=cfg['logistic_regression']['random_state'])
        transformed=np.zeros((len(y),1))
    else:
        estimator=LogisticRegression(**cfg['logistic_regression'])
        transformed=pre.transform(x)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        estimator.fit(transformed,y)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):
        raise ValueError('Frozen logistic model failed to converge; preserve run for review')
    return {'preprocessor':pre,'estimator':estimator,'columns':columns,'fallback':fallback,
            'warnings':[str(w.message) for w in caught]}


def probabilities(model,x):
    transformed=model['preprocessor'].transform(x) if model['preprocessor'] else np.zeros((len(x),1))
    return model['estimator'].predict_proba(transformed)[:,list(model['estimator'].classes_).index(1)]


def feature_support(row,columns,empty):
    observed=sum(row[c] is not None for c in columns)
    count=len(columns)
    return {'requested_count':count,'observed_count':observed,'missing_count':count-observed,
        'observed_fraction':observed/count if count else 1.,
        'raw_fully_observed':observed==count,'supported':observed==count and not empty,
        'training_all_missing_columns':empty,
        'facial_observed_fraction':sum(row[c] is not None for c in BEHAVIOUR)/len(BEHAVIOUR),
        'camera_bpm_observed_fraction':sum(row[c] is not None for c in PULSE)/len(PULSE)}


def metrics(rows):
    counts=np.zeros((2,2),dtype=int)
    for r in rows:counts[r['truth'],r['prediction']]+=1
    tn,fp,fn,tp=map(int,counts.ravel());n=len(rows)
    recall=tp/(tp+fn) if tp+fn else None
    fpr=fp/(tn+fp) if tn+fp else None
    both=recall is not None and fpr is not None
    result={'n':n,'class_counts':{'rest':tn+fp,'active':tp+fn},'confusion_matrix':counts.tolist(),
        'confusion_order':'rows true, columns predicted; [rest, active]',
        'accuracy':(tn+tp)/n if n else None,
        'balanced_accuracy':(recall+1-fpr)/2 if both else None,
        'macro_f1':((2*tn/(2*tn+fn+fp))+(2*tp/(2*tp+fn+fp)))/2 if both else None,
        'active_recall':recall,'rest_false_positive_rate':fpr,
        'brier':sum((r['probability_active']-r['truth'])**2 for r in rows)/n if n else None}
    result['undefined']={m:('no rows' if not n else 'both true classes required' if m in ('balanced_accuracy','macro_f1')
        else 'no active true rows' if m=='active_recall' else 'no rest true rows') for m in METRICS if result[m] is None}
    return result


def prediction_inventory(predictions,data,cfg,config_id):
    expected={(contrast,model,m['id_window_key']) for contrast,d in data.items() for model in cfg['models'] for m in d['index']}
    seen=set()
    metadata={c:{m['id_window_key']:m for m in d['index']} for c,d in data.items()}
    raw={c:{m['id_window_key']:x for m,x in zip(d['index'],d['x'])} for c,d in data.items()}
    for p in predictions:
        key=(p['contrast'],p['model'],p['window_key'])
        if key not in expected or key in seen:
            raise ValueError('Duplicate/unknown held-out prediction')
        seen.add(key);meta=metadata[p['contrast']][p['window_key']]
        if (p['configuration_id']!=config_id or p['participant']!=meta['id_participant']
                or p['participant'] in p['training_participants'] or len(set(p['training_participants']))!=5
                or set(p['training_participants'])!=set(cfg['participants'])-{p['participant']}
                or p['fold_id']!='held-out-'+p['participant'] or p['truth']!=meta['target']
                or p['condition']!=meta['label_condition'] or not finite(p['probability_active'])
                or not 0<=p['probability_active']<=1
                or p['prediction']!=int(p['probability_active']>cfg['decision_threshold'])):
            raise ValueError('Participant leakage, truth, threshold or probability mismatch')
        columns=cfg['models'][p['model']]
        empty=p['support']['training_all_missing_columns']
        if not set(empty)<=set(columns) or p['support']!=feature_support(raw[p['contrast']][p['window_key']],columns,empty):
            raise ValueError('Prediction support mismatch')
    if seen!=expected:
        raise ValueError('Incomplete prediction inventory: require 72 per model per contrast')


def macro(participant_results):
    result={}
    for m in METRICS:
        values=[r[m] for r in participant_results.values() if r[m] is not None]
        result[m]={'mean':sum(values)/len(values) if len(values)==len(participant_results) else None,
            'available_mean':sum(values)/len(values) if values else None,
            'participants_defined':len(values),'participants_total':len(participant_results)}
    return result


def report_from_predictions(predictions,cfg):
    report={'interpretation':cfg['interpretation'],'primary':'all scheduled rows; no rejection',
        'secondary':cfg['secondary_evaluation'],'uncertainty':cfg['uncertainty_intervals'],'contrasts':{}}
    for contrast in cfg['contrasts']:
        models={}
        for name in cfg['models']:
            rows=[r for r in predictions if r['contrast']==contrast and r['model']==name]
            entry={}
            for analysis,selected in (('all',rows),('supported',[r for r in rows if r['support']['supported']])):
                by_person={p:metrics([r for r in selected if r['participant']==p]) for p in cfg['participants']}
                entry[analysis]={'pooled':metrics(selected),'per_participant':by_person,'participant_macro':macro(by_person)}
            entry['coverage_by_class_and_participant']=[]
            for participant in cfg['participants']:
                for label in (0,1):
                    selected=[r for r in rows if r['participant']==participant and r['truth']==label]
                    entry['coverage_by_class_and_participant'].append({'participant':participant,'truth':label,
                        'scheduled':len(selected),'predicted':len(selected),
                        'supported':sum(r['support']['supported'] for r in selected),
                        'rows_with_missing_values':sum(r['support']['missing_count']>0 for r in selected),
                        'mean_observed_feature_fraction':sum(r['support']['observed_fraction'] for r in selected)/len(selected) if selected else None,
                        'mean_facial_observed_fraction':sum(r['support']['facial_observed_fraction'] for r in selected)/len(selected) if selected else None,
                        'mean_camera_bpm_observed_fraction':sum(r['support']['camera_bpm_observed_fraction'] for r in selected)/len(selected) if selected else None})
            models[name]=entry
        report['contrasts'][contrast]=models
    return report


def load_plan(folder):
    plan=read(folder/'plan.json');cfg=load_config()
    if (plan['configuration']!=cfg or plan['configuration_id']!=digest(cfg)
            or plan['software']!=versions() or plan['code']!=code_hashes()):
        raise ValueError('Prepared configuration/code/software changed; prepare a new run')
    return plan,cfg


def prepare(feature_run,output):
    cfg=load_config();data,inputs=load_features(feature_run,cfg)
    require_ignored(output);output.mkdir(parents=True,exist_ok=False)
    plan={'prepared_at':now(),'configuration':cfg,'configuration_id':digest(cfg),'feature_run':str(feature_run.resolve()),
        'input_provenance':inputs,'software':versions(),'code':code_hashes(),
        'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'git_status_at_prepare':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
        'platform':platform.platform(),'architecture':platform.machine(),
        'folds':{c:[{**{k:v for k,v in f.items() if k not in ('train','test')},
            'training_row_keys':[d['index'][i]['id_window_key'] for i in f['train']],
            'evaluation_row_keys':[d['index'][i]['id_window_key'] for i in f['test']]} for f in folds(d['index'],cfg)] for c,d in data.items()}}
    atomic(output/'plan.json',plan);atomic(output/'configuration.json',cfg)
    atomic(output/'feature-lists.json',cfg['models'])
    (output/'pip-freeze.txt').write_text(subprocess.check_output([str(ROOT/'.venv/bin/python'),'-m','pip','freeze'],text=True))
    atomic(output/'status.json',{'status':'prepared','configuration_id':digest(cfg),'plan_sha256':digest(plan),'prepared_at':plan['prepared_at']})
    return plan


def execute(output):
    plan,cfg=load_plan(output)
    status=read(output/'status.json')
    if status['status']!='prepared':
        raise ValueError('Refuse overwrite/retraining; prepare a fresh output directory')
    if status.get('plan_sha256')!=digest(plan) or read(output/'configuration.json')!=cfg or read(output/'feature-lists.json')!=cfg['models']:
        raise ValueError('Prepared plan/configuration snapshot changed')
    data,inputs=load_features(Path(plan['feature_run']),cfg)
    if inputs!=plan['input_provenance']:
        raise ValueError('Feature inputs changed after freeze')
    atomic(output/'status.json',{'status':'running','started':now(),'plan_sha256':digest(plan)});start=time.perf_counter()
    try:
        with threadpool_limits(limits=cfg['thread_limit']):
            atomic(output/'threadpools.json',threadpool_info())
            with (output/'predictions.jsonl').open('x') as target:
                for contrast,d in data.items():
                    y=np.asarray([m['target'] for m in d['index']])
                    for name,columns in cfg['models'].items():
                        x=matrix(d['x'],columns)
                        for fold in folds(d['index'],cfg):
                            train,test=fold['train'],fold['test']
                            print(contrast,name,fold['participant'],flush=True)
                            model=fit_fold(x[train],y[train],columns,cfg)
                            probs=probabilities(model,x[test])
                            location=output/'models'/contrast/name/fold['participant'];location.mkdir(parents=True)
                            joblib.dump(model,location/'model.joblib')
                            state=model['preprocessor'].snapshot(columns) if model['preprocessor'] else {'requested_columns':[],'retained_columns':[],'training_all_missing_columns':[],'median':[],'scaler_mean':[],'scaler_scale':[],'scaler_variance':[]}
                            state.update(fallback_to_prior=model['fallback'],warnings=model['warnings'],
                                estimator_parameters=model['estimator'].get_params(),
                                training_participants=fold['training_participants'],evaluation_participants=fold['evaluation_participants'],
                                training_row_keys=[d['index'][i]['id_window_key'] for i in train],
                                evaluation_row_keys=[d['index'][i]['id_window_key'] for i in test],
                                configuration_id=plan['configuration_id'])
                            atomic(location/'fit.json',state)
                            for i,probability in zip(test,probs):
                                meta=d['index'][i]
                                row={'contrast':contrast,'model':name,'window_key':meta['id_window_key'],
                                    'participant':fold['participant'],'fold_id':fold['fold_id'],
                                    'training_participants':fold['training_participants'],
                                    'configuration_id':plan['configuration_id'],'truth':int(y[i]),'condition':meta['label_condition'],
                                    'probability_active':float(probability),'prediction':int(probability>cfg['decision_threshold']),
                                    'support':feature_support(d['x'][i],columns,state['training_all_missing_columns'])}
                                target.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
        saved=read_jsonl(output/'predictions.jsonl');prediction_inventory(saved,data,cfg,plan['configuration_id'])
        atomic(output/'metrics.json',report_from_predictions(saved,cfg))
        render_report(output,cfg)
        # Inputs are immutable; report generation never changes feature tables.
        if inventory(Path(plan['feature_run'])) != {**plan['input_provenance']['feature_files'],
                                                   'receipt.json':plan['input_provenance']['feature_receipt']}:
            raise ValueError('Feature inputs changed during experiment')
        validation=validate_models(output,plan,cfg,data,saved)
        atomic(output/'validation.json',validation)
        files=inventory(output);files.pop('status.json',None)
        atomic(output/'status.json',{'status':'completed','ended':now(),'elapsed_seconds':time.perf_counter()-start,
                                    'configuration_id':plan['configuration_id'],'plan_sha256':digest(plan),'output_files':files})
    except BaseException as exc:
        atomic(output/'status.json',{'status':'failed','plan_sha256':digest(plan),'failure':f'{type(exc).__name__}: {exc}','ended':now()})
        raise
    return read(output/'metrics.json')


def validate_models(output,plan,cfg,data,predictions):
    prediction_inventory(predictions,data,cfg,plan['configuration_id'])
    count=0
    with threadpool_limits(limits=cfg['thread_limit']):
        for contrast,d in data.items():
            y=np.asarray([m['target'] for m in d['index']])
            for name,columns in cfg['models'].items():
                x=matrix(d['x'],columns)
                for fold in folds(d['index'],cfg):
                    location=output/'models'/contrast/name/fold['participant'];state=read(location/'fit.json')
                    model=joblib.load(location/'model.joblib')  # Only our own ignored, hashed artifacts.
                    expected=FoldPreprocessor().fit(x[fold['train']]).snapshot(columns) if columns else None
                    if expected and any(state[k]!=v for k,v in expected.items()):
                        raise ValueError('Fold preprocessing statistics differ from training-only recomputation')
                    if (state['training_participants']!=fold['training_participants'] or state['evaluation_participants']!=[fold['participant']]
                            or state['training_row_keys']!=[d['index'][i]['id_window_key'] for i in fold['train']]
                            or state['evaluation_row_keys']!=[d['index'][i]['id_window_key'] for i in fold['test']]):
                        raise ValueError('Fold fit provenance mismatch')
                    if columns and model['preprocessor'].snapshot(columns)!=expected:
                        raise ValueError('Serialized preprocessor differs from saved training statistics')
                    expected_fallback=bool(columns and not np.isfinite(x[fold['train']]).any(axis=0).any())
                    if model['columns']!=columns or model['fallback']!=expected_fallback or state['fallback_to_prior']!=expected_fallback:
                        raise ValueError('Fold feature/fallback mismatch')
                    estimator=model['estimator']
                    params=estimator.get_params()
                    if params!=state['estimator_parameters']:
                        raise ValueError('Saved estimator parameter mismatch')
                    if not columns or expected_fallback:
                        if not isinstance(estimator,DummyClassifier) or params['strategy']!=cfg['dummy_strategy']:
                            raise ValueError('Dummy configuration mismatch')
                    elif not isinstance(estimator,LogisticRegression) or any(params[k]!=v for k,v in cfg['logistic_regression'].items()):
                        raise ValueError('Frozen logistic configuration mismatch')
                    expected_probs=probabilities(model,x[fold['test']])
                    selected=[p for p in predictions if p['contrast']==contrast and p['model']==name and p['participant']==fold['participant']]
                    if ([p['window_key'] for p in selected]!=[d['index'][i]['id_window_key'] for i in fold['test']]
                            or not np.array_equal(expected_probs,np.asarray([p['probability_active'] for p in selected]))):
                        raise ValueError('Saved predictions do not reproduce from fold models')
                    empty=state['training_all_missing_columns']
                    for p,i in zip(selected,fold['test']):
                        if p['support']!=feature_support(d['x'][i],columns,empty):
                            raise ValueError('Held-out support differs from training-only mask')
                    count+=1
    report=report_from_predictions(predictions,cfg)
    if read(output/'metrics.json')!=report:
        raise ValueError('Metrics must reproduce from saved held-out predictions')
    return {'status':'passed','predictions':len(predictions),'predictions_per_model_per_contrast':72,
        'fold_models':count,'participant_leakage':False,'fold_preprocessing_recomputed_from_training_only':True,
        'saved_models_reproduce_probabilities_exactly':True,'all_scheduled_rows_retained':True,
        'metrics_reproduced_from_saved_predictions':True,'reference_predictors':False}


def render_report(output,cfg):
    """All report values/plots come from metrics derived from the saved JSONL."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    report=read(output/'metrics.json')
    lines=['# Exploratory participant-held-out task classification','',cfg['interpretation'],
        'Configuration: '+digest(cfg)+'. No hyperparameter search, calibration or rejection tuning.',
        'Primary: all 72 scheduled predictions per model/contrast. Secondary: model-specific supported rows; subsets differ across models.',
        'Probabilities are uncalibrated. No uncertainty intervals are claimed from six development-informed people.','']
    def fmt(value):return 'undefined' if value is None else f'{value:.4f}'
    for contrast,models in report['contrasts'].items():
        lines += ['## '+contrast,'',
            '| Model | N | Accuracy | Balanced accuracy | Macro-F1 | Active recall | Rest FPR | Brier | Confusion [[TN,FP],[FN,TP]] | Supported N (rest/active) |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
        for name,entry in models.items():
            m=entry['all']['pooled'];s=entry['supported']['pooled']
            lines.append('| '+name+' | '+str(m['n'])+' | '+' | '.join(fmt(m[k]) for k in METRICS)+f" | {m['confusion_matrix']} | {s['n']} ({s['class_counts']['rest']}/{s['class_counts']['active']}) |")
        lines += ['', '### Supported-only secondary results','',
            '| Model | N | Accuracy | Balanced accuracy | Macro-F1 | Recall | FPR | Brier | Undefined reasons |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---|']
        for name,entry in models.items():
            m=entry['supported']['pooled'];lines.append('| '+name+' | '+str(m['n'])+' | '+' | '.join(fmt(m[k]) for k in METRICS)+f" | {m['undefined']} |")
        lines += ['', '### Equal-participant primary means','',
            '| Model | Accuracy | Balanced accuracy | Macro-F1 | Recall | FPR | Brier |',
            '|---|---:|---:|---:|---:|---:|---:|']
        for name,entry in models.items():
            lines.append('| '+name+' | '+' | '.join(fmt(entry['all']['participant_macro'][k]['mean']) for k in METRICS)+' |')
        lines += ['', '### Per-participant primary results','',
            '| Model | Participant | N | Accuracy | Balanced accuracy | Macro-F1 | Recall | FPR | Brier | Confusion | Supported / scheduled |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
        for name,entry in models.items():
            for p,m in entry['all']['per_participant'].items():
                n=entry['supported']['per_participant'][p]['n']
                lines.append(f"| {name} | {p} | {m['n']} | "+' | '.join(fmt(m[k]) for k in METRICS)+f" | {m['confusion_matrix']} | {n}/{m['n']} |")
        lines += ['', '### Support and imputation by class/participant','',
            '| Model | Participant | Class | Predicted / scheduled | Supported | Rows with missing values | Mean observed feature fraction |',
            '|---|---|---|---|---:|---:|---:|']
        for name,entry in models.items():
            for row in entry['coverage_by_class_and_participant']:
                lines.append(f"| {name} | {row['participant']} | {row['truth']} | {row['predicted']}/{row['scheduled']} | {row['supported']} | {row['rows_with_missing_values']} | {fmt(row['mean_observed_feature_fraction'])} |")
        names=list(models);fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
        for axis,metric in zip(axes,('balanced_accuracy','brier')):
            axis.bar(np.arange(len(names)),[models[n]['all']['pooled'][metric] for n in names])
            axis.set_xticks(np.arange(len(names)),names,rotation=35,ha='right');axis.set_ylim(0,1)
            axis.set_title(contrast+' — '+metric);axis.set_ylabel('All scheduled rows')
        fig.savefig(output/(contrast+'-comparison.png'),dpi=150);plt.close(fig)
        fig,axes=plt.subplots(2,3,figsize=(10,6),layout='constrained')
        for axis,name in zip(axes.ravel(),names):
            counts=np.asarray(models[name]['all']['pooled']['confusion_matrix'])
            axis.imshow(counts,vmin=0,vmax=36,cmap='Blues');axis.set_title(name)
            for (i,j),v in np.ndenumerate(counts):axis.text(j,i,str(v),ha='center',va='center')
            axis.set_xticks([0,1],['rest','active']);axis.set_yticks([0,1],['rest','active']);axis.set_xlabel('Predicted');axis.set_ylabel('True')
        fig.savefig(output/(contrast+'-confusions.png'),dpi=150);plt.close(fig)
    lines += ['', '## Interpretation limits','',
        'Speech, mouth/eye motion, head motion, exposure/ROI geometry, order and data availability can reveal experimental task. No accuracy here establishes psychological stress measurement. Quality-only or missingness-only success is a confound warning.',
        'Arithmetic contains known facial support failures (s3 all six active windows; s4 four; s2 one). Primary results retain and impute them. Value-only models have no explicit indicator features, but median imputation and other values can still encode missingness. Supported-only subsets have different denominators/class balances and are descriptive, not fair replacement headlines.',
        's25 remains development-only and is excluded. The six pilot participants previously informed pipeline engineering; results are exploratory, with no independent final test or population claim. Camera/wrist synchronization is unverified; no wrist/questionnaire/reference inputs are used.',
        'Next experiments should freeze motion-removal and acquisition-artifact ablations, audit missingness by task, and use a separately planned untouched cohort for final evaluation. Calibration and rejection-policy tuning remain later work.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')


def validate_run(output):
    plan,cfg=load_plan(output);status=read(output/'status.json')
    if status['status']!='completed' or status.get('plan_sha256')!=digest(plan):raise ValueError('Incomplete/changed experiment output')
    files=inventory(output);files.pop('status.json',None)
    if files!=status['output_files']:raise ValueError('Experiment output hash mismatch')
    data,inputs=load_features(Path(plan['feature_run']),cfg)
    if inputs!=plan['input_provenance']:raise ValueError('Feature sources changed')
    return validate_models(output,plan,cfg,data,read_jsonl(output/'predictions.jsonl'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare',action='store_true');modes.add_argument('--execute',action='store_true');modes.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        if not args.feature_run:parser.error('--feature-run required to prepare')
        plan=prepare(args.feature_run,args.output);print('Prepared without fitting:',plan['configuration_id'])
    elif args.execute:
        execute(args.output);print('Completed both exploratory task contrasts')
    else:print(json.dumps(validate_run(args.output),indent=2))


if __name__=='__main__':main()
