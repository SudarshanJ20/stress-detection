"""Resumable local UBFC-Phys engineering pilot; no acquisition or training."""

import argparse
import copy
from collections import Counter
from dataclasses import asdict
import fcntl
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

from .manifest import discover, fingerprint
from .policy import DEFAULT_POLICY, load_policy
from .pilot_state import (GIB, StageStore, atomic, digest, extract_zip, inspect_zip,
                          inventory, now, read)
from .pulse import (METHODS, REGIONS, Settings, analyze_region, load_face_run,
                    recording_summary, reference_summary)
from .validate_sample import inspect_info, inspect_numeric, missing_files, require_ignored
from .validate_sample import write_private_json

TASKS = ('T1', 'T2', 'T3')
ROOT = Path(__file__).resolve().parents[2]


def selection(path):
    config = read(path)
    if (config.get('schema_version') != '1.0' or config.get('final_test_cohort') != 'unassigned'
            or config.get('pilot_selected_before_quality') is not True
            or not isinstance(config.get('selection_reason'), str) or not config['selection_reason'].strip()
            or not isinstance(config.get('participants'), list) or not config['participants']):
        raise ValueError('Explicit participants, roles, prior selection reason and unassigned final test required')
    seen = set()
    for entry in config['participants']:
        p = entry.get('id', '')
        role = 'development_only' if p == 's25' else 'pilot_development'
        if (not re.fullmatch(r's[1-9][0-9]*', p) or p in seen or entry.get('role') != role
                or sum(k in entry for k in ('directory', 'zip')) != 1):
            raise ValueError('Invalid/duplicate participant, missing input, or forbidden role')
        seen.add(p)
        for key in ('directory', 'zip'):
            if key in entry:
                entry[key] = str(Path(entry[key]).expanduser().resolve())
        reuse = entry.get('reuse', {})
        if set(reuse) - {'manifest', 'face', 'pulse', 'reference'}:
            raise ValueError('Unsupported reuse stage')
        if 'manifest' in reuse:
            if Path(reuse['manifest']).name != 'manifest.json':
                raise ValueError('Reused manifest must be named manifest.json')
            reuse['manifest'] = str(Path(reuse['manifest']).expanduser().resolve())
        for key in ('face', 'pulse', 'reference'):
            for task, value in reuse.get(key, {}).items():
                if task not in TASKS:
                    raise ValueError('Unknown reuse task')
                reuse[key][task] = str(Path(value).expanduser().resolve())
    if len(seen - {'s25'}) > 2:
        raise ValueError('At most two additional participants per pilot batch')
    return config


def context(model, model_config, track_policy=None, policy_path=DEFAULT_POLICY):
    policy, stamp = load_policy(policy_path)
    frozen_track = policy['tracking']['policy']
    if track_policy is not None and track_policy != frozen_track:
        raise ValueError('Track override conflicts with frozen pilot policy')
    info = read(model_config)
    if fingerprint(model, model.name)['sha256'] != info['sha256']:
        raise ValueError('Local face model does not match model configuration')
    return {'policy': stamp, 'policy_path': str(policy_path.resolve()),
            'pulse_settings': policy['pulse']['settings'], 'face_track_policy': frozen_track,
            'face_settings': policy['tracking']['measurements'],
            'model': info, 'python': platform.python_version(),
            'software': {p: version(p) for p in ('av', 'numpy', 'mediapipe', 'opencv-contrib-python', 'matplotlib')},
            'code': {p.name: fingerprint(p, p.name)['sha256'] for p in sorted(Path(__file__).parent.glob('*.py'))}}


def command(module, arguments, log):
    args = [sys.executable, '-m', 'stress_detection.' + module, *map(str, arguments)]
    with log.open('x') as target:
        target.write(json.dumps(args) + '\n')
        target.flush()
        subprocess.run(args, cwd=ROOT, stdout=target, stderr=subprocess.STDOUT, check=True)


