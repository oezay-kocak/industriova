"""Finalize new documentation/inventory after the protected-file audit."""
import json,hashlib,difflib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase6';BASE=OUT/'before-tree'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
protected=read(OUT/'protected-verification.json');assert protected['ok']
expected=read(OUT/'tested-source-sha256.json')['sha256']
actual={p.relative_to(ROOT).as_posix():sha(p) for folder in ('src','tests') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==expected
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));known={r['path']:r for r in read(backup/'manifest.json')['entries']}
rows=[];diff=[]
for folder in ('src','tests','scripts','docs'):
    for p in sorted((ROOT/folder).rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:continue
        name=p.relative_to(ROOT).as_posix();digest=sha(p)
        if name in known and digest==known[name]['sha256']:continue
        assert p.suffix in {'.py','.md'},name
        rows.append(dict(path=name,bytes=p.stat().st_size,sha256=digest,new=name not in known))
        before=BASE/name
        old=before.read_text(encoding='utf8').splitlines(True) if before.is_file() else []
        diff.extend(difflib.unified_diff(old,p.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name if old else '/dev/null',tofile='after/'+name))
report=ROOT/'docs/industriova-03-phase6-freight-statistics-report.md'
text=report.read_text(encoding='utf8');assert not any(ord(c)<32 and c not in '\n\r\t' for c in text)
assert sum(r['path'].startswith('src/') for r in rows)==8
assert sum(r['path'].startswith('tests/') for r in rows)==5
(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
(OUT/'deliverables-manifest.json').write_text(json.dumps(dict(files=rows,productive_and_test_sources_frozen=True,method='Existing protected files and five personal saves verified by protected-verification.json. Only the newly created P6 report/deliverable inventory finalized afterward; productive sources and tests rehashed unchanged. Diff rebuilt against actual source baseline, never Git HEAD.'),indent=2),encoding='utf8')
for r in rows:assert sha(ROOT/r['path'])==r['sha256'] and (ROOT/r['path']).stat().st_size==r['bytes']
import platform,PySide6
(OUT/'environment.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),qt=PySide6.__version__,native_windows_hand_acceptance=False),indent=2),encoding='utf8')
print(json.dumps(dict(deliverables=len(rows),report_bytes=report.stat().st_size,all_sha256_verified=True)))
