"""Opt-in, video-only diagnostics. Never reads questionnaires or changes pulse decisions."""
from dataclasses import asdict
import argparse
import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from stress_detection import pulse
from stress_detection.face_measurements import REGIONS as ROI_POINTS, face_masks, region_rgb
from stress_detection.pulse_diagnostics import describe_signal, spectrum
from stress_detection.validate_sample import require_ignored
from stress_detection.video_reader import VideoReader


def clean(value):
    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [clean(v) for v in value]
    if isinstance(value, np.ndarray): return clean(value.tolist())
    if isinstance(value, (np.floating, float)): return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.bool_): return bool(value)
    return value


def correlation(a, b):
    if np.std(a) <= 1e-12 or np.std(b) <= 1e-12: return None
    return float(np.corrcoef(a, b)[0, 1])


def candidate_band(f, power, bpm, width=2):
    selection = np.abs(f * 60 - bpm) <= width + 1e-9
    total = power.sum()
    return float(power[selection].sum() / total) if total > 0 else None


def checked_signal(signal, row, cfg):
    diagnostic, arrays = describe_signal(signal, cfg.grid_hz, cfg)
    if any(diagnostic[k] != row[k] for k in ('status', 'rejection_reason', 'estimated_bpm', 'spectral_peak_fraction')):
        raise ValueError('Spectrum differs from production')
    if diagnostic['spectral_peak_fraction'] is None:
        # argmax of a flat spectrum is arbitrary; never present it as a peak.
        diagnostic['winning_bin'] = None
        for key in ('strongest_in_band_bins', 'strongest_in_band_local_maxima', 'strongest_out_of_band_local_maxima'):
            diagnostic[key] = []
        diagnostic['strongest_full_spectrum_bin'] = None
    return diagnostic, arrays


