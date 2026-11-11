"""Raw, camera-only original-window feature tables; no fitting or wrist alignment."""

import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
import platform
import re
import time

import numpy as np

from .face_measurements import normalized_motion
from .manifest import TASK_CONDITIONS, fingerprint
from .pilot_state import atomic, digest, inventory, now, read
from .policy import load_policy
from .pulse import METHODS, REGIONS, Settings
from .pulse_diagnostics import edge_info
from .validate_sample import require_ignored

VERSION = 'window-features-v1'
ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'configs/window-features-v1.json'
MIN_FRACTION = .90
MIN_SAMPLES = 2
MAX_MOTION_GAP = .15
APERTURES = {'mouth': ([13, 14], [61, 291]),
             'eye_a': ([159, 145], [33, 133]),
             'eye_b': ([386, 374], [263, 362])}
BEHAVIOUR = ['beh_mouth_mean', 'beh_mouth_std', 'beh_mouth_p95',
             'beh_eye_mean', 'beh_eye_std', 'beh_eye_p10',
             'beh_motion_median', 'beh_motion_p95']
PULSE = [f'cam_{m}_{r}_bpm' for m in METHODS for r in REGIONS]
COVERAGE = ['q_face_detected_fraction', 'q_track_fraction', 'q_multiple_faces_fraction',
            'q_clipped_face_fraction', 'q_timestamp_issue_fraction', 'q_long_gap_fraction',
            'q_track_break_fraction', 'q_no_frames', 'q_mouth_valid_fraction',
            'q_eye_valid_fraction', 'q_motion_valid_fraction', 'q_brightness_change_valid_fraction']
VIDEO_QUALITY = COVERAGE + ['q_brightness_mean', 'q_brightness_std', 'q_dark_fraction_mean',
    'q_saturated_fraction_mean', 'q_laplacian_variance_mean', 'q_face_area_mean',
    'q_brightness_change_abs_median'] + [f'q_region_{r}_{s}' for r in REGIONS for s in ('valid_fraction', 'area_mean')]
PULSE_QUALITY = [f'q_pulse_{m}_{r}_{s}' for m in METHODS for r in REGIONS
                 for s in ('missing', 'peak_fraction', 'near_edge')]
IDENTIFIERS = ['id_window_key', 'id_participant', 'id_role', 'id_recording', 'id_task',
    'id_window_index', 'id_start_seconds', 'id_end_seconds', 'id_origin_fraction', 'id_frame_count',
    'id_video_sha256', 'id_frames_sha256', 'id_pulse_sha256', 'id_face_config_sha256',
    'id_manifest_sha256', 'id_summary_sha256', 'id_face_run', 'id_pulse_run', 'id_manifest',
    'id_policy_version', 'id_policy_sha256', 'id_feature_version', 'id_feature_schema_sha256', 'id_policy_basis']


def schema():
    groups = {'identifiers_and_provenance': IDENTIFIERS,
        'facial_behaviour': BEHAVIOUR,
        'camera_pulse': [f'cam_{m}_{r}_{s}' for m in METHODS for r in REGIONS for s in ('bpm', 'status', 'reason')],
        'video_quality_and_missingness': VIDEO_QUALITY + PULSE_QUALITY +
            ['q_mouth_reason', 'q_eye_reason', 'q_motion_reason'],
        'task_labels': ['label_condition'],
        'reference_only_diagnostics': ['ref_participant', 'ref_task', 'ref_time_basis', 'ref_wrist', 'ref_eda_metadata']}
    missingness = [c for c in COVERAGE if c not in ('q_clipped_face_fraction', 'q_long_gap_fraction',
                                                  'q_timestamp_issue_fraction', 'q_track_break_fraction')]
    missingness += [f'q_region_{r}_valid_fraction' for r in REGIONS]
    missingness += [f'q_pulse_{m}_{r}_missing' for m in METHODS for r in REGIONS]
    lists = {'facial_only': BEHAVIOUR, 'pulse_only': PULSE, 'ordinary_fusion': BEHAVIOUR + PULSE,
        'motion_only': BEHAVIOUR[-2:], 'fusion_without_motion': BEHAVIOUR[:-2] + PULSE,
        'video_quality_only': VIDEO_QUALITY, 'missingness_only': missingness,
        'quality_and_missingness': VIDEO_QUALITY + PULSE_QUALITY}
    definition = {'version': VERSION, 'window_seconds': 30, 'minimum_valid_fraction': MIN_FRACTION,
        'minimum_samples': MIN_SAMPLES, 'maximum_motion_gap_seconds': MAX_MOTION_GAP,
        'aperture_landmark_pairs': APERTURES, 'groups': groups, 'model_feature_lists': lists,
        'model_columns': BEHAVIOUR + PULSE + VIDEO_QUALITY + PULSE_QUALITY,
        'statistics': 'unweighted observed-frame mean/population std; NumPy linear quantiles',
        'coordinates': 'normalized x*image width, y*image height; ignore z; aperture distance / local corner width',
        'motion': 'existing 468-point RMS displacement / mean sqrt(clipped face-box pixel area) / original elapsed seconds; only unclipped adjacent retained frames in same window/segment; no interpolation',
        'support': 'each aperture requires finite retained single-face landmarks and in-image selected points; both eyes required. Each statistic requires >=2 valid samples and >=90% of decoded frames (motion: adjacent within-window pairs). Distribution summaries can span an explicitly missing gap; motion never crosses one.',
        'units': {'apertures': 'dimensionless projected 2D ratios; geometric proxies',
                  'motion': 'face sizes per second; head movement and expression combined',
                  'brightness': 'uint8 gray level', 'laplacian_variance': 'gray level squared',
                  'brightness_change': 'absolute gray levels per second', 'areas': 'fraction of frame pixels',
                  'pulse': 'BPM; fixed engineering screen, not validated accuracy'},
        'reference_storage': 'separate reference-recordings.jsonl; independent recording grain, no video-window join; EDA metadata only, no EDA values',
        'fitting': 'none; fit normalization/imputation/selection only inside later training folds'}
    return json.loads(json.dumps(definition))


