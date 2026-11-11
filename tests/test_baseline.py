"""Synthetic LOPO leakage, preprocessing, provenance and prediction inventories."""

import copy
import json
from pathlib import Path
import platform
import subprocess
import sys

import joblib
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection.baseline import (FoldPreprocessor, METRICS, code_hashes, execute,
    feature_support, fit_fold, folds, load_config, load_features, matrix, metrics,
    prediction_inventory, prepare, probabilities, report_from_predictions,
    validate_allowlists, validate_run)
from stress_detection.features import (read_jsonl, schema, validate_rows, write_tables)
from stress_detection.pilot_state import atomic, digest, inventory, read
from stress_detection.policy import load_policy
from test_features import example_rows

ROOT=Path(__file__).resolve().parents[1]


def synthetic_feature_run(folder):
    folder.mkdir()
    templates,_,_=example_rows();rows=[];references=[];schedules=[]
    for person in range(1,7):
        p=f's{person}'
        for template in templates:
            task=template['id_task']
            for i in range(6):
                row=copy.deepcopy(template)
                row.update(id_participant=p,id_role='pilot_development',id_recording=p+'/'+task,
                    id_window_key=f'{p}/{task}/{i}',id_window_index=i,id_origin_fraction='0',
                    id_start_seconds=30*i,id_end_seconds=30*(i+1))
                row['beh_mouth_mean']+=1000 if person==6 else person*.01+i*.001
                if person!=6:
                    row.update(cam_green_forehead_bpm=None,cam_green_forehead_status='rejected',
                        cam_green_forehead_reason='long_gap',q_pulse_green_forehead_missing=1,
                        q_pulse_green_forehead_peak_fraction=None,q_pulse_green_forehead_near_edge=None)
                rows.append(row)
            schedules.append({'recording':p+'/'+task,'origin_fraction':'0','complete_windows':6})
            references.append({'ref_participant':p,'ref_task':task,'ref_time_basis':'independent nominal',
                               'ref_wrist':{'median_bpm':999999},'ref_eda_metadata':{'rows':720,'sampling_rate_hz':4,'nominal_duration_seconds':180}})
    cfg={'schema_version':'1.0','cohort':'pilot','expected_rows':108,'final_test_cohort':'unassigned',
        'participants':[{'id':f's{i}','role':'pilot_development','summary':'synthetic'} for i in range(1,7)]}
    validate_rows(rows,108,{p['id']:p['role'] for p in cfg['participants']},schedules)
    write_tables(folder,rows,references)
    atomic(folder/'validation.json',{'status':'passed','rows':108,'schedules':schedules})
    receipt={'status':'completed','policy':load_policy()[1],'feature_schema_sha256':digest(schema()),
        'code':code_hashes(),'software':{'numpy':np.__version__,'python':platform.python_version()},
        'selection':cfg,'output_files':inventory(folder)}
    atomic(folder/'receipt.json',receipt)


