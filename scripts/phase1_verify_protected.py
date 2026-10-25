"""Read-only hash verification of P1 source boundaries and protected user files."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase1'
BACKUP=OUT/'backup-20261021T185035Z'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
manifest=json.loads((BACKUP/'manifest.json').read_text(encoding='utf8'))
personal=json.loads((BACKUP/'personal-saves-manifest.json').read_text(encoding='utf8'))
result=dict(protected=[],personal=[],changed_existing_source=[],missing=[])
for entry in manifest['entries']:
    name=entry['path'].replace('\\','/');path=ROOT/name
    protected=(name.startswith(('build/','dist/','artifacts/phase0/','src/production_zero/data/','src/production_zero/assets/','src/production_zero/ui/game_ui/'))
               and '__pycache__/' not in name)
    protected=protected or (name.startswith('src/production_zero/core/') and '__pycache__/' not in name and name!='src/production_zero/core/progression.py')
    protected=protected or name=='src/production_zero/persistence/sqlite_store.py'
    protected=protected or name=='src/production_zero/ui/theme.py'
    source=name.startswith(('src/','scripts/','docs/','tests/')) and '__pycache__/' not in name
    if not (protected or source):continue
    if not path.is_file():result['missing'].append(name);continue
    actual=sha(path);same=actual==entry['sha256']
    if protected:result['protected'].append(dict(path=name,unchanged=same))
    if source and not same:result['changed_existing_source'].append(name)
for entry in personal:
    path=Path(entry['original'])
    result['personal'].append(dict(path=str(path),unchanged=path.is_file() and sha(path)==entry['sha256']))
result['ok']=(not result['missing'] and all(e['unchanged'] for e in result['protected']+result['personal']))
(OUT/'protected-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(ok=result['ok'],protected=len(result['protected']),personal=result['personal'],changed_existing_source=result['changed_existing_source'],missing=result['missing']),indent=2))
if not result['ok']:raise SystemExit(1)