def verify_validation(output):
    report = read(output / 'validation.json')
    if (report.get('validation_completed') is not True or report.get('missing_files')
            or len(report.get('signals', [])) != 6 or len(report.get('videos', [])) != 3
            or not all(r.get('valid') for r in report['signals'])
            or not report.get('info', {}).get('valid') or not report.get('questionnaire', {}).get('valid')):
        raise ValueError('Incomplete validation or unsafe participant/reference structure')


def verify_manifest(output, participant, files):
    report = read(output / 'manifest.json')
    records = report['records']
    if (report.get('schema_version') != '1.0' or report.get('validation_status') not in ('passed', 'needs_review')
            or report.get('discovery_issues') or len(records) != 3
            or {r['recording_id'] for r in records} != {participant + '/' + t for t in TASKS}):
        raise ValueError('Incomplete/failed/wrong-participant manifest')
    for record in records:
        if (record.get('camera_eligibility_policy') != 'decoded-pts-v1'
                or record['video'].get('camera_eligibility_policy') != 'decoded-pts-v1'):
            raise ValueError('Manifest lacks audited timing policy; rebuild eligibility')
        if record['participant_id'] != participant or record['validation_status'] not in ('passed', 'needs_review'):
            raise ValueError('Manifest participant/status mismatch')
        for kind, ext in (('vid', 'avi'), ('bvp', 'csv'), ('eda', 'csv')):
            name = f'{kind}_{participant}_{record["task_id"]}.{ext}'
            expected = {**files[name], 'path': participant + '/' + name}
            if record['files'][kind] != expected or len(record['candidates'][kind]) != 1:
                raise ValueError('Manifest input fingerprint/pairing mismatch')
        if (record['signals']['bvp']['sampling_rate_hz'] != 64
                or record['signals']['eda']['sampling_rate_hz'] != 4):
            raise ValueError('Manifest rate/decode mismatch')


def save_reference(output, path):
    """Use the frozen independent wrist estimator even when camera input fails."""
    output.mkdir(parents=True, exist_ok=False)
    write_private_json(output / 'reference.json', reference_summary(path, Settings()))


def verify_reference(output, path):
    report = read(output / 'reference.json')
    if report.get('status') != 'completed' or report != reference_summary(path, Settings()):
        raise ValueError('Independent reference incomplete or not reproducible')


def verify_face(output, record, ctx):
    cfg, times, _, _ = load_face_run(output)
    summary = read(output / 'summary.json')
    if (cfg.get('max_frames') is not None or cfg['source'] != record['files']['vid']
            or cfg['recording_id'] != record['recording_id'] or cfg['model'] != ctx['model']
            or cfg['measurements'] != ctx['face_settings']
            or ('policy' in ctx and cfg.get('policy') != ctx['policy'])
            or cfg.get('python') != ctx['python']
            or cfg['software'] != {p: ctx['software'][p] for p in ('av', 'mediapipe', 'numpy', 'opencv-contrib-python')}
            or len(times) != record['video']['decoded_frames']
            or summary['reader']['decoded_frames'] != len(times)):
        raise ValueError('Face provenance/settings/completeness mismatch')


def verify_pulse(output, face, record, folder):
    cfg = read(output / 'config.json')
    if (read(output / 'status.json')['status'] != 'completed' or cfg['settings'] != asdict(Settings())
            or cfg['recording_id'] != record['recording_id'] or cfg['source'] != record['files']['vid']
            or cfg['reference'] != record['files']['bvp']
            or cfg['face_frames']['sha256'] != fingerprint(face / 'frames.jsonl', 'frames.jsonl')['sha256']
            or cfg['software'] != {'numpy': version('numpy'), 'python': platform.python_version()}
            or cfg['source_model'] != read(face / 'config.json')['model']):
        raise ValueError('Pulse completion/settings/provenance mismatch')
    _, times, regions, timing = load_face_run(face)
    rows, traces = [], []
    for region in REGIONS:
        r, t = analyze_region(times, regions[region], times[0], timing['duration_seconds'], region, Settings())
        rows.extend(r)
        traces.extend(t)
    if rows != [json.loads(line) for line in (output / 'windows.jsonl').read_text().splitlines()]:
        raise ValueError('Saved camera decisions do not reproduce')
    if (traces != [json.loads(line) for line in (output / 'pulse-traces.jsonl').read_text().splitlines()]
            or timing != read(output / 'source-timing.json')):
        raise ValueError('Saved pulse traces/timing do not reproduce')
    ref = reference_summary(folder / Path(record['files']['bvp']['path']).name, Settings())
    if ref != read(output / 'reference.json'):
        raise ValueError('Saved reference does not reproduce')
    groups = recording_summary(rows)
    for group in groups.values():
        a, b = group['median_bpm'], ref.get('median_bpm')
        group['camera_minus_reference_median_bpm'] = a - b if a is not None and b is not None else None
    summary = read(output / 'summary.json')
    if summary['status'] != 'completed' or summary['groups'] != groups:
        raise ValueError('Incomplete/incorrect pulse summary')


