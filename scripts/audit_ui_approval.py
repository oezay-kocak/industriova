"""Compare dev6 UI-only changes against the saved dev5 working tree."""
import ast,hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();out=root/'artifacts/final-ui-approval';backup=out/'20261019T165458Z'
manifest=json.loads((backup/'manifest.json').read_text(encoding='utf-8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[name for name in manifest if name.startswith(('src/production_zero/core/','src/production_zero/data/','src/production_zero/assets/','src/production_zero/persistence/')) and not name.endswith('persistence/paths.py')]
protected += ['src/production_zero/ui/'+name for name in ('contract_product.py','freight_view.py','freight_drag.py','release_freight.py','release_board.py','production_templates.py','research_hover.py','research_view.py','research_specialization.py','game_ui/widgets.py')]
assert all(sha(root/name)==manifest[name] for name in protected)
def tests(source):return {n.name for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
with zipfile.ZipFile(backup/'working-tree.zip') as archive:
 assert archive.testzip() is None
 retained={name:not(tests(archive.read(name))-tests((root/name).read_bytes())) for name in archive.namelist() if name.startswith('tests/test_') and name.endswith('.py')}
 assert all(retained.values())
 old_classes={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(archive.read('src/production_zero/ui/factory_view_v2.py')).body if isinstance(n,ast.ClassDef)}
 new_classes={n.name:ast.dump(n,include_attributes=False) for n in ast.parse((root/'src/production_zero/ui/factory_view_v2.py').read_bytes()).body if isinstance(n,ast.ClassDef)}
 assert all(old_classes[name]==new_classes[name] for name in ('FactoryV2MachineCard','FactoryV2BuildSlot','FactoryV2LockedSlot','FactoryV2TrackPanel'))
results=json.loads((out/'regression-verified/results.json').read_text())
assert len(results)==80 and sum(r['passed'] for r in results)==1257 and all(r['exit_code']==0 and r['skipped']==0 for r in results)
old=root/'dist/playtest/Industriova-0.2.0-dev5-Windows-Playtest.zip';assert sha(old)=='e11772de275ca0b83e97491104efdbee74ccfffff39dbde29a7caf8670920d5f'
for dpi in ('dpi1','dpi2'):
 assert all(row['visible_expansions']==1 for row in json.loads((out/'after'/dpi/'layout-metrics.json').read_text()))
result={'backup_files':len(manifest),'backup_sha256':sha(backup/'working-tree.zip'),'unchanged_protected_files':len(protected),'existing_card_and_track_classes_unchanged':True,
 'unchanged_core_files':sum(name.startswith('src/production_zero/core/') for name in protected),'protected_files':protected,
 'retained_prior_modules':len(retained),'retained_prior_tests':sum(r['passed'] for r in results if r['module']!='test_final_ui_approval.py'),
 'passed':1257,'modules':80,'skipped':0,'dev5_zip_unchanged_sha256':sha(old),
 'changed_existing_files':[name for name,digest in manifest.items() if not (root/name).exists() or sha(root/name)!=digest]}
(out/'source-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='protected_files'},indent=2))
