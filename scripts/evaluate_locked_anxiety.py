"""Score saved locked predictions without refitting.

Lock verification replays frozen inference before questionnaire release.

Kept outside stress_detection so the frozen computation-module hash map is unchanged.
"""
import argparse
from collections import Counter
import csv
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

from stress_detection import independent_anxiety as study
from stress_detection import session_anxiety_regression as regression
from stress_detection.features import finite, read_jsonl, write_jsonl
from stress_detection.manifest import fingerprint
from stress_detection.pilot_state import atomic, digest, inventory, now, read
from stress_detection.validate_sample import inspect_info, require_ignored

ROOT = Path(__file__).resolve().parents[1]
MODEL_SHA = '79b9b2b67fd87a8ab0b3297e91ca502ffa674c1ec83e92bfe1cea676248ed30c'
PREDICTION_SHA = 'f1fa66929d9bb75d58859225ad5db7a7c803af0d090f4b305503317f16eec234'
ORDER = ('mean', 'facial', 'camera_bpm', 'facial_camera_bpm', 'quality_values', 'missingness')
ROWS = ('cognitive_anxiety', 'somatic_anxiety', 'self_confidence')
COLUMNS = ('pre_session', 'post_session')
MAPPING = {'cognitive_post': (ROWS[0], COLUMNS[1]), 'somatic_post': (ROWS[1], COLUMNS[1])}


def procedure():
    return {'version': 'locked-outcome-evaluation-v1', 'rows': list(ROWS), 'columns': list(COLUMNS),
            'target_mapping': {t: list(v) for t, v in MAPPING.items()}, 'range': [1., 4.], 'model_order': list(ORDER),
            'mapping_source': 'official UBFC-Phys README; docs/released-anxiety-targets.md',
            'unit': 'one protocol session per reserved participant',
            'invalid_outcome': 'null for that outcome; retain predictions and scheduled denominator; never impute y',
            'paired_difference': 'absolute model error minus absolute training-mean error; negative is better',
            'secondary_subset': 'model-specific fully observed session inputs; matched mean on identical people; not full-window support',
            'uncertainty': 'none: locked plan specifies no confidence intervals, significance or winner selection',
            'refit': False, 'clipping': False, 'target_transformation': False}


def verify_lock(plan_path, lock_root):
    """No questionnaire bytes are accessed, even when verification fails."""
    cfg, plan = study.load_design(plan_path)
    require_ignored(lock_root)
    lock = read(lock_root / 'receipt.json')
    study.check_context(lock, cfg, plan)
    if (lock['kind'] != 'pre_outcome_prediction_lock' or lock['status'] != 'completed'
            or any(lock[k] for k in ('questionnaire_values_read', 'questionnaires_released', 'outcomes_evaluated'))
            or lock['scheduled_windows'] != 180 or lock['scheduled_recordings'] != 30):
        raise ValueError('Incomplete or previously unblinded lock')
    recorded = read(lock_root / 'hashes.json'); actual = study.artifact_inventory(lock_root)
    if set(actual) != set(recorded) | {'hashes.json'} or any(actual[k] != v for k, v in recorded.items()):
        raise ValueError('Original lock artifact hashes changed')
    if read(lock_root / 'configuration.json') != cfg:
        raise ValueError('Lock configuration differs from frozen design')
    predictions = Path(lock['prediction_run']); pr = read(predictions / 'receipt.json')
    models = Path(pr['models_run'])
    if (study.artifact_inventory(predictions) != lock['prediction_artifacts']
            or study.artifact_inventory(models) != lock['model_artifacts']
            or lock['prediction_artifacts']['predictions.jsonl']['sha256'] != PREDICTION_SHA
            or digest(read(models / 'receipt.json')['output_files']) != MODEL_SHA
            or lock['models_inventory_sha256'] != MODEL_SHA):
        raise ValueError('Frozen prediction or model hash mismatch')
    result = study.validate_predictions(predictions, plan_path)
    if result != lock['validation'] or not result['all_scheduled_predictions_locked'] or result['predictions'] != 120:
        raise ValueError('Complete 120-prediction inventory is required')
    windows = read_jsonl(lock_root / 'scheduled-windows.jsonl')
    expected = {(p, t, i) for p in plan['locked_final'] for t in ('T1', 'T2', 'T3') for i in range(6)}
    keys = [(r['id_participant'], r['id_task'], r['id_window_index']) for r in windows]
    if len(keys) != 180 or set(keys) != expected or any(r['id_role'] != 'locked_final' for r in windows):
        raise ValueError('Scheduled window/role inventory changed')
    source_windows = [r for path in pr['exports'] for r in read_jsonl(Path(path) / 'windows.jsonl')]
    if {r['id_window_key']: r for r in source_windows} != {r['id_window_key']: r for r in windows}:
        raise ValueError('Lock window copy differs from verified exports')
    rows = read_jsonl(predictions / 'predictions.jsonl')
    study.prediction_inventory(rows, plan['locked_final'], cfg, plan)
    proof = {'status': 'passed', 'verified_at': now(), 'validation': result,
             'configuration_id': digest(cfg), 'original_lock_files': actual,
             'prediction_run': str(predictions.resolve()), 'prediction_files': study.artifact_inventory(predictions),
             'models_run': str(models.resolve()), 'model_files': study.artifact_inventory(models),
             'model_inventory_sha256': MODEL_SHA, 'prediction_sha256': PREDICTION_SHA,
             'questionnaire_values_read': False, 'scheduled_windows': 180}
    return cfg, plan, rows, proof