class FoldLocalTests(unittest.TestCase):
    def test_imputation_and_scaling_see_training_only_no_indicators(self):
        train=np.array([[1.,np.nan,7.],[3.,np.nan,7.],[np.nan,np.nan,7.]])
        pre=FoldPreprocessor().fit(train)
        np.testing.assert_array_equal(pre.keep_,[True,False,True])
        np.testing.assert_allclose(pre.imputer_.statistics_,[2,7])
        np.testing.assert_allclose(pre.scaler_.mean_,[2,7])
        np.testing.assert_allclose(pre.scaler_.var_,[2/3,0])
        before=copy.deepcopy(pre.snapshot(['a','b','c']))
        held=np.array([[1000000.,12345.,7.],[np.nan,99999.,7.]])
        result=pre.transform(held)
        self.assertEqual(result.shape,(2,2))
        self.assertEqual(pre.snapshot(['a','b','c']),before)
        self.assertEqual(result[1,0],0)
        self.assertFalse(pre.imputer_.add_indicator)
        np.testing.assert_array_equal(pre.transform(np.array([[3.,1.,7.]])),pre.transform(np.array([[3.,999.,7.]])))

    def test_all_missing_training_features_use_logged_prior_even_if_test_observed(self):
        cfg=load_config();columns=['a','b']
        model=fit_fold(np.full((4,2),np.nan),np.array([0,1,0,1]),columns,cfg)
        self.assertTrue(model['fallback'])
        np.testing.assert_array_equal(probabilities(model,np.array([[999.,1.],[np.nan,3.]])),[.5,.5])
        support=feature_support({**{c:1. for c in schema()['model_columns']},'a':9.,'b':10.},columns,columns)
        self.assertTrue(support['raw_fully_observed']);self.assertFalse(support['supported'])
        self.assertEqual(model['preprocessor'].snapshot(columns)['training_all_missing_columns'],columns)
        self.assertFalse(bool(.5>cfg['decision_threshold']))

    def test_forbidden_metadata_reference_and_missing_flags_are_not_value_inputs(self):
        cfg=load_config();validate_allowlists(cfg)
        for forbidden in ('id_participant','id_task','id_start_seconds','id_manifest','label_condition',
                          'recording_order','ref_wrist','questionnaire','q_pulse_green_forehead_missing'):
            bad=copy.deepcopy(cfg);bad['models']['facial'].append(forbidden)
            with self.assertRaises(ValueError):validate_allowlists(bad)
        self.assertFalse(set(cfg['models']['quality_values'])&set(cfg['models']['missingness']))

    def test_undefined_supported_metrics_are_null_not_zero(self):
        result=metrics([])
        self.assertEqual(result['n'],0)
        self.assertTrue(all(result[m] is None for m in METRICS))
        single=metrics([{'truth':0,'prediction':1,'probability_active':.8}])
        self.assertIsNone(single['balanced_accuracy']);self.assertIsNone(single['macro_f1'])
        self.assertIsNone(single['active_recall']);self.assertEqual(single['rest_false_positive_rate'],1)
        self.assertAlmostEqual(single['brier'],.64)
        both=metrics([{'truth':0,'prediction':0,'probability_active':.1},
                      {'truth':1,'prediction':1,'probability_active':.9}])
        self.assertEqual(both['balanced_accuracy'],1);self.assertEqual(both['macro_f1'],1)
        self.assertAlmostEqual(both['brier'],.01)


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.features=self.root/'features'
        synthetic_feature_run(self.features);self.cfg=load_config()
        self.data,self.inputs=load_features(self.features,self.cfg)

    def fake_predictions(self):
        predictions=[]
        for contrast,d in self.data.items():
            for name,columns in self.cfg['models'].items():
                for meta,row in zip(d['index'],d['x']):
                    p=meta['id_participant']
                    predictions.append({'contrast':contrast,'model':name,'window_key':meta['id_window_key'],
                        'participant':p,'fold_id':'held-out-'+p,'configuration_id':digest(self.cfg),
                        'training_participants':sorted(set(self.cfg['participants'])-{p}),
                        'truth':meta['target'],'condition':meta['label_condition'],'probability_active':.5,'prediction':0,
                        'support':feature_support(row,columns,[])})
        return predictions

    def test_all_six_folds_have_disjoint_people_and_every_class_row(self):
        for d in self.data.values():
            fs=folds(d['index'],self.cfg);self.assertEqual(len(fs),6)
            self.assertEqual(sorted(i for f in fs for i in f['test']),list(range(72)))
            for f in fs:
                self.assertEqual(len(f['train']),60);self.assertEqual(len(f['test']),12)
                self.assertFalse(set(f['training_participants'])&set(f['evaluation_participants']))
            bad=copy.deepcopy(d['index']);bad[0]['id_participant']='s25'
            with self.assertRaises(ValueError):folds(bad,self.cfg)
            bad=copy.deepcopy(d['index']);bad[1]['id_window_key']=bad[0]['id_window_key']
            with self.assertRaises(ValueError):folds(bad,self.cfg)

    def test_saved_source_hashes_roles_and_development_exclusion(self):
        path=self.features/'receipt.json';receipt=read(path)
        for fault in ('role','development','code'):
            bad=copy.deepcopy(receipt)
            if fault=='role':bad['selection']['participants'][0]['role']='final_test'
            elif fault=='development':bad['selection']['cohort']='development'
            else:bad['code']['features.py']='0'*64
            atomic(path,bad)
            with self.assertRaises(ValueError):load_features(self.features,self.cfg)
        atomic(path,receipt)
        (self.features/'rest-vs-speech/X.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):load_features(self.features,self.cfg)

    def test_inventory_rejects_missing_duplicate_leaked_or_wrong_predictions(self):
        rows=self.fake_predictions();prediction_inventory(rows,self.data,self.cfg,digest(self.cfg))
        for fault in ('missing','duplicate','participant','training_overlap','probability','truth','threshold','support'):
            bad=copy.deepcopy(rows)
            if fault=='missing':bad.pop()
            elif fault=='duplicate':bad.append(copy.deepcopy(bad[0]))
            elif fault=='participant':bad[0]['participant']='s25'
            elif fault=='training_overlap':bad[0]['training_participants'][0]=bad[0]['participant']
            elif fault=='probability':bad[0]['probability_active']=float('nan')
            elif fault=='truth':bad[0]['truth']=1-bad[0]['truth']
            elif fault=='threshold':bad[0]['prediction']=1
            else:bad[0]['support']['observed_count']=999
            with self.assertRaises(ValueError,msg=fault):prediction_inventory(bad,self.data,self.cfg,digest(self.cfg))
        report=report_from_predictions(rows,self.cfg)
        m=report['contrasts']['rest-vs-speech']['dummy']['all']
        self.assertEqual(m['pooled']['accuracy'],.5)
        self.assertEqual(m['participant_macro']['accuracy']['participants_defined'],6)
        self.assertEqual(m['pooled']['confusion_matrix'],[[36,0],[36,0]])

    def test_prepare_does_not_fit_and_tampered_plan_cannot_execute(self):
        out=self.root/'prepared'
        with patch('stress_detection.baseline.fit_fold',side_effect=AssertionError('fit during preparation')):
            plan=prepare(self.features,out)
        self.assertEqual(read(out/'status.json')['status'],'prepared')
        self.assertFalse((out/'predictions.jsonl').exists())
        self.assertIn('git_revision',plan);self.assertEqual(plan['configuration_id'],digest(self.cfg))
        bad=read(out/'plan.json');bad['folds']['rest-vs-speech'][0]['training_participants']=['s1']
        atomic(out/'plan.json',bad)
        with self.assertRaisesRegex(ValueError,'snapshot changed'):execute(out)

    def test_end_to_end_all_predictions_fold_models_and_training_statistics(self):
        out=self.root/'run';prepare(self.features,out)
        with patch('stress_detection.baseline.render_report'):
            execute(out)
        validation=validate_run(out)
        self.assertEqual(validation['predictions'],864);self.assertEqual(validation['fold_models'],72)
        self.assertFalse(validation['participant_leakage'])
        rows=read_jsonl(out/'predictions.jsonl')
        self.assertTrue(all(p['support']['supported'] for p in rows if p['model']=='dummy'))
        state=read(out/'models/rest-vs-speech/facial/s6/fit.json')
        self.assertLess(state['scaler_mean'][0],10)  # Held-out participant's 1000-unit outlier not fitted.
        pulse=read(out/'models/rest-vs-speech/camera_bpm/s6/fit.json')
        self.assertEqual(pulse['training_all_missing_columns'],['cam_green_forehead_bpm'])
        self.assertTrue(all(not p['support']['supported'] for p in rows if p['model']=='camera_bpm' and p['participant']=='s6'))
        before=inventory(out)
        with self.assertRaises(ValueError):execute(out)
        self.assertEqual(inventory(out),before)
        (out/'predictions.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_run(out)

    def test_cli_models_reload_from_imported_api_without_main_alias(self):
        out=self.root/'cli-run'
        base=[sys.executable,'-m','stress_detection.baseline','--output',str(out)]
        subprocess.run([*base,'--prepare','--feature-run',str(self.features)],cwd=ROOT,check=True,capture_output=True,text=True)
        subprocess.run([*base,'--execute'],cwd=ROOT,check=True,capture_output=True,text=True)
        model=joblib.load(out/'models/rest-vs-speech/facial/s1/model.joblib')
        self.assertEqual(type(model['preprocessor']).__module__,'stress_detection.baseline_preprocessing')
        self.assertEqual(validate_run(out)['predictions'],864)
