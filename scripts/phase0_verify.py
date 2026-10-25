"""Verify backup contents and unchanged pre-audit sources, data, tests and saves."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase0'
backup=next(OUT.glob('backup-*'))
manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'))
checked=0
with zipfile.ZipFile(backup/'working-tree.zip') as z:
    assert len(z.infolist())==len(manifest['entries'])
    for row in manifest['entries']:
        h=hashlib.sha256()
        with z.open(row['path']) as f:
            for c in iter(lambda:f.read(4*1024*1024),b''):h.update(c)
        assert h.hexdigest()==row['sha256'],row['path'];checked+=1
print('Verified archive entries:',checked,flush=True)
build_checked=0;build_changed=[]
for row in manifest['entries']:
    if not row['path'].startswith(('dist/','build/')):continue
    p=ROOT/row['path'];h=hashlib.sha256()
    if not p.exists():build_changed.append(row['path']);continue
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=row['sha256']:build_changed.append(row['path'])
    build_checked+=1
source=json.loads((backup/'source-manifest.json').read_text(encoding='utf8'));changed=[];protected=0
for row in source:
    p=ROOT/row['path']
    if row['path'].startswith('.git/'):continue
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:changed.append(row['path'])
    protected+=1
saves=json.loads((backup/'personal-saves-manifest.json').read_text(encoding='utf8'))
personal_changed=[r['original'] for r in saves if hashlib.sha256(Path(r['original']).read_bytes()).hexdigest()!=r['sha256']]
regression=json.loads((OUT/'regression/results.json').read_text(encoding='utf8'))
totals={k:sum(r.get(k,0) for r in regression) for k in ('tests','passed','failures','errors','skipped')}
result={'verified_archive_entries':checked,'protected_existing_files':protected,'changed_existing_files':changed,
        'verified_existing_build_files':build_checked,'changed_existing_build_files':build_changed,
        'personal_saves_unchanged':not personal_changed,'changed_personal_saves':personal_changed,
        'regression_modules':len(regression),'regression_totals':totals,
        'failed_modules':[r['module'] for r in regression if r['exit_code']!=0]}
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)
assert not changed and not personal_changed and not build_changed
