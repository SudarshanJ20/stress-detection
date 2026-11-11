"""Explicit final roles, sealed-outcome traps, native camera compatibility and model freeze."""

import copy
import io
import json
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection import independent_anxiety as study
from stress_detection import final_camera_features as export
from stress_detection import session_anxiety_audit as audit
from stress_detection import pulse
from stress_detection.features import read_jsonl, schema, summarize_frames, write_jsonl
from stress_detection.manifest import fingerprint
from stress_detection.pilot_state import atomic,digest,inventory,read
from stress_detection.policy import load_policy
from test_baseline import synthetic_feature_run
from test_features import frame

ROOT=Path(__file__).resolve().parents[1]


class IndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cfg=study.load_config()
        self.plan={'training_participants':[f's{i}' for i in range(1,7)],'engineering_only':['s25'],
                   'locked_final':[f's{i}' for i in range(101,111)],'participants':[{'id':f's{i}','role':'locked_final'} for i in range(101,111)]}
        self.plan_path=self.root/'plan.json';atomic(self.plan_path,self.plan)
        self.context=patch.object(study,'load_design',return_value=(self.cfg,self.plan));self.context.start();self.addCleanup(self.context.stop)

    def training_source(self):
        feature=self.root/'features';synthetic_feature_run(feature);entries=[]
        for i in range(1,7):
            p=f's{i}';folder=self.root/p;folder.mkdir()
            (folder/f'info_{p}.txt').write_text(f'{p}\nf\nctrl\n2020-01-01\n12-00-00\n')
            (folder/f'selfReportedAnx_{p}.csv').write_text(f'4,{round(2+i/7,3)}\n3,{round(1+i/7,3)}\n2,3\n')
            entries.append({'id':p,'role':'development_only','directory':str(folder)})
        selection=self.root/'train-selection.json';atomic(selection,{'version':'session-audit-selection-v1','participants':entries})
        source=self.root/'audit';audit.audit(feature,selection,source);return source

    def models(self):
        source=self.training_source();folder=self.root/'models';study.train(self.plan_path,source,folder)
        self.assertEqual(study.validate_models(folder,self.plan_path,True)['models'],12)
        return folder,source

    def camera_selection(self):
        entries=[]
        for p in self.plan['locked_final']:
            native=self.root/'inputs'/p;raw=native/p;raw.mkdir(parents=True)
            (raw/f'info_{p}.txt').write_text(f'{p}\nf\ntest\n2020-01-01\n12-00-00\n')
            (raw/f'selfReportedAnx_{p}.csv').write_text('DO NOT READ RESERVED OUTCOME\n')
            mf=self.root/(p+'-manifest.json')
            atomic(mf,{'records':[{'participant_id':p,'recording_id':p+'/'+task,'task_id':task,'split_role':'test',
                                 'video':{'valid':False}} for task in ('T1','T2','T3')]})
            entries.append({'id':p,'role':'locked_final','input_root':str(native),'manifest':str(mf),
                            'tasks':{task:{'face':str(self.root/'derived'/p/task/'face'),
                                           'pulse':str(self.root/'derived'/p/task/'pulse')} for task in ('T1','T2','T3')}})
        selection=self.root/'camera-selection.json';atomic(selection,{'version':'final-camera-selection-v1','participants':entries})
        return selection,entries

    def seal_guard(self):
        original=io.open
        def guarded(file,*args,**kwargs):
            if not isinstance(file,int):
                p=Path(file)
                if p.name.startswith('selfReportedAnx') or p.name=='outcomes.jsonl' or 'sealed-outcomes' in p.parts:
                    raise AssertionError('Questionnaire/outcome access during camera export/inference')
            return original(file,*args,**kwargs)
        return patch('io.open',side_effect=guarded)

    def native_recording(self,entry,task='T1'):
        p=entry['id'];native=Path(entry['input_root']);video=native/p/f'vid_{p}_{task}.avi';video.write_bytes(b'synthetic video transport')
        fp=fingerprint(video,p+'/'+video.name);face=Path(entry['tasks'][task]['face']);face.mkdir(parents=True)
        frames=[]
        for i in range(1801):
            f=frame(i);f.update(pts=i,time_base='1/10',presentation_time_seconds=i/10)
            for region in pulse.REGIONS:f['regions'][region]['mean_rgb']=[100+2*np.sin(2*np.pi*1.2*i/10),110+np.sin(2*np.pi*1.2*i/10),120.]
            frames.append(f)
        cfg={'schema_version':'1.0','source':fp,'recording_id':p+'/'+task,
             'model':read(ROOT/'configs/face-landmarker.json'),'measurements':load_policy()[0]['tracking']['measurements'],
             'max_frames':None,'policy':load_policy()[1],'python':platform.python_version(),'architecture':platform.machine(),
             'delegate':'CPU','software':{k:export.version(k) for k in ('mediapipe','numpy','opencv-contrib-python','av')}}
        atomic(face/'config.json',cfg);atomic(face/'status.json',{'status':'completed'})
        atomic(face/'summary.json',{'status':'completed','processed_frames':1801,
               'reader':{'decode_complete':True,'last_frame_duration_seconds':.1,'width':200,'height':100}})
        write_jsonl(face/'frames.jsonl',frames)
        pulse.run(face,Path(entry['tasks'][task]['pulse']),pulse.Settings())
        path=Path(entry['manifest']);mf=read(path)
        mf['records'][0].update(camera_eligibility_policy=load_policy()[1]['timing'],files={'vid':fp},
            video={'valid':True,'decoded_frames':1801,'observed_duration_seconds':180.1})
        atomic(path,mf);return frames

    def test_locked_manifest_and_design_cannot_be_changed(self):
        self.context.stop()
        with self.assertRaisesRegex(ValueError,'manifest changed'):study.load_design(self.plan_path)
        self.context.start()
        self.assertEqual(self.cfg['regression'],{'class':'Ridge','alpha':10.,'solver':'svd','fit_intercept':True})

    def test_missing_recordings_retained_and_no_questionnaire_access_end_to_end(self):
        models,source=self.models();before=inventory(source);selection,entries=self.camera_selection()
        out=self.root/'export';pred=self.root/'predictions'
        with self.seal_guard():
            result=export.export(self.plan_path,selection,models,out)
            self.assertEqual(result['scheduled_windows'],180)
            result=study.predict_batches(self.plan_path,models,[out],pred)
            self.assertEqual(result['predictions'],120);self.assertFalse(result['outcomes_read'])
            self.assertEqual(study.validate_predictions(pred,self.plan_path),result)
        self.assertEqual(inventory(source),before)
        rows=read_jsonl(pred/'predictions.jsonl');self.assertTrue(all('truth' not in r for r in rows))
        self.assertTrue(all(r['participant'] not in r['training_participants'] for r in rows))
        self.assertEqual(len(read_jsonl(out/'windows.jsonl')),180)
        self.assertTrue(all(r['id_start_seconds'] is None for r in read_jsonl(out/'windows.jsonl')))
        with self.assertRaises(FileExistsError):study.train(self.plan_path,source,models)
        with self.assertRaises(FileExistsError):study.predict_batches(self.plan_path,models,[out],pred)
        with self.assertRaises(ValueError):study.predict_batches(self.plan_path,models,[out,out],self.root/'duplicate')
        changed=copy.deepcopy(rows);changed[0]['role']='pilot_development'
        with self.assertRaises(ValueError):study.prediction_inventory(changed,self.plan['locked_final'],self.cfg,self.plan)
        with self.assertRaises(ValueError):study.prediction_inventory(rows[:-1],self.plan['locked_final'],self.cfg,self.plan)
        changed=copy.deepcopy(rows);changed[0]['truth']=2.
        with self.assertRaises(ValueError):study.prediction_inventory(changed,self.plan['locked_final'],self.cfg,self.plan)
        (models/'selfReportedAnx_reserved.csv').write_text('must not be read')
        with self.seal_guard(),self.assertRaisesRegex(ValueError,'Questionnaire payload forbidden'):
            study.validate_models(models,self.plan_path)
        (models/'selfReportedAnx_reserved.csv').unlink()
        (pred/'predictions.jsonl').write_text('{}\n')
        with self.assertRaises(ValueError):study.validate_predictions(pred,self.plan_path)

    def test_partial_batches_role_separation_and_info_content_not_filename(self):
        models,_=self.models();selection,entries=self.camera_selection()
        for fault in ['training','engineering','pilot_role']:
            bad=copy.deepcopy(entries[:1])
            if fault=='training':bad[0]['id']='s1'
            elif fault=='engineering':bad[0]['id']='s25'
            else:bad[0]['role']='pilot_development'
            atomic(selection,{'version':'final-camera-selection-v1','participants':bad})
            with self.subTest(fault=fault),self.assertRaises(ValueError):export.selected(selection,self.plan)
        atomic(selection,{'version':'final-camera-selection-v1','participants':entries[:1]})
        p=entries[0]['id'];info=Path(entries[0]['input_root'])/p/f'info_{p}.txt';info.write_text('2,3\n1,2\n3,4\n')
        with self.assertRaises(ValueError):export.export(self.plan_path,selection,models,self.root/'bad-info')
        self.assertEqual(read(self.root/'bad-info/receipt.json')['status'],'failed')
        info.write_text(f'{p}\nf\nctrl\n2020-01-01\n12-00-00\n')
        out=self.root/'one';export.export(self.plan_path,selection,models,out)
        with self.assertRaises(ValueError):study.predict_batches(self.plan_path,models,[out],self.root/'incomplete')
        self.assertEqual(study.predict_batches(self.plan_path,models,[out],self.root/'partial',False)['predictions'],12)
        self.assertFalse((self.root/'incomplete').exists())

    def test_native_features_match_existing_geometry_pulse_and_session_rules(self):
        models,_=self.models();selection,entries=self.camera_selection();
        with self.seal_guard():frames=self.native_recording(entries[0])
        atomic(selection,{'version':'final-camera-selection-v1','participants':entries[:1]})
        out=self.root/'native-export'
        with self.seal_guard():export.export(self.plan_path,selection,models,out)
        rows=read_jsonl(out/'windows.jsonl');first=rows[0]
        for i,f in enumerate(frames):f['_previous_gap']=.1 if i else None
        expected,quality=summarize_frames(frames[:300],200,100)
        for key,value in {**expected,**quality}.items():
            if key in first['values']:self.assertEqual(first['values'][key],value,key)
        self.assertEqual(first['values']['cam_green_forehead_bpm'],72.)
        self.assertEqual(first['id_start_seconds'],0.);self.assertEqual(rows[5]['id_end_seconds'],180.)
        self.assertEqual(first['id_role'],'locked_final')
        self.assertTrue(all(r['status']=='unsupported' for r in rows[6:]))
        ix,x,_=export.load_export(out,self.plan_path,models)
        self.assertEqual(x[0]['beh_mouth_mean'],expected['beh_mouth_mean'])
        self.assertAlmostEqual(x[0]['q_pulse_green_forehead_missing'],12/18)
        self.assertEqual(x[0]['q_track_fraction'],1.)  # observed windows only, never invented zeros
        pc=Path(entries[0]['tasks']['T1']['pulse'])/'config.json';bad=read(pc);bad['settings']['max_gap_seconds']=10.;atomic(pc,bad)
        with self.assertRaises(ValueError):export.export(self.plan_path,selection,models,self.root/'bad-policy')
        self.assertEqual(read(self.root/'bad-policy/receipt.json')['status'],'failed')
        with self.assertRaises(ValueError):export.load_export(out,self.plan_path,models)

    def test_all_missing_training_features_fallback_without_final_fit(self):
        cfg=study.load_config();cols=['a','b'];y=np.arange(6.)
        model=study.reg.fit_fold(np.full((6,2),np.nan),y,cols,cfg)
        self.assertTrue(model['fallback'])
        np.testing.assert_array_equal(study.reg.predict(model,np.array([[999.,1.],[1.,999.]])),[2.5,2.5])
        self.assertEqual(model['preprocessor'].snapshot(cols)['training_all_missing_columns'],cols)
