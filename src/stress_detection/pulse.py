"""Offline green/POS baselines and independent recording-level BVP summaries."""

import argparse
from collections import Counter
import csv
from dataclasses import asdict, dataclass
from fractions import Fraction
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np

from .manifest import fingerprint
from .validate_sample import inspect_numeric, require_ignored, write_private_json

REGIONS = ('forehead', 'cheek_image_left', 'cheek_image_right')
METHODS = ('green', 'pos')
POS_DOI = 'https://doi.org/10.1109/TBME.2016.2609282'


@dataclass(frozen=True)
class Settings:
    window_seconds: float = 30.0
    grid_hz: float = 40.0
    max_gap_seconds: float = 0.15
    min_valid_fraction: float = 0.90
    min_bpm: float = 42.0
    max_bpm: float = 240.0
    pos_seconds: float = 1.6
    min_std: float = 1e-8
    min_peak_fraction: float = 0.10

    def validate(self):
        numbers = np.array(list(asdict(self).values()))
        if (not np.isfinite(numbers).all() or self.window_seconds <= 0
                or self.grid_hz <= 2 * self.max_bpm / 60
                or not 0 < self.min_bpm < self.max_bpm
                or not 0 < self.min_valid_fraction <= 1
                or not 0 <= self.min_peak_fraction <= 1 or self.max_gap_seconds <= 0
                or self.min_std <= 0 or self.pos_seconds <= 0
                or self.pos_seconds >= self.window_seconds
                or abs(self.grid_hz * self.window_seconds - round(self.grid_hz * self.window_seconds)) > 1e-8):
            raise ValueError('Invalid pulse settings')


def extract_pulse(rgb, method, rate, cfg):
    """POS Algorithm 1: mean normalization, projection, std ratio, SUM overlap-add.

    No overlap-count division or bandpass is part of the bare POS core.
    """
    rgb = np.asarray(rgb, dtype=float)
    if rgb.ndim != 2 or rgb.shape[1] != 3 or not np.isfinite(rgb).all():
        raise ValueError('invalid_rgb')
    if np.any(rgb.mean(axis=0) <= cfg.min_std):
        raise ValueError('unusable_channel_mean')
    if method == 'green':
        return rgb[:, 1] / rgb[:, 1].mean() - 1
    if method != 'pos':
        raise ValueError('unknown_method')
    length = int(np.floor(cfg.pos_seconds * rate + .5))
    if length < 2 or len(rgb) < length:
        raise ValueError('insufficient_pos_samples')
    pulse = np.zeros(len(rgb))
    for start in range(len(rgb) - length + 1):
        block = rgb[start:start + length]
        mean = block.mean(axis=0)
        if np.any(mean <= cfg.min_std):
            raise ValueError('unusable_channel_mean')
        normalized = block / mean
        s1 = normalized[:, 1] - normalized[:, 2]
        s2 = -2 * normalized[:, 0] + normalized[:, 1] + normalized[:, 2]
        std1, std2 = np.std(s1), np.std(s2)
        if std2 <= cfg.min_std:
            raise ValueError('degenerate_pos_projection')
        h = s1 + (std1 / std2) * s2
        pulse[start:start + length] += h - h.mean()
    return pulse


def spectral_rate(signal, rate, cfg):
    """Linear detrend, Hann taper, unpadded FFT; no reference-dependent settings."""
    x = np.asarray(signal, dtype=float)
    if x.ndim != 1 or len(x) < 4 or not np.isfinite(x).all():
        raise ValueError('invalid_signal')
    t = np.arange(len(x), dtype=float)
    t -= t.mean()
    detrended = x - x.mean() - t * (np.dot(t, x) / np.dot(t, t))
    if np.std(detrended) <= cfg.min_std:
        raise ValueError('flat_signal')
    power = abs(np.fft.rfft(detrended * np.hanning(len(x)))) ** 2
    frequencies = np.fft.rfftfreq(len(x), 1 / rate)
    band = (frequencies >= cfg.min_bpm / 60) & (frequencies <= cfg.max_bpm / 60)
    total = power[band].sum()
    if total <= np.finfo(float).eps * power.sum() or total <= 0:
        raise ValueError('no_in_band_power')
    candidates = np.flatnonzero(band)
    peak = candidates[np.argmax(power[band])]
    quality = float(power[peak] / total)
    # A threshold is an engineering screen, not a calibrated confidence.
    if quality < cfg.min_peak_fraction:
        return None, quality, 'diffuse_spectrum'
    return float(frequencies[peak] * 60), quality, None


