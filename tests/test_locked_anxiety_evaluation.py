"""Outcome release gate, documented endpoints, saved-prediction metrics and preservation."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluate_locked_anxiety as evaluation
from stress_detection import independent_anxiety as study
from stress_detection import final_camera_features as camera
from stress_detection import session_anxiety_regression as regression
from stress_detection.features import read_jsonl, write_jsonl
from stress_detection.manifest import fingerprint
from stress_detection.pilot_state import atomic, digest, inventory, read
import test_independent_anxiety as fixtures

ROOT = Path(__file__).resolve().parents[1]


class EvaluationUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'data/processed'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = study.load_config()
        self.plan = {'locked_final': [f's{i}' for i in range(101, 111)], 'training_participants': [f's{i}' for i in range(1, 7)]}

    def predictions(self):
        return [{'participant': p, 'role': 'locked_final', 'session_key': p + '/session-1',
                 'target': t, 'model': m, 'prediction': 0. if m == 'facial' else 2.,
                 'configuration_id': digest(self.cfg), 'training_participants': self.plan['training_participants'],
                 'support': {'requested': len(cols), 'observed': len(cols), 'missing': 0,
                             'fully_observed': True, 'training_empty_columns': []}}
                for t in self.cfg['targets'] for m, cols in self.cfg['models'].items() for p in self.plan['locked_final']]

    def outcomes(self):
        path = self.root / 'scores.csv'; path.write_text('1,2\n3,4\n2,1\n')
        return [evaluation.outcome(path, p) for p in self.plan['locked_final']]

    def test_post_dimensions_range_and_no_reconstruction(self):
        rows = self.outcomes(); row = rows[0]
        self.assertEqual(row['targets'], {'cognitive_post': 2., 'somatic_post': 4.})
        self.assertEqual(row['dimensions']['self_confidence']['post_session'], 1.)
        path = self.root / 'bad.csv'; path.write_text('1,nan\n3,2.5\n2,4.1\n')
        bad = evaluation.outcome(path, 's101')
        self.assertIsNone(bad['targets']['cognitive_post']); self.assertEqual(bad['targets']['somatic_post'], 2.5)
        self.assertIsNone(bad['dimensions']['self_confidence']['post_session'])
        path.write_text('1,2,3\n2,3,4\n'); self.assertTrue(all(v is None for v in evaluation.outcome(path, 's101')['targets'].values()))
        path.write_text('pre,post\n1,2\n3,4\n')
        self.assertTrue(all(v is None for v in evaluation.outcome(path, 's101')['targets'].values()))
        path.write_text('1,2.123456789\n1,3\n2,3\n')
        self.assertEqual(evaluation.outcome(path, 's101')['targets']['cognitive_post'], 2.123456789)

    def test_inventory_participant_separation_missing_labels_and_no_clipping(self):
        outcomes = self.outcomes(); outcomes[0]['targets']['cognitive_post'] = None
        rows = evaluation.join_predictions(self.predictions(), outcomes, self.cfg, self.plan)
        self.assertEqual(len(rows), 120)
        summary = evaluation.summarize(rows, self.cfg)
        self.assertEqual(summary['cognitive_post']['facial']['n'], 9)
        self.assertEqual(summary['somatic_post']['facial']['n'], 10)
        self.assertEqual(summary['cognitive_post']['facial']['unscorable'], 1)
        self.assertEqual(next(r for r in rows if r['model'] == 'facial')['prediction'], 0.)
        for fault in ['duplicate', 'missing', 'role', 'session', 'training']:
            bad = copy.deepcopy(outcomes)
            if fault == 'duplicate': bad[-1] = bad[0]
            if fault == 'missing': bad.pop()
            if fault == 'role': bad[0]['role'] = 'development_only'
            if fault == 'session': bad[0]['session_key'] = 's999/session-1'
            if fault == 'training': bad[0]['participant'] = 's1'
            with self.subTest(fault=fault), self.assertRaises(ValueError): evaluation.join_predictions(self.predictions(), bad, self.cfg, self.plan)
        for bad in [self.predictions()[:-1], self.predictions() + self.predictions()[:1]]:
            with self.assertRaises(ValueError): evaluation.join_predictions(bad, outcomes, self.cfg, self.plan)

    def test_metrics_paired_sign_undefined_r2_and_matched_subset(self):
        outcomes = self.outcomes(); rows = evaluation.join_predictions(self.predictions(), outcomes, self.cfg, self.plan)
        summary = evaluation.summarize(rows, self.cfg)
        self.assertEqual(summary['cognitive_post']['mean']['mae'], 0.)
        self.assertEqual(summary['cognitive_post']['facial']['mae'], 2.)
        self.assertEqual(summary['cognitive_post']['facial']['mean_paired_absolute_error_difference'], 2.)
        self.assertIsNone(summary['cognitive_post']['facial']['r2'])
        self.assertEqual(summary['cognitive_post']['facial']['worse_than_mean'], 10)
        m = regression.metrics([{'truth': 1., 'prediction': 0.}, {'truth': 3., 'prediction': 4.}])
        self.assertEqual((m['mae'], m['rmse'], m['r2']), (1., 1., 0.))
        self.assertIsNone(regression.metrics([])['r2'])
        for r in rows:
            if r['model'] == 'facial' and r['participant'] == 's101': r['support']['fully_observed'] = False
        secondary = evaluation.summarize(rows, self.cfg)['cognitive_post']['facial']['secondary_aggregate_complete_inputs']
        self.assertEqual(secondary['n'], 9); self.assertEqual(secondary['matched_training_mean']['n'], 9)
        self.assertEqual(secondary['matched_training_mean']['mae'], 0.)

    def test_failed_gate_never_invokes_release_or_opens_questionnaires(self):
        def denied(file, *args, **kwargs):
            if not isinstance(file, int) and ('selfReportedAnx' in str(file) or 'sealed-outcomes' in str(file)):
                raise AssertionError('Questionnaire accessed before verification')
            return original(file, *args, **kwargs)
        original = io.open
        with patch.object(evaluation, 'verify_lock', side_effect=ValueError('lock failed')), patch.object(evaluation, 'release_outcomes') as release, patch('io.open', side_effect=denied):
            with self.assertRaisesRegex(ValueError, 'lock failed'):
                evaluation.execute(self.root / 'plan.json', self.root / 'lock', self.root / 'evaluation')
            release.assert_not_called()
        self.assertEqual(read(self.root / 'evaluation/receipt.json')['status'], 'failed')


class EvaluationIntegrationTests(unittest.TestCase):
    def test_synthetic_lock_release_evaluation_revalidation_and_tamper_guards(self):
        fixture = fixtures.IndependentTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        models, _ = fixture.models(); selection, entries = fixture.camera_selection()
        exported = fixture.root / 'export'; camera.export(fixture.plan_path, selection, models, exported)
        prediction_run = fixture.root / 'predictions'; validation = study.predict_batches(fixture.plan_path, models, [exported], prediction_run)
        sealed = fixture.root / 'sealed-outcomes'; sealed.mkdir()
        for i, entry in enumerate(entries):
            p = entry['id']; raw = Path(entry['input_root']) / p
            source = raw / f'selfReportedAnx_{p}.csv'; source.write_text(f'1,{2+i/10}\n2,{3-i/10}\n1,4\n')
            proof = fingerprint(source, source.name); source.rename(sealed / source.name)
            atomic(fixture.root / f'{p}-transport.json', {'sealed_questionnaire': proof})
        lock = fixture.root / 'lock'; lock.mkdir()
        atomic(lock / 'configuration.json', fixture.cfg); write_jsonl(lock / 'scheduled-windows.jsonl', read_jsonl(exported / 'windows.jsonl'))
        model_sha = digest(read(models / 'receipt.json')['output_files']); pred_sha = study.artifact_inventory(prediction_run)['predictions.jsonl']['sha256']
        receipt = {**study.context(fixture.cfg, fixture.plan), 'kind': 'pre_outcome_prediction_lock', 'status': 'completed',
                   'questionnaire_values_read': False, 'questionnaires_released': False, 'outcomes_evaluated': False,
                   'scheduled_windows': 180, 'scheduled_recordings': 30, 'prediction_run': str(prediction_run),
                   'prediction_artifacts': study.artifact_inventory(prediction_run), 'model_artifacts': study.artifact_inventory(models),
                   'models_inventory_sha256': model_sha, 'validation': validation}
        atomic(lock / 'receipt.json', receipt); atomic(lock / 'hashes.json', study.artifact_inventory(lock))
        before = {str(p): inventory(p) for p in [models, prediction_run, lock, sealed]}
        out = fixture.root / 'evaluation'
        with patch.object(evaluation, 'MODEL_SHA', model_sha), patch.object(evaluation, 'PREDICTION_SHA', pred_sha), patch.object(regression, 'fit_fold', side_effect=AssertionError('Refitting forbidden')), patch('sklearn.linear_model.Ridge.fit', side_effect=AssertionError('Refitting forbidden')):
            result = evaluation.execute(fixture.plan_path, lock, out)
            self.assertEqual(result['predictions'], 120); self.assertEqual(result['scorable'], {'cognitive_post': 10, 'somatic_post': 10})
            self.assertFalse(result['refitted']); self.assertEqual(evaluation.validate(out), result)
            self.assertTrue(all((out / n).is_file() for n in ['aggregate-errors.png', 'paired-errors.png', 'observed-vs-predicted.png']))
            self.assertEqual(before, {str(p): inventory(p) for p in [models, prediction_run, lock, sealed]})
            with self.assertRaises(FileExistsError): evaluation.execute(fixture.plan_path, lock, out)
            # A partial-cohort claim cannot authorize release, even with updated local lock hashes.
            original_receipt = (lock / 'receipt.json').read_bytes(); original_hashes = (lock / 'hashes.json').read_bytes()
            changed = read(lock / 'receipt.json'); changed['validation']['predictions'] = 119
            atomic(lock / 'receipt.json', changed)
            changed_files = study.artifact_inventory(lock); changed_files.pop('hashes.json')
            atomic(lock / 'hashes.json', changed_files)
            with patch.object(evaluation, 'release_outcomes') as release, self.assertRaisesRegex(ValueError, '120-prediction'):
                evaluation.execute(fixture.plan_path, lock, fixture.root / 'partial-evaluation')
            release.assert_not_called()
            (lock / 'receipt.json').write_bytes(original_receipt); (lock / 'hashes.json').write_bytes(original_hashes)
            # A prediction hash failure blocks release of a second outcome copy.
            predfile = prediction_run / 'predictions.jsonl'; original = predfile.read_bytes()
            rows = read_jsonl(predfile); rows[0]['prediction'] += .01
            predfile.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            with patch.object(evaluation, 'release_outcomes') as release, self.assertRaisesRegex(ValueError, 'hash mismatch'):
                evaluation.execute(fixture.plan_path, lock, fixture.root / 'blocked-evaluation')
            release.assert_not_called()
            predfile.write_bytes(original)
            (out / 'released/s101/selfReportedAnx_s101.csv').write_text('1,4\n2,3\n1,4\n')
            with self.assertRaisesRegex(ValueError, 'changed evaluation output'): evaluation.validate(out)
