"""Released-score alignment, participant separation and fold-local regression."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection import session_anxiety_audit as audit
from stress_detection import session_anxiety_regression as reg
from stress_detection.features import read_jsonl
from stress_detection.pilot_state import atomic, inventory, read
from test_baseline import synthetic_feature_run

ROOT=Path(__file__).resolve().parents[1]


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cfg=reg.load_config()

    def source(self):
        features=self.root/'features';synthetic_feature_run(features)
        entries=[]
        for i in range(1,7):
            p=f's{i}';folder=self.root/p;folder.mkdir()
            (folder/f'info_{p}.txt').write_text(f'{p}\nf\nctrl\n2020-01-01\n12-00-00\n')
            (folder/f'selfReportedAnx_{p}.csv').write_text(f'4,{round(2+i/7,3)}\n3,{round(1+i/7,3)}\n2,3\n')
            entries.append({'id':p,'role':'development_only','directory':str(folder)})
        selection=self.root/'selection.json';atomic(selection,{'version':'session-audit-selection-v1','participants':entries})
        out=self.root/'audit';audit.audit(features,selection,out)
        return out

    def test_mean_and_fold_local_drop_imputation_without_held_out_statistics(self):
        x=np.array([[1.,np.nan],[3.,np.nan],[np.nan,np.nan]])
        model=reg.fit_fold(x,np.array([1.,2.,3.]),['a','b'],self.cfg)
        before=copy.deepcopy(model['preprocessor'].snapshot(['a','b']))
        self.assertEqual(before['median'],[2.]);self.assertEqual(before['training_all_missing_columns'],['b'])
        reg.predict(model,np.array([[99999.,9.],[np.nan,8.]]))
        self.assertEqual(before,model['preprocessor'].snapshot(['a','b']))
        fallback=reg.fit_fold(np.full((3,2),np.nan),np.array([1.,2.,3.]),['a','b'],self.cfg)
        self.assertTrue(fallback['fallback']);self.assertEqual(reg.predict(fallback,np.array([[99.,9.]]))[0],2.)
        mean=reg.fit_fold(np.empty((3,0)),np.array([1.,2.,3.]),[],self.cfg)
        self.assertEqual(reg.predict(mean,np.empty((1,0)))[0],2.)
        with self.assertRaises(ValueError):reg.fit_fold(x,np.array([1.,np.nan,3.]),['a','b'],self.cfg)

    def test_metrics_defined_only_at_appropriate_unit(self):
        one=reg.metrics([{'truth':2.,'prediction':3.}])
        self.assertEqual(one['mae'],1.);self.assertIsNone(one['r2'])
        self.assertIsNone(reg.metrics([{'truth':2.,'prediction':3.}]*3)['r2'])
        self.assertEqual(reg.metrics([{'truth':1.,'prediction':1.},{'truth':3.,'prediction':3.}])['r2'],1.)
        self.assertLess(reg.metrics([{'truth':1.,'prediction':4.},{'truth':3.,'prediction':0.}])['r2'],0)

    def test_frozen_allowlists_and_target_mapping_no_prescore_or_category(self):
        self.assertEqual(self.cfg['targets']['cognitive_post'],{'dimension':'cognitive_anxiety','occasion':'post_session','priority':'primary'})
        self.assertFalse(self.cfg['classification']['available'])
        for cols in self.cfg['models'].values():
            self.assertFalse(any(c.startswith(('id_','label_','ref_')) or 'anxiety' in c for c in cols))
        bad=copy.deepcopy(self.cfg);bad['models']['facial'].append('cognitive_pre')
        path=self.root/'bad.json';atomic(path,bad)
        with patch.object(reg,'CONFIG',path),self.assertRaises(ValueError):reg.load_config()

    def test_end_to_end_exact_inventory_source_preservation_and_reloaded_models(self):
        source=self.source();before=inventory(source);out=self.root/'regression'
        plan=reg.prepare(source,out)
        self.assertFalse((out/'models').exists())
        self.assertEqual(plan['configuration']['regression']['alpha'],10.)
        with patch.object(reg,'render'):checks=reg.execute(out)
        self.assertEqual(checks['predictions'],72);self.assertEqual(checks['fold_models'],72)
        self.assertEqual(inventory(source),before)
        self.assertEqual(reg.validate(out),checks)
        index,x,ys,_=reg.load_sessions(source,self.cfg)
        self.assertEqual(ys['cognitive_post'][0],2.143)
        self.assertEqual(ys['somatic_post'][0],1.143)
        preds=read_jsonl(out/'predictions.jsonl');reg.validate_inventory(preds,index,ys,self.cfg)
        for p in preds:
            self.assertNotIn(p['participant'],p['training_participants'])
            self.assertEqual(len(p['training_participants']),5)
            if p['model']=='mean':
                i=self.cfg['participants'].index(p['participant'])
                self.assertEqual(p['prediction'],float(np.mean(np.delete(ys[p['target']],i))))
        for name,mutate in [('duplicate',lambda rows:rows[:-1]+[rows[0]]),('missing',lambda rows:rows[:-1]),
                             ('leak',lambda rows:[{**rows[0],'training_participants':['s1']*5}]+rows[1:]),
                             ('wrong_y',lambda rows:[{**rows[0],'truth':4.0}]+rows[1:])]:
            with self.subTest(name=name),self.assertRaises(ValueError):reg.validate_inventory(mutate(copy.deepcopy(preds)),index,ys,self.cfg)
        with self.assertRaises(ValueError):reg.execute(out)
        (out/'predictions.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'hashes changed'):reg.validate(out)

    def test_source_mutation_and_changed_plan_refused_before_fit(self):
        source=self.source();out=self.root/'regression';reg.prepare(source,out)
        plan=read(out/'plan.json');plan['folds'][0]['test']=[1];atomic(out/'plan.json',plan)
        with self.assertRaises(ValueError):reg.execute(out)
        self.assertFalse((out/'models').exists())
        (source/'outcomes.jsonl').write_text('{}\n')
        with self.assertRaises(ValueError):reg.load_sessions(source,self.cfg)
