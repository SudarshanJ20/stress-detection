"""Synthetic geometry, missingness, provenance, leakage and output lifecycle checks."""

import copy
from fractions import Fraction
import json
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection.features import (APERTURES, BEHAVIOUR, CONFIG, IDENTIFIERS,
    METHODS, REGIONS, VERSION, aperture_values, missingness, pulse_columns, read_jsonl,
    run, schema, selection, statistics, summarize_frames, transition_values,
    validate_feature_lists, validate_rows, validate_run, validate_tables, verified_source, write_tables)
from stress_detection.manifest import fingerprint
from stress_detection.pilot_state import atomic, digest, inventory, read
from stress_detection.policy import load_policy

ROOT=Path(__file__).resolve().parents[1]


def frame(i=0, segment=1):
    points=np.full((478,3),.5)
    points[13,:2]=[.5,.55];points[14,:2]=[.5,.65]
    points[61,:2]=[.3,.6];points[291,:2]=[.7,.6]
    for vertical,horizontal in (APERTURES['eye_a'],APERTURES['eye_b']):
        points[vertical[0],:2]=[.3,.39];points[vertical[1],:2]=[.3,.41]
        points[horizontal[0],:2]=[.225,.4];points[horizontal[1],:2]=[.375,.4]
    return {'frame_index':i,'presentation_time_fraction':str(Fraction(i,10)),
        'face_count':1,'detection_available':True,'track_segment_id':segment,
        'landmarks_normalized_xyz':points.tolist(),'face_box':{'clipped':False,'xyxy_pixels':[20,10,180,90],'frame_area_fraction':.64},
        'track_event':{'type':'acquire'} if i==0 else None,'timestamp_issues':[],
        'motion_face_sizes_per_second':None if i==0 else 0.,'brightness_change_per_second':None if i==0 else 0.,
        'measurements':{'valid':True,'brightness':100.,'dark_fraction':0.,'saturated_fraction':0.,'laplacian_variance':9.},
        'regions':{r:{'valid':True,'pixel_count':100,'mean_rgb':[1,2,3]} for r in REGIONS}}


def pulse_rows(count=1,origin=2.5):
    return [{'window_index':i,'method':m,'region':r,'start_original_seconds':origin+30*i,
        'end_original_seconds':origin+30*(i+1),'status':'accepted','estimated_bpm':72.,
        'spectral_peak_fraction':.3,'rejection_reason':None}
        for i in range(count) for m in METHODS for r in REGIONS]


def example_rows():
    behaviour,quality=summarize_frames([frame(i) for i in range(10)],200,100)
    pulse=pulse_columns(pulse_rows(),2.5,1)[0]
    stamp=load_policy()[1]
    rows=[]
    for task,condition in (('T1','rest'),('T2','speech'),('T3','arithmetic')):
        row={c:'synthetic' for c in IDENTIFIERS}
        row.update(id_window_key=f's999/{task}/0',id_participant='s999',id_role='pilot_development',
            id_recording='s999/'+task,id_task=task,id_window_index=0,id_start_seconds=2.5,id_end_seconds=32.5,
            id_origin_fraction='5/2',id_frame_count=10,id_policy_version=stamp['version'],id_policy_sha256=stamp['sha256'],
            id_feature_version=VERSION,id_feature_schema_sha256=digest(schema()),label_condition=condition,
            **behaviour,**quality,**pulse)
        for name in IDENTIFIERS:
            if name.endswith('_sha256') and name not in ('id_policy_sha256','id_feature_schema_sha256'):
                row[name]='a'*64
        rows.append(row)
    references=[{'ref_participant':'s999','ref_task':t,'ref_time_basis':'independent nominal recording',
        'ref_wrist':{'median_bpm':777777.,'windows':[{'estimated_bpm':777777.}]},
        'ref_eda_metadata':{'rows':1234567,'sampling_rate_hz':4,'nominal_duration_seconds':180}} for t in ('T1','T2','T3')]
    schedules=[{'recording':'s999/'+t,'origin_fraction':'5/2','complete_windows':1} for t in ('T1','T2','T3')]
    return rows,references,schedules


