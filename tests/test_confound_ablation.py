"""Synthetic shared-mask, preservation, fold-local and frozen-model checks."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection import baseline as base
from stress_detection import confound_ablation as ca
from stress_detection.features import read_jsonl
from stress_detection.pilot_state import atomic, digest, inventory, read
from test_baseline import synthetic_feature_run

ROOT=Path(__file__).resolve().parents[1]


class MaskDesignTests(unittest.TestCase):
    def test_frozen_ablations_remove_exact_families_and_preserve_settings(self):
        cfg,original=ca.load_config();models=cfg['ablation_models']
        self.assertEqual(models,ca.expected_ablations(original))
        self.assertEqual(len(models['facial_no_mouth']),5)
        self.assertEqual(len(models['facial_no_motion']),6)
        self.assertEqual(models['facial_no_mouth_no_motion'],['beh_eye_mean','beh_eye_std','beh_eye_p10'])
        self.assertEqual(cfg['logistic_regression'],original['logistic_regression'])
        self.assertEqual(cfg['preprocessing'],original['preprocessing'])
        for name,columns in models.items():
            self.assertFalse(any(c.startswith(('id_','ref_','label_')) for c in columns))
            if name.endswith('plus_bpm'):self.assertEqual(columns[-6:],original['models']['camera_bpm'])
        self.assertEqual(len(cfg['masking']['columns']),41)

    def test_rng_uses_only_shape_seed_is_reproducible_and_nested(self):
        a=ca.scores(9,4,123);b=ca.scores(9,4,123)
        np.testing.assert_array_equal(a,b)
        self.assertFalse(np.array_equal(a,ca.scores(9,4,124)))
        self.assertTrue(np.isfinite(a).all());self.assertTrue(((a>=0)&(a<1)).all())
        small=a<.1;large=a<.5
        self.assertTrue(np.all(~small|large))
        import inspect
        self.assertEqual(list(inspect.signature(ca.scores).parameters),['n_rows','n_columns','seed'])

    def test_only_observed_values_masked_natural_null_and_zero_preserved_correctly(self):
        row={'a':None,'b':0.,'c':12.,'participant':'s1','label':0};before=copy.deepcopy(row)
        columns=['a','b','c'];draws=[0.,.05,.7]
        self.assertEqual(ca.mask_row(row,draws,columns,0),row)
        masked=ca.mask_row(row,draws,columns,.1)
        self.assertIsNone(masked['a']);self.assertIsNone(masked['b']);self.assertEqual(masked['c'],12.)
        self.assertEqual(row,before)
        changed={**row,'participant':'different','label':1}
        other=ca.mask_row(changed,draws,columns,.1)
        self.assertEqual([masked[c] for c in columns],[other[c] for c in columns])
        records=ca.mask_records([{'id_window_key':'r',**row}],np.array([draws]),columns,[0.,.1,.8])
        self.assertEqual(records[1]['natural_missing_columns'],['a'])
        self.assertEqual(records[1]['added_missing_columns'],['b'])
        self.assertEqual(records[2]['added_missing_columns'],['b','c'])
        self.assertEqual(records[1]['eligible_count'],2)

    def test_shared_rest_mask_across_contrasts_and_feature_subsets(self):
        rest={'a':1.,'b':2.};speech={'a':3.,'b':4.};arithmetic={'a':5.,'b':6.}
        data={'speech':{'x':[rest,speech],'index':[{'id_window_key':'r'},{'id_window_key':'s'}]},
              'arithmetic':{'x':[rest,arithmetic],'index':[{'id_window_key':'r'},{'id_window_key':'a'}]}}
        draws=np.array([[.05,.8],[.8,.05],[.1,.2]])
        result=ca.masked_data(data,['r','s','a'],draws,['a','b'],.3)
        self.assertEqual(result['speech']['x'][0],result['arithmetic']['x'][0])
        self.assertTrue(np.isnan(base.matrix(result['speech']['x'],['a'])[0,0]))
        np.testing.assert_array_equal(base.matrix(result['speech']['x'],['b','a'])[:,1],base.matrix(result['speech']['x'],['a'])[:,0])
        self.assertEqual(rest,{'a':1.,'b':2.})

    def test_empty_set_is_unavailable_and_never_fit(self):
        self.assertFalse(ca.availability({'empty':[]})['empty']['available'])
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed') as tmp:
            cfg,original=ca.load_config();cfg['ablation_models']={'empty':[]}
            with patch.object(base,'fit_fold',side_effect=AssertionError('empty set fitted')):
                result=ca.fit_ablations(Path(tmp),{'configuration_id':'synthetic'},cfg,original,{})
            self.assertEqual(result['fold_models'],0)
            self.assertEqual(read_jsonl(Path(tmp)/'predictions.jsonl'),[])

    def test_modified_design_and_forbidden_allowlists_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed') as tmp:
            path=Path(tmp)/'config.json';cfg,_=ca.load_config()
            for fault in ('columns','seed','settings'):
                bad=copy.deepcopy(cfg)
                if fault=='columns':bad['ablation_models']['facial_no_mouth'].append('id_participant')
                elif fault=='seed':bad['masking']['seed']+=1
                else:bad['logistic_regression']['C']=100
                atomic(path,bad)
                with patch.object(ca,'CONFIG',path):
                    with self.assertRaises(ValueError):ca.load_config()


class EndToEndStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.feature_run=self.root/'features'
        synthetic_feature_run(self.feature_run)
        self.baseline=self.root/'baseline';base.prepare(self.feature_run,self.baseline)
        with patch.object(base,'render_report'):base.execute(self.baseline)

    def test_prepare_preserves_baseline_and_changed_plan_refused(self):
        before=inventory(self.baseline);out=self.root/'study'
        with patch.object(base,'fit_fold',side_effect=AssertionError('fit during freeze')):
            plan=ca.prepare(self.baseline,out)
        self.assertEqual(inventory(self.baseline),before)
        self.assertEqual(plan['folds'],read(self.baseline/'plan.json')['folds'])
        self.assertFalse((out/'models').exists())
        plan['ordered_window_keys'].reverse();atomic(out/'plan.json',plan)
        with self.assertRaises(ValueError):ca.execute(out)

    def test_all_predictions_shared_masks_no_refitting_and_preserved_inputs(self):
        before=inventory(self.baseline);features=inventory(self.feature_run)
        out=self.root/'study';ca.prepare(self.baseline,out)
        real_fit=base.fit_fold
        with patch.object(base,'fit_fold',wraps=real_fit) as fits,patch.object(ca,'render_report'):
            result=ca.execute(out)
        self.assertEqual(fits.call_count,72)  # Six new ablations only, never per mask level/baseline.
        self.assertEqual(result['clean_ablation_predictions'],864)
        self.assertEqual(result['stress_predictions'],6912)
        self.assertEqual(result['mask_shape'],[108,41]);self.assertEqual(result['mask_rows'],432)
        self.assertEqual(inventory(self.baseline),before);self.assertEqual(inventory(self.feature_run),features)
        self.assertEqual(ca.validate(out)['status'],'passed')
        stress=read_jsonl(out/'stress-predictions.jsonl')
        for level in (0.,.1,.3,.5):
            selected=[r for r in stress if r['mask_level']==level]
            self.assertEqual(len(selected),1728)
            self.assertTrue(all(r['participant'] not in r['training_participants'] for r in selected))
        dummy=[r for r in stress if r['model']=='dummy']
        self.assertTrue(all(r['probability_active']==.5 for r in dummy))
        for r in stress:
            if r['mask_level']==0:self.assertEqual(r['added_missing_count'],0)
            self.assertGreaterEqual(r['support']['missing_count'],r['natural_support']['missing_count'])
        with self.assertRaises(ValueError):ca.execute(out)
        # Completed artifacts cannot silently validate after a mask mutation.
        (out/'masks.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'outputs changed'):ca.validate(out)

    def test_tampered_saved_baseline_is_not_reused(self):
        (self.baseline/'predictions.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'hashes changed'):ca.prepare(self.baseline,self.root/'study')
        self.assertFalse((self.root/'study').exists())
