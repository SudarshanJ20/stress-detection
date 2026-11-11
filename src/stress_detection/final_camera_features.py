"""Outcome-blind camera export with explicit locked_final roles and scheduled failures."""

import argparse
from fractions import Fraction
import json
import math
import platform
from importlib.metadata import version
from pathlib import Path

from . import baseline as base
from . import features as features
from . import independent_anxiety as study
from . import pulse
from .features import finite, read_jsonl, write_jsonl
from .manifest import fingerprint
from .pilot_state import atomic, digest, now, read
from .policy import load_policy
from .validate_sample import inspect_info, require_ignored


def checked_path(path):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)) or any('selfreportedanx' in x.lower() or 'sealed-outcome' in x.lower() for x in (*path.parts,*path.resolve().parts)):
        raise ValueError('Outcome/symlink path forbidden in camera export')
    require_ignored(path)
    return path


def selected(path,plan):
    data=read(checked_path(path))
    if set(data)!={'version','participants'} or data['version']!='final-camera-selection-v1' or not data['participants']:
        raise ValueError('Explicit final-role camera selection required')
    seen=set()
    for e in data['participants']:
        if (set(e)!={'id','role','input_root','manifest','tasks'} or e['id'] not in plan['locked_final']
                or e['id'] in seen or e['role']!='locked_final' or set(e['tasks'])!={'T1','T2','T3'}):
            raise ValueError('Final participant/role/task selection mismatch')
        seen.add(e['id'])
        for task,paths in e['tasks'].items():
            if set(paths)!={'face','pulse'}:raise ValueError('Only face/pulse paths are allowed')
            for value in paths.values():checked_path(value)
        checked_path(e['input_root']);checked_path(e['manifest'])
    return data


def failure_window(p,task,i,reason,origin=None):
    # Unknown coverage/PTS is null, not an invented observed zero or nominal timestamp.
    values={c:None for c in features.schema()['model_columns']}
    for method in features.METHODS:
        for region in features.REGIONS:values[f'q_pulse_{method}_{region}_missing']=1
    return {'id_window_key':f'{p}/{task}/{i}','id_participant':p,'id_role':'locked_final','id_task':task,
            'id_window_index':i,'id_start_seconds':float(origin)+30*i if origin is not None else None,
            'id_end_seconds':float(origin)+30*(i+1) if origin is not None else None,
            'status':'unsupported','reason':reason,'values':values}


def stage_files(folder,names,proof):
    for name in names:
        path=checked_path(folder/name)
        proof[str(path.resolve())]=fingerprint(path,str(path.resolve()))