def validate_feature_lists(definition):
    allowed = set(BEHAVIOUR + PULSE + VIDEO_QUALITY + PULSE_QUALITY)
    if set(definition['model_columns']) != allowed or len(definition['model_columns']) != len(allowed):
        raise ValueError('Model column allowlist mismatch')
    for columns in definition['model_feature_lists'].values():
        if len(columns) != len(set(columns)) or not set(columns) <= allowed:
            raise ValueError('Forbidden or duplicate model feature')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def supported(values, denominator):
    good = [float(x) for x in values if finite(x)]
    fraction = len(good) / denominator if denominator else None
    reason = ('no_observations' if not denominator else 'insufficient_valid_data'
              if len(good) < MIN_SAMPLES or fraction + 1e-12 < MIN_FRACTION else None)
    return good, fraction, reason


def statistics(values, denominator, operations):
    good, fraction, reason = supported(values, denominator)
    result = {}
    for op in operations:
        if reason:
            result[op] = None
        elif op == 'mean':
            result[op] = float(np.mean(good))
        elif op == 'std':
            result[op] = float(np.std(good, ddof=0))
        else:
            q = {'median': .5, 'p10': .1, 'p95': .95}[op]
            result[op] = float(np.quantile(good, q, method='linear'))
    return result, fraction, reason


def aperture_values(frame, width, height):
    """Two-point projected opening ratios; not blink, emotion or clinical scores."""
    if frame.get('face_count') != 1 or frame.get('track_segment_id') is None:
        return None, None
    points = np.asarray(frame.get('landmarks_normalized_xyz'), dtype=float)
    if points.shape != (478, 3) or not np.isfinite(points).all():
        return None, None
    values = {}
    for name, (vertical, horizontal) in APERTURES.items():
        selected = points[vertical + horizontal, :2]
        if np.any(selected < 0) or np.any(selected > 1):
            values[name] = None
            continue
        xy = selected * [width, height]
        scale = np.linalg.norm(xy[2] - xy[3])
        values[name] = float(np.linalg.norm(xy[0] - xy[1]) / scale) if scale > 1e-8 else None
    eyes = (values['eye_a'] + values['eye_b']) / 2 if all(values[k] is not None for k in ('eye_a', 'eye_b')) else None
    return values['mouth'], eyes


def transition_values(previous, current, width, height):
    """Never use the saved motion across breaks, windows or unsupported time gaps."""
    if previous is None:
        return None, None
    dt = float(Fraction(current['presentation_time_fraction']) - Fraction(previous['presentation_time_fraction']))
    segment = current.get('track_segment_id')
    if (segment is None or previous.get('track_segment_id') != segment or not 0 < dt <= MAX_MOTION_GAP + 1e-9
            or (current.get('track_event') or {}).get('type') in ('acquire', 'restart', 'break')
            or any(f.get('face_count') != 1 or not f.get('face_box') or f['face_box']['clipped'] for f in (previous, current))):
        return None, None
    saved = current.get('motion_face_sizes_per_second')
    motion = None
    if finite(saved):
        a, b = (np.asarray(f['landmarks_normalized_xyz'], dtype=float)[:, :2] * [width, height] for f in (previous, current))
        motion = normalized_motion(a[:468], b[:468], previous['face_box']['xyxy_pixels'], current['face_box']['xyxy_pixels'], dt)
        if motion is None or not math.isclose(motion, saved, rel_tol=1e-9, abs_tol=1e-10):
            raise ValueError('Saved motion does not reproduce from adjacent landmarks')
    brightness = current.get('brightness_change_per_second')
    return motion, abs(float(brightness)) if finite(brightness) else None