def resample_window(times, rgb, start, cfg):
    """Interpolate only between valid endpoints separated by <= configured gap."""
    end = start + cfg.window_seconds
    grid = start + np.arange(round(cfg.window_seconds * cfg.grid_hz)) / cfg.grid_hz
    inside = (times >= start) & (times < end)
    valid = np.isfinite(rgb).all(axis=1)
    fraction = float(valid[inside].mean()) if inside.any() else 0.0
    result = {'valid_data_fraction': fraction, 'supported_grid_fraction': 0.0}
    if fraction < cfg.min_valid_fraction:
        return None, result, 'insufficient_valid_data'
    vt, values = times[valid], rgb[valid]
    if len(vt) < 2:
        return None, result, 'insufficient_valid_data'
    right = np.searchsorted(vt, grid, side='left')
    clipped = np.minimum(right, len(vt) - 1)
    exact = np.abs(vt[clipped] - grid) <= 1e-9
    left = np.maximum(right - 1, 0)
    bounded = (right > 0) & (right < len(vt))
    gap = vt[clipped] - vt[left]
    supported = exact | (bounded & (gap <= cfg.max_gap_seconds + 1e-9))
    result['supported_grid_fraction'] = float(supported.mean())
    result['interpolated_grid_fraction'] = float((supported & ~exact).mean())
    if not supported.all():
        reason = 'long_gap' if np.any(bounded & ~exact & (gap > cfg.max_gap_seconds + 1e-9)) else 'unsupported_window_boundary'
        return None, result, reason
    # Do not use a source below the pulse search band's Nyquist requirement.
    local = times[inside]
    if len(local) < 2 or 1 / np.median(np.diff(local)) <= 2 * cfg.max_bpm / 60:
        return None, result, 'insufficient_source_sampling_rate'
    uniform = np.column_stack([np.interp(grid, vt, values[:, c]) for c in range(3)])
    return uniform, result, None


def analyze_region(times, rgb, origin, duration, region, cfg):
    rows, traces = [], []
    count = int(np.floor((duration + 1e-9) / cfg.window_seconds))
    for i in range(count):
        start = origin + i * cfg.window_seconds
        uniform, availability, rejection = resample_window(times, rgb, start, cfg)
        for method in METHODS:
            row = {'method': method, 'region': region, 'window_index': i,
                   'start_original_seconds': start, 'end_original_seconds': start + cfg.window_seconds,
                   **availability, 'estimated_bpm': None, 'spectral_peak_fraction': None,
                   'status': 'rejected', 'rejection_reason': rejection}
            pulse = None
            if rejection is None:
                try:
                    pulse = extract_pulse(uniform, method, cfg.grid_hz, cfg)
                    bpm, peak, reason = spectral_rate(pulse, cfg.grid_hz, cfg)
                    row.update(estimated_bpm=bpm, spectral_peak_fraction=peak,
                               status='accepted' if reason is None else 'rejected', rejection_reason=reason)
                except ValueError as exc:
                    row['rejection_reason'] = str(exc)
            rows.append(row)
            # Failed windows retain null waveforms as well as null BPM.
            traces.append({'method': method, 'region': region, 'window_index': i,
                           'start_original_seconds': start, 'grid_hz': cfg.grid_hz,
                           'pulse': pulse.tolist() if row['status'] == 'accepted' else None})
    return rows, traces


def recording_summary(rows):
    groups = {method + '/' + region: [] for method in METHODS for region in REGIONS}
    for row in rows:
        key = row['method'] + '/' + row['region']
        groups.setdefault(key, []).append(row)
    result = {}
    for key, group in sorted(groups.items()):
        accepted = [r['estimated_bpm'] for r in group if r['status'] == 'accepted']
        result[key] = {'accepted': len(accepted), 'total': len(group),
                       'coverage': len(accepted) / len(group) if group else None,
                       'median_bpm': float(np.median(accepted)) if accepted else None,
                       'rejections': dict(sorted(Counter(r['rejection_reason'] for r in group if r['status'] != 'accepted').items()))}
    return result


