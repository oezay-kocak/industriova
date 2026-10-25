"""Bind accepted evidence and final productive files to the tested source."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((O/'final-source-sha256.json').read_text(encoding='utf8'))
for name,digest in frozen.items():assert sha(R/name)==digest,name
protected=json.loads((O/'protected-verification.json').read_text(encoding='utf8'));assert protected['ok']
files={R/name for name in frozen}
files.update((R/'scripts').glob('phase8_*.py'))
files.add(R/'docs/industriova-03-phase8-contract-balance-report.md')
files.add(O/'capacity-before-optional-fuel.py')
files.update(O.glob('*.json'));files.update(O.glob('*.log'));files.add(O/'implementation.diff')
for folder in ('final-regression','dpi2-regression','before-matched','after-matched','consortium-before-matched','consortium-after-matched','performance','screenshots','screenshots-accepted'):
    for p in (O/folder).rglob('*'):
        if p.is_file() and p.suffix in {'.json','.xml','.txt','.png'} and not any(part in {'tmp','appdata','cache'} for part in p.relative_to(O/folder).parts):files.add(p)
backup=Path((O/'backup-location.txt').read_text(encoding='utf8'))
files.add(backup/'SHA256SUMS.json');files.add(backup/'manifest.json');files.add(backup/'personal-saves-manifest.json')
files.discard(O/'delivery-manifest.json')
rows=[dict(path=p.relative_to(R).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files) if p.is_file()]
report=dict(files=rows,source_unchanged_since_validation=True,protected_files=len(protected['protected']),personal_saves=len(protected['personal']),backup_chain='Backup SHA256SUMS.json and manifest preserve archive dependencies through P7 to P0; archive hashes were recorded and CRC-verified before edits.',excluded='Temporary AppData/caches/databases, candidate diagnostic trees, Python bytecode and this self-referential manifest.')
(O/'delivery-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(dict(files=len(rows),source_unchanged=True,protected=report['protected_files'],personal=report['personal_saves'])))
