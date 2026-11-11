"""Private append-only pilot attempts, content verification and safe local ZIPs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import time
import uuid
import zipfile

from .manifest import fingerprint
from .validate_sample import missing_files, require_ignored

GIB = 1024 ** 3


def read(path):
    return json.loads(Path(path).read_text())


def atomic(path, value):
    require_ignored(path.parent)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def inventory(folder):
    """Hash every file; no symlink traversal or mtime-only resume decisions."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Expected a nonsymlink directory')
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in input/output tree')
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = fingerprint(path, path.relative_to(folder).as_posix())
    return result


def inspect_zip(path, participant):
    """Read central directory only; require canonical participant paths, keep ZIP."""
    names, files, total = set(), set(), 0
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename.rstrip('/')
            parts = PurePosixPath(name).parts
            mode = entry.external_attr >> 16
            if (not parts or name.startswith('/') or '\\' in name or ':' in name
                    or any(p in ('', '.', '..') for p in name.split('/'))
                    or parts[0] != participant or len(parts) > 2
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('Unsafe, encrypted, unsupported or noncanonical ZIP member')
            folded = name.casefold()
            if folded in names:
                raise ValueError('Duplicate/case-colliding ZIP member')
            names.add(folded)
            if not entry.is_dir():
                if len(parts) != 2:
                    raise ValueError('ZIP file conflicts with participant directory')
                files.add(parts[1])
                total += entry.file_size
        expected = {f'{kind}_{participant}_T{t}.{ext}' for t in (1, 2, 3)
                    for kind, ext in (('vid', 'avi'), ('bvp', 'csv'), ('eda', 'csv'))}
        expected |= {f'info_{participant}.txt', f'selfReportedAnx_{participant}.csv'}
        if files != expected:
            raise ValueError('ZIP must contain exactly the documented participant file set')
    return {'archive_bytes': path.stat().st_size, 'declared_extracted_bytes': total,
            'file_count': len(files), 'paths_checked': True, 'crc_check': 'pending full extraction'}


def extract_zip(path, participant, output):
    inspect_zip(path, participant)
    before = fingerprint(path, path.name)
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            target = output / entry.filename
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('xb') as dest:
                    shutil.copyfileobj(source, dest, length=1024 * 1024)
                if target.stat().st_size != entry.file_size:
                    raise ValueError('Extracted size mismatch')
    if fingerprint(path, path.name) != before:
        raise ValueError('Archive changed during extraction')
    if missing_files(output / participant):
        raise ValueError('Incomplete extraction')


class StageStore:
    """Only a completed receipt plus exact signature AND output hashes can resume."""

    def __init__(self, root):
        require_ignored(root)
        self.root = root

    def lookup(self, key, signature):
        for receipt in sorted((self.root / key).glob('*/receipt.json'), reverse=True):
            try:
                meta = read(receipt)
                output = Path(meta['output'])
                require_ignored(output)
                if (meta['status'] == 'completed' and meta['signature'] == signature
                        and meta.get('policy') == meta['specification'].get('context', {}).get('policy')
                        and meta['output_files'] and inventory(output) == meta['output_files']):
                    return meta
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return None

    def run(self, key, specification, action, verify, candidate=None):
        started = time.perf_counter()
        signature = digest(specification)
        cached = self.lookup(key, signature)
        if cached:
            return {**cached, 'decision': 'resume', 'decision_seconds': time.perf_counter() - started}
        attempt = self.root / key / (str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        attempt.mkdir(parents=True, exist_ok=False)
        output = attempt / 'output'
        meta = {'key': key, 'signature': signature, 'specification': specification,
                'policy': specification.get('context', {}).get('policy'),
                'status': 'running', 'started': now(), 'output': str(output.resolve()),
                'receipt': str((attempt / 'receipt.json').resolve())}
        atomic(attempt / 'receipt.json', meta)
        started = time.perf_counter()
        try:
            imported = False
            if candidate is not None:
                try:
                    require_ignored(candidate)
                    verify(candidate)
                    output = candidate
                    imported = True
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    meta['candidate_rejected'] = f'{type(exc).__name__}: {exc}'
            if not imported:
                action(output, attempt / 'command.log')
                verify(output)
            outputs = inventory(output)
            if not outputs:
                raise ValueError('Empty stage output')
            meta.update(status='completed', output=str(output.resolve()), output_files=outputs,
                        imported=imported, output_bytes=sum(f['bytes'] for f in outputs.values()))
        except BaseException as exc:
            meta.update(status='failed', failure=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            meta.update(ended=now(), elapsed_seconds=time.perf_counter() - started)
            atomic(attempt / 'receipt.json', meta)
        return {**meta, 'decision': 'import' if imported else 'run',
                'decision_seconds': time.perf_counter() - started}