def recording(entry,task,record,cfg,stamp):
    p=entry['id'];face=Path(entry['tasks'][task]['face']);prun=Path(entry['tasks'][task]['pulse']);proof={}
    def failed(reason):return [failure_window(p,task,i,reason) for i in range(6)],proof
    if record.get('split_role')!='test':raise ValueError('Native source manifest must preserve test role')
    if record.get('camera_eligibility_policy')!=stamp['timing'] or not record.get('video',{}).get('valid'):
        return failed('video_decode_or_timing_ineligible')
    if not (face/'status.json').is_file():return failed('face_stage_missing')
    stage_files(face,['status.json'],proof)
    status=read(face/'status.json')['status']
    if status not in ('completed','completed_with_warnings'):return failed('face_stage_'+status)
    stage_files(face,['config.json','summary.json','frames.jsonl'],proof)
    fc,times,_,timing=pulse.load_face_run(face)
    fs=read(face/'summary.json');policy=load_policy()[0]
    if (fc['recording_id']!=p+'/'+task or fc['source']!=record['files']['vid']
            or fc.get('policy')!=stamp or fc['measurements']!=policy['tracking']['measurements']
            or fc['max_frames'] is not None or fc['model']!=read(study.ROOT/'configs/face-landmarker.json')
            or fc['python']!=platform.python_version() or fc['architecture']!=platform.machine() or fc['delegate']!='CPU'
            or fc['software']!={p:version(p) for p in ('mediapipe','numpy','opencv-contrib-python','av')}
            or fs['processed_frames']!=record['video']['decoded_frames']
            or abs(timing['duration_seconds']-record['video']['observed_duration_seconds'])>1e-8):
        raise ValueError('Face feature/policy/model compatibility mismatch')
    video=checked_path(Path(entry['input_root'])/fc['source']['path'])
    if fingerprint(video,fc['source']['path'])!=fc['source']:raise ValueError('Video source changed')
    proof[str(video.resolve())]=fingerprint(video,str(video.resolve()))
    origin=Fraction(timing['origin_fraction']);count=int(math.floor((timing['duration_seconds']+1e-9)/30))
    camera=None;pulse_reason='pulse_stage_missing'
    if (prun/'status.json').is_file():
        stage_files(prun,['status.json'],proof);ps=read(prun/'status.json')['status'];pulse_reason='pulse_stage_'+ps
        if ps=='completed':
            stage_files(prun,['config.json','source-timing.json','windows.jsonl'],proof)
            pc=read(prun/'config.json')
            if (pc['recording_id']!=p+'/'+task or pc['source']!=fc['source'] or pc['source_model']!=fc['model']
                    or pc['face_frames']['sha256']!=proof[str((face/'frames.jsonl').resolve())]['sha256']
                    or pc['settings']!=policy['pulse']['settings'] or read(prun/'source-timing.json')!=timing
                    or pc['software']!={'numpy':version('numpy'),'python':platform.python_version()}):
                raise ValueError('Pulse feature/policy/source compatibility mismatch')
            camera=features.pulse_columns(read_jsonl(prun/'windows.jsonl'),float(origin),count)
    rows=[];frames=[];current=0;previous=None;n=0
    width,height=fs['reader']['width'],fs['reader']['height']
    def emit(i,group):
        if i>=count:return failure_window(p,task,i,'incomplete_original_window',origin)
        beh,quality=features.summarize_frames(group,width,height)
        values={**beh,**quality}
        if camera is None:
            values.update({k:v for k,v in failure_window(p,task,i,pulse_reason)['values'].items() if k.startswith(('cam_','q_pulse_'))})
        else:values.update(camera[i])
        numeric={c:values[c] for c in features.schema()['model_columns']}
        return {'id_window_key':f'{p}/{task}/{i}','id_participant':p,'id_role':'locked_final','id_task':task,
            'id_window_index':i,'id_start_seconds':float(origin)+30*i,'id_end_seconds':float(origin)+30*(i+1),
            'status':'derived','reason':pulse_reason if camera is None else None,'values':numeric}
    with (face/'frames.jsonl').open() as source:
        for line in source:
            frame=json.loads(line);t=Fraction(frame['presentation_time_fraction'])
            if (frame['frame_index']!=n or str(t)!=timing['original_time_fractions'][n]
                    or frame['pts']!=timing['pts'][n] or frame['time_base']!=timing['time_bases'][n]
                    or abs(float(t)-frame['presentation_time_seconds'])>1e-9):
                raise ValueError('Frame sequence/PTS changed')
            frame['_previous_gap']=float(t-previous) if previous is not None else None
            i=int((t-origin)//30)
            while current<min(i,6):rows.append(emit(current,frames));frames=[];current+=1
            if i<6:frames.append(frame)
            previous=t;n+=1
    while current<6:rows.append(emit(current,frames));frames=[];current+=1
    if n!=len(times):raise ValueError('Incomplete source frame inventory')
    for file,checksum in proof.items():
        if fingerprint(Path(file),file)!=checksum:raise ValueError('Source changed during export')
    return rows,proof


def derive(selection,cfg,plan):
    rows=[];proof={}
    for e in selection['participants']:
        p=e['id'];manifest_path=checked_path(e['manifest']);mf=read(manifest_path)
        info=checked_path(Path(e['input_root'])/p/f'info_{p}.txt')
        if not inspect_info(info,p)['valid']:raise ValueError('Info content/participant metadata mismatch')
        for path in (manifest_path,info):proof[str(path.resolve())]=fingerprint(path,str(path.resolve()))
        records=[r for r in mf['records'] if r['participant_id']==p]
        if len(records)!=3 or {r['task_id'] for r in records}!={'T1','T2','T3'}:
            raise ValueError('Ambiguous/missing scheduled task manifest')
        for r in sorted(records,key=lambda r:r['task_id']):
            if r['recording_id']!=p+'/'+r['task_id']:raise ValueError('Recording identity mismatch')
            windows,inputs=recording(e,r['task_id'],r,cfg,load_policy()[1]);rows+=windows;proof.update(inputs)
    return rows,proof


def summarize(rows,people,cfg):
    names=sorted({c for cols in cfg['models'].values() for c in cols});x=[];index=[];support=[]
    expected={(p,t,i) for p in people for t in ('T1','T2','T3') for i in range(6)}
    seen=set()
    for r in rows:
        key=(r['id_participant'],r['id_task'],r['id_window_index'])
        if (key not in expected or key in seen or r['id_role']!='locked_final'
                or r['id_window_key']!=f'{key[0]}/{key[1]}/{key[2]}'
                or set(r['values'])!=set(features.schema()['model_columns'])
                or any(v is not None and not finite(v) for v in r['values'].values())):
            raise ValueError('Role/window/schema/finite-value mismatch')
        if r['status'] not in ('derived','unsupported'):
            raise ValueError('Unknown window completion state')
        start,end=r['id_start_seconds'],r['id_end_seconds']
        if ((start is None)!=(end is None) or (start is not None and
                (not finite(start) or not finite(end) or not math.isclose(end-start,30.,abs_tol=1e-9)))):
            raise ValueError('Invalid/partial original window timing')
        if r['status']=='unsupported' and (not r['reason'] or r['values']!=failure_window(*key,r['reason'])['values']):
            raise ValueError('Unsupported measurements must remain null')
        seen.add(key)
    if seen!=expected:raise ValueError('Incomplete scheduled window inventory')
    import numpy as np
    for p in people:
        group=[r for r in rows if r['id_participant']==p];value={};counts={}
        for name in names:
            observed=[r['values'][name] for r in group if r['values'][name] is not None]
            agg=np.mean if name in cfg['models']['missingness'] else np.median
            value[name]=float(agg(observed)) if observed else None
            counts[name]={'scheduled':18,'observed':len(observed),'by_task':{
                task:sum(r['values'][name] is not None for r in group if r['id_task']==task) for task in ('T1','T2','T3')}}
        x.append(value);index.append({'participant':p,'role':'locked_final','session_key':p+'/session-1'})
        support.append({'participant':p,'columns':counts,'failures':[{'window':r['id_window_key'],'reason':r['reason']} for r in group if r['reason']]})
    return index,x,support


def export(plan_path,selection_path,models_run,output):
    cfg,plan=study.load_design(plan_path);study.validate_models(models_run,plan_path)
    selection=selected(selection_path,plan)
    require_ignored(output);output.mkdir(parents=True,exist_ok=False)
    receipt={**study.context(cfg,plan),'kind':'outcome_blind_final_features','status':'running','selection':selection,
        'models_run':str(models_run.resolve()),'model_files':study.artifact_inventory(models_run),'outcomes_read':False,
        'selection_path':str(selection_path.resolve()),'policy':load_policy()[1],'feature_schema_sha256':digest(features.schema())}
    atomic(output/'receipt.json',receipt)
    try:
        rows,proof=derive(selection,cfg,plan);people=[e['id'] for e in selection['participants']]
        index,x,support=summarize(rows,people,cfg)
        for name,data in [('windows',rows),('index',index),('X',x),('support',support)]:write_jsonl(output/(name+'.jsonl'),data)
        receipt.update(status='completed',source_files=proof,ended=now(),output_files=study.artifact_inventory(output));receipt['output_files'].pop('receipt.json',None)
    except BaseException as exc:
        receipt.update(status='failed',failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:atomic(output/'receipt.json',receipt)
    index,x,_=load_export(output,plan_path,models_run)
    return {'status':'passed','participants':len(index),'scheduled_windows':18*len(index),'outcomes_read':False,'role':'locked_final'}


def load_export(folder,plan_path,models_run):
    cfg,plan=study.load_design(plan_path);require_ignored(folder);r=read(folder/'receipt.json')
    study.check_context(r,cfg,plan);study.complete_files(folder,r)
    if (r['kind']!='outcome_blind_final_features' or r['outcomes_read'] or r['policy']!=load_policy()[1]
            or r['feature_schema_sha256']!=cfg['feature_schema_sha256']
            or Path(r['models_run'])!=models_run.resolve() or study.artifact_inventory(models_run)!=r['model_files']):
        raise ValueError('Feature role/policy/model/schema mismatch')
    selection=selected(Path(r['selection_path']),plan)
    if selection!=r['selection']:raise ValueError('Export selection changed')
    for path,checksum in r['source_files'].items():
        if fingerprint(checked_path(path),path)!=checksum:raise ValueError('Camera source changed')
    rows=read_jsonl(folder/'windows.jsonl');people=[e['id'] for e in selection['participants']]
    index,x,support=summarize(rows,people,cfg)
    if index!=read_jsonl(folder/'index.jsonl') or x!=read_jsonl(folder/'X.jsonl') or support!=read_jsonl(folder/'support.jsonl'):
        raise ValueError('Session summaries/predictor alignment do not reproduce')
    return index,x,r


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--models-run',type=Path,required=True)
    parser.add_argument('--selection',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validate',action='store_true');a=parser.parse_args()
    if a.validate:
        ix,_,_=load_export(a.output,a.plan,a.models_run);print({'status':'passed','sessions':len(ix),'outcomes_read':False})
    else:
        if not a.selection:parser.error('--selection required')
        print(export(a.plan,a.selection,a.models_run,a.output))


if __name__=='__main__':main()