def read_scores(path):
    """Use the documented row/column semantics; never infer order from values."""
    dimensions = {r: {c: None for c in COLUMNS} for r in ROWS}; invalid = []
    try:
        with path.open(newline='') as source:
            matrix = list(csv.reader(source))
    except (OSError, UnicodeError):
        return dimensions, ['questionnaire_unavailable_or_unreadable']
    if len(matrix) != 3 or any(len(r) != 2 for r in matrix):
        return dimensions, ['invalid_headerless_3x2_structure']
    header_tokens = {'pre', 'post', 'pre_session', 'post_session', *ROWS}
    if any(cell.strip().lower() in header_tokens for row in matrix for cell in row):
        return dimensions, ['unexpected_header_or_dimension_labels']
    for r, cells in zip(ROWS, matrix):
        for c, cell in zip(COLUMNS, cells):
            try:
                value = float(cell)
            except (TypeError, ValueError):
                value = None
            if not finite(value) or not 1 <= value <= 4:
                invalid.append(r + '/' + c + ':nonfinite_nonnumeric_or_out_of_range')
            else:
                dimensions[r][c] = value
    return dimensions, invalid


def outcome(path, participant):
    dims, invalid = read_scores(path)
    return {'participant': participant, 'role': 'locked_final', 'session_key': participant + '/session-1',
            'dimensions': dims, 'invalid_fields': invalid,
            'targets': {t: dims[r][c] for t, (r, c) in MAPPING.items()}}


def release_outcomes(plan_path, plan, output):
    """Called only after a persisted passing gate. Copy for evaluation; preserve sealed originals."""
    root = plan_path.parent; released = output / 'released'; released.mkdir()
    outcomes = []; sources = {}
    for p in plan['locked_final']:
        folder = released / p; folder.mkdir()
        info = root / 'inputs' / p / p / f'info_{p}.txt'
        source = root / 'sealed-outcomes' / f'selfReportedAnx_{p}.csv'
        if info.is_symlink() or source.is_symlink() or not inspect_info(info, p)['valid']:
            raise ValueError('Questionnaire participant metadata identity mismatch')
        shutil.copyfile(info, folder / info.name)
        if source.exists():
            original = fingerprint(source, source.name)
            if original != read(root / f'{p}-transport.json')['sealed_questionnaire']:
                raise ValueError('Sealed questionnaire differs from transport identity')
            target = folder / source.name; shutil.copyfile(source, target)
            if fingerprint(source, source.name) != original or fingerprint(target, source.name) != original:
                raise ValueError('Outcome changed during release')
            sources[p] = original
        else:
            sources[p] = None
        outcomes.append(outcome(folder / source.name, p))
    return outcomes, sources


