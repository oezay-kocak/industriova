"""Verify exact P8 scope against the complete P7 working-tree backup."""
import hashlib,json,difflib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase8'
BACKUP=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));BASE=OUT/'before-tree'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
allowed_source={
 'src/production_zero/core/commands.py','src/production_zero/core/consortium.py',
 'src/production_zero/core/contracts.py','src/production_zero/core/production_values.py',
 'src/production_zero/persistence/sqlite_store.py','src/production_zero/tools/economy_stress_test.py',
 'src/production_zero/ui/consortium_view.py','src/production_zero/ui/contracts_view.py',
 'src/production_zero/ui/contract_product.py'}
allowed_tests={
 'tests/contract_acceptance_fixture.py','tests/test_commands_and_simulation.py',
 'tests/test_company_xp_progression.py','tests/test_consortium.py',
 'tests/test_global_storage_and_contract_diversification.py','tests/test_industriova_release_integration.py',
 'tests/test_phase2_inventory_backend.py','tests/test_phase6_freight_statistics.py',
 'tests/test_phase7_economy.py','tests/test_playtest_fix_pass.py','tests/test_research.py',
 'tests/test_research_specialization.py'}
manifest=json.loads((BACKUP/'manifest.json').read_text(encoding='utf8'))
personal=json.loads((BACKUP/'personal-saves-manifest.json').read_text(encoding='utf8'))
result=dict(changed_existing_source=[],protected=[],personal=[],missing=[],unexpected=[],new_files=[])
diff=[]
def needs_hash(name):
    if '__pycache__/' in name:return False
    return name.startswith(('src/','tests/','scripts/','docs/','build/','dist/')) or (name.startswith('artifacts/') and not name.startswith('artifacts/phase8/') and not name.endswith('.zip')) or name in {'pyproject.toml','README.md','Industriova.spec','ProductionZero.spec','.gitignore','.gitattributes'}
targets=[e['path'] for e in manifest['entries'] if needs_hash(e['path']) and (ROOT/e['path']).is_file()]
digests={}
with ThreadPoolExecutor(max_workers=4) as pool:
    for index,(name,digest) in enumerate(zip(targets,pool.map(sha,(ROOT/name for name in targets))),1):
        digests[name]=digest
        if index%5000==0:print('hashed',index,'of',len(targets),flush=True)
for entry in manifest['entries']:
    name=entry['path'];path=ROOT/name
    if '__pycache__/' in name:continue
    source=name.startswith(('src/','tests/','scripts/','docs/'))
    protected=name.startswith(('build/','dist/'))
    protected=protected or (name.startswith('artifacts/') and not name.startswith('artifacts/phase8/') and not name.endswith('.zip'))
    protected=protected or (name.startswith('src/') and name not in allowed_source)
    protected=protected or name in {'pyproject.toml','README.md','Industriova.spec','ProductionZero.spec','.gitignore','.gitattributes'}
    if not(source or protected):continue
    if not path.is_file():result['missing'].append(name);continue
    digest=digests.get(name) or sha(path);same=digest==entry['sha256']
    if protected:result['protected'].append(dict(path=name,sha256=digest,unchanged=same))
    if source and not same:
        result['changed_existing_source'].append(name)
        if name not in allowed_source|allowed_tests:result['unexpected'].append(name)
        before=BASE/name
        if before.is_file() and path.suffix in {'.py','.md','.json','.csv'}:
            diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),path.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
known={e['path'] for e in manifest['entries']}
for folder in ('src','tests','scripts','docs'):
    for path in sorted((ROOT/folder).rglob('*')):
        name=path.relative_to(ROOT).as_posix()
        if path.is_file() and path.suffix in {'.py','.md','.json','.csv'} and name not in known and '__pycache__/' not in name:
            result['new_files'].append(name)
            if name.startswith('src/') and name!='src/production_zero/core/contract_capacity.py':result['unexpected'].append(name)
            diff.extend(difflib.unified_diff([],path.read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/'+name))
for entry in personal:
    path=Path(entry['original']);digest=sha(path)
    result['personal'].append(dict(path=str(path),sha256=digest,unchanged=digest==entry['sha256']))
for name in ('game_definitions.json','resource_definitions.json','research_definitions.json'):
    relative='src/production_zero/data/'+name
    assert sha(ROOT/relative)==sha(BASE/relative),relative
result['catalog_resources_research_unchanged']=True
result['ok']=not(result['missing'] or result['unexpected']) and all(e['unchanged'] for e in result['protected']+result['personal'])
(OUT/'protected-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
print(json.dumps(dict(ok=result['ok'],protected=len(result['protected']),personal=result['personal'],unexpected=result['unexpected'],missing=result['missing']),indent=2))
assert result['ok']