def verify_diagnostics(output):
    report = read(output / 'report.json')
    if (read(output / 'status.json')['status'] != 'completed' or report['implementation_check'] != 'passed'
            or not report['reference_reproduced_exactly'] or not report['camera_rows_reproduced_exactly']
            or not (output / 'bvp-windows.png').is_file()):
        raise ValueError('Incomplete/failed diagnostics')


def space(output, additional, storage):
    existing = output
    while not existing.exists():
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    required = math.ceil((storage['reserve_gib'] + storage['workspace_gib']) * GIB + additional)
    return {'free_bytes': free, 'additional_budget_bytes': additional,
            'reserve_and_workspace_bytes': required - additional,
            'required_free_bytes': required, 'passed': free >= required}


def input_audit(entry):
    if 'zip' in entry:
        path = Path(entry['zip'])
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/symlink ZIP')
        return {'zip': fingerprint(path, path.name), 'zip_audit': inspect_zip(path, entry['id'])}
    folder = Path(entry['directory'])
    if folder.name != entry['id'] or folder.is_symlink() or not folder.is_dir():
        raise ValueError('Directory must match participant ID and be nonsymlink')
    files = inventory(folder)
    missing = missing_files(folder)
    records, issues = discover(folder.parent, entry['id'])
    structural_errors = [i['code'] for i in issues] + [w for r in records for w in r['warnings']]
    signals = {}
    for task in TASKS:
        for kind, rate in (('bvp', 64), ('eda', 4)):
            name = f'{kind}_{entry["id"]}_{task}.csv'
            if (folder / name).is_file():
                signals[name] = inspect_numeric(folder / name, 1, rate)
                if not signals[name]['valid']:
                    structural_errors.append('malformed_signal:' + name)
    info = folder / f'info_{entry["id"]}.txt'
    questionnaire = folder / f'selfReportedAnx_{entry["id"]}.csv'
    if info.is_file() and not inspect_info(info, entry['id'])['valid']:
        structural_errors.append('malformed_info')
    if questionnaire.is_file():
        audit = inspect_numeric(questionnaire, 2)
        if not audit['valid'] or audit['rows'] != 3:
            structural_errors.append('malformed_questionnaire')
    return {'files': files, 'missing_files': missing, 'structural_errors': structural_errors,
            'signals': signals, 'input_bytes': sum(f['bytes'] for f in files.values())}


def spec(ctx, entry, inputs, stage):
    return {'context': ctx, 'participant': entry['id'], 'role': entry['role'],
            'inputs': copy.deepcopy(inputs), 'stage': stage}


def task_specs(ctx, entry, files, manifest, record, face=None, pulse=None):
    base = {'files': files, 'manifest': fingerprint(manifest, 'manifest.json')}
    result = {s: spec(ctx, entry, base, s) for s in ('reference', 'face')}
    if face:
        result['pulse'] = spec(ctx, entry, {**base, 'face_files': inventory(face)}, 'pulse')
    if pulse:
        result['diagnostics'] = spec(ctx, entry, {**base, 'face_files': inventory(face),
                                                'pulse_files': inventory(pulse)}, 'diagnostics')
    return result


