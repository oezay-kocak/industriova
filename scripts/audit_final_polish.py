"""Compare final dev5 sources and tests with the pre-pass backup."""
import ast,hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();out=root/'artifacts/final-polish';backup=out/'20261019T162014Z'
manifest=json.loads((backup/'manifest.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=['core/cards.py','core/enums.py','core/economy.py','core/fixed_prices.py','core/mk_upgrades.py',
 'core/modifiers.py','core/supply.py','core/progression.py','core/production_values.py','core/release_balance.py',
 'core/contracts.py','core/infrastructure.py','core/research.py','core/state.py','core/commands.py',
 'core/simulation.py','core/production_pause.py','core/production_templates.py',
 'persistence/sqlite_store.py','persistence/session_writer.py','persistence/dev_save_store.py','data/definitions.py']
unchanged={name:sha(root/'src/production_zero'/name)==manifest['src/production_zero/'+name] for name in protected}
assert all(unchanged.values()),unchanged
def functions(source):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
def tests(source):
 return {n.name for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
with zipfile.ZipFile(backup/'working-tree.zip') as archive:
 assert archive.testzip() is None
 retained={name:not(tests(archive.read(name))-tests((root/name).read_bytes())) for name in archive.namelist() if name.startswith('tests/test_') and name.endswith('.py')}
 assert all(retained.values())
 old=functions(archive.read('src/production_zero/core/freight.py'));new=functions((root/'src/production_zero/core/freight.py').read_bytes())
 assert old==new,'Freight pricing/simulation functions changed'
assets=[name for name in manifest if name.startswith('src/production_zero/assets/') or name.startswith('src/production_zero/data/')]
assert all(sha(root/name)==manifest[name] for name in assets)
results=json.loads((out/'regression-verified/results.json').read_text())
assert len(results)==79 and sum(r['passed'] for r in results)==1242 and all(r['exit_code']==0 and r['skipped']==0 for r in results)
old_zip=root/'dist/playtest/Industriova-0.2.0-dev4-Windows-Playtest.zip'
assert sha(old_zip)=='883eeb2abd509087c2ebb8399513c4574f5c7bc7d7ba4af643309877bb801fee'
layout=[]
for dpi in ('dpi1','dpi2'):
 before=json.loads((out/'before'/dpi/'layout-metrics.json').read_text());after=json.loads((out/'after'/dpi/'layout-metrics.json').read_text())
 for b,a in zip(before,after):
  for bc,ac in zip(b['cards'],a['cards']):
   ratio=ac['products_height']/bc['products_height'];assert .4<ratio<.6,(dpi,a,ratio)
   layout.append({'dpi':dpi,'size':a['size'],'kind':ac['kind'],'product_height_before':bc['products_height'],'product_height_after':ac['products_height'],'ratio':round(ratio,3),'reward_height_after':ac['rewards_height']})
result={'backup_files':len(manifest),'backup_sha256':sha(backup/'working-tree.zip'),'unchanged_protected_files':unchanged,
 'freight_price_and_simulation_functions_unchanged':True,'unchanged_asset_and_data_files':len(assets),'prior_test_modules_retained':len(retained),
 'prior_tests':sum(r['passed'] for r in results if r['module']!='test_final_micro_polish.py'),'passed':1242,'modules':79,'skipped':0,
 'changed_existing_files':[name for name,value in manifest.items() if not (root/name).exists() or sha(root/name)!=value],
 'dev4_zip_unchanged_sha256':sha(old_zip),'contract_layout':layout}
(out/'source-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