def summarize_frames(frames, width, height):
    """Scalar-only aggregation of one original half-open interval; no fitting."""
    n = len(frames)
    q, behaviour = {}, {}
    def fraction(predicate):
        return sum(bool(predicate(f)) for f in frames) / n if n else None
    q.update(q_no_frames=int(n == 0), q_face_detected_fraction=fraction(lambda f: f.get('detection_available')),
        q_track_fraction=fraction(lambda f: f.get('track_segment_id') is not None),
        q_multiple_faces_fraction=fraction(lambda f: (f.get('face_count') or 0) > 1),
        q_clipped_face_fraction=fraction(lambda f: (f.get('face_box') or {}).get('clipped')),
        q_timestamp_issue_fraction=fraction(lambda f: f.get('timestamp_issues')),
        q_track_break_fraction=fraction(lambda f: (f.get('track_event') or {}).get('type') == 'break'))
    intervals = [f['_previous_gap'] for f in frames if f.get('_previous_gap') is not None]
    q['q_long_gap_fraction'] = sum(x > MAX_MOTION_GAP + 1e-9 for x in intervals) / len(intervals) if intervals else None
    mouths, eyes, motions, brightness_changes = [], [], [], []
    previous = None
    for f in frames:
        mouth, eye = aperture_values(f, width, height)
        mouths.append(mouth); eyes.append(eye)
        motion, brightness = transition_values(previous, f, width, height)
        if previous is not None:
            motions.append(motion); brightness_changes.append(brightness)
        previous = f
    for family, values, denominator, ops in (
            ('mouth', mouths, n, ('mean', 'std', 'p95')),
            ('eye', eyes, n, ('mean', 'std', 'p10')),
            ('motion', motions, max(0, n-1), ('median', 'p95'))):
        stats, valid, reason = statistics(values, denominator, ops)
        behaviour.update({f'beh_{family}_{op}': value for op, value in stats.items()})
        q[f'q_{family}_valid_fraction'] = valid
        q[f'q_{family}_reason'] = reason
    for metric, ops in (('brightness', ('mean', 'std')), ('dark_fraction', ('mean',)),
                        ('saturated_fraction', ('mean',)), ('laplacian_variance', ('mean',))):
        values = [(f.get('measurements') or {}).get(metric) if (f.get('measurements') or {}).get('valid') else None for f in frames]
        stats, _, _ = statistics(values, n, ops)
        q.update({f'q_{metric}_{op}': value for op, value in stats.items()})
    stats, _, _ = statistics([(f.get('face_box') or {}).get('frame_area_fraction') for f in frames], n, ('mean',))
    q['q_face_area_mean'] = stats['mean']
    stats, valid, _ = statistics(brightness_changes, max(0, n-1), ('median',))
    q['q_brightness_change_abs_median'] = stats['median']
    q['q_brightness_change_valid_fraction'] = valid
    for region in REGIONS:
        q[f'q_region_{region}_valid_fraction'] = fraction(lambda f: f['regions'][region]['valid'])
        stats, _, _ = statistics([f['regions'][region]['pixel_count'] / (width * height)
            if f['regions'][region]['valid'] else None for f in frames], n, ('mean',))
        q[f'q_region_{region}_area_mean'] = stats['mean']
    return behaviour, q


def pulse_columns(rows, origin, count):
    """Validate all six variants and preserve rejected-null semantics and bounds."""
    result = [{} for _ in range(count)]
    seen = set()
    for row in rows:
        key = (row['window_index'], row['method'], row['region'])
        i, method, region = key
        if (key in seen or type(i) is not int or not 0 <= i < count or method not in METHODS or region not in REGIONS
                or not math.isclose(row['start_original_seconds'], origin + 30*i, abs_tol=1e-9, rel_tol=0)
                or not math.isclose(row['end_original_seconds'], origin + 30*(i+1), abs_tol=1e-9, rel_tol=0)):
            raise ValueError('Duplicate/invalid pulse row or original window boundary')
        seen.add(key)
        accepted = row['status'] == 'accepted'
        bpm, reason, peak = row['estimated_bpm'], row['rejection_reason'], row['spectral_peak_fraction']
        if ((accepted and (not finite(bpm) or not 42 <= bpm <= 240 or reason is not None
                          or not finite(peak) or not .1 <= peak <= 1))
                or (not accepted and (row['status'] != 'rejected' or bpm is not None or not isinstance(reason, str) or not reason))):
            raise ValueError('Invalid pulse status/null/rejection/quality semantics')
        prefix = f'{method}_{region}'
        result[i].update({f'cam_{prefix}_bpm': bpm, f'cam_{prefix}_status': row['status'],
                         f'cam_{prefix}_reason': reason, f'q_pulse_{prefix}_missing': int(not accepted),
                         f'q_pulse_{prefix}_peak_fraction': peak,
                         f'q_pulse_{prefix}_near_edge': int(edge_info(bpm, 2, Settings())['near_edge_within_one_bin']) if accepted else None})
    if len(seen) != count * len(METHODS) * len(REGIONS):
        raise ValueError('Incomplete scheduled pulse inventory')
    return result