def join_predictions(predictions, outcomes, cfg, plan):
    study.prediction_inventory(predictions, plan['locked_final'], cfg, plan)
    if (Counter(r['participant'] for r in outcomes) != Counter(plan['locked_final'])
            or any(r['role'] != 'locked_final' or r['session_key'] != r['participant'] + '/session-1' for r in outcomes)):
        raise ValueError('Outcome identity/session/role inventory mismatch')
    lookup = {r['participant']: r for r in outcomes}
    means = {(r['target'], r['participant']): r['prediction'] for r in predictions if r['model'] == 'mean'}
    result = []
    for row in predictions:
        truth = lookup[row['participant']]['targets'][row['target']]
        if truth is not None and (not finite(truth) or not 1 <= truth <= 4):
            raise ValueError('Invalid evaluation outcome')
        error = row['prediction'] - truth if truth is not None else None
        baseline = abs(means[row['target'], row['participant']] - truth) if truth is not None else None
        result.append({**row, 'truth': truth, 'scorable': truth is not None, 'signed_error': error,
                       'absolute_error': abs(error) if error is not None else None,
                       'squared_error': error * error if error is not None else None,
                       'mean_absolute_error': baseline, 'training_mean_prediction': means[row['target'], row['participant']],
                       'paired_absolute_error_difference': abs(error) - baseline if error is not None else None,
                       'individual_r2': None, 'individual_r2_reason': 'one independent session per person'})
    return result


def summarize(rows, cfg):
    results = {}
    for target in cfg['targets']:
        results[target] = {}
        for model in ORDER:
            scheduled = [r for r in rows if r['target'] == target and r['model'] == model]
            valid = [r for r in scheduled if r['scorable']]
            complete = [r for r in valid if r['support']['fully_observed']]
            diffs = [r['paired_absolute_error_difference'] for r in valid]
            secondary = regression.metrics(complete)
            secondary['matched_training_mean'] = regression.metrics([{**r, 'prediction': r['training_mean_prediction']} for r in complete])
            results[target][model] = {**regression.metrics(valid), 'scheduled': len(scheduled),
                'unscorable': len(scheduled) - len(valid), 'aggregate_complete_input_n': len(complete),
                'better_than_mean': sum(d < 0 for d in diffs), 'worse_than_mean': sum(d > 0 for d in diffs),
                'tied_with_mean': sum(d == 0 for d in diffs),
                'mean_paired_absolute_error_difference': float(np.mean(diffs)) if diffs else None,
                'secondary_aggregate_complete_inputs': secondary}
    return results


def display(value):
    return 'undefined' if value is None else f'{value:.4f}'