def load_face_run(run):
    config = json.loads((run / 'config.json').read_text())
    summary = json.loads((run / 'summary.json').read_text())
    status = json.loads((run / 'status.json').read_text())['status']
    if (config['schema_version'] != '1.0' or status not in ('completed', 'completed_with_warnings')
            or summary['status'] != status or not summary['reader']['decode_complete']):
        raise ValueError('A completed schema-1 face-quality run is required')
    times, exact_times, indices, pts, bases = [], [], [], [], []
    regions = {r: [] for r in REGIONS}
    with (run / 'frames.jsonl').open() as source:
        for row in map(json.loads, source):
            if row['presentation_time_fraction'] is None or row['pts'] is None or row['time_base'] is None:
                raise ValueError('Missing source timing; no fallback is allowed')
            exact = Fraction(row['presentation_time_fraction'])
            if exact != row['pts'] * Fraction(row['time_base']):
                raise ValueError('Inconsistent source PTS/time base')
            if exact_times and exact <= Fraction(exact_times[-1]):
                raise ValueError('Nonmonotonic or duplicate source timing')
            if row['frame_index'] != len(times):
                raise ValueError('Missing/duplicate frame row')
            times.append(float(exact)); exact_times.append(str(exact))
            indices.append(row['frame_index']); pts.append(row['pts']); bases.append(row['time_base'])
            for region in REGIONS:
                value = row['regions'][region]
                if value['valid']:
                    rgb = np.asarray(value['mean_rgb'], dtype=float)
                    if rgb.shape != (3,) or not np.isfinite(rgb).all() or np.any((rgb < 0) | (rgb > 255)):
                        raise ValueError('Malformed valid RGB value')
                    regions[region].append(rgb)
                else:
                    regions[region].append([np.nan] * 3)
    if len(times) < 2 or len(times) != summary['processed_frames']:
        raise ValueError('Source frame count mismatch or too short')
    last_duration = summary['reader'].get('last_frame_duration_seconds')
    if last_duration is None or not np.isfinite(last_duration) or last_duration <= 0:
        raise ValueError('Documented final-frame extent is required; no nominal FPS substitution')
    duration = times[-1] - times[0] + last_duration
    timing = {'frame_indices': indices, 'pts': pts, 'time_bases': bases,
              'original_time_fractions': exact_times, 'origin_fraction': exact_times[0],
              'duration_seconds': duration, 'last_frame_duration_seconds': last_duration}
    return config, np.array(times), {r: np.array(v) for r, v in regions.items()}, timing


def reference_summary(path, cfg):
    audit = inspect_numeric(path, 1, 64)
    if not audit['valid']:
        return {'status': 'failed', 'reason': 'malformed_bvp', 'audit': audit}
    with path.open(newline='', encoding='utf-8-sig') as source:
        values = np.array([float(row[0]) for row in csv.reader(source)])
    n = round(cfg.window_seconds * 64)
    rows = []
    for start in range(0, len(values) - n + 1, n):
        row = {'start_nominal_seconds': start / 64, 'end_nominal_seconds': (start + n) / 64,
               'estimated_bpm': None, 'spectral_peak_fraction': None, 'status': 'rejected', 'rejection_reason': None}
        try:
            bpm, peak, reason = spectral_rate(values[start:start+n], 64, cfg)
            row.update(estimated_bpm=bpm, spectral_peak_fraction=peak,
                       status='accepted' if reason is None else 'rejected', rejection_reason=reason)
        except ValueError as exc:
            row['rejection_reason'] = str(exc)
        rows.append(row)
    accepted = [r['estimated_bpm'] for r in rows if r['status'] == 'accepted']
    return {'status': 'completed', 'sampling_rate_hz': 64, 'sample_count': len(values),
            'time_basis': 'nominal sample index / 64; origin and video synchronization unverified',
            'accepted': len(accepted), 'total': len(rows), 'coverage': len(accepted) / len(rows) if rows else None,
            'median_bpm': float(np.median(accepted)) if accepted else None, 'windows': rows,
            'trailing_seconds': (len(values) % n) / 64}


