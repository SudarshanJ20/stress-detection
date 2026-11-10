"""Pulse recovery and failure coverage use only synthetic RGB/BVP fixtures."""

from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from stress_detection.pulse import (Settings, analyze_region, extract_pulse, load_face_run,
    matched_bvp, recording_summary, reference_summary, resample_window, run, spectral_rate)


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Settings()
        self.times = 7.5 + np.arange(1200) / 40
        wave = np.sin(2 * np.pi * 1.2 * (self.times - 7.5))
        self.rgb = np.array([150, 110, 90]) * (1 + wave[:, None] * [.001, .004, .002])

    def test_known_pulse_both_methods_nonzero_origin(self):
        rows, traces = analyze_region(self.times, self.rgb, 7.5, 30, 'forehead', self.cfg)
        self.assertEqual(len(rows), 2)
        for row, trace in zip(rows, traces):
            self.assertEqual(row['status'], 'accepted')
            self.assertAlmostEqual(row['estimated_bpm'], 72)
            self.assertEqual(row['start_original_seconds'], 7.5)
            self.assertEqual(row['valid_data_fraction'], 1)
            self.assertIsNotNone(trace['pulse'])

    def test_pos_matches_independent_algorithm_one_calculation(self):
        rgb = self.rgb[:70]
        expected = np.zeros(70)
        for end in range(64, 71):
            block = rgb[end-64:end].T
            normalized = block / np.mean(block, axis=1)[:, None]
            s = np.array([[0, 1, -1], [-2, 1, 1]]) @ normalized
            h = s[0] + np.std(s[0]) / np.std(s[1]) * s[1]
            expected[end-64:end] += h - h.mean()
        np.testing.assert_allclose(extract_pulse(rgb, 'pos', 40, self.cfg), expected, atol=1e-13)

    def test_irregular_source_resampling_retains_origin(self):
        t = 10 + np.arange(1055) / 35.138
        x = np.array([150, 110, 90]) * (1 + np.sin(2*np.pi*1.2*(t-10))[:, None]*[.001,.004,.002])
        uniform, info, error = resample_window(t, x, 10, self.cfg)
        self.assertIsNone(error)
        self.assertEqual(uniform.shape, (1200, 3))
        self.assertEqual(info['supported_grid_fraction'], 1)
        self.assertAlmostEqual(spectral_rate(extract_pulse(uniform, 'pos', 40, self.cfg),40,self.cfg)[0],72)

    def test_flat_signals_rejected_and_null(self):
        rows, traces = analyze_region(self.times, np.full((1200,3),100.),7.5,30,'forehead',self.cfg)
        self.assertTrue(all(r['status']=='rejected' and r['estimated_bpm'] is None for r in rows))
        self.assertTrue(all(t['pulse'] is None for t in traces))
        with self.assertRaisesRegex(ValueError, 'flat_signal'):
            spectral_rate(np.ones(1920),64,self.cfg)

    def test_insufficient_valid_data(self):
        rgb=self.rgb.copy();rgb[:200]=np.nan
        rows,_=analyze_region(self.times,rgb,7.5,30,'forehead',self.cfg)
        self.assertTrue(all(r['rejection_reason']=='insufficient_valid_data' for r in rows))
        self.assertEqual(recording_summary(rows)['green/forehead']['coverage'],0)

    def test_long_gap_rejected_even_above_valid_fraction_threshold(self):
        rgb=self.rgb.copy();rgb[100:120]=np.nan
        rows,_=analyze_region(self.times,rgb,7.5,30,'forehead',self.cfg)
        self.assertTrue(all(r['rejection_reason']=='long_gap' for r in rows))
        self.assertTrue(all(r['valid_data_fraction']>.9 for r in rows))

    def test_missing_source_frames_also_count_as_gap(self):
        keep=np.ones(len(self.times),bool);keep[100:120]=False
        _,_,error=resample_window(self.times[keep],self.rgb[keep],7.5,self.cfg)
        self.assertEqual(error,'long_gap')

    def test_short_gap_interpolated_but_no_boundary_extrapolation(self):
        rgb=self.rgb.copy();rgb[100:103]=np.nan
        uniform,info,error=resample_window(self.times,rgb,7.5,self.cfg)
        self.assertIsNone(error);self.assertTrue(np.isfinite(uniform).all())
        self.assertGreater(info['interpolated_grid_fraction'],0)
        rgb[0]=np.nan
        self.assertEqual(resample_window(self.times,rgb,7.5,self.cfg)[2],'unsupported_window_boundary')

    def test_diffuse_spectrum_is_rejected_not_confident(self):
        rng=np.random.default_rng(2)
        bpm,quality,reason=spectral_rate(rng.normal(size=1200),40,replace(self.cfg,min_peak_fraction=.99))
        self.assertIsNone(bpm);self.assertLess(quality,.99);self.assertEqual(reason,'diffuse_spectrum')

    def test_invalid_settings_and_rgb(self):
        for cfg in (replace(self.cfg,max_gap_seconds=-1),replace(self.cfg,grid_hz=4),replace(self.cfg,min_bpm=float('nan'))):
            with self.assertRaises(ValueError):cfg.validate()
        with self.assertRaises(ValueError):extract_pulse(np.full((1200,3),np.nan),'pos',40,self.cfg)


class PrivateRunTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'data/processed')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.face=self.root/'face';self.face.mkdir()
        (self.face/'config.json').write_text(json.dumps({'schema_version':'1.0','source':{'sha256':'synthetic'},'model':{},'recording_id':'synthetic/recording'}))
        (self.face/'status.json').write_text(json.dumps({'status':'completed'}))
        (self.face/'summary.json').write_text(json.dumps({'status':'completed','processed_frames':1200,
            'reader':{'decode_complete':True,'last_frame_duration_seconds':.025}}))
        with (self.face/'frames.jsonl').open('w') as f:
            for i in range(1200):
                wave=np.sin(2*np.pi*1.2*i/40)
                rgb=(np.array([150,110,90])*(1+wave*np.array([.001,.004,.002]))).tolist()
                f.write(json.dumps({'frame_index':i,'pts':i+300,'time_base':'1/40',
                  'presentation_time_fraction':str(Fraction(i+300,40)),
                  'regions':{r:{'valid':True,'mean_rgb':rgb} for r in ('forehead','cheek_image_left','cheek_image_right')}})+'\n')

    def test_run_outputs_no_labels_and_refuses_overwrite(self):
        output=self.root/'pulse'
        report=run(self.face,output,Settings())
        self.assertEqual(report['status'],'completed')
        self.assertTrue(all(g['accepted']==g['total']==1 for g in report['groups'].values()))
        self.assertEqual(json.loads((output/'source-timing.json').read_text())['origin_fraction'],'15/2')
        self.assertFalse(json.loads((output/'config.json').read_text())['classification_labels_used'])
        with self.assertRaises(FileExistsError):run(self.face,output,Settings())

    def test_incomplete_or_duplicate_timestamp_run_rejected(self):
        (self.face/'status.json').write_text('{"status":"partial"}')
        with self.assertRaises(ValueError):load_face_run(self.face)
        (self.face/'status.json').write_text('{"status":"completed"}')
        p=self.face/'frames.jsonl';lines=p.read_text().splitlines();lines[1]=lines[0];p.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):load_face_run(self.face)

    def test_independent_bvp_recovery_and_malformed_rejection(self):
        p=self.root/'bvp.csv'
        np.savetxt(p,np.sin(2*np.pi*1.5*np.arange(1920)/64))
        report=reference_summary(p,Settings())
        self.assertEqual(report['median_bpm'],90)
        self.assertEqual(report['accepted'],1)
        p.write_text('1\nnan\n')
        self.assertEqual(reference_summary(p,Settings())['status'],'failed')

    def test_manifest_pairing_hash_and_path_guards(self):
        p=self.root/'bvp.csv';p.write_text('1\n2\n')
        record={'recording_id':'synthetic/recording','candidates':{'bvp':['bvp.csv']},
                'files':{'vid':{'sha256':'synthetic'},'bvp':{'path':'bvp.csv','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}}
        manifest=self.root/'manifest.json';manifest.write_text(json.dumps({'records':[record]}))
        config=json.loads((self.face/'config.json').read_text())
        self.assertEqual(matched_bvp(manifest,self.root,config)[0],p)
        p.write_text('changed')
        with self.assertRaisesRegex(ValueError,'checksum'):matched_bvp(manifest,self.root,config)
        record['files']['bvp']['path']='../outside.csv';manifest.write_text(json.dumps({'records':[record]}))
        with self.assertRaisesRegex(ValueError,'Unsafe'):matched_bvp(manifest,self.root,config)

    def test_diagnostics_reproduce_saved_runs_and_preserve_inputs(self):
        from stress_detection.pulse_diagnostics import audit
        p = self.root / 'bvp.csv'
        values = np.r_[np.sin(2*np.pi*1.5*np.arange(1920)/64),
                       np.sin(2*np.pi*2*np.arange(1920)/64), [0, 1, 2]]
        np.savetxt(p, values)
        entry = {'path': 'bvp.csv', 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps({'records': [{'recording_id': 'synthetic/recording',
            'candidates': {'bvp': ['bvp.csv']},
            'files': {'vid': {'sha256': 'synthetic'}, 'bvp': entry}}]}))
        saved = self.root / 'saved'
        run(self.face, saved, Settings(), manifest, self.root)
        before = {f.name: f.read_bytes() for f in saved.iterdir()}
        output = self.root / 'diagnostics'
        report = audit(self.face, saved, manifest, self.root, output)
        self.assertEqual(report['implementation_check'], 'passed')
        self.assertEqual(report['trailing_samples'], 3)
        self.assertEqual([r['estimated_bpm'] for r in report['bvp_windows']], [90, 120])
        self.assertEqual([r['start_sample_inclusive'] for r in report['bvp_windows']], [0, 1920])
        self.assertEqual([r['end_sample_exclusive'] for r in report['bvp_windows']], [1920, 3840])
        self.assertTrue((output / 'bvp-windows.png').is_file())
        self.assertEqual(before, {f.name: f.read_bytes() for f in saved.iterdir()})
        with self.assertRaises(FileExistsError):
            audit(self.face, saved, manifest, self.root, output)
        with self.assertRaises(ValueError):
            audit(self.face, saved, manifest, self.root, Path('/tmp/public-diagnostics'))
        config = json.loads((saved / 'config.json').read_text())
        config['settings']['min_peak_fraction'] = .09
        (saved / 'config.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'frozen'):
            audit(self.face, saved, manifest, self.root, self.root / 'different-settings')


if __name__=='__main__':unittest.main()
