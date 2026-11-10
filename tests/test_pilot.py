"""Pilot lifecycle and archive tests use synthetic files only."""

import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from stress_detection.pilot import (execute_participant, plan, run, selection, spec,
                                    summarize, verify_validation, TASKS)
from stress_detection.pilot_state import (GIB, atomic, extract_zip,
                                         inspect_zip, inventory, read)

ROOT = Path(__file__).resolve().parents[1]


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'data/processed')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def config(self, participant='s25'):
        return {'schema_version': '1.0', 'pilot_selected_before_quality': True,
                'selection_reason': 'synthetic development fixture', 'final_test_cohort': 'unassigned',
                'participants': [{'id': participant, 'role': 'development_only' if participant == 's25' else 'pilot_development',
                                  'directory': str(self.root / participant)}]}

    def fixture(self, participant='s25'):
        folder = self.root / participant
        folder.mkdir()
        for t in (1, 2, 3):
            (folder / f'vid_{participant}_T{t}.avi').write_bytes(b'synthetic stub')
            (folder / f'bvp_{participant}_T{t}.csv').write_text('1\n' * 1920)
            (folder / f'eda_{participant}_T{t}.csv').write_text('1\n' * 120)
        (folder / f'info_{participant}.txt').write_text(f'{participant}\nf\nctrl\n2000-01-01\n12-00-00\n')
        (folder / f'selfReportedAnx_{participant}.csv').write_text('1,1\n1,1\n1,1\n')
        return folder

    def test_selection_requires_explicit_roles_and_no_final_test(self):
        path = self.root / 'selection.json'
        valid = self.config()
        atomic(path, valid)
        self.assertEqual(selection(path)['participants'][0]['role'], 'development_only')
        for mutate in (lambda d: d['participants'][0].update(role='pilot_development'),
                       lambda d: d.update(final_test_cohort=['s999']),
                       lambda d: d.update(pilot_selected_before_quality=False),
                       lambda d: d.update(participants=[]),
                       lambda d: d['participants'].append(d['participants'][0].copy())):
            bad = json.loads(json.dumps(valid))
            mutate(bad)
            atomic(path, bad)
            with self.assertRaises(ValueError):
                selection(path)

    def test_dry_run_checks_space_and_inputs_without_writing(self):
        self.fixture()
        output = self.root / 'runner'
        storage = {'reserve_gib': 100, 'workspace_gib': 40, 'outputs_gib_per_participant': 5}
        with patch('stress_detection.pilot.shutil.disk_usage', return_value=Mock(free=200 * GIB)):
            report = plan(self.config(), output, {}, storage)
        self.assertTrue(report['passed'])
        self.assertEqual(report['participants'][0]['tasks'], list(TASKS))
        self.assertEqual(len(report['participants'][0]['stages']), 14)
        self.assertFalse(output.exists())
        with patch('stress_detection.pilot.shutil.disk_usage', return_value=Mock(free=10 * GIB)):
            self.assertFalse(plan(self.config(), output, {}, storage)['passed'])
        (self.root / 's25/bvp_s25_T2.csv').unlink()
        report = plan(self.config(), output, {}, storage)
        self.assertFalse(report['passed'])
        self.assertTrue(report['participants'][0]['errors'])

    def test_failure_summary_retains_all_tasks_and_known_reference_windows(self):
        folder = self.fixture()
        tasks, windows = summarize(self.config()['participants'][0], folder, {}, {t: 'failed validation' for t in TASKS})
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(t['status'] == 'failed' and t['unknown_window_inventory'] for t in tasks))
        self.assertEqual(len(windows), 3)
        self.assertTrue(all(w['source'] == 'bvp' and w['status'] == 'rejected' for w in windows))
        self.assertTrue(all(t['scheduled_camera_windows_per_group'] is None for t in tasks))

    def test_batch_failure_does_not_drop_later_participants_or_mix_s25(self):
        self.fixture()
        self.fixture('s999')
        cfg = self.config()
        cfg['participants'] += self.config('s999')['participants']
        storage = {'reserve_gib': 0, 'workspace_gib': 0, 'outputs_gib_per_participant': 0}
        with patch('stress_detection.pilot.execute_participant', side_effect=ValueError('synthetic validation failure')) as execute:
            result = run(cfg, self.root / 'run', {}, storage)
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['development_tasks']), 3)
        self.assertEqual(len(result['pilot_tasks']), 3)
        self.assertEqual({t['participant'] for t in result['pilot_tasks']}, {'s999'})
        cfg['selection_reason'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'Selection'):
            run(cfg, self.root / 'run', {}, storage)

    def make_zip(self, extras=()):
        folder = self.fixture('s999')
        path = self.root / 'sample.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for member in folder.iterdir():
                archive.write(member, 's999/' + member.name)
            for name, data in extras:
                archive.writestr(name, data)
        return path

    def test_zip_declared_size_crc_extraction_and_original_preservation(self):
        path = self.make_zip()
        before = path.read_bytes()
        report = inspect_zip(path, 's999')
        self.assertEqual(report['declared_extracted_bytes'], sum(f.stat().st_size for f in (self.root / 's999').iterdir()))
        out = self.root / 'extracted'
        extract_zip(path, 's999', out)
        self.assertEqual(inventory(self.root / 's999'), inventory(out / 's999'))
        self.assertEqual(before, path.read_bytes())
        with self.assertRaises(FileExistsError):
            extract_zip(path, 's999', out)

    def test_zip_unsafe_paths_duplicates_symlinks_and_missing_files(self):
        for member in ('../escape', '/absolute', 's999/../escape', 's999\\escape', 's998/file', 's999//file'):
            with self.subTest(member=member):
                path = self.root / 'unsafe.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr(member, 'synthetic')
                with self.assertRaises(ValueError):
                    inspect_zip(path, 's999')
        path = self.root / 'symlink.zip'
        item = zipfile.ZipInfo('s999/link')
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(item, '../target')
        with self.assertRaises(ValueError):
            inspect_zip(path, 's999')

    def test_case_colliding_zip_members_are_rejected(self):
        path = self.make_zip([('s999/BVP_s999_T1.csv', 'duplicate')])
        with self.assertRaises(ValueError):
            inspect_zip(path, 's999')

    def test_bad_zip_and_crc_failure_are_reported_without_success_or_dropped_tasks(self):
        path = self.make_zip()
        cfg = self.config('s999')
        cfg['participants'][0].pop('directory')
        cfg['participants'][0]['zip'] = str(path)
        storage = {'reserve_gib': 0, 'workspace_gib': 0, 'outputs_gib_per_participant': 0}
        # Corrupt stored data while preserving the valid central directory.
        with zipfile.ZipFile(path) as archive:
            member = next(i for i in archive.infolist() if i.file_size > 0)
            offset = member.header_offset
        raw = bytearray(path.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', raw, offset + 26)
        raw[offset + 30 + name_length + extra_length] ^= 1
        path.write_bytes(raw)
        self.assertTrue(plan(cfg, self.root / 'crc-run', {}, storage)['passed'])
        result = run(cfg, self.root / 'crc-run', {}, storage)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['pilot_tasks']), 3)
        self.assertTrue(all(t['status'] == 'failed' for t in result['pilot_tasks']))
        self.assertEqual(len(result['failed_or_incomplete_attempts']), 1)
        self.assertEqual(result['failed_or_incomplete_attempts'][0]['status'], 'failed')
        path.write_bytes(b'not a ZIP archive')
        self.assertFalse(plan(cfg, self.root / 'bad-run', {}, storage)['passed'])
    def test_stage_specification_does_not_change_with_dependency_dict(self):
        values = {'source': 'original'}
        receipt_spec = spec({}, {'id': 's999', 'role': 'pilot_development'}, values, 'face')
        values['pulse'] = 'later stage'
        self.assertEqual(receipt_spec['inputs'], {'source': 'original'})

    def test_completed_validation_can_retain_ineligible_video_but_not_partial_report(self):
        output = self.root / 'validation'
        output.mkdir()
        report = {'validation_completed': True, 'structural_checks_passed': False,
                  'missing_files': [], 'signals': [{'valid': True}] * 6,
                  'videos': [{'valid': False}, {'valid': True}, {'valid': True}],
                  'info': {'valid': True}, 'questionnaire': {'valid': True}}
        atomic(output / 'validation.json', report)
        verify_validation(output)
        report.pop('validation_completed')
        atomic(output / 'validation.json', report)
        with self.assertRaises(ValueError):
            verify_validation(output)

    def test_orchestration_and_dry_run_agree_on_all_resumed_stage_signatures(self):
        folder = self.fixture('s999')
        entry = self.config('s999')['participants'][0]
        files = inventory(folder)
        records = [{'participant_id': 's999', 'task_id': task, 'recording_id': 's999/' + task,
                    'validation_status': 'passed',
                    'files': {kind: {**files[f'{kind}_s999_{task}.{ext}'], 'path': f's999/{kind}_s999_{task}.{ext}'}
                              for kind, ext in (('vid', 'avi'), ('bvp', 'csv'), ('eda', 'csv'))},
                    'candidates': {k: ['one'] for k in ('vid', 'bvp', 'eda')},
                    'signals': {'bvp': {'sampling_rate_hz': 64}, 'eda': {'sampling_rate_hz': 4}},
                    'video': {'valid': True, 'decode_complete': True, 'decoded_frames': 1200,
                              'observed_duration_seconds': 30}}
                   for task in TASKS]
        def fake_command(module, arguments, log):
            # Synthetic subprocess outputs; this test checks orchestration, not estimators.
            target = Path(arguments[arguments.index('--output') + 1])
            if module == 'manifest':
                target.parent.mkdir(parents=True)
                atomic(target, {'schema_version': '1.0',
                                'validation_status': 'passed' if all(r['validation_status'] == 'passed' for r in records) else 'needs_review',
                                'discovery_issues': [], 'records': records})
            else:
                target.mkdir()
                atomic(target / 'status.json', {'status': 'completed'})
        ctx = {'model_path': 'synthetic', 'model_config_path': 'synthetic'}
        storage = {'reserve_gib': 0, 'workspace_gib': 0, 'outputs_gib_per_participant': 0}
        output = self.root / 'orchestrator'
        with patch('stress_detection.pilot.command', side_effect=fake_command) as calls, \
                patch('stress_detection.pilot.verify_validation'), patch('stress_detection.pilot.verify_face'), \
                patch('stress_detection.pilot.verify_pulse'), patch('stress_detection.pilot.verify_diagnostics'):
            first = []
            _, stages, failures = execute_participant(entry, output, ctx, storage, first)
            self.assertFalse(failures)
            self.assertEqual(len(stages), 14)
            self.assertEqual(calls.call_count, 11)
            report = plan(self.config('s999'), output, ctx, storage)
            self.assertTrue(report['passed'])
            self.assertTrue(all(s['decision'] == 'resume' for s in report['participants'][0]['stages']))
            second = []
            execute_participant(entry, output, ctx, storage, second)
            self.assertEqual(calls.call_count, 11)
            self.assertTrue(all(e['decision'] == 'resume' for e in second))
            # A failed camera record must not suppress independent BVP or healthy tasks.
            records[0]['validation_status'] = 'needs_review'
            records[0]['warnings'] = ['synthetic_frame_count_mismatch']
            records[0]['video']['valid'] = False
            _, retained, failures = execute_participant(entry, self.root / 'ineligible', ctx, storage, [])
            self.assertEqual(set(failures), {'T1'})
            self.assertNotIn('T1/face', retained)
            self.assertIn('T1/reference', retained)
            self.assertIn('T2/diagnostics', retained)
            self.assertIn('T3/diagnostics', retained)
            only_references = {k: v for k, v in retained.items() if k == 'manifest' or k.endswith('/reference')}
            tasks, windows = summarize(entry, folder, only_references, {t: 'synthetic camera failure' for t in TASKS})
            self.assertTrue(all(t['scheduled_camera_windows_per_group'] == 1 for t in tasks))
            self.assertTrue(all(t['bvp']['total'] == 1 for t in tasks))
            self.assertEqual(len([w for w in windows if w['source'] == 'camera']), 18)
            self.assertEqual(len([w for w in windows if w['source'] == 'bvp']), 3)
            self.assertTrue(all(w['status'] == 'rejected' for w in windows if w['source'] == 'camera'))


if __name__ == '__main__':
    unittest.main()