def matched_bvp(manifest_path, dataset_root, config):
    manifest = json.loads(manifest_path.read_text())
    records = [r for r in manifest['records'] if r['recording_id'] == config['recording_id']
               and r.get('files', {}).get('vid', {}).get('sha256') == config['source']['sha256']]
    if len(records) != 1 or len(records[0].get('candidates', {}).get('bvp', [])) != 1:
        raise ValueError('Reference pairing must be unique in the manifest')
    entry = records[0]['files']['bvp']
    root = dataset_root.resolve()
    path = (root / entry['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Unsafe or missing reference path')
    if fingerprint(path, entry['path'])['sha256'] != entry['sha256']:
        raise ValueError('BVP checksum mismatch')
    return path, entry


def run(face_run, output, cfg, manifest=None, dataset_root=None):
    cfg.validate()
    require_ignored(output)
    config, times, regions, timing = load_face_run(face_run)
    if (manifest is None) != (dataset_root is None):
        raise ValueError('Reference comparison requires both manifest and dataset root')
    reference_path = reference_entry = None
    if manifest is not None:
        reference_path, reference_entry = matched_bvp(manifest, dataset_root, config)
    output.mkdir(parents=True, exist_ok=False)
    def status(value):
        temporary = output / 'status.tmp'
        temporary.write_text(json.dumps({'status': value}) + '\n')
        temporary.replace(output / 'status.json')
    status('running')
    try:
        write_private_json(output / 'config.json', {
            'schema_version': '1.0', 'settings': asdict(cfg), 'pos_source': POS_DOI,
            'software': {'numpy': version('numpy'), 'python': platform.python_version()},
            'source': config['source'], 'source_model': config['model'],
            'face_frames': fingerprint(face_run / 'frames.jsonl', 'frames.jsonl'),
            'recording_id': config['recording_id'], 'reference': reference_entry,
            'synchronization': 'unverified', 'classification_labels_used': False,
            'spectral_diagnostic': 'largest in-band FFT-bin power / total in-band power; not confidence',
            'grid': 'origin + k/grid_hz; half-open windows; no extrapolation; short-gap linear interpolation',
            'pos': f'{cfg.pos_seconds} s mean normalization, projection, population std ratio, mean removal, SUM overlap-add; no core bandpass',
            'spectrum': 'linear detrend, symmetric Hann, unpadded FFT, largest bin in configured BPM band'})
        write_private_json(output / 'source-timing.json', timing)
        rows, traces = [], []
        for region in REGIONS:
            r, t = analyze_region(times, regions[region], times[0], timing['duration_seconds'], region, cfg)
            rows.extend(r); traces.extend(t)
        with (output / 'windows.jsonl').open('x') as target:
            for row in rows:
                target.write(json.dumps(row, allow_nan=False) + '\n')
        with (output / 'pulse-traces.jsonl').open('x') as target:
            for trace in traces:
                target.write(json.dumps(trace, allow_nan=False) + '\n')
        summaries = recording_summary(rows)
        # Camera results are fully computed before independent reference estimation.
        reference = reference_summary(reference_path, cfg) if reference_path else None
        if reference is not None:
            write_private_json(output / 'reference.json', reference)
        for group in summaries.values():
            ref_bpm = reference.get('median_bpm') if reference else None
            group['camera_minus_reference_median_bpm'] = (group['median_bpm'] - ref_bpm
                if group['median_bpm'] is not None and ref_bpm is not None else None)
        report = {'schema_version': '1.0', 'status': 'completed', 'recording_id': config['recording_id'],
                  'synchronization': 'unverified', 'groups': summaries,
                  'scheduled_windows_per_group': int(timing['duration_seconds'] // cfg.window_seconds),
                  'trailing_seconds': timing['duration_seconds'] % cfg.window_seconds,
                  'reference_status': reference.get('status') if reference else 'not_requested',
                  'comparison': 'difference of independent recording-level medians; NOT paired-window error or waveform agreement'}
        write_private_json(output / 'summary.json', report)
        status('completed')
        return report
    except BaseException:
        status('failed')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--face-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--dataset-root', type=Path)
    parser.add_argument('--max-gap-seconds', type=float, default=Settings.max_gap_seconds)
    args = parser.parse_args()
    result = run(args.face_run, args.output, Settings(max_gap_seconds=args.max_gap_seconds),
                 args.manifest, args.dataset_root)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
