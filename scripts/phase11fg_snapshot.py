"""Reproducible, read-only protection and source snapshots for P11-F/G."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'phase11fg'

def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def snapshot(name):
    target = OUT / name
    target.mkdir(parents=True, exist_ok=False)
    files = []
    for folder in ('src', 'tests', 'scripts', 'docs', 'tools'):
        files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(p for p in ROOT.iterdir() if p.is_file())
    manifest = {}
    for path in sorted(files):
        relative = path.relative_to(ROOT)
        dest = target / 'source' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        manifest[str(relative)] = digest(path)
        assert digest(dest) == manifest[str(relative)]
    (target / 'sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    git = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'status', '--short'], cwd=ROOT, capture_output=True, text=True)
    (target / 'version.json').write_text(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'head': git.stdout.strip(), 'git_status': status.stdout, 'pyproject': (ROOT / 'pyproject.toml').read_text(), 'files': len(manifest)}, indent=2), encoding='utf-8')
    if name == 'starting-snapshot':
        prior = json.loads((ROOT / 'artifacts/phase11e/baseline.json').read_text())
        protected = {}
        for value in prior:
            p = Path(value)
            if not p.is_absolute():
                p = ROOT / p
            if 'src' not in p.relative_to(ROOT).parts[:1] if p.is_relative_to(ROOT) else True:
                # Entire prior audits/builds/saves are protected; productive source/tests may change.
                if p.is_relative_to(ROOT) and p.relative_to(ROOT).parts[0] in ('src', 'tests', 'scripts'):
                    continue
                protected[str(p)] = digest(p)
        for folder in ('artifacts/phase11e', 'artifacts/phase11d'):
            for p in (ROOT / folder).rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:
                    protected[str(p)] = digest(p)
        (OUT / 'protected-sha256.json').write_text(json.dumps(protected, indent=2), encoding='utf-8')
    print(json.dumps({'snapshot': str(target), 'files': len(manifest)}))

def verify():
    hashes = json.loads((OUT / 'protected-sha256.json').read_text())
    changed = [p for p, h in hashes.items() if not Path(p).exists() or digest(Path(p)) != h]
    print(json.dumps({'protected': len(hashes), 'changed': changed}))
    assert not changed

if __name__ == '__main__':
    verify() if sys.argv[1] == 'verify' else snapshot(sys.argv[1])