def plan(config, output, ctx, storage):
    store = StageStore(output / 'stages')
    participants, additional = [], 0
    for entry in config['participants']:
        p = {'id': entry['id'], 'role': entry['role'], 'tasks': list(TASKS), 'stages': [], 'errors': []}
        participants.append(p)
        try:
            inputs = input_audit(entry)
            p['inputs'] = inputs
            if inputs.get('missing_files'):
                p['errors'].append('missing required files: ' + ', '.join(inputs['missing_files']))
            p['errors'].extend(inputs.get('structural_errors', []))
            files = inputs.get('files')
            if 'zip' in inputs:
                extraction = store.lookup(entry['id'] + '/extract', digest(spec(ctx, entry, inputs, 'extract')))
                p['stages'].append({'stage': 'extract', 'decision': 'resume' if extraction else 'run',
                                    'declared_bytes': inputs['zip_audit']['declared_extracted_bytes']})
                if extraction:
                    files = inventory(Path(extraction['output']) / entry['id'])
                else:
                    additional += inputs['zip_audit']['declared_extracted_bytes']
            additional += math.ceil(storage['outputs_gib_per_participant'] * GIB)
            if files is None or p['errors']:
                p['stages'].extend({'stage': s, 'decision': 'pending valid extraction/inputs'}
                                   for s in ('validate', 'manifest', *[t + '/' + s for t in TASKS for s in ('reference', 'face', 'pulse', 'diagnostics')]))
                continue
            validation = store.lookup(entry['id'] + '/validate', digest(spec(ctx, entry, files, 'validate')))
            p['stages'].append({'stage': 'validate', 'decision': 'resume' if validation else 'run'})
            signature = spec(ctx, entry, files, 'manifest')
            cached = store.lookup(entry['id'] + '/manifest', digest(signature))
            candidate = entry.get('reuse', {}).get('manifest')
            manifest_dir = Path(cached['output']) if cached else Path(candidate).parent if candidate else None
            if manifest_dir:
                try:
                    verify_manifest(manifest_dir, entry['id'], files)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    p.setdefault('incompatible_reuse', []).append(
                        {'stage': 'manifest', 'candidate': str(manifest_dir), 'reason': str(exc)})
                    manifest_dir = None
            p['stages'].append({'stage': 'manifest', 'decision': 'resume' if cached else 'verify-import' if manifest_dir else 'run'})
            for task in TASKS:
                face = pulse = None
                if manifest_dir:
                    mf = manifest_dir / 'manifest.json'
                    record = next(r for r in read(mf)['records'] if r['task_id'] == task)
                for stage in ('reference', 'face', 'pulse', 'diagnostics'):
                    if manifest_dir and stage != 'reference' and record['validation_status'] != 'passed':
                        p['stages'].append({'stage': task + '/' + stage, 'decision': 'blocked: ineligible camera record'})
                        continue
                    key = entry['id'] + '/' + task + '/' + stage
                    cached = None
                    specs = task_specs(ctx, entry, files, mf, record, face, pulse) if manifest_dir else {}
                    if stage in specs:
                        cached = store.lookup(key, digest(specs[stage]))
                    candidate = entry.get('reuse', {}).get(stage, {}).get(task)
                    selected = Path(cached['output']) if cached else Path(candidate) if candidate else None
                    if selected and not cached:
                        try:
                            if stage == 'reference' and manifest_dir:
                                folder = Path(entry.get('directory', ''))
                                verify_reference(selected, folder / Path(record['files']['bvp']['path']).name)
                            elif stage == 'face' and manifest_dir:
                                verify_face(selected, record, ctx)
                            elif stage == 'pulse' and face:
                                folder = Path(entry.get('directory', ''))
                                if not folder.is_dir():
                                    raise ValueError('Pulse import awaits extracted input')
                                verify_pulse(selected, face, record, folder)
                            else:
                                raise ValueError('Stage dependencies unavailable')
                        except (OSError, ValueError, KeyError, TypeError) as exc:
                            p.setdefault('incompatible_reuse', []).append(
                                {'stage': task + '/' + stage, 'candidate': str(selected), 'reason': str(exc)})
                            selected = None
                    p['stages'].append({'stage': task + '/' + stage,
                                        'decision': 'resume' if cached else 'verify-import' if selected else 'run after dependencies'})
                    if stage == 'face':
                        face = selected
                    elif stage == 'pulse':
                        pulse = selected
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
            p['errors'].append(f'{type(exc).__name__}: {exc}')
    disk = space(output, additional, storage)
    selection_matches = not (output / 'selection.json').exists() or read(output / 'selection.json') == config
    return {'schema_version': '1.0', 'mode': 'dry-run', 'participants': participants, 'disk': disk,
            'storage_policy': storage, 'context': ctx, 'synchronization': 'unverified',
            'selection_matches_frozen_root': selection_matches,
            'passed': selection_matches and disk['passed'] and not any(p['errors'] for p in participants)}


