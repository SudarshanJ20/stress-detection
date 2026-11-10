"""Audit frozen saved pulse runs; participant reports/plots remain Git ignored."""

import argparse
import csv
from dataclasses import asdict
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np

from .manifest import fingerprint
from .pulse import (Settings, REGIONS, analyze_region, load_face_run, matched_bvp,
                    reference_summary, spectral_rate)
from .validate_sample import require_ignored, write_private_json


def spectrum(x, rate):
    """Independent diagnostic reconstruction, checked against production decisions."""
    x = np.asarray(x, dtype=float)
    t = np.arange(len(x), dtype=float)
    t -= t.mean()
    slope = float(np.dot(t, x) / np.dot(t, t))
    detrended = x - x.mean() - slope * t
    return (detrended, np.fft.rfftfreq(len(x), 1 / rate),
            abs(np.fft.rfft(detrended * np.hanning(len(x)))) ** 2, slope * rate)


def longest_run(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return int(max(ends - starts, default=0))


def edge_info(bpm, bin_bpm, cfg):
    if bpm is None:
        return None
    lower, upper = float(bpm - cfg.min_bpm), float(cfg.max_bpm - bpm)
    return {'lower_distance_bpm': lower, 'upper_distance_bpm': upper,
            'near_edge_within_one_bin': min(abs(lower), abs(upper)) <= bin_bpm + 1e-9}


def describe_signal(values, rate, cfg):
    """Measurements only: repeat/jump/drift statistics are not new rejection gates."""
    x = np.asarray(values, dtype=float)
    detrended, f, power, slope = spectrum(x, rate)
    band = (f >= cfg.min_bpm / 60) & (f <= cfg.max_bpm / 60)
    candidates = np.flatnonzero(band)
    total = float(power[band].sum())
    winner = int(candidates[np.argmax(power[band])])
    try:
        bpm, fraction, reason = spectral_rate(x, rate, cfg)
    except ValueError as exc:
        bpm, fraction, reason = None, None, str(exc)
    if fraction is not None:
        if not np.isclose(fraction, power[winner] / total, rtol=1e-13, atol=0):
            raise ValueError('Diagnostic spectrum disagrees with production fraction')
    if bpm is not None and bpm != float(f[winner] * 60):
        raise ValueError('Diagnostic frequency/BPM disagrees with production estimate')

    def peaks(indices):
        ranked = sorted(indices, key=lambda i: (-power[i], i))[:5]
        return [{'hz': float(f[i]), 'bpm': float(f[i] * 60), 'power': float(power[i]),
                 'fraction_of_in_band_power': float(power[i] / total) if total else None,
                 'edges': edge_info(float(f[i] * 60), rate / len(x) * 60, cfg)}
                for i in ranked]

    local = np.flatnonzero((power[1:-1] > power[:-2]) & (power[1:-1] >= power[2:])) + 1
    jumps = np.diff(x)
    largest = np.argsort(-abs(jumps), kind='stable')[:5]
    equal = x[1:] == x[:-1]
    result = {
        'status': 'accepted' if reason is None else 'rejected', 'rejection_reason': reason,
        'estimated_bpm': bpm, 'spectral_peak_fraction': fraction,
        'decision_rule': 'production spectral_rate; unchanged frozen Settings',
        'threshold_margin': fraction - cfg.min_peak_fraction if fraction is not None else None,
        'bin_spacing_bpm': rate / len(x) * 60,
        'winning_bin': peaks([winner])[0], 'strongest_in_band_bins': peaks(candidates),
        'strongest_in_band_local_maxima': peaks(local[band[local]]),
        'strongest_out_of_band_local_maxima': peaks(local[~band[local]]),
        'strongest_full_spectrum_bin': peaks([int(np.argmax(power))])[0],
        'raw_min': float(x.min()), 'raw_max': float(x.max()), 'raw_std': float(x.std()),
        'detrended_std': float(detrended.std()), 'linear_slope_units_per_second': slope,
        'fitted_drift_over_window': slope * (len(x) - 1) / rate,
        'below_band_power_fraction': float(power[f < cfg.min_bpm / 60].sum() / power.sum()) if power.sum() else None,
        'longest_exact_constant_samples': longest_run(equal) + 1,
        'exact_equal_adjacent_pairs': int(equal.sum()),
        'minimum_count': int((x == x.min()).sum()), 'maximum_count': int((x == x.max()).sum()),
        'longest_minimum_run_samples': longest_run(x == x.min()),
        'longest_maximum_run_samples': longest_run(x == x.max()),
        'absolute_step_quantiles_50_95_99': np.quantile(abs(jumps), [.5, .95, .99]).tolist(),
        'largest_steps': [{'left_sample': int(i), 'right_sample': int(i + 1),
                           'delta': float(jumps[i])} for i in largest],
        'limitations': 'Exact plateaus/extrema are observable; ADC rails/units unknown. '
                       'Large steps and low-frequency energy do not establish motion, contact loss, or clipping.',
    }
    return result, (detrended, f, power)


def plot_windows(windows, output, rate, cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(windows), 4, figsize=(20, 3 * len(windows)), squeeze=False)
    for i, (x, report, (detrended, f, power)) in enumerate(windows):
        t = report['start_nominal_seconds'] + np.arange(len(x)) / rate
        axes[i, 0].plot(t, x, lw=.6)
        axes[i, 0].set(title=f"Window {i}: raw BVP", xlabel='Nominal seconds', ylabel='CSV units (unspecified)')
        axes[i, 1].plot(t, detrended, lw=.6)
        axes[i, 1].set(title='Linear detrend', xlabel='Nominal seconds')
        scaled = power / max(float(power.max()), np.finfo(float).tiny)
        for ax in axes[i, 2:]:
            ax.plot(f * 60, scaled, lw=.8)
            ax.axvspan(cfg.min_bpm, cfg.max_bpm, alpha=.12, color='green')
            ax.set(xlabel='Frequency × 60 (BPM)', ylabel='Power / full-spectrum maximum')
        axes[i, 2].set(title='Detrended Hann FFT: full axis', xlim=(0, rate * 30))
        axes[i, 3].set(title=f"{report['status']}: {report['rejection_reason'] or 'peak screen passed'}",
                       xlim=(0, cfg.max_bpm + 30))
        peak = report['winning_bin']
        axes[i, 3].axvline(peak['bpm'], color='red', lw=.7)
        for candidate in report['strongest_in_band_local_maxima']:
            axes[i, 3].plot(candidate['bpm'], candidate['power'] / max(float(power.max()), np.finfo(float).tiny),
                            marker='o', ms=3, color='black')
        axes[i, 3].text(.99, .95, f"peak fraction={report['spectral_peak_fraction']}; threshold={cfg.min_peak_fraction}",
                        transform=axes[i, 3].transAxes, ha='right', va='top', fontsize=7)
    fig.tight_layout()
    fig.savefig(output, dpi=130)
    plt.close(fig)


def read_json(path):
    return json.loads(path.read_text())


def audit(face_run, pulse_run, manifest, dataset_root, output):
    require_ignored(output)
    cfg = Settings()
    cfg.validate()
    saved = read_json(pulse_run / 'config.json')
    if saved['settings'] != asdict(cfg):
        raise ValueError('Saved settings differ from frozen baseline defaults')
    if read_json(pulse_run / 'status.json')['status'] != 'completed':
        raise ValueError('Completed saved pulse run required')
    face_config, times, regions, timing = load_face_run(face_run)
    if (saved['recording_id'] != face_config['recording_id']
            or saved['source'] != face_config['source']
            or saved['face_frames']['sha256'] != fingerprint(face_run / 'frames.jsonl', 'frames.jsonl')['sha256']):
        raise ValueError('Saved pulse/face provenance mismatch')
    path, entry = matched_bvp(manifest, dataset_root, face_config)
    if saved['reference'] != entry:
        raise ValueError('Saved reference differs from uniquely paired manifest reference')
    reference = reference_summary(path, cfg)
    if reference['status'] != 'completed':
        raise ValueError('Malformed BVP')
    reference_equal = reference == read_json(pulse_run / 'reference.json')
    rows = [json.loads(line) for line in (pulse_run / 'windows.jsonl').read_text().splitlines()]
    regenerated = []
    for region in REGIONS:
        r, _ = analyze_region(times, regions[region], times[0], timing['duration_seconds'], region, cfg)
        regenerated.extend(r)
    camera_equal = rows == regenerated
    output.mkdir(parents=True, exist_ok=False)
    write_private_json(output / 'status.json', {'status': 'running'})
    try:
        with path.open(newline='', encoding='utf-8-sig') as source:
            values = np.array([float(row[0]) for row in csv.reader(source)])
        n = round(cfg.window_seconds * 64)
        windows, reports = [], []
        for i, saved_row in enumerate(reference['windows']):
            x = values[i*n:(i+1)*n]
            report, arrays = describe_signal(x, 64, cfg)
            report.update(window_index=i, start_sample_inclusive=i*n, end_sample_exclusive=(i+1)*n,
                          start_nominal_seconds=i*n/64, end_nominal_seconds=(i+1)*n/64)
            if any(report[key] != saved_row[key] for key in
                   ('status', 'rejection_reason', 'estimated_bpm', 'spectral_peak_fraction')):
                raise ValueError('Window diagnostic disagrees with reference estimator')
            reports.append(report)
            windows.append((x, report, arrays))
        camera = [{**r, 'edge_diagnostic': edge_info(r['estimated_bpm'], 60 / cfg.window_seconds, cfg)} for r in rows]
        plot_windows(windows, output / 'bvp-windows.png', 64, cfg)
        report = {
            'schema_version': '1.0', 'settings': asdict(cfg), 'synchronization': 'unverified',
            'comparison_level': 'recording only; no offset estimated',
            'software': {'python': platform.python_version(), 'numpy': version('numpy'), 'matplotlib': version('matplotlib')},
            'inputs': {name: fingerprint(p, name) for name, p in {
                'manifest.json': manifest, 'saved-config.json': pulse_run / 'config.json',
                'saved-reference.json': pulse_run / 'reference.json', 'saved-windows.jsonl': pulse_run / 'windows.jsonl',
                'diagnostic-source.py': Path(__file__), 'pulse-source.py': Path(__file__).with_name('pulse.py')}.items()},
            'recording_id': saved['recording_id'], 'reference': entry,
            'reference_reproduced_exactly': reference_equal, 'camera_rows_reproduced_exactly': camera_equal,
            'implementation_check': 'passed' if reference_equal and camera_equal else 'saved/current discrepancy; investigate',
            'time_axis': 'BVP sample index / 64; half-open 1920-sample windows; unpadded FFT; Hz × 60',
            'sample_count': len(values), 'trailing_samples': len(values) % n,
            'bvp_windows': reports, 'camera_windows': camera,
            'interpretation': 'Diffuse/edge/reference spectra can be ambiguous; physical cause unresolved. '
                              'Acceptance is only the frozen engineering screen, not validated heart rate.',
        }
        write_private_json(output / 'report.json', report)
        (output / 'status.json').write_text(json.dumps({'status': 'completed'}) + '\n')
        return report
    except BaseException:
        (output / 'status.json').write_text(json.dumps({'status': 'failed'}) + '\n')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('face-run', 'pulse-run', 'manifest', 'dataset-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.face_run, args.pulse_run, args.manifest, args.dataset_root, args.output)
    print('Private diagnostics completed; saved/current reproduction: ' + report['implementation_check'])
    if report['implementation_check'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