def reports(output, rows, metrics, cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = ('Mean', 'Facial', 'BPM', 'Combined', 'Quality', 'Missingness')
    targets = list(cfg['targets'])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, target in zip(axes, targets):
        x = np.arange(6)
        for offset, metric in [(-.18, 'mae'), (.18, 'rmse')]:
            ax.bar(x + offset, [metrics[target][m][metric] if metrics[target][m][metric] is not None else np.nan for m in ORDER], width=.36, label=metric.upper())
        ax.set(xticks=x, xticklabels=labels, ylabel='Released score units', title=target)
        ax.tick_params(axis='x', rotation=30); ax.legend()
    fig.suptitle('Ten reserved participants; external exposure history unconfirmed; no intervals')
    fig.tight_layout(); fig.savefig(output / 'aggregate-errors.png', dpi=150); plt.close(fig)
    people = list(dict.fromkeys(r['participant'] for r in rows))
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, target in zip(axes, targets):
        data = np.array([[next(r['paired_absolute_error_difference'] for r in rows if r['target'] == target and r['model'] == m and r['participant'] == p) for m in ORDER[1:]] for p in people], dtype=float)
        bound = max(float(np.nanmax(np.abs(data))) if np.isfinite(data).any() else 1., .01)
        im = ax.imshow(np.ma.masked_invalid(data), cmap='RdBu_r', vmin=-bound, vmax=bound, aspect='auto')
        ax.set(xticks=range(5), xticklabels=labels[1:], yticks=range(len(people)), yticklabels=people, title=target)
        ax.tick_params(axis='x', rotation=30); fig.colorbar(im, ax=ax, label='AE(model) - AE(mean); negative improves')
    fig.tight_layout(); fig.savefig(output / 'paired-errors.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(2, 6, figsize=(19, 7))
    for i, target in enumerate(targets):
        for j, model in enumerate(ORDER):
            ax = axes[i, j]; valid = [r for r in rows if r['target'] == target and r['model'] == model and r['scorable']]
            ax.scatter([r['truth'] for r in valid], [r['prediction'] for r in valid]); ax.plot([1, 4], [1, 4], '--', color='gray')
            ax.set(title=target + '\n' + labels[j], xlabel='Observed', ylabel='Saved prediction')
    fig.tight_layout(); fig.savefig(output / 'observed-vs-predicted.png', dpi=150); plt.close(fig)
    lines = ['# Locked session-anxiety evaluation', '', 'Ten reserved participants; external exposure history unconfirmed. No refitting, tuning, clipping, categories, confidence intervals, significance tests or deployment-model selection.',
             'One independent session per person. Cognitive post is primary; somatic post secondary. Negative paired AE differences favor the model.', '']
    for target in targets:
        lines += ['## ' + target, '', '| Model | Scored/scheduled | MAE | RMSE | R2 | Mean paired AE difference | Better/worse/tied vs mean | Complete session inputs |', '|---|---|---:|---:|---:|---:|---|---:|']
        for model in ORDER:
            v = metrics[target][model]
            lines.append(f'| {model} | {v["n"]}/{v["scheduled"]} | {display(v["mae"])} | {display(v["rmse"])} | {display(v["r2"])} | {display(v["mean_paired_absolute_error_difference"])} | {v["better_than_mean"]}/{v["worse_than_mean"]}/{v["tied_with_mean"]} | {v["aggregate_complete_input_n"]} |')
        lines += ['', '| Participant | Model | Post score | Saved prediction | Signed error | Absolute error | Paired AE difference | Input support |', '|---|---|---:|---:|---:|---:|---:|---|']
        for row in rows:
            if row['target'] == target:
                lines.append('| ' + ' | '.join([row['participant'], row['model'], *[display(row[k]) for k in ('truth', 'prediction', 'signed_error', 'absolute_error', 'paired_absolute_error_difference')], str(row['support']['observed']) + '/' + str(row['support']['requested'])]) + ' |')
        lines.append('')
    lines += ['Aggregate-complete inputs do not mean all 18 source windows were supported. See support.json for per-column/per-task window denominators and metrics.json for matched-subset secondary comparisons.',
              'This describes transfer under UBFC protocol conditions; it does not establish ordinary webcam performance, momentary anxiety, causal sensing, or removal of task/recording/missingness confounding.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    with (output / 'individual-errors.csv').open('w', newline='') as stream:
        fields = ['participant', 'target', 'model', 'truth', 'prediction', 'signed_error', 'absolute_error', 'paired_absolute_error_difference', 'scorable']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in rows)


def execute(plan_path, lock_root, output):
    require_ignored(output); output.mkdir(parents=True, exist_ok=False); started = time.perf_counter()
    receipt = {'status': 'verifying_lock', 'procedure': procedure(), 'script': fingerprint(Path(__file__), str(Path(__file__).resolve())),
               'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'plan_path': str(plan_path.resolve()), 'lock_root': str(lock_root.resolve()), 'created': now(),
               'outcomes_released_for_evaluation': False, 'refitted': False}
    atomic(output / 'receipt.json', receipt)
    try:
        cfg, plan, predictions, proof = verify_lock(plan_path, lock_root)
        atomic(output / 'pre-release-verification.json', proof)
        atomic(output / 'configuration.json', cfg); atomic(output / 'evaluation-procedure.json', procedure())
        receipt.update(status='release_authorized_after_verification', gate_passed_at=proof['verified_at']); atomic(output / 'receipt.json', receipt)
        receipt.update(status='releasing_outcomes_for_evaluation', outcomes_released_for_evaluation=True, release_started_at=now())
        atomic(output / 'receipt.json', receipt)
        outcomes, sources = release_outcomes(plan_path, plan, output)
        receipt.update(outcomes_released_for_evaluation=True, release_sources=sources)
        write_jsonl(output / 'outcomes.jsonl', outcomes)
        rows = join_predictions(predictions, outcomes, cfg, plan); write_jsonl(output / 'individual-predictions-errors.jsonl', rows)
        support = [r for path in read(Path(proof['prediction_run']) / 'receipt.json')['exports'] for r in read_jsonl(Path(path) / 'support.jsonl')]
        atomic(output / 'support.json', support)
        metrics = summarize(rows, cfg); atomic(output / 'metrics.json', metrics); reports(output, rows, metrics, cfg)
        if (study.artifact_inventory(Path(proof['prediction_run'])) != proof['prediction_files']
                or study.artifact_inventory(Path(proof['models_run'])) != proof['model_files']
                or study.artifact_inventory(lock_root) != proof['original_lock_files']):
            raise ValueError('Original lock, predictions or models changed during evaluation')
        receipt.update(status='completed', ended=now(), elapsed_seconds=time.perf_counter()-started,
                       output_files=inventory(output)); receipt['output_files'].pop('receipt.json', None)
    except BaseException as exc:
        receipt.update(status='failed', failure=type(exc).__name__ + ': ' + str(exc)); raise
    finally:
        atomic(output / 'receipt.json', receipt)
    return validate(output)


def validate(output):
    receipt = read(output / 'receipt.json')
    actual = inventory(output); actual.pop('receipt.json', None)
    if receipt['status'] != 'completed' or not actual or actual != receipt['output_files']:
        raise ValueError('Incomplete/changed evaluation output')
    cfg, plan = study.load_design(Path(receipt['plan_path']))
    if (receipt['status'] != 'completed' or receipt['refitted'] or receipt['procedure'] != read(output / 'evaluation-procedure.json')
            or receipt['procedure'] != procedure() or read(output / 'configuration.json') != cfg
            or fingerprint(Path(__file__), str(Path(__file__).resolve())) != receipt['script']):
        raise ValueError('Evaluation procedure/source/configuration changed')
    proof = read(output / 'pre-release-verification.json')
    if (study.artifact_inventory(Path(receipt['lock_root'])) != proof['original_lock_files']
            or study.artifact_inventory(Path(proof['prediction_run'])) != proof['prediction_files']
            or study.artifact_inventory(Path(proof['models_run'])) != proof['model_files']):
        raise ValueError('Original lock/predictions/models changed')
    outcomes = read_jsonl(output / 'outcomes.jsonl')
    for row in outcomes:
        p = row['participant']; folder = output / 'released' / p
        if not inspect_info(folder / f'info_{p}.txt', p)['valid'] or row != outcome(folder / f'selfReportedAnx_{p}.csv', p):
            raise ValueError('Released outcome alignment/dimensions changed')
        source = receipt['release_sources'][p]
        if source and fingerprint(folder / f'selfReportedAnx_{p}.csv', f'selfReportedAnx_{p}.csv') != source:
            raise ValueError('Released questionnaire changed')
    predictions = read_jsonl(Path(proof['prediction_run']) / 'predictions.jsonl')
    joined = join_predictions(predictions, outcomes, cfg, plan)
    if joined != read_jsonl(output / 'individual-predictions-errors.jsonl') or summarize(joined, cfg) != read(output / 'metrics.json'):
        raise ValueError('Saved errors/metrics do not reproduce from locked predictions and released outcomes')
    return {'status': 'passed', 'sessions': len(outcomes), 'predictions': len(joined), 'model_outcome_comparisons': 12,
            'scorable': {t: sum(r['targets'][t] is not None for r in outcomes) for t in cfg['targets']},
            'refitted': False, 'original_lock_preserved': True, 'uncertainty_intervals': 'none per locked plan'}


def main():
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--validate', action='store_true')
    parser.add_argument('--plan', type=Path); parser.add_argument('--lock-run', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.execute:
        if not args.plan or not args.lock_run: parser.error('--execute requires --plan and --lock-run')
        result = execute(args.plan, args.lock_run, args.output)
    else: result = validate(args.output)
    print(result)
    if args.execute:
        for target, models in read(args.output / 'metrics.json').items():
            for name in ORDER:
                v = models[name]; print(target, name, {k: v[k] for k in ('n', 'mae', 'rmse', 'r2', 'better_than_mean', 'worse_than_mean', 'mean_paired_absolute_error_difference')})


if __name__ == '__main__':
    main()