def generate(folder):
    """Use existing face/pulse outputs; new diagnostic files are separate and private."""
    folder = Path(folder)
    require_ignored(folder)
    config, times, regions, timing = pulse.load_face_run(folder / 'face')
    with (folder / 'input.webm').open('rb') as source:
        source_hash = hashlib.file_digest(source, 'sha256').hexdigest()
    if source_hash != config['source']['sha256']: raise ValueError('Source video differs from face-run provenance')
    cfg = pulse.Settings()
    saved_config = json.loads((folder / 'pulse/config.json').read_text())
    if saved_config['settings'] != asdict(cfg): raise ValueError('Frozen pulse settings mismatch')
    with (folder / 'face/frames.jsonl').open() as source: frames = [json.loads(line) for line in source]
    with (folder / 'pulse/windows.jsonl').open() as source: saved = [json.loads(line) for line in source]
    regenerated = []
    for region in pulse.REGIONS:
        rows, _ = pulse.analyze_region(times, regions[region], times[0], timing['duration_seconds'], region, cfg)
        regenerated.extend(rows)
    if regenerated != saved: raise ValueError('Diagnostic replay differs from saved production decisions')
    out = folder / 'diagnostics'; out.mkdir(exist_ok=False, mode=0o700)
    relative = times - times[0]
    dt = np.diff(times)
    nuisance = {
        'face_brightness': np.array([(r.get('measurements') or {}).get('brightness', np.nan) for r in frames]),
        'landmark_motion': np.array([r.get('motion_face_sizes_per_second') if r.get('motion_face_sizes_per_second') is not None else np.nan for r in frames]),
    }
    for region, indices in ROI_POINTS.items():
        nuisance[region + '_x'] = np.array([np.mean(np.asarray(r['landmarks_normalized_xyz'])[indices, 0]) if r.get('landmarks_normalized_xyz') else np.nan for r in frames])
        nuisance[region + '_y'] = np.array([np.mean(np.asarray(r['landmarks_normalized_xyz'])[indices, 1]) if r.get('landmarks_normalized_xyz') else np.nan for r in frames])
        nuisance[region + '_pixels'] = np.array([r['regions'][region]['pixel_count'] for r in frames], dtype=float)
    report = {'privacy': 'Video-only opt-in diagnostics; no questionnaire data read.',
              'policy': config.get('policy'), 'settings': asdict(cfg), 'source_sha256': config['source']['sha256'],
              'duration_seconds': timing['duration_seconds'], 'timestamps': {
                  'frames': len(times), 'first_pts_seconds': times[0], 'last_pts_seconds': times[-1],
                  'last_frame_duration_seconds': timing['last_frame_duration_seconds'],
                  'interval_quantiles_seconds': np.quantile(dt, [0, .01, .5, .99, 1]),
                  'measured_interval_rate_hz': (len(times)-1)/(times[-1]-times[0]),
                  'nonpositive_intervals': int(np.sum(dt <= 0)), 'intervals_over_frozen_max_gap': int(np.sum(dt > cfg.max_gap_seconds + 1e-9))},
              'tracking': json.loads((folder / 'face/summary.json').read_text()), 'windows': [],
              'limitations': 'Diagnostic peaks/correlations do not establish cardiac origin, movement causality, lighting causality or accuracy. No reference measurement is supplied. Rejected production BPM remains null.'}
    # Summary contains video-only provenance and numeric quality; not questionnaire answers.
    report['tracking'].pop('preview_files', None)
    traces = {'original_seconds': relative, 'raw_rgb': regions, 'nuisance': nuisance, 'windows': []}
    plot_rows = []
    for window in range(int(np.floor((timing['duration_seconds'] + 1e-9) / cfg.window_seconds))):
        start = times[0] + window * cfg.window_seconds
        grid = start + np.arange(round(cfg.grid_hz * cfg.window_seconds)) / cfg.grid_hz
        uniform_nuisance = {}; nuisance_unavailable = {}
        for key, values in nuisance.items():
            uniform, _, reason = pulse.resample_window(times, np.repeat(values[:, None], 3, axis=1), start, cfg)
            if reason is None: uniform_nuisance[key] = spectrum(uniform[:, 0], cfg.grid_hz)[0]
            else: nuisance_unavailable[key] = reason
        signals, window_rows = {}, []
        trace = {'index': window, 'relative_seconds': grid-times[0], 'uniform_rgb': {}, 'diagnostic_signals': {}, 'detrended_nuisance': uniform_nuisance}
        for region in pulse.REGIONS:
            uniform, availability, rejection = pulse.resample_window(times, regions[region], start, cfg)
            trace['uniform_rgb'][region] = uniform
            for method in pulse.METHODS:
                key = method + '/' + region
                row = next(r for r in saved if r['region'] == region and r['method'] == method and r['window_index'] == window)
                item = {**row, 'interpolation': availability, 'diagnostic_candidate': None}
                if rejection is None:
                    try:
                        signal = pulse.extract_pulse(uniform, method, cfg.grid_hz, cfg)
                        diagnostic, (detrended, frequency, power) = checked_signal(signal, row, cfg)
                        item['diagnostic_candidate'] = diagnostic
                        if diagnostic['winning_bin'] is None: raise ValueError(diagnostic['rejection_reason'])
                        signals[key] = detrended
                        winner = diagnostic['winning_bin']['bpm']
                        item['harmonic_inspection_full_spectrum_power_fraction'] = {str(bpm): candidate_band(frequency, power, bpm) for bpm in (winner/2, winner, winner*2)}
                        item['nuisance_correlation'] = {k: correlation(detrended, v) for k, v in uniform_nuisance.items()}
                        item['nuisance_power_near_candidate'] = {k: candidate_band(*spectrum(v, cfg.grid_hz)[1:3], winner) for k,v in uniform_nuisance.items()}
                        trace['diagnostic_signals'][key] = {'raw': signal, 'detrended': detrended, 'hz': frequency, 'power': power, 'status': row['status'], 'use': 'Diagnostic only; rejected traces are not supported measurements.'}
                        plot_rows.append((window, key, grid-times[0], detrended, frequency, power, row, diagnostic))
                    except ValueError as exc:
                        if str(exc) not in ('unusable_channel_mean', 'degenerate_pos_projection', 'insufficient_pos_samples', 'flat_signal', 'no_in_band_power', 'invalid_signal'): raise
                        item['diagnostic_error'] = str(exc)
                window_rows.append(item)
        band_signals = {key: band_component(value, cfg.grid_hz, cfg) for key, value in signals.items()}
        band_nuisance = {key: band_component(value, cfg.grid_hz, cfg) for key, value in uniform_nuisance.items()}
        band_agreement = {a: {b: correlation(x, y) for b, y in band_signals.items()} for a, x in band_signals.items()}
        band_nuisance_correlation = {a: {b: correlation(x, y) for b, y in band_nuisance.items()} for a, x in band_signals.items()}
        agreement = {a: {b: correlation(x, y) for b,y in signals.items()} for a,x in signals.items()}
        report['windows'].append({'index': window, 'estimates': window_rows, 'zero_lag_signal_correlation': agreement, 'diagnostic_band_correlation': band_agreement, 'diagnostic_band_nuisance_correlation': band_nuisance_correlation, 'nuisance_unavailable': nuisance_unavailable, 'diagnostic_band_note': 'FFT mask 42–240 BPM for exploratory correlations only; no production filtering or decision change.'})
        traces['windows'].append(trace)
    # Decode again to inspect actual codec/color metadata and replay ROI means at selected frames.
    targets = {0, len(frames)//2, len(frames)-1}
    for key in ('face_brightness', 'landmark_motion'):
        values = nuisance[key]
        if np.isfinite(values).any(): targets.add(int(np.nanargmax(values)))
    overlays = []; colors = []; checks = []
    with VideoReader(folder / 'input.webm') as reader:
        for frame in reader:
            if frame.index not in targets: continue
            row = frames[frame.index]; rgb = frame.rgb.to_ndarray(format='rgb24')
            colors.append({'frame': frame.index, **{k: str(getattr(frame.rgb, k, None)) for k in ('colorspace', 'color_range', 'color_primaries', 'color_trc')}})
            if row.get('landmarks_normalized_xyz'):
                _, _, _, masks, _ = face_masks(row['landmarks_normalized_xyz'], rgb.shape[:2], config['measurements']['exclusion_margin_fraction'])
                differences = {r: np.max(abs(np.array(region_rgb(rgb, mask)['mean_rgb']) - row['regions'][r]['mean_rgb'])) if row['regions'][r]['valid'] else None for r,mask in masks.items()}
                checks.append({'frame': frame.index, 'saved_rgb_max_absolute_difference': differences,
                    'roi_center_x_pixels': {r: float(np.where(mask)[1].mean()) if np.any(mask) else None for r,mask in masks.items()}})
                overlays.append((frame.index, rgb, masks))
        report['decoder'] = reader.summary()
    # Inspect source color tags before conversion separately; RGB frames need not retain YUV tags.
    import av
    with av.open(str(folder / 'input.webm')) as container:
        stream = container.streams.video[0]; raw = next(container.decode(stream))
        report['source_encoding'] = {'codec': stream.codec_context.name, 'pixel_format': raw.format.name,
             **{k: str(getattr(raw,k,None)) for k in ('colorspace','color_range','color_primaries','color_trc')}}
    report['rgb_replay_checks'] = checks; report['rgb_frame_metadata'] = colors
    (out / 'analysis.json').write_text(json.dumps(clean(report), indent=2, allow_nan=False))
    (out / 'traces.json').write_text(json.dumps(clean(traces), allow_nan=False))
    plots(out, relative, regions, nuisance, plot_rows, overlays, cfg)
    return clean(report)


def band_component(values, hz, cfg):
    frequency = np.fft.rfftfreq(len(values), d=1/hz)
    transform = np.fft.rfft(values)
    transform[(frequency < cfg.min_bpm/60) | (frequency > cfg.max_bpm/60)] = 0
    return np.fft.irfft(transform, n=len(values))


def plots(out, times, regions, nuisance, rows, overlays, cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    for ax,(region,rgb) in zip(axes,regions.items()):
        for channel,color in enumerate(('red','green','blue')): ax.plot(times,rgb[:,channel],color=color,label=color,lw=.7)
        ax.set(title=region,ylabel='Decoded RGB / 0–255'); ax.legend(loc='upper right')
    axes[-1].set_xlabel('Seconds from first decoded PTS');fig.tight_layout();fig.savefig(out/'rgb-traces.png',dpi=140);plt.close(fig)
    if rows:
        fig, axes = plt.subplots((len(rows)+1)//2, 2, figsize=(15, 3.3*((len(rows)+1)//2)), squeeze=False)
        inspection_by_window = {}
        for row in rows:
            if row[-2]['status'] == 'accepted': inspection_by_window.setdefault(row[0], row[-1]['winning_bin']['bpm'])
        for ax, (window, key, _, _, f, p, row, _) in zip(axes.flat, rows):
            inspection = inspection_by_window.get(window)
            inside = (f*60 >= cfg.min_bpm) & (f*60 <= cfg.max_bpm)
            ax.plot(f[inside]*60, p[inside]/max(float(p[inside].max()), 1e-30), lw=.9)
            if inspection is not None: ax.axvline(inspection, color='gray', ls='--', lw=.7)
            ax.set(title=f'Window {window} · {key} · {row["status"]}', xlabel='Frequency × 60 (BPM)', ylabel='Power / in-band maximum', xlim=(42, 240))
        fig.tight_layout(); fig.savefig(out/'in-band-spectra.png', dpi=140); plt.close(fig)
        fig, axes = plt.subplots((len(rows)+1)//2, 2, figsize=(15, 3.3*((len(rows)+1)//2)), squeeze=False)
        for ax, (window, key, t, x, _, _, row, _) in zip(axes.flat, rows):
            from matplotlib.mlab import specgram
            power, frequencies, centers = specgram(x, NFFT=320, Fs=cfg.grid_hz, noverlap=280, mode='psd')
            image = ax.pcolormesh(centers + t[0], frequencies, 10*np.log10(np.maximum(power, np.finfo(float).tiny)), shading='auto')
            fig.colorbar(image, ax=ax, label='PSD / dB (extraction units²/Hz)')
            ax.set(title=f'Window {window} · {key} · diagnostic only', xlabel='PTS-relative seconds (8 s windows)', ylabel='Frequency / Hz', xlim=(float(t[0]), float(t[-1])), ylim=(cfg.min_bpm/60, cfg.max_bpm/60))
            inspection = inspection_by_window.get(window)
            if inspection is not None: ax.axhline(inspection/60, color='white', ls='--', lw=.7)
        fig.tight_layout(); fig.savefig(out/'time-frequency.png', dpi=140); plt.close(fig)
        fig,axes=plt.subplots(len(rows),2,figsize=(17,2.5*len(rows)),squeeze=False)
        for (ax,sp),(window,key,t,x,f,p,row,diagnostic) in zip(axes,rows):
            ax.plot(t,x,lw=.7);ax.set(title=f'{key} · {row["status"]} · {row["rejection_reason"] or "screen passed"}',xlabel='PTS-relative seconds',ylabel='Dimensionless GREEN ratio' if key.startswith('green/') else 'Dimensionless POS projection sum')
            sp.plot(f*60,p/max(float(p.max()),1e-30),lw=.8);sp.set(xlim=(0,300),xlabel='Frequency × 60 (BPM)',ylabel='Power / spectrum maximum')
            candidate=diagnostic['winning_bin']['bpm'];sp.axvline(candidate,color='red',lw=.7);sp.axvline(candidate/2,color='gray',ls='--');sp.set_title(f'Candidate {candidate:.1f}; peak fraction {row["spectral_peak_fraction"]:.6f}; gate ≥ {cfg.min_peak_fraction:.2f}')
        fig.tight_layout();fig.savefig(out/'processed-spectra.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(14,9),sharex=True)
    axes[0].plot(times,nuisance['face_brightness']);axes[0].set_ylabel('Face gray level / 0–255')
    axes[1].plot(times,nuisance['landmark_motion']);axes[1].set_ylabel('Landmark motion / face sizes/s')
    for region in regions:axes[2].plot(times,nuisance[region+'_pixels'],label=region)
    axes[2].legend();axes[2].set(ylabel='Usable ROI pixels',xlabel='PTS-relative seconds');fig.tight_layout();fig.savefig(out/'exposure-motion-regions.png',dpi=140);plt.close(fig)
    if overlays:
        fig,axes=plt.subplots(1,len(overlays),figsize=(5*len(overlays),4),squeeze=False)
        for ax,(index,rgb,masks) in zip(axes[0],overlays):
            ax.imshow(rgb)
            for region,mask in masks.items():ax.contour(mask>0,levels=[.5],linewidths=.8)
            ax.set_title(f'Decoded frame {index}');ax.axis('off')
        fig.tight_layout();fig.savefig(out/'roi-placement-private.png',dpi=120);plt.close(fig)


OWNERSHIP = 'still-private-video-diagnostics-v1\n'
ROOT = Path(__file__).resolve().parents[1]


def collect(recording, output, provenance='webcam'):
    """Explicit offline opt-in: retain a video-only bundle, never touch the original."""
    output = Path(output)
    require_ignored(output)
    if output.exists() or output.is_symlink(): raise ValueError('Output must be a new ignored directory')
    output.mkdir(parents=True, mode=0o700)
    try:
        (output / '.still-diagnostic-owned').write_text(OWNERSHIP)
        shutil.copyfile(recording, output / 'input.webm')
        (output / 'input.webm').chmod(0o600)
        subprocess.run([sys.executable, '-m', 'app_backend.worker', str(output.resolve()), provenance],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return generate(output)
    except BaseException:
        shutil.rmtree(output)
        raise


def delete_bundle(folder):
    folder = Path(folder)
    require_ignored(folder)
    if folder.is_symlink() or not (folder / '.still-diagnostic-owned').is_file() or (folder / '.still-diagnostic-owned').is_symlink():
        raise ValueError('Only an owned diagnostic bundle can be deleted')
    if (folder / '.still-diagnostic-owned').read_text() != OWNERSHIP:
        raise ValueError('Unknown diagnostic bundle marker')
    shutil.rmtree(folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--job-dir', type=Path, help='Existing private native face/pulse outputs')
    mode.add_argument('--recording', type=Path, help='Explicitly selected, already consented recording')
    mode.add_argument('--delete-bundle', type=Path, help='Delete an owned diagnostic bundle; original recording is separate')
    parser.add_argument('--source', choices=('webcam', 'prerecorded'), default='webcam', help='Actual recording source; label development inputs prerecorded')
    parser.add_argument('--output', type=Path, help='New ignored directory for a retained video diagnostic bundle')
    parser.add_argument('--confirm-private-diagnostics', action='store_true', help='Explicitly retain identifying video, face overlays and traces locally until manually deleted.')
    args = parser.parse_args()
    if args.delete_bundle:
        delete_bundle(args.delete_bundle)
    else:
        if not args.confirm_private_diagnostics:
            parser.error('Explicit --confirm-private-diagnostics is required; identifying files will be retained locally.')
        if args.recording:
            if not args.output: parser.error('--recording requires --output')
            collect(args.recording, args.output, args.source)
        else:
            if args.output: parser.error('--output is only valid with --recording')
            generate(args.job_dir)
