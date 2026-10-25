"""Verify P4 boundaries against the full working-tree backup, never Git HEAD."""
import hashlib,json,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7';BACKUP=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));BASE=OUT/'before-tree'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
manifest=json.loads((BACKUP/'manifest.json').read_text(encoding='utf8'));personal=json.loads((BACKUP/'personal-saves-manifest.json').read_text(encoding='utf8'))
allowed={'src/production_zero/ui/factory_view_v2.py', 'src/production_zero/data/definitions.py', 'src/production_zero/core/production_templates.py', 'src/production_zero/core/definitions.py', 'src/production_zero/core/supply.py', 'src/production_zero/core/release_balance.py', 'src/production_zero/core/state.py', 'src/production_zero/core/machine_operations.py', 'src/production_zero/core/economy.py', 'src/production_zero/ui/release_board.py', 'src/production_zero/ui/main_window.py', 'src/production_zero/persistence/sqlite_store.py', 'src/production_zero/data/game_definitions.json', 'src/production_zero/ui/freight_lines.py', 'src/production_zero/core/commands.py', 'src/production_zero/ui/freight_view.py', 'src/production_zero/core/freight.py', 'src/production_zero/ui/factory_view.py', 'src/production_zero/core/freight_routes.py'}
result=dict(changed_existing_source=[],protected=[],personal=[],missing=[],unexpected=[]);diff=[]
for entry in manifest['entries']:
 name=entry['path'];path=ROOT/name
 if '__pycache__/' in name:continue
 source=name.startswith(('src/','tests/','scripts/','docs/'))
 protected=name.startswith(('build/','dist/','artifacts/phase0/','artifacts/phase1/','artifacts/phase2/','artifacts/phase3/','artifacts/phase4/','artifacts/phase5/','artifacts/phase6/')) and not name.endswith('.zip')
 protected=protected or name.startswith(('build/','dist/'))
 protected=protected or (name.startswith('artifacts/') and not name.startswith('artifacts/phase7/') and path.suffix in {'.png','.sqlite','.db'})
 # Hash all existing productive source and data, including all P1 UI/cache code.
 protected=protected or (name.startswith('src/') and name not in allowed) or name in {'pyproject.toml','README.md','Industriova.spec','ProductionZero.spec','.gitignore','.gitattributes'}
 if not(source or protected):continue
 if not path.is_file():result['missing'].append(name);continue
 same=sha(path)==entry['sha256']
 if protected:result['protected'].append(dict(path=name,unchanged=same))
 if source and not same:
  result['changed_existing_source'].append(name)
  if name.startswith('src/') and name not in allowed:result['unexpected'].append(name)
  before=BASE/name
  if before.is_file() and path.suffix in {'.py','.md','.json','.csv'}:
   diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),path.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
known={e['path'] for e in manifest['entries']}
result['new_files']=[]
for folder in ('src','tests','scripts','docs'):
 for path in sorted((ROOT/folder).rglob('*')):
  name=path.relative_to(ROOT).as_posix()
  if path.is_file() and path.suffix in {'.py','.md','.json','.csv'} and name not in known and '__pycache__/' not in name:
   result['new_files'].append(name)
   if name.startswith('src/') and name not in {'src/production_zero/core/infrastructure_prices.py'}:result['unexpected'].append(name)
   diff.extend(difflib.unified_diff([],path.read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/'+name))
for entry in personal:
 path=Path(entry['original']);result['personal'].append(dict(path=str(path),unchanged=sha(path)==entry['sha256']))
expected_existing=allowed|{'tests/test_freight.py', 'tests/test_factory_view_v2.py', 'tests/test_commands_and_simulation.py', 'tests/test_industriova_release_ui.py', 'tests/test_phase6_freight_statistics.py', 'tests/test_unified_production_ux.py', 'tests/test_phase1_performance.py', 'tests/test_ui_interaction_recovery.py', 'tests/test_industriova_release_integration.py', 'tests/test_factory_ui.py', 'tests/test_final_micro_polish.py', 'tests/test_final_visual_audit_fix_pass.py', 'tests/test_paid_templates.py', 'tests/test_ui_polish_interactions.py', 'tests/test_production_board_split.py', 'tests/test_phase2_inventory_backend.py', 'tests/test_sqlite_store.py', 'tests/test_resources_and_cash.py', 'tests/test_recipe_retirement.py'}
result['unexpected'].extend(name for name in result['changed_existing_source'] if name not in expected_existing)
old_catalog=json.loads((BASE/'src/production_zero/data/game_definitions.json').read_text(encoding='utf8'))
new_catalog=json.loads((ROOT/'src/production_zero/data/game_definitions.json').read_text(encoding='utf8'))
# Pin the complete catalog except the three authorized raw Ship fields.
from copy import deepcopy
catalog_copy=deepcopy(new_catalog)
def undo_ship(new,old):
 if isinstance(new,dict):
  if new.get('definition_id')=='freight.ship' or new.get('id')=='freight.ship':
   for key in ('base_capacity','base_transport_time_seconds','supply_price_cash'):
    if key in old:new[key]=old[key]
    else:new.pop(key,None)
  else:
   for key,value in new.items():
    if key in old:undo_ship(value,old[key])
 elif isinstance(new,list):
  for value,previous in zip(new,old):undo_ship(value,previous)
undo_ship(catalog_copy,old_catalog)
result['catalog_except_ship_unchanged']=catalog_copy==old_catalog
assert result['catalog_except_ship_unchanged'],'Unexpected non-Ship catalog delta'
result['ok']=not(result['missing'] or result['unexpected']) and all(e['unchanged'] for e in result['protected']+result['personal'])
(OUT/'protected-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
print(json.dumps(dict(ok=result['ok'],protected=len(result['protected']),personal=result['personal'],changed=result['changed_existing_source'],unexpected=result['unexpected'],missing=result['missing']),indent=2))
assert result['ok']