def validate_rows(rows, expected, selected, schedules=None):
    definition = schema()
    columns = set().union(*(set(v) for k, v in definition['groups'].items() if k != 'reference_only_diagnostics'))
    seen = set()
    schedule = Counter()
    stamp = load_policy()[1]
    for row in rows:
        if set(row) != columns:
            raise ValueError('Feature column/provenance schema mismatch')
        p, task, i = row['id_participant'], row['id_task'], row['id_window_index']
        key = (p, task, i)
        if key in seen or p not in selected or row['id_role'] != selected[p] or type(i) is not int or i < 0:
            raise ValueError('Duplicate row key or participant-role leakage')
        seen.add(key); schedule[p, task] += 1
        if row['id_window_key'] != f'{p}/{task}/{i}' or row['id_recording'] != f'{p}/{task}':
            raise ValueError('Identifier key mismatch')
        if task not in TASK_CONDITIONS or row['label_condition'] != TASK_CONDITIONS[task]:
            raise ValueError('Task condition mismatch')
        origin = float(Fraction(row['id_origin_fraction']))
        if row['id_start_seconds'] != origin+30*i or row['id_end_seconds'] != origin+30*(i+1):
            raise ValueError('Original boundary mismatch')
        if row['id_feature_version'] != VERSION or row['id_feature_schema_sha256'] != digest(definition):
            raise ValueError('Feature provenance/version mismatch')
        if row['id_policy_version'] != stamp['version'] or row['id_policy_sha256'] != stamp['sha256']:
            raise ValueError('Pulse/tracking policy mismatch')
        for name in definition['model_columns']:
            if row[name] is not None and not finite(row[name]):
                raise ValueError('Nonfinite or nonnumeric model feature')
        for family, stats in (('mouth', ('mean', 'std', 'p95')), ('eye', ('mean', 'std', 'p10')), ('motion', ('median', 'p95'))):
            values = [row[f'beh_{family}_{op}'] for op in stats]
            reason = row[f'q_{family}_reason']
            fraction = row[f'q_{family}_valid_fraction']
            denominator = row['id_frame_count'] if family != 'motion' else max(0, row['id_frame_count']-1)
            good_count = round(fraction * denominator) if fraction is not None else 0
            expected_reason = 'no_observations' if not denominator else 'insufficient_valid_data' if good_count < MIN_SAMPLES or fraction is None or fraction < MIN_FRACTION-1e-12 else None
            if reason != expected_reason:
                raise ValueError('Facial support reason/count mismatch')
            if ((reason is not None and any(v is not None for v in values))
                    or (reason is None and (any(v is None for v in values) or fraction is None or fraction < MIN_FRACTION - 1e-12))):
                raise ValueError('Unsupported facial feature must be null')
        for method in METHODS:
            for region in REGIONS:
                prefix = f'{method}_{region}'
                accepted = row[f'cam_{prefix}_status'] == 'accepted'
                if accepted != (row[f'cam_{prefix}_bpm'] is not None) or accepted != (row[f'cam_{prefix}_reason'] is None):
                    raise ValueError('Pulse null/status mismatch')
        for name in ('id_video_sha256', 'id_frames_sha256', 'id_pulse_sha256', 'id_face_config_sha256', 'id_manifest_sha256', 'id_summary_sha256'):
            value = row[name]
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Missing feature source fingerprint')
    if len(rows) != expected or set(schedule) != {(p,t) for p in selected for t in TASK_CONDITIONS}:
        raise ValueError('Unexpected scheduled row/task count')
    if schedules is not None:
        expected_schedule = {tuple(s['recording'].split('/')):s for s in schedules}
        if set(expected_schedule) != set(schedule):
            raise ValueError('Original recording schedules missing')
        for key, count in schedule.items():
            if count != expected_schedule[key]['complete_windows'] or any(r['id_origin_fraction'] != expected_schedule[key]['origin_fraction'] for r in rows if (r['id_participant'],r['id_task']) == key):
                raise ValueError('Scheduled window count/origin mismatch')
    for (p, task), count in schedule.items():
        if {r['id_window_index'] for r in rows if (r['id_participant'], r['id_task']) == (p, task)} != set(range(count)):
            raise ValueError('Missing scheduled window')


