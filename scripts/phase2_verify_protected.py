"""Verify P2 boundaries against the full working-tree backup, never Git HEAD."""
import hashlib,json,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase2';BACKUP=Path((OUT/'backup-location.txt').read_text());BASE=OUT/'before-tree'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
manifest=json.loads((BACKUP/'manifest.json').read_text());personal=json.loads((BACKUP/'personal-saves-manifest.json').read_text())
allowed={'src/production_zero/core/'+name+'.py' for name in ('commands','state','inventory','supply','machine_operations','production_templates')}
result=dict(changed_existing_source=[],protected=[],personal=[],missing=[],unexpected=[]);diff=[]
for entry in manifest['entries']:
 name=entry['path'];path=ROOT/name
 if '__pycache__/' in name:continue
 source=name.startswith(('src/','tests/','scripts/','docs/'))
 protected=name.startswith(('build/','dist/','artifacts/phase0/','artifacts/phase1/')) and not name.endswith('.zip')
 # Hash all existing productive source and data, including all P1 UI/cache code.
 protected=protected or (name.startswith('src/') and name not in allowed)
 if not(source or protected):continue
 if not path.is_file():result['missing'].append(name);continue
 same=sha(path)==entry['sha256']
 if protected:result['protected'].append(dict(path=name,unchanged=same))
 if source and not same:
  result['changed_existing_source'].append(name)
  if name.startswith('src/') and name not in allowed:result['unexpected'].append(name)
  before=BASE/name
  if before.is_file() and path.suffix in {'.py','.md'}:
   diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),path.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
for entry in personal:
 path=Path(entry['original']);result['personal'].append(dict(path=str(path),unchanged=sha(path)==entry['sha256']))
result['ok']=not(result['missing'] or result['unexpected']) and all(e['unchanged'] for e in result['protected']+result['personal'])
(OUT/'protected-verification.json').write_text(json.dumps(result,indent=2));(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
print(json.dumps(dict(ok=result['ok'],protected=len(result['protected']),personal=result['personal'],changed=result['changed_existing_source'],unexpected=result['unexpected'],missing=result['missing']),indent=2))
assert result['ok']
