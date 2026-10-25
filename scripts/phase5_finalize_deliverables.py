"""Add the finished report to the already verified delta without re-running tests or timings."""
import json,hashlib,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
protected=json.loads((OUT/'protected-verification.json').read_text(encoding='utf8'));assert protected['ok']
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'))
baseline=json.loads((backup/'manifest.json').read_text(encoding='utf8'));known={r['path'] for r in baseline['entries']}
new=[]
for folder in ('src','tests','scripts','docs'):
    for p in (ROOT/folder).rglob('*'):
        name=p.relative_to(ROOT).as_posix()
        if p.is_file() and p.suffix in {'.py','.md'} and '__pycache__/' not in name and name not in known:new.append(name)
protected['new_files']=sorted(new)
protected['post_verification_additions']='Only the new P5 report and audit-script inventory/diff were finalized after protected-file hashing; productive source/tests remain pinned by tested-source-sha256.json.'
(OUT/'protected-verification.json').write_text(json.dumps(protected,indent=2),encoding='utf8')
files=sorted(set(protected['changed_existing_source']+new));diff=[];manifest=[]
frozen=json.loads((OUT/'tested-source-sha256.json').read_text(encoding='utf8'))
for name in files:
    p=ROOT/name;data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if name.startswith(('src/','tests/')):
        assert digest==frozen.get(str(Path(name))),name
    before=OUT/'before-tree'/name
    old=before.read_text(encoding='utf8').splitlines(True) if before.exists() else []
    diff.extend(difflib.unified_diff(old,p.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name if before.exists() else '/dev/null',tofile='after/'+name))
    manifest.append(dict(path=name,sha256=digest,bytes=len(data)))
(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
(OUT/'deliverables-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
assert 'docs/industriova-03-phase5-freight-ui-report.md' in files
print(json.dumps(dict(deliverables=len(manifest),report_in_diff=True,protected=protected['ok'])),flush=True)