def validate_selection(cfg):
    cfg = json.loads(json.dumps(cfg))
    if (cfg.get('schema_version') != '1.0' or cfg.get('cohort') not in ('pilot', 'development')
            or cfg.get('final_test_cohort') != 'unassigned' or type(cfg.get('expected_rows')) is not int
            or cfg['expected_rows'] <= 0 or not cfg.get('participants')):
        raise ValueError('Explicit cohort, participants, expected rows and unassigned final test required')
    seen = set()
    for entry in cfg['participants']:
        p = entry['id']; role = 'development_only' if p == 's25' else 'pilot_development'
        if (p in seen or entry.get('role') != role or not re.fullmatch(r's[1-9][0-9]*', p)
                or (cfg['cohort'] == 'development') != (p == 's25')):
            raise ValueError('Duplicate participant or pilot/development role leakage')
        seen.add(p)
        for key in ('summary', 'legacy_compatibility'):
            if key in entry:
                entry[key] = str(Path(entry[key]).expanduser().resolve())
    return cfg


def selection(path):
    return validate_selection(read(path))


def verified_source(entry, stamp):
    path = Path(entry['summary']); require_ignored(path)
    summary = read(path); ctx = summary['context']; p = entry['id']
    if (summary['status'] != 'completed' or summary['selection']['final_test_cohort'] != 'unassigned'
            or next(e['role'] for e in summary['selection']['participants'] if e['id'] == p) != entry['role']):
        raise ValueError('Incomplete source run or source role mismatch')
    policy = load_policy()[0]
    if ctx['face_settings'] != policy['tracking']['measurements'] or ctx['pulse_settings'] != policy['pulse']['settings']:
        raise ValueError('Source numeric policies incompatible')
    for name in ('face_measurements.py', 'pulse.py', 'video_reader.py', 'manifest.py', 'validate_sample.py'):
        if ctx['code'][name] != fingerprint(Path(__file__).parent/name, name)['sha256']:
            raise ValueError('Source core implementation changed: ' + name)
    if ctx['python'] != platform.python_version() or ctx['software']['numpy'] != np.__version__:
        raise ValueError('Feature numerical runtime differs from source run')
    basis = 'registered_bundle'
    attestation = None
    if ctx.get('policy') != stamp:
        attestation = Path(entry.get('legacy_compatibility', ''))
        require_ignored(attestation)
        att = read(attestation)
        if (att.get('status') != 'completed' or att.get('compatible_policy') != stamp
                or Path(att['summary']).resolve() != path or p not in {e['id'] for e in att['participants']}
                or not att.get('core_code_hashes_match') or not att.get('face_computation_ast_matches_audited_commit')):
            raise ValueError('Missing/invalid explicit legacy compatibility attestation')
        basis = 'explicit_verified_legacy_components'
    events = {}
    for event in summary['stage_events']:
        if not event['key'].startswith(p+'/'):
            continue
        receipt = read(Path(event['receipt']))
        output = Path(event['output']); require_ignored(output)
        if (receipt['status'] != 'completed' or receipt['signature'] != digest(receipt['specification'])
                or receipt['specification']['participant'] != p or receipt['specification']['role'] != entry['role']
                or receipt['output_files'] != event['output_files'] or receipt['output'] != event['output']
                or inventory(output) != event['output_files']
                or (basis == 'registered_bundle' and receipt.get('policy') != stamp)):
            raise ValueError('Incomplete/tampered source receipt or output')
        events[event['key'].removeprefix(p+'/')] = event
    mf = Path(events['manifest']['output'])/'manifest.json'
    manifest = read(mf)
    records = {r['task_id']:r for r in manifest['records'] if r['participant_id'] == p}
    if set(records) != set(TASK_CONDITIONS):
        raise ValueError('Missing or ambiguous task manifest')
    folder = Path(events['extract']['output'])/p if 'extract' in events else None
    if folder is None:
        folder = Path(next(e['directory'] for e in summary['selection']['participants'] if e['id']==p))
    # Hash originals, including signal provenance, without parsing wrist values into features.
    files = inventory(folder)
    for task,record in records.items():
        if record['validation_status'] != 'passed' or record.get('camera_eligibility_policy') != stamp['timing']:
            raise ValueError('Camera manifest is ineligible for this feature schema')
        if record['task_condition'] != TASK_CONDITIONS[task] or record['recording_id'] != p+'/'+task:
            raise ValueError('Wrong task pairing/condition')
        for kind in ('vid','bvp','eda'):
            f = record['files'][kind]
            if {**files[Path(f['path']).name], 'path': f['path']} != f:
                raise ValueError('Original source fingerprint mismatch')
    provenance = {'summary':fingerprint(path,path.name), 'manifest':fingerprint(mf,mf.name),
        'compatibility':fingerprint(attestation,attestation.name) if attestation else None,
        'basis':basis, 'output_inventories':{k:e['output_files'] for k,e in events.items()}}
    return events, records, mf, provenance, ctx


