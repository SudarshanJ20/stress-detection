"""Scoring-gated session feature/questionnaire audit. Deliberately has no fit API."""

import argparse
from collections import Counter
import csv
from pathlib import Path
import subprocess

import numpy as np

from . import baseline as base
from .features import finite, read_jsonl, write_jsonl
from .manifest import fingerprint
from .pilot_state import atomic, digest, inventory, now, read
from .validate_sample import inspect_info, require_ignored

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'configs/session-anxiety-audit-v1.json'
REGISTERED = '2caf3fffe1ace181c24a0e7787c32b5c3e513e512aa3836be30d1878d821aec9'


def load_config():
    cfg = read(CONFIG)
    if (digest(cfg) != REGISTERED or cfg['models'] != base.load_config()['models']
            or cfg['questionnaire']['fit_authorized'] or cfg['regression']['fit_enabled']):
        raise ValueError('Modified/unregistered audit or attempted scoring-gate override')
    return cfg


def load_selection(path, cfg):
    require_ignored(path)
    selection = read(path)
    if set(selection) != {'version', 'participants'} or selection['version'] != 'session-audit-selection-v1':
        raise ValueError('Invalid session audit selection')
    entries = selection['participants']
    if (len(entries) != cfg['expected_sessions']
            or Counter(e.get('id') for e in entries) != Counter(cfg['participants'])):
        raise ValueError('Duplicate, missing or excluded participant')
    result = {}
    for e in entries:
        if set(e) != {'id', 'role', 'directory'} or e['role'] != cfg['role']:
            raise ValueError('Participant-role/selection metadata leakage')
        folder = Path(e['directory']).resolve()
        if folder.name != e['id'] or not folder.is_dir():
            raise ValueError('Participant directory mismatch')
        require_ignored(folder)
        result[e['id']] = folder
    return result


def questionnaire(folder, participant, cfg):
    path = folder / f'selfReportedAnx_{participant}.csv'
    info = folder / f'info_{participant}.txt'
    if (folder.name != participant or path.is_symlink() or info.is_symlink()
            or not inspect_info(info, participant)['valid']):
        raise ValueError('Questionnaire/metadata identity or structure mismatch')
    before = {name: fingerprint(p, str(p.resolve())) for name, p in [('questionnaire', path), ('info', info)]}
    try:
        with path.open(newline='') as source:
            rows = list(csv.reader(source))
        if len(rows) != 3 or any(len(r) != 2 for r in rows):
            raise ValueError('Questionnaire must be exactly headerless 3x2')
        values = [[float(x) for x in r] for r in rows]
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid questionnaire 3x2 numeric structure') from exc
    low, high = cfg['questionnaire']['range']
    if any(not finite(x) or not low <= x <= high for r in values for x in r):
        raise ValueError('Nonfinite/out-of-range released questionnaire mean')
    checks = []
    for row, n in zip(values, cfg['questionnaire']['items']):
        checks.append(all(abs(x*n-round(x*n)) <= cfg['questionnaire']['mean_precision_tolerance']*n for x in row))
    after = {name: fingerprint(p, str(p.resolve())) for name, p in [('questionnaire', path), ('info', info)]}
    if before != after:
        raise ValueError('Questionnaire changed while reading')
    dimensions = {dimension: dict(zip(cfg['questionnaire']['columns'], row))
                  for dimension, row in zip(cfg['questionnaire']['rows'], values)}
    return {'session_key': participant+'/session-1', 'participant': participant,
            'dimensions': dimensions, 'scoring_status': cfg['questionnaire']['scoring_status'],
            'item_mean_grid_compatible_within_precision': checks,
            'grid_check_is_scoring_verification': False,
            'primary_candidate': dimensions['cognitive_anxiety']['post_session'],
            'secondary_candidate': dimensions['somatic_anxiety']['post_session'],
            'modeling_eligible': False}, before


def columns(cfg):
    return sorted({c for group in cfg['models'].values() for c in group})