def execute_participant(entry, output, ctx, storage, events):
    p = entry['id']
    store = StageStore(output / 'stages')
    inputs = input_audit(entry)

    def stage(key, inputs, action, verify, candidate=None, extra=0):
        if not space(output, 0, storage)['passed']:
            raise ValueError('Insufficient free disk before stage')
        def guarded_action(out, log):
            # A resumed extraction already occupies disk: budget it only for new work.
            if not space(output, extra + storage['outputs_gib_per_participant'] * GIB, storage)['passed']:
                raise ValueError('Insufficient free disk for new stage output')
            action(out, log)
        print(p, key, flush=True)
        meta = store.run(p + '/' + key, spec(ctx, entry, inputs, key.split('/')[-1]), guarded_action, verify, candidate)
        events.append({**meta, 'participant': p})
        print(p, key, meta['decision'], flush=True)
        return Path(meta['output'])

    if 'zip' in inputs:
        def verify_extraction(path):
            if missing_files(path / p):
                raise ValueError('Incomplete extraction')
        extracted = stage('extract', inputs,
                          lambda out, log: extract_zip(Path(entry['zip']), p, out), verify_extraction,
                          extra=inputs['zip_audit']['declared_extracted_bytes'])
        folder = extracted / p
        files = inventory(folder)
    else:
        folder = Path(entry['directory'])
        files = inputs['files']
    stages = {}
    stages['validate'] = stage('validate', files,
        lambda out, log: command('validate_sample', [folder, '--output', out, '--retain-failures'], log), verify_validation)
    candidate = entry.get('reuse', {}).get('manifest')
    stages['manifest'] = stage('manifest', files,
        lambda out, log: command('manifest', [folder.parent, '--participant', p, '--output', out / 'manifest.json', '--retain-failures'], log),
        lambda out: verify_manifest(out, p, files), Path(candidate).parent if candidate else None)
    manifest = stages['manifest'] / 'manifest.json'
    records = {r['task_id']: r for r in read(manifest)['records']}
    failures = {}
    for task in TASKS:
        record = records[task]
        base = {'files': files, 'manifest': fingerprint(manifest, 'manifest.json')}
        try:
            bvp = folder / Path(record['files']['bvp']['path']).name
            stages[task + '/reference'] = stage(task + '/reference', base,
                lambda out, log: save_reference(out, bvp), lambda out: verify_reference(out, bvp),
                Path(entry['reuse']['reference'][task]) if task in entry.get('reuse', {}).get('reference', {}) else None)
            if record['validation_status'] != 'passed':
                failures[task] = 'structural_camera_ineligible: ' + ','.join(record.get('warnings', []))
                continue
            reuse = entry.get('reuse', {})
            candidate = reuse.get('face', {}).get(task)
            face = stage(task + '/face', base,
                lambda out, log: command('face_quality', ['--input', folder / Path(record['files']['vid']['path']).name,
                    '--manifest', manifest, '--model', ctx['model_path'], '--model-config', ctx['model_config_path'],
                    '--track-policy', ctx.get('face_track_policy', 'contiguous'),
                    *(['--policy', ctx['policy_path']] if 'policy_path' in ctx else []), '--output', out], log),
                lambda out: verify_face(out, record, ctx), Path(candidate) if candidate else None)
            stages[task + '/face'] = face
            base['face_files'] = inventory(face)
            candidate = reuse.get('pulse', {}).get(task)
            pulse = stage(task + '/pulse', base,
                lambda out, log: command('pulse', ['--face-run', face, '--manifest', manifest,
                    '--dataset-root', folder.parent, '--output', out], log),
                lambda out: verify_pulse(out, face, record, folder), Path(candidate) if candidate else None)
            stages[task + '/pulse'] = pulse
            base['pulse_files'] = inventory(pulse)
            diagnostics = stage(task + '/diagnostics', base,
                lambda out, log: command('pulse_diagnostics', ['--face-run', face, '--pulse-run', pulse,
                    '--manifest', manifest, '--dataset-root', folder.parent, '--output', out], log), verify_diagnostics)
            stages[task + '/diagnostics'] = diagnostics
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
            failures[task] = f'{type(exc).__name__}: {exc}'
    # Inputs changed during processing cannot acquire a successful batch receipt.
    if files != inventory(folder):
        raise ValueError('Participant inputs changed during processing')
    return folder, stages, failures