class GeometryTests(unittest.TestCase):
    def test_apertures_use_pixel_aspect_and_local_dimensionless_scale(self):
        f=frame();mouth,eyes=aperture_values(f,200,100)
        self.assertAlmostEqual(mouth,.125)
        self.assertAlmostEqual(eyes,1/15)
        self.assertEqual(aperture_values(f,400,200),(mouth,eyes))
        moved=copy.deepcopy(f)
        points=np.array(moved['landmarks_normalized_xyz']);points[:,:2]=points[:,:2]*.8+.05
        moved['landmarks_normalized_xyz']=points.tolist()
        np.testing.assert_allclose(aperture_values(moved,200,100),(mouth,eyes))

    def test_degenerate_out_of_image_or_invalid_landmarks_are_not_measurements(self):
        f=frame();f['landmarks_normalized_xyz'][61]=f['landmarks_normalized_xyz'][291]
        self.assertIsNone(aperture_values(f,200,100)[0])
        f=frame();f['landmarks_normalized_xyz'][159][0]=-1
        self.assertIsNone(aperture_values(f,200,100)[1])
        for change in ('nonfinite','lost','multiple'):
            f=frame()
            if change=='nonfinite':f['landmarks_normalized_xyz'][0][0]=float('nan')
            elif change=='lost':f['track_segment_id']=None
            else:f['face_count']=2
            self.assertEqual(aperture_values(f,200,100),(None,None))

    def test_valid_fraction_boundary_and_empty_summaries(self):
        good,fraction,reason=statistics([1.]*9+[None],10,('mean','std','p95'))
        self.assertEqual(reason,None);self.assertEqual(fraction,.9);self.assertEqual(good['mean'],1)
        bad,_,reason=statistics([1.]*8+[None]*2,10,('mean',))
        self.assertEqual(bad['mean'],None);self.assertEqual(reason,'insufficient_valid_data')
        self.assertEqual(statistics([1],1,('mean',))[0]['mean'],None)
        b,q=summarize_frames([],200,100)
        self.assertTrue(all(v is None for v in b.values()))
        self.assertEqual(q['q_no_frames'],1)
        self.assertIsNone(q['q_brightness_mean'])

    def test_motion_never_crosses_segments_restart_gaps_or_window_boundary(self):
        a,b=frame(0),frame(1)
        self.assertEqual(transition_values(a,b,200,100),(0.,0.))
        b['track_segment_id']=2;b['motion_face_sizes_per_second']=999
        self.assertEqual(transition_values(a,b,200,100),(None,None))
        b=frame(1);b['track_event']={'type':'restart'}
        self.assertEqual(transition_values(a,b,200,100),(None,None))
        b=frame(2)
        self.assertEqual(transition_values(a,b,200,100),(None,None))
        b=frame(1)
        self.assertEqual(transition_values(None,b,200,100),(None,None))
        # Two frames have only one in-window transition: insufficient samples, not a carried value.
        behaviour,_=summarize_frames([frame(20),frame(21)],200,100)
        self.assertIsNone(behaviour['beh_motion_median'])
        b['motion_face_sizes_per_second']=100
        with self.assertRaisesRegex(ValueError,'does not reproduce'):
            transition_values(a,b,200,100)


class FeatureTableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows,self.refs,self.schedules=example_rows()

    def test_complete_schema_and_feature_allowlists_exclude_metadata_labels_reference(self):
        self.assertEqual(read(CONFIG),schema())
        validate_feature_lists(schema());validate_rows(self.rows,3,{'s999':'pilot_development'},self.schedules)
        for forbidden in ('id_participant','id_start_seconds','id_task','id_manifest','label_condition','ref_wrist','recording_order'):
            bad=copy.deepcopy(schema());bad['model_feature_lists']['ordinary_fusion'].append(forbidden)
            with self.assertRaises(ValueError):validate_feature_lists(bad)

    def test_duplicate_missing_count_task_and_role_are_failures(self):
        variants=[self.rows+[copy.deepcopy(self.rows[0])],self.rows[:-1]]
        bad=copy.deepcopy(self.rows);bad[0]['id_role']='development_only';variants.append(bad)
        bad=copy.deepcopy(self.rows);bad[0]['id_participant']='s25';variants.append(bad)
        for rows in variants:
            with self.assertRaises(ValueError):validate_rows(rows,3,{'s999':'pilot_development'},self.schedules)
        wrong=copy.deepcopy(self.schedules);wrong[0]['complete_windows']=2
        with self.assertRaisesRegex(ValueError,'count/origin'):validate_rows(self.rows,3,{'s999':'pilot_development'},wrong)

    def test_original_boundaries_task_labels_and_hash_provenance_are_checked(self):
        for key,value in [('id_start_seconds',0),('id_end_seconds',30),('id_origin_fraction','0'),
                          ('label_condition','arithmetic'),('id_video_sha256','missing'),
                          ('id_feature_schema_sha256','a'*64),('id_policy_sha256','b'*64)]:
            rows=copy.deepcopy(self.rows);rows[0][key]=value
            with self.assertRaises(ValueError,msg=key):validate_rows(rows,3,{'s999':'pilot_development'},self.schedules)

    def test_facial_null_and_finite_semantics(self):
        for key,value in [('beh_mouth_mean',float('nan')),('beh_mouth_mean',None),('q_mouth_reason','insufficient_valid_data')]:
            rows=copy.deepcopy(self.rows);rows[0][key]=value
            with self.assertRaises(ValueError):validate_rows(rows,3,{'s999':'pilot_development'},self.schedules)
        rows=copy.deepcopy(self.rows);rows[0]['q_mouth_valid_fraction']=.5;rows[0]['q_mouth_reason']='insufficient_valid_data'
        for name in ('mean','std','p95'):rows[0]['beh_mouth_'+name]=None
        validate_rows(rows,3,{'s999':'pilot_development'},self.schedules)
        self.assertEqual(missingness(rows)[0]['null_counts']['beh_mouth_mean'],1)

    def test_all_pulse_variants_and_rejected_null_are_preserved(self):
        rows=pulse_rows();rows[0].update(status='rejected',estimated_bpm=None,rejection_reason='diffuse_spectrum')
        result=pulse_columns(rows,2.5,1)[0]
        self.assertIsNone(result['cam_green_forehead_bpm']);self.assertEqual(result['q_pulse_green_forehead_missing'],1)
        for mutation in ('duplicate','missing','boundary','filled_failure','accepted_null'):
            bad=copy.deepcopy(rows)
            if mutation=='duplicate':bad.append(bad[0])
            elif mutation=='missing':bad.pop()
            elif mutation=='boundary':bad[0]['start_original_seconds']=0
            elif mutation=='filled_failure':bad[0]['estimated_bpm']=0
            else:bad[1]['estimated_bpm']=None
            with self.assertRaises(ValueError,msg=mutation):pulse_columns(bad,2.5,1)

    def test_predictor_only_contrasts_keep_indices_labels_and_references_separate(self):
        write_tables(self.root,self.rows,self.refs);validate_tables(self.root,self.rows,self.refs)
        for name,condition in [('rest-vs-speech','speech'),('rest-vs-arithmetic','arithmetic')]:
            x=read_jsonl(self.root/name/'X.jsonl');index=read_jsonl(self.root/name/'index.jsonl')
            self.assertEqual(len(x),2);self.assertEqual([r['target'] for r in index],[0,1])
            self.assertEqual([r['label_condition'] for r in index],['rest',condition])
            for row in x:
                self.assertEqual(set(row),set(schema()['model_columns']))
                self.assertNotIn(777777.,row.values());self.assertNotIn(1234567,row.values())
                self.assertFalse(any(c.startswith(('id_','label_','ref_')) for c in row))
        path=self.root/'rest-vs-speech/X.jsonl';data=read_jsonl(path);data[0]['id_participant']='s999'
        path.write_text('\n'.join(json.dumps(r) for r in data)+'\n')
        with self.assertRaisesRegex(ValueError,'model input columns'):validate_tables(self.root,self.rows,self.refs)

    def test_selection_forbids_pilot_development_mixture(self):
        base={'schema_version':'1.0','cohort':'pilot','expected_rows':3,'final_test_cohort':'unassigned',
              'participants':[{'id':'s999','role':'pilot_development','summary':str(self.root/'summary.json')}]}
        path=self.root/'selection.json';atomic(path,base);selection(path)
        for wrong in ('s25','role','cohort','final_test'):
            bad=copy.deepcopy(base)
            if wrong=='s25':bad['participants'][0].update(id='s25',role='development_only')
            elif wrong=='role':bad['participants'][0]['role']='final_test'
            elif wrong=='cohort':bad['cohort']='development'
            else:bad['final_test_cohort']='assigned'
            atomic(path,bad)
            with self.assertRaises(ValueError):selection(path)

    def test_source_rejects_changed_policies_code_and_incomplete_receipts(self):
        policy,stamp=load_policy();path=self.root/'summary.json'
        ctx={'policy':stamp,'face_settings':policy['tracking']['measurements'],'pulse_settings':policy['pulse']['settings'],
             'python':platform.python_version(),'software':{'numpy':np.__version__},
             'code':{p.name:fingerprint(p,p.name)['sha256'] for p in (ROOT/'src/stress_detection').glob('*.py')}}
        summary={'status':'completed','context':ctx,'selection':{'final_test_cohort':'unassigned',
             'participants':[{'id':'s999','role':'pilot_development'}]},'stage_events':[]}
        entry={'id':'s999','role':'pilot_development','summary':str(path)}
        for fault in ('policy','code','legacy','receipt'):
            bad=copy.deepcopy(summary)
            if fault=='policy':bad['context']['pulse_settings']['min_bpm']=40
            elif fault=='code':bad['context']['code']['pulse.py']='0'*64
            elif fault=='legacy':
                bad['context'].pop('policy');att=self.root/'compatibility.json'
                atomic(att,{'status':'failed','compatible_policy':stamp});entry['legacy_compatibility']=str(att)
            else:
                output=self.root/'old-output';output.mkdir();receipt=self.root/'old-receipt.json'
                atomic(receipt,{'status':'running'})
                bad['stage_events']=[{'key':'s999/manifest','receipt':str(receipt),'output':str(output)}]
            atomic(path,bad)
            with self.assertRaises(ValueError,msg=fault):verified_source(entry,stamp)

    def test_completed_output_receipt_revalidation_and_interrupted_or_corrupt_output(self):
        cfg={'schema_version':'1.0','cohort':'pilot','expected_rows':3,'final_test_cohort':'unassigned',
             'participants':[{'id':'s999','role':'pilot_development','summary':'synthetic'}]}
        def recording(entry,task,*args):
            i=int(task[1:])-1
            return [self.rows[i]],self.refs[i],self.schedules[i]
        with patch('stress_detection.features.verified_source',return_value=({}, {}, Path('unused'),{},{})), \
             patch('stress_detection.features.recording_rows',side_effect=recording):
            # Records are still explicitly keyed by task even in the synthetic source.
            with patch('stress_detection.features.verified_source',return_value=({}, {t:{} for t in ('T1','T2','T3')},Path('unused'),{},{})):
                out=self.root/'run';run(cfg,out)
                self.assertEqual(validate_run(out)['rows'],3)
                before=inventory(out)
                with self.assertRaises(FileExistsError):run(cfg,out)
                self.assertEqual(inventory(out),before)
        receipt=read(out/'receipt.json')
        for field in ('code','software','selection'):
            bad=copy.deepcopy(receipt)
            if field=='code':bad['code']['face_measurements.py']='0'*64
            elif field=='software':bad['software']['numpy']='different'
            else:bad['selection']['cohort']='development'
            atomic(out/'receipt.json',bad)
            with self.assertRaises(ValueError):validate_run(out)
        receipt['status']='running';atomic(out/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'Incomplete'):validate_run(out)
        receipt['status']='completed';atomic(out/'receipt.json',receipt)
        (out/'rest-vs-speech/X.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_run(out)
        with patch('stress_detection.features.verified_source',side_effect=ValueError('synthetic provenance failure')):
            failed=self.root/'failed'
            with self.assertRaises(ValueError):run(cfg,failed)
            self.assertEqual(read(failed/'receipt.json')['status'],'failed')
            self.assertFalse((failed/'validation.json').exists())