def summarize(rows, cfg):
    """Pool raw window summaries without using outcomes, tasks or assignments as X."""
    names = columns(cfg)
    result, support = [], []
    for participant in cfg['participants']:
        source = [r for r in rows if r['id_participant'] == participant]
        expected = {(f'T{t}', i) for t in (1, 2, 3) for i in range(6)}
        keys = [(r['id_task'], r['id_window_index']) for r in source]
        if len(source) != cfg['expected_windows_per_session'] or len(set(keys)) != len(keys) or set(keys) != expected:
            raise ValueError('Missing/duplicate scheduled window or participant alignment')
        vector, counts = {}, {}
        for name in names:
            raw = [r[name] for r in source]
            if any(x is not None and not finite(x) for x in raw):
                raise ValueError('Nonfinite session source predictor')
            observed = [x for x in raw if x is not None]
            aggregate = np.mean if name in cfg['models']['missingness'] else np.median
            vector[name] = float(aggregate(observed)) if observed else None
            counts[name] = {'scheduled': len(raw), 'observed': len(observed), 'missing': len(raw)-len(observed),
                'by_task': {task: {'scheduled': 6, 'observed': sum(r[name] is not None for r in source if r['id_task'] == task)}
                            for task in ('T1', 'T2', 'T3')}}
        result.append(vector)
        support.append({'session_key': participant+'/session-1', 'participant': participant,
                        'columns': counts, 'window_keys': sorted(r['id_window_key'] for r in source)})
    return result, support


def fold_inventory(index):
    participants = [r['participant'] for r in index]
    keys = [r['session_key'] for r in index]
    if len(participants) != 6 or len(set(participants)) != 6 or len(set(keys)) != 6 or 's25' in participants:
        raise ValueError('Session/participant leakage or incomplete inventory')
    return [{'held_out_participant': p, 'training_participants': [v for v in participants if v != p],
             'evaluation_participants': [p], 'training_sessions': [r['session_key'] for r in index if r['participant'] != p],
             'evaluation_sessions': [r['session_key'] for r in index if r['participant'] == p]}
            for p in participants]


def derive(feature_run, selection_path, cfg):
    _, feature_proof = base.load_features(feature_run, base.load_config())
    selected = load_selection(selection_path, cfg)
    rows = read_jsonl(feature_run/'windows.jsonl')
    x, support = summarize(rows, cfg)
    index, outcomes, inputs = [], [], {}
    for participant in cfg['participants']:
        outcome, proof = questionnaire(selected[participant], participant, cfg)
        index.append({'session_key': outcome['session_key'], 'participant': participant,
                      'role': cfg['role'], 'scheduled_windows': cfg['expected_windows_per_session']})
        outcomes.append(outcome)
        inputs[participant] = proof
    folds = fold_inventory(index)
    if any(set(v) != set(columns(cfg)) for v in x):
        raise ValueError('Predictor allowlist leakage')
    if ([o['session_key'] for o in outcomes] != [r['session_key'] for r in index]
            or [s['session_key'] for s in support] != [r['session_key'] for r in index]):
        raise ValueError('Outcome/session alignment mismatch')
    return {'X.jsonl': x, 'index.jsonl': index, 'outcomes.jsonl': outcomes, 'support.jsonl': support}, {
        'feature_inputs': feature_proof, 'questionnaire_inputs': inputs,
        'selection': fingerprint(selection_path, str(selection_path.resolve())), 'folds': folds}