def summarize(entry, folder, stages, failures):
    tasks, windows = [], []
    manifest = read(stages['manifest'] / 'manifest.json') if 'manifest' in stages else None
    records = {r['task_id']: r for r in manifest['records']} if manifest else {}
    for task in TASKS:
        face = stages.get(task + '/face')
        pulse = stages.get(task + '/pulse')
        diagnostics = stages.get(task + '/diagnostics')
        wrist = stages.get(task + '/reference')
        fs = read(face / 'summary.json') if face else {}
        ps = read(pulse / 'summary.json') if pulse else {}
        ds = read(diagnostics / 'report.json') if diagnostics else {}
        video_duration = records.get(task, {}).get('video', {}).get('observed_duration_seconds')
        count = ps.get('scheduled_windows_per_group', int(video_duration // 30) if video_duration is not None else None)
        reason = failures.get(task)
        camera = ds.get('camera_windows', []) or ([json.loads(line) for line in (pulse / 'windows.jsonl').read_text().splitlines()] if pulse else [])
        if not pulse and count is not None:
            camera = [{'method': method, 'region': region, 'window_index': i, 'status': 'rejected',
                       'estimated_bpm': None, 'rejection_reason': 'stage_failure'}
                      for i in range(count) for method in METHODS for region in REGIONS]
        if pulse:
            reference = read(pulse / 'reference.json')
        elif wrist:
            reference = read(wrist / 'reference.json')
        else:
            path = folder / f'bvp_{entry["id"]}_{task}.csv' if folder else None
            audit = inspect_numeric(path, 1, 64) if path and path.is_file() else {}
            ref_count = audit['rows'] // 1920 if audit.get('valid') else None
            reference = {'accepted': 0, 'total': ref_count, 'coverage': 0 if ref_count else None,
                         'windows': [{'window_index': i, 'status': 'rejected', 'rejection_reason': 'stage_failure',
                                      'estimated_bpm': None} for i in range(ref_count or 0)]}
        camera_edges = [r for r in ds.get('camera_windows', []) if (r.get('edge_diagnostic') or {}).get('near_edge_within_one_bin')]
        bvp_edges = [r['window_index'] for r in ds.get('bvp_windows', []) if r['winning_bin']['edges']['near_edge_within_one_bin']]
        for source, rows in (('camera', camera), ('bvp', reference.get('windows', []))):
            for i, r in enumerate(rows):
                extra = {}
                if source == 'bvp':
                    extra['window_index'] = i
                    if ds:
                        extra['winning_candidate'] = ds['bvp_windows'][i]['winning_bin']
                windows.append({'participant': entry['id'], 'role': entry['role'], 'task': task,
                                'source': source, **r, **extra, 'stage_failure': reason})
        tasks.append({'participant': entry['id'], 'role': entry['role'], 'task': task,
            'status': 'failed' if reason else 'completed', 'failure': reason,
            'camera_validation_status': records.get(task, {}).get('validation_status'),
            'camera_validation_warnings': records.get(task, {}).get('warnings', []),
            'scheduled_camera_windows_per_group': count, 'scheduled_bvp_windows': reference.get('total'),
            'unknown_window_inventory': count is None or reference.get('total') is None,
            'face_detection_coverage': fs.get('detection_coverage'), 'face_tracked_coverage': fs.get('tracked_coverage'),
            'track_event_counts': fs.get('track_event_counts'), 'track_segments': fs.get('track_segments'),
            'region_coverage': fs.get('region_coverage'), 'face_status_counts': fs.get('frame_status_counts'),
            'camera_groups': recording_summary(camera),
            'recording_comparisons': ps.get('groups'),
            'bvp': {k: reference.get(k) for k in ('accepted', 'total', 'coverage', 'median_bpm')},
            'camera_edge_flags': [{k: r[k] for k in ('method', 'region', 'window_index')} for r in camera_edges],
            'bvp_candidate_edge_windows': bvp_edges,
            'camera_rejections': dict(Counter(r['rejection_reason'] for r in camera if r['status'] != 'accepted')),
            'bvp_rejections': dict(Counter(r['rejection_reason'] for r in reference.get('windows', []) if r['status'] != 'accepted')),
            'diagnostics_status': 'completed' if diagnostics else 'unavailable',
            'source_face_runtime_seconds': fs.get('total_seconds'),
            'comparison': 'recording-level medians only; synchronization unverified'})
    return tasks, windows


def aggregate(tasks):
    participants = sorted({t['participant'] for t in tasks})
    groups = {}
    for key in (m + '/' + r for m in METHODS for r in REGIONS):
        per_person = []
        for participant in participants:
            selected = [t for t in tasks if t['participant'] == participant]
            known = all(t['scheduled_camera_windows_per_group'] is not None for t in selected)
            accepted = sum(t['camera_groups'][key]['accepted'] for t in selected)
            total = sum(t['camera_groups'][key]['total'] for t in selected)
            per_person.append({'participant': participant, 'accepted': accepted, 'known_total': total,
                               'complete_denominator': known, 'coverage': accepted / total if known and total else None})
        coverages = [p['coverage'] for p in per_person if p['coverage'] is not None]
        groups[key] = {'participants': per_person,
                       'equal_participant_coverage': sum(coverages) / len(coverages)
                           if coverages and len(coverages) == len(per_person) else None,
                       'participants_with_unknown_coverage': sum(p['coverage'] is None for p in per_person)}
    return {'participant_count': len(participants), 'scheduled_tasks': len(tasks),
            'failed_tasks': sum(t['status'] != 'completed' for t in tasks),
            'tasks_with_unknown_window_inventory': sum(t['unknown_window_inventory'] for t in tasks),
            'camera_groups': groups,
            'bvp_accepted': sum(t['bvp']['accepted'] or 0 for t in tasks),
            'bvp_known_total': sum(t['bvp']['total'] or 0 for t in tasks),
            'camera_edge_flag_count': sum(len(t['camera_edge_flags']) for t in tasks),
            'bvp_candidate_edge_flag_count': sum(len(t['bvp_candidate_edge_windows']) for t in tasks),
            'tasks_without_edge_diagnostics': sum(t['diagnostics_status'] != 'completed' for t in tasks)}


def run(config, output, ctx, storage):
    require_ignored(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        frozen = output / 'selection.json'
        if frozen.exists() and read(frozen) != config:
            raise ValueError('Selection/roles changed; use a new runner output root')
        if not frozen.exists():
            atomic(frozen, config)
        invocation = output / 'invocations' / (str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        invocation.mkdir(parents=True)
        started = time.perf_counter()
        atomic(invocation / 'status.json', {'status': 'running', 'started': now()})
        events, tasks, windows = [], [], []
        try:
            preflight = plan(config, output, ctx, storage)
            atomic(invocation / 'plan.json', preflight)
            stop = None if preflight['passed'] else 'preflight failed; inspect plan.json'
            for entry in config['participants']:
                folder, stages, failures = Path(entry['directory']) if 'directory' in entry else None, {}, {}
                if stop:
                    failures = {t: stop for t in TASKS}
                else:
                    try:
                        folder, stages, failures = execute_participant(entry, output, ctx, storage, events)
                    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
                        stop = f'{type(exc).__name__}: {exc}'
                        failures = {t: stop for t in TASKS}
                t, w = summarize(entry, folder, stages, failures)
                tasks.extend(t)
                windows.extend(w)
            with (invocation / 'windows.jsonl').open('x') as target:
                for row in windows:
                    target.write(json.dumps(row, allow_nan=False) + '\n')
            summary = {'status': 'failed' if any(t['status'] == 'failed' for t in tasks) else 'completed',
                       'selection': config, 'context': ctx, 'storage_policy': storage,
                       'synchronization': 'unverified', 'comparison': 'recording only; no offset estimation',
                       'development_tasks': [t for t in tasks if t['participant'] == 's25'],
                       'pilot_tasks': [t for t in tasks if t['participant'] != 's25'],
                       'pilot_summary': aggregate([t for t in tasks if t['participant'] != 's25']),
                       'development_summary': aggregate([t for t in tasks if t['participant'] == 's25']),
                       'pilot_participants': [e['id'] for e in config['participants'] if e['id'] != 's25'],
                       'stage_events': events, 'stage_decisions': dict(Counter(e['decision'] for e in events)),
                       'failed_or_incomplete_attempts': [read(p) for p in (output / 'stages').rglob('receipt.json')
                                                          if read(p).get('status') != 'completed'],
                       'runtime_seconds': time.perf_counter() - started,
                       'runner_tree_bytes': sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
                       'referenced_output_bytes_by_stage': {e['key']: e['output_bytes'] for e in events},
                       'disk_after': space(output, 0, storage),
                       'retained_input_bytes': {p['id']: p.get('inputs', {}).get('input_bytes',
                           p.get('inputs', {}).get('zip', {}).get('bytes')) for p in preflight['participants']},
                       'storage_note': 'Tree is logical bytes, includes preserved attempts; stage references can share files. Original archives retained.'}
            atomic(invocation / 'summary.json', summary)
            atomic(invocation / 'status.json', {'status': summary['status'], 'ended': now()})
            print('Private invocation:', invocation, 'status:', summary['status'], flush=True)
            return summary
        except BaseException as exc:
            atomic(invocation / 'status.json', {'status': 'failed', 'failure': f'{type(exc).__name__}: {exc}', 'ended': now()})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--track-policy', choices=('contiguous', 'bounded-reacquire'), default=None)
    parser.add_argument('--policy', type=Path, default=DEFAULT_POLICY)
    parser.add_argument('--model', type=Path, default=ROOT / 'models/mediapipe/face_landmarker.task')
    parser.add_argument('--model-config', type=Path, default=ROOT / 'configs/face-landmarker.json')
    parser.add_argument('--reserve-gib', type=float, default=100)
    parser.add_argument('--workspace-gib', type=float, default=40)
    parser.add_argument('--outputs-gib-per-participant', type=float, default=5)
    args = parser.parse_args()
    storage = {k: getattr(args, k) for k in ('reserve_gib', 'workspace_gib', 'outputs_gib_per_participant')}
    if any(not math.isfinite(v) or v < 0 for v in storage.values()):
        parser.error('Storage allowances must be finite and nonnegative')
    config = selection(args.selection)
    require_ignored(args.output)
    ctx = context(args.model, args.model_config, args.track_policy, args.policy)
    ctx.update(model_path=str(args.model.resolve()), model_config_path=str(args.model_config.resolve()))
    if args.dry_run:
        result = plan(config, args.output, ctx, storage)
        print(json.dumps(result, indent=2, allow_nan=False))
        if not result['passed']:
            raise SystemExit(1)
    else:
        if run(config, args.output, ctx, storage)['status'] != 'completed':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
