"""Session identity, scoring gates, raw aggregation and no-fit inventory checks."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from stress_detection import baseline as base
from stress_detection import session_anxiety_audit as audit
from stress_detection.features import read_jsonl, write_jsonl
from stress_detection.pilot_state import atomic, inventory, read
from test_baseline import synthetic_feature_run

ROOT = Path(__file__).resolve().parents[1]


class SessionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'data/processed')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = audit.load_config()
        entries = []
        for i in range(1, 7):
            participant = f's{i}'
            folder = self.root/participant; folder.mkdir()
            (folder/f'info_{participant}.txt').write_text(f'{participant}\nf\ntest\n2020-01-01\n12-00-00\n')
            (folder/f'selfReportedAnx_{participant}.csv').write_text(f'2,{round(3+i/7, 3)}\n1,2\n3,1\n')
            entries.append({'id': participant, 'directory': str(folder), 'role': 'development_only'})
        self.selection = self.root/'selection.json'
        atomic(self.selection, {'version': 'session-audit-selection-v1', 'participants': entries})

    def test_dimensions_pre_post_alignment_range_and_direction_remain_separate(self):
        row, proof = audit.questionnaire(self.root/'s1', 's1', self.cfg)
        self.assertEqual(row['dimensions']['cognitive_anxiety']['pre_session'], 2.)
        self.assertEqual(row['primary_candidate'], 3.143)
        self.assertEqual(row['secondary_candidate'], 2.)
        self.assertEqual(row['dimensions']['self_confidence']['post_session'], 1.)
        self.assertFalse(row['modeling_eligible'])
        self.assertFalse(row['grid_check_is_scoring_verification'])
        self.assertEqual(set(proof), {'questionnaire', 'info'})

    def test_bad_shape_headers_nonfinite_and_out_of_range_are_rejected(self):
        path = self.root/'s1/selfReportedAnx_s1.csv'
        for text in ['pre,post\n1,2\n2,3\n', '1,2,3\n1,2,3\n1,2,3\n', '1,2\n1,2\n',
                     'nan,2\n1,2\n1,2\n', '1,inf\n1,2\n1,2\n', '.9,2\n1,2\n1,2\n',
                     '1,4.1\n1,2\n1,2\n']:
            path.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                audit.questionnaire(self.root/'s1', 's1', self.cfg)

    def test_mismatched_metadata_and_questionnaire_directory_rejected(self):
        with self.assertRaises(ValueError):
            audit.questionnaire(self.root/'s2', 's1', self.cfg)
        (self.root/'s1/info_s1.txt').write_text('s2\nf\ntest\n2020-01-01\n12-00-00\n')
        with self.assertRaises(ValueError):
            audit.questionnaire(self.root/'s1', 's1', self.cfg)

    def test_duplicate_excluded_missing_participant_or_wrong_role_rejected(self):
        original = read(self.selection)
        for fault in ['duplicate', 's25', 'missing', 'role', 'metadata']:
            changed = copy.deepcopy(original)
            if fault == 'duplicate': changed['participants'][-1] = changed['participants'][0]
            elif fault == 's25': changed['participants'][-1]['id'] = 's25'
            elif fault == 'missing': changed['participants'].pop()
            elif fault == 'role': changed['participants'][0]['role'] = 'final_test'
            else: changed['participants'][0]['anxiety_label'] = 'test'
            atomic(self.selection, changed)
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                audit.load_selection(self.selection, self.cfg)

    def test_modified_or_self_authorized_scoring_config_rejected(self):
        bad = copy.deepcopy(self.cfg)
        bad['questionnaire']['fit_authorized'] = True
        path = self.root/'config.json'; atomic(path, bad)
        with patch.object(audit, 'CONFIG', path), self.assertRaises(ValueError):
            audit.load_config()
        bad = copy.deepcopy(self.cfg); bad['models']['facial'].append('id_participant')
        atomic(path, bad)
        with patch.object(audit, 'CONFIG', path), self.assertRaises(ValueError):
            audit.load_config()

    def test_raw_summaries_null_support_and_no_metadata_or_outcome_predictors(self):
        feature_run = self.root/'features'; synthetic_feature_run(feature_run)
        rows = read_jsonl(feature_run/'windows.jsonl')
        for i, row in enumerate(rows):
            row['beh_mouth_mean'] = None
            row['beh_eye_mean'] = None if i % 2 else 0.
            row['q_track_fraction'] = i % 2
            row['questionnaire'] = 999
            row['test_ctrl'] = 123
        x, support = audit.summarize(rows, self.cfg)
        self.assertEqual(len(x), 6)
        self.assertIsNone(x[0]['beh_mouth_mean'])
        self.assertEqual(x[0]['beh_eye_mean'], 0.)
        self.assertEqual(x[0]['q_track_fraction'], .5)
        self.assertEqual(support[0]['columns']['beh_eye_mean']['observed'], 9)
        self.assertEqual(set(x[0]), set(audit.columns(self.cfg)))
        self.assertFalse(any(c.startswith(('id_', 'label_', 'ref_')) for c in x[0]))
        self.assertNotIn('questionnaire', x[0]); self.assertNotIn('test_ctrl', x[0])
        with self.assertRaises(ValueError): audit.summarize(rows[:-1], self.cfg)
        with self.assertRaises(ValueError): audit.summarize(rows+[rows[0]], self.cfg)
        rows[0]['beh_eye_mean'] = np.inf
        with self.assertRaises(ValueError): audit.summarize(rows, self.cfg)

    def test_no_fit_full_session_fold_inventory_preservation_and_tampering(self):
        features = self.root/'features'; synthetic_feature_run(features)
        before = inventory(features)
        out = self.root/'audit'
        with (patch.object(base, 'fit_fold', side_effect=AssertionError('No classifier fitting')),
              patch.object(base.FoldPreprocessor, 'fit', side_effect=AssertionError('No preprocessing fitting'))):
            result = audit.audit(features, self.selection, out)
            self.assertEqual(audit.validate(out), result)
        self.assertEqual(result['sessions'], 6); self.assertEqual(result['predictions'], 0)
        self.assertEqual(result['model_fitting'], 'blocked')
        self.assertEqual(inventory(features), before)
        self.assertFalse(list(out.rglob('*.joblib')))
        self.assertFalse(list(out.rglob('*predictions*')))
        x = read_jsonl(out/'X.jsonl'); outcomes = read_jsonl(out/'outcomes.jsonl')
        self.assertEqual(len(x), 6); self.assertEqual(len(outcomes), 6)
        self.assertEqual(outcomes[0]['participant'], 's1')
        self.assertEqual(outcomes[-1]['primary_candidate'], 3.857)
        for fold in read(out/'folds.json'):
            self.assertFalse(set(fold['training_participants']) & set(fold['evaluation_participants']))
            self.assertEqual(len(fold['training_sessions']), 5)
            self.assertEqual(len(fold['evaluation_sessions']), 1)
        with self.assertRaises(FileExistsError): audit.audit(features, self.selection, out)
        (out/'outcomes.jsonl').write_text('{}\n')
        with self.assertRaises(ValueError): audit.validate(out)

    def test_failed_output_not_success_and_changed_inputs_invalidate_reuse(self):
        features = self.root/'features'; synthetic_feature_run(features)
        (self.root/'s6/selfReportedAnx_s6.csv').write_text('bad\n')
        with self.assertRaises(ValueError): audit.audit(features, self.selection, self.root/'failed')
        self.assertEqual(read(self.root/'failed/receipt.json')['status'], 'failed')
        with self.assertRaises(ValueError): audit.validate(self.root/'failed')
        (self.root/'s6/selfReportedAnx_s6.csv').write_text('2,3\n1,2\n3,1\n')
        out = self.root/'good'; audit.audit(features, self.selection, out)
        (self.root/'s1/selfReportedAnx_s1.csv').write_text('2,3\n1,2\n3,1\n')
        with self.assertRaisesRegex(ValueError, 'source/configuration changed'):
            audit.validate(out)

    def test_reordered_outcomes_rejected_even_with_rehashed_receipt(self):
        features = self.root/'features'; synthetic_feature_run(features)
        out = self.root/'audit'; audit.audit(features, self.selection, out)
        outcomes = read_jsonl(out/'outcomes.jsonl'); outcomes.reverse()
        (out/'outcomes.jsonl').unlink()
        write_jsonl(out/'outcomes.jsonl', outcomes)
        receipt = read(out/'receipt.json'); files = inventory(out); files.pop('receipt.json')
        receipt['output_files'] = files; atomic(out/'receipt.json', receipt)
        with self.assertRaisesRegex(ValueError, 'alignment do not reproduce'):
            audit.validate(out)