def audit(feature_run, selection, output):
    cfg = load_config()
    require_ignored(output)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'status': 'running', 'started': now(), 'configuration': cfg, 'configuration_id': digest(cfg),
               'feature_run': str(feature_run.resolve()), 'selection_path': str(selection.resolve()),
               'code': base.code_hashes(), 'software': base.versions(),
               'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'git_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)}
    atomic(output/'receipt.json', receipt)
    try:
        tables, proof = derive(feature_run, selection, cfg)
        for name, data in tables.items():
            write_jsonl(output/name, data)
        atomic(output/'configuration.json', cfg)
        atomic(output/'allowlists.json', cfg['models'])
        atomic(output/'folds.json', proof['folds'])
        report = {'status': 'audit_passed_fitting_blocked', 'sessions': len(tables['index.jsonl']),
                  'scheduled_source_windows': 108, 'predictor_columns': len(columns(cfg)),
                  'scoring_status': 'unresolved', 'missing_information': cfg['questionnaire']['missing_information'],
                  'regression': {'status': 'not_run_scoring_unresolved', 'prediction_count': 0,
                                 'mae': None, 'rmse': None, 'r2': None, 'baseline_comparison': 'unavailable'},
                  'classification': {**cfg['classification'], 'class_counts': None, 'accuracy': None,
                       'balanced_accuracy': None, 'macro_f1': None, 'confusion_matrix': None},
                  'participant_outputs_private': True,
                  'no_fitted_preprocessing_or_models': True,
                  'model_widths_and_training_size': {name: {'columns': len(cols), 'training_sessions': 5,
                       'note': 'no feasibility/performance claim; fitting blocked'} for name, cols in cfg['models'].items()}}
        atomic(output/'audit.json', report)
        lines = ['# Session-anxiety data audit: fitting blocked', '',
                 'One row per participant-session; six exposed development participants only. s25 excluded.',
                 'Primary candidate: released post-session cognitive-anxiety mean. Secondary: post-session somatic mean. Confidence audited separately.',
                 'Scores are not task/condition labels. No thresholds, predictions, MAE, RMSE, R² or accuracy were produced.',
                 'Scoring blockers: '+ '; '.join(report['missing_information']), '',
                 '| Participant | Scheduled windows | Observed family cells / scheduled |', '|---|---:|---|']
        for meta, support in zip(tables['index.jsonl'], tables['support.jsonl']):
            groups = []
            for name, names in cfg['models'].items():
                if names:
                    count = sum(support['columns'][n]['observed'] for n in names)
                    groups.append(f'{name}: {count}/{18*len(names)}')
            lines.append(f"| {meta['participant']} | 18 | {'; '.join(groups)} |")
        lines += ['', 'Raw scores by dimension and occasion are in outcomes.jsonl; per-task support is in support.jsonl.',
                  'Feature medians pool observed original windows; missingness controls use means. A non-null aggregate can have sparse support; all-missing stays null.',
                  'The item-mean precision check is not proof of item coding. Six sessions, not108 windows, are independent outcome units.',
                  'The mean/Ridge comparisons are specified but remain unavailable, with no fitted artifact. Do not infer an accuracy percentage.']
        (output/'report.md').write_text('\n'.join(lines)+'\n')
        receipt.update(status='completed', ended=now(), source_proof=proof, output_files=inventory(output))
        receipt['output_files'].pop('receipt.json', None)
    except BaseException as exc:
        receipt.update(status='failed', ended=now(), failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        atomic(output/'receipt.json', receipt)
    return validate(output)


def validate(output):
    require_ignored(output)
    cfg = load_config()
    receipt = read(output/'receipt.json')
    actual = inventory(output); actual.pop('receipt.json', None)
    if (receipt['status'] != 'completed' or receipt['configuration'] != cfg
            or receipt['configuration_id'] != digest(cfg) or receipt['code'] != base.code_hashes()
            or receipt['software'] != base.versions() or receipt['output_files'] != actual):
        raise ValueError('Incomplete/changed audit artifacts or computation context')
    tables, proof = derive(Path(receipt['feature_run']), Path(receipt['selection_path']), cfg)
    if proof != receipt['source_proof'] or read(output/'configuration.json') != cfg or read(output/'allowlists.json') != cfg['models']:
        raise ValueError('Audit source/configuration changed')
    for name, expected in tables.items():
        if read_jsonl(output/name) != expected:
            raise ValueError('Session summaries/outcomes/alignment do not reproduce')
    if read(output/'folds.json') != proof['folds']:
        raise ValueError('Participant-held-out fold inventory changed')
    return {'status': 'passed', 'sessions': 6, 'source_windows': 108, 'folds': 6,
            'scoring_status': 'unresolved', 'model_fitting': 'blocked', 'predictions': 0,
            'classification': 'unavailable', 'outcomes_separate_from_predictors': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-run', type=Path)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    if args.validate:
        result = validate(args.output)
    else:
        if not args.feature_run or not args.selection:
            parser.error('--feature-run and --selection are required for a new audit')
        result = audit(args.feature_run, args.selection, args.output)
    print(result)


if __name__ == '__main__':
    main()
