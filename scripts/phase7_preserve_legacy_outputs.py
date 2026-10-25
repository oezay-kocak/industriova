"""Retain fresh legacy-test screenshots in P3; restore their old references."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7';backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'))
cache={}
def manifest(path):
 if path not in cache:
  value=json.loads(path.read_text(encoding='utf8'));cache[path]=(value,{e['path']:e for e in value['entries']})
 return cache[path]
def original(path,name):
 m,entries=manifest(path);entry=entries[name];storage=entry['storage']
 if storage.startswith('previous-'):return original(Path(m['previous_manifest']),name)
 if storage=='delta-entry':archive=path.parent/'working-tree-delta.zip'
 elif storage=='base-entry':archive=Path(m['base_archive'])
 else:raise ValueError((name,storage))
 with zipfile.ZipFile(archive) as z:data=z.read(name)
 assert hashlib.sha256(data).hexdigest()==entry['sha256']
 return data
prefixes=('artifacts/phase3/legacy-test-captures/','artifacts/charts-polish/','artifacts/contracts-polish/','artifacts/inventory-workspaces/',
 'artifacts/leaderboard_jump_','artifacts/leaderboard_polish_','artifacts/market-polish/','artifacts/packs_',
 'artifacts/supply-polish/','artifacts/ui/research-canvas-background/','artifacts/ui/research-final-refinement/',
 'artifacts/ui/research-generic-icon/','artifacts/ui/research-layout-stability/',
 'artifacts/charts_detail_empty_redesign_preview.png','artifacts/contracts_redesign_preview.png',
 'artifacts/freight_factory_language_','artifacts/industrial_supply_')
record_path=OUT/'legacy-capture-preservation.json'
records=json.loads(record_path.read_text(encoding='utf8'))['files'] if record_path.exists() else []
m,entries=manifest(backup/'manifest.json');restored_this_run=0
for name,e in entries.items():
 if not name.endswith('.png') or name.startswith('artifacts/phase7/'):continue
 path=ROOT/name
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256']:continue
 preserved=OUT/'legacy-test-captures'/path.relative_to(ROOT/'artifacts');preserved.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(path,preserved)
 path.write_bytes(original(backup/'manifest.json',name))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256']
 records.append(dict(reference=name,preserved=str(preserved.relative_to(ROOT)),restored_sha256=e['sha256']))
 restored_this_run+=1
records=list({r['reference']:r for r in records}.values())
record_path.write_text(json.dumps(dict(restored=len(records),files=records),indent=2),encoding='utf8')
print(json.dumps(dict(restored_this_run=restored_this_run,total_references_preserved=len(records))),flush=True)