def recording_rows(entry, task, event, record, manifest, provenance, ctx, stamp):
    p = entry['id']; face = Path(event[task+'/face']['output']); pulse = Path(event[task+'/pulse']['output'])
    cfg = read(face/'config.json'); fs = read(face/'summary.json'); pc = read(pulse/'config.json')
    timing = read(pulse/'source-timing.json')
    frames_hash = fingerprint(face/'frames.jsonl','frames.jsonl')['sha256']
    if (cfg['recording_id'] != p+'/'+task or cfg['source'] != record['files']['vid']
            or cfg['measurements'] != load_policy()[0]['tracking']['measurements'] or cfg['max_frames'] is not None
            or cfg['model'] != ctx['model'] or fs['status'] not in ('completed','completed_with_warnings')
            or not fs['reader']['decode_complete'] or fs['processed_frames'] != record['video']['decoded_frames']
            or read(face/'status.json')['status'] != fs['status']
            or (provenance['basis']=='registered_bundle' and cfg.get('policy') != stamp)
            or pc['recording_id'] != p+'/'+task or pc['source'] != record['files']['vid']
            or pc['face_frames']['sha256'] != frames_hash or pc['source_model'] != cfg['model']
            or pc['settings'] != load_policy()[0]['pulse']['settings'] or read(pulse/'status.json')['status'] != 'completed'):
        raise ValueError('Face/pulse feature provenance or completion mismatch')
    origin = Fraction(fs['reader']['origin_pts'])*Fraction(fs['reader']['origin_time_base'])
    duration = timing['duration_seconds']; count = int(math.floor((duration+1e-9)/30))
    if not finite(duration) or duration <= 0 or abs(duration-record['video']['observed_duration_seconds'])>1e-8:
        raise ValueError('Source duration mismatch')
    camera = [json.loads(line) for line in (pulse/'windows.jsonl').open()]
    pulse_data = pulse_columns(camera,float(origin),count)
    width,height = fs['reader']['width'],fs['reader']['height']
    common = {'id_participant':p,'id_role':entry['role'],'id_recording':p+'/'+task,'id_task':task,
        'id_origin_fraction':str(origin),'id_video_sha256':record['files']['vid']['sha256'],
        'id_frames_sha256':frames_hash,'id_pulse_sha256':fingerprint(pulse/'windows.jsonl','windows.jsonl')['sha256'],
        'id_face_config_sha256':fingerprint(face/'config.json','config.json')['sha256'],
        'id_manifest_sha256':provenance['manifest']['sha256'],'id_summary_sha256':provenance['summary']['sha256'],
        'id_face_run':str(face),'id_pulse_run':str(pulse),'id_manifest':str(manifest),
        'id_policy_version':stamp['version'],'id_policy_sha256':stamp['sha256'],
        'id_feature_version':VERSION,'id_feature_schema_sha256':digest(schema()),'id_policy_basis':provenance['basis'],
        'label_condition':TASK_CONDITIONS[task]}
    result=[]
    def emit(i, frames):
        behaviour,quality=summarize_frames(frames,width,height)
        result.append({**common,'id_window_key':f'{p}/{task}/{i}','id_window_index':i,
            'id_start_seconds':float(origin)+30*i,'id_end_seconds':float(origin)+30*(i+1),
            'id_frame_count':len(frames),**behaviour,**quality,**pulse_data[i]})
    previous_time=None
    n=0; current=0; frames=[]
    # Bound landmark memory to one 30-second interval. Never reconstruct timestamps.
    with (face/'frames.jsonl').open() as source:
        for line in source:
            f=json.loads(line);t=Fraction(f['presentation_time_fraction'])
            if (n >= len(timing['pts']) or f['frame_index'] != n or t < origin
                    or (previous_time is not None and t <= previous_time)
                    or abs(float(t)-f['presentation_time_seconds']) > 1e-9
                    or t != Fraction(f['pts'])*Fraction(f['time_base'])
                    or f['pts'] != timing['pts'][n] or f['time_base'] != timing['time_bases'][n]
                    or f['frame_index'] != timing['frame_indices'][n]
                    or str(t) != timing['original_time_fractions'][n]):
                raise ValueError('Missing/changed original PTS or frame sequence')
            f['_previous_gap']=float(t-previous_time) if previous_time is not None else None
            i=int((t-origin)//30)
            while current < min(i,count):
                emit(current,frames);frames=[];current+=1
            if i < count:
                frames.append(f)
            previous_time=t;n+=1
    while current < count:
        emit(current,frames);frames=[];current+=1
    if n != fs['processed_frames'] or n != len(timing['pts']) or str(origin) != timing['origin_fraction']:
        raise ValueError('Incomplete decoded frame inventory or source origin')
    if fingerprint(face/'frames.jsonl','frames.jsonl')['sha256'] != frames_hash:
        raise ValueError('Frame features changed during derivation')
    reference = read(Path(event[task+'/reference']['output'])/'reference.json')
    if reference != read(pulse/'reference.json'):
        raise ValueError('Independent reference provenance mismatch')
    ref={'ref_participant':p,'ref_task':task,'ref_time_basis':'independent recording; BVP nominal sample index/64; no video-window alignment',
        'ref_wrist':reference,'ref_eda_metadata':{k:record['signals']['eda'][k] for k in ('rows','sampling_rate_hz','nominal_duration_seconds')}}
    return result,ref,{'recording':p+'/'+task,'origin_fraction':str(origin),'complete_windows':count,
                      'trailing_seconds':duration-count*30,'duration_seconds':duration}


def write_jsonl(path, rows):
    with path.open('x') as target:
        for row in rows:
            target.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')


def write_tables(output, rows, references):
    definition=schema();validate_feature_lists(definition)
    write_jsonl(output/'windows.jsonl',rows)
    write_jsonl(output/'reference-recordings.jsonl',references)
    for name,positive in (('rest-vs-speech','speech'),('rest-vs-arithmetic','arithmetic')):
        selected=[r for r in rows if r['label_condition'] in ('rest',positive)]
        folder=output/name;folder.mkdir()
        write_jsonl(folder/'X.jsonl',[{c:r[c] for c in definition['model_columns']} for r in selected])
        write_jsonl(folder/'index.jsonl',[{**{c:r[c] for c in IDENTIFIERS},
            'label_condition':r['label_condition'],'target':int(r['label_condition']==positive)} for r in selected])
    atomic(output/'feature-lists.json',definition['model_feature_lists'])
    atomic(output/'schema.json',definition)


def read_jsonl(path):
    return [json.loads(line) for line in path.open()]


def validate_tables(output, rows, references):
    """Read back predictor-only files; IDs/labels/references never enter X."""
    definition=schema();validate_feature_lists(definition)
    if read_jsonl(output/'windows.jsonl') != rows or read_jsonl(output/'reference-recordings.jsonl') != references:
        raise ValueError('Written window/reference tables differ from derived data')
    ref_keys={(r['ref_participant'],r['ref_task']) for r in references}
    if len(ref_keys)!=len(references) or ref_keys!={(r['id_participant'],r['id_task']) for r in rows}:
        raise ValueError('Reference recording inventory mismatch')
    if any(set(r)!=set(definition['groups']['reference_only_diagnostics']) for r in references):
        raise ValueError('Reference diagnostics schema mismatch')
    for name,positive in (('rest-vs-speech','speech'),('rest-vs-arithmetic','arithmetic')):
        selected=[r for r in rows if r['label_condition'] in ('rest',positive)]
        x=read_jsonl(output/name/'X.jsonl');index=read_jsonl(output/name/'index.jsonl')
        if len(x)!=len(selected) or len(index)!=len(selected):
            raise ValueError('Contrast row count mismatch')
        for values,meta,source in zip(x,index,selected):
            if set(values)!=set(definition['model_columns']):
                raise ValueError('Forbidden/missing model input columns')
            if any(value is not None and not finite(value) for value in values.values()):
                raise ValueError('Model inputs must be raw finite numbers or null')
            if values!={c:source[c] for c in definition['model_columns']}:
                raise ValueError('Model inputs transformed or misordered')
            if (meta!={**{c:source[c] for c in IDENTIFIERS},'label_condition':source['label_condition'],
                       'target':int(source['label_condition']==positive)}):
                raise ValueError('Contrast identity/label/participant alignment mismatch')
    if read(output/'schema.json')!=definition or read(output/'feature-lists.json')!=definition['model_feature_lists']:
        raise ValueError('Feature schema/allowlists changed')


def validate_run(output):
    require_ignored(output)
    receipt=read(output/'receipt.json')
    if (receipt['status']!='completed' or receipt['feature_schema_sha256']!=digest(schema())
            or receipt['code']!={p.name:fingerprint(p,p.name)['sha256'] for p in Path(__file__).parent.glob('*.py')}
            or receipt['software']!={'numpy':np.__version__,'python':platform.python_version()}
            or receipt['policy']!=load_policy()[1]):
        raise ValueError('Incomplete/incompatible feature receipt')
    files=inventory(output);files.pop('receipt.json',None)
    if files!=receipt['output_files']:
        raise ValueError('Feature output hash mismatch')
    report=read(output/'validation.json');config=validate_selection(receipt['selection'])
    rows=read_jsonl(output/'windows.jsonl');references=read_jsonl(output/'reference-recordings.jsonl')
    validate_rows(rows,config['expected_rows'],{e['id']:e['role'] for e in config['participants']},report['schedules'])
    validate_tables(output,rows,references)
    return report


def missingness(rows):
    report=[]
    for p,task in sorted({(r['id_participant'],r['id_task']) for r in rows}):
        group=[r for r in rows if (r['id_participant'],r['id_task'])==(p,task)]
        report.append({'participant':p,'task':task,'condition':TASK_CONDITIONS[task],'scheduled_rows':len(group),
            'null_counts':{c:sum(r[c] is None for r in group) for c in schema()['model_columns']},
            'facial_reasons':{family:dict(Counter(r[f'q_{family}_reason'] or 'supported' for r in group)) for family in ('mouth','eye','motion')},
            'pulse_rejections':{f'{m}/{region}':dict(Counter(r[f'cam_{m}_{region}_reason'] or 'accepted' for r in group)) for m in METHODS for region in REGIONS}})
    return report


def run(config,output):
    config=validate_selection(config)
    require_ignored(output)
    if read(CONFIG)!=schema():
        raise ValueError('Feature configuration differs from implementation schema')
    definition=schema();validate_feature_lists(definition)
    policy,stamp=load_policy()
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    receipt={'status':'running','started':now(),'selection':config,'policy':stamp,'feature_schema_sha256':digest(definition),
        'code':{p.name:fingerprint(p,p.name)['sha256'] for p in Path(__file__).parent.glob('*.py')},
        'software':{'numpy':np.__version__,'python':platform.python_version()},'fitting_performed':False,'inputs':[]}
    atomic(output/'receipt.json',receipt)
    try:
        rows=[];refs=[];schedules=[]
        for entry in config['participants']:
            print('Verify and derive',entry['id'],flush=True)
            events,records,manifest,provenance,ctx=verified_source(entry,stamp)
            receipt['inputs'].append({'participant':entry['id'],**provenance})
            for task in TASK_CONDITIONS:
                data,reference,schedule=recording_rows(entry,task,events,records[task],manifest,provenance,ctx,stamp)
                rows.extend(data);refs.append(reference);schedules.append(schedule)
        validate_rows(rows,config['expected_rows'],{e['id']:e['role'] for e in config['participants']},schedules)
        rows.sort(key=lambda r:(int(r['id_participant'][1:]),r['id_task'],r['id_window_index']))
        write_tables(output,rows,refs)
        validate_tables(output,rows,refs)
        report={'status':'passed','cohort':config['cohort'],'rows':len(rows),'recordings':len(refs),
            'contrast_rows':{name:sum(r['label_condition'] in ('rest',condition) for r in rows)
                for name,condition in (('rest-vs-speech','speech'),('rest-vs-arithmetic','arithmetic'))},
            'schedules':schedules,'missingness':missingness(rows),'model_feature_count':len(definition['model_columns']),
            'no_reference_values_in_model_inputs':True,'participant_role_separation':True,'fitting_performed':False}
        atomic(output/'validation.json',report)
        # New-run tables are immutable; an interrupted/failed receipt is never success.
        receipt.update(status='completed',output_files=inventory(output))
        receipt['output_files'].pop('receipt.json',None)
    except BaseException as exc:
        receipt.update(status='failed',failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        receipt.update(ended=now(),elapsed_seconds=time.perf_counter()-started)
        atomic(output/'receipt.json',receipt)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--print-schema',action='store_true')
    parser.add_argument('--validate-run',type=Path)
    args=parser.parse_args()
    if args.validate_run:
        result=validate_run(args.validate_run)
        print('Verified',result['rows'],'rows and predictor-only contrasts');return
    if args.print_schema:
        print(json.dumps(schema(),indent=2,sort_keys=True));return
    if not args.selection or not args.output:
        parser.error('--selection and --output required')
    result=run(selection(args.selection),args.output)
    print('Completed',result['rows'],'rows; contrasts',result['contrast_rows'])


if __name__=='__main__':
    main()
