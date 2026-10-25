"""Final source/evidence integrity, test retention and complete working-tree diff."""
import ast,difflib,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7';BASE=OUT/'before-tree'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tested=read(OUT/'tested-source-sha256.json');assert all(sha(ROOT/n)==h for n,h in tested.items())
protected=read(OUT/'protected-verification.json');assert protected['ok']
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'))
personal=read(backup/'personal-saves-manifest.json');assert all(sha(Path(e['original']))==e['sha256'] for e in personal)
retention=[]
for old in sorted((BASE/'tests').glob('test_*.py')):
    current=ROOT/'tests'/old.name
    def names(p):return {n.name for n in ast.walk(ast.parse(p.read_text(encoding='utf8'))) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')}
    assert names(old)<=names(current),old.name
    retention.append(dict(module=old.name,retained_test_functions=len(names(old))))
assert len(retention)==89
summary=read(OUT/'final-test-summary.json');assert summary['passed']==1779 and summary['retained_baseline_tests']==1670
dpi=ET.parse(OUT/'dpi2-accepted-tests.xml').getroot();suites=list(dpi.iter('testsuite'));assert sum(int(s.get('tests',0)) for s in suites)==120
assert all(all(int(s.get(k,0))==0 for k in ('errors','failures','skipped')) for s in suites)
assert read(OUT/'migration-after.json')['passed']==16
economy=read(OUT/'after/economy-simulation.json');old=read(OUT/'before-refined/economy-simulation.json');assert len(economy['scenarios'])==56 and economy==old
assert read(OUT/'after/early-progression.json')==read(OUT/'before-refined/early-progression.json')
visual=read(OUT/'visual-verification.json');assert visual['captures']==132 and all(sha(ROOT/r['file'])==r['sha256'] for r in visual['rows'])
review=read(OUT/'visual-review.json');assert all(sha(ROOT/r['file'])==r['sha256'] for r in review['reviewed'])
diff=[];changed=[];new=[]
for folder in ('src','tests','scripts','docs'):
    for p in sorted((ROOT/folder).rglob('*')):
        if not p.is_file() or p.suffix not in {'.py','.json','.md','.csv'} or '__pycache__' in p.parts:continue
        rel=p.relative_to(ROOT).as_posix();baseline=BASE/rel
        if baseline.is_file() and baseline.read_bytes()==p.read_bytes():continue
        before=baseline.read_text(encoding='utf8').splitlines(True) if baseline.exists() else []
        diff.extend(difflib.unified_diff(before,p.read_text(encoding='utf8').splitlines(True),fromfile='before/'+rel if baseline.exists() else '/dev/null',tofile='after/'+rel))
        (changed if baseline.exists() else new).append(rel)
(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
complete=dict(ok=True,tests=summary,additional_dpi2_tests=120,historical_migrations=16,matched_economy_scenarios=56,visual_captures=132,protected_files=len(protected['protected']),unchanged_personal_saves=len(personal),retained_test_modules=retention,changed_existing_files=changed,new_files=new,productive_sources_and_tests_frozen=True,native_windows_hand_acceptance='open',windows_build_created=False)
(OUT/'postchecks-complete.json').write_text(json.dumps(complete,indent=2),encoding='utf8')
paths={ROOT/n for n in changed+new}
paths.update([OUT/n for n in ('backup-location.txt','source-baseline-verification.json','runtime-price-parity.json','live-price-table.json','marginal-comparison.json','migration-before.json','migration-after.json','final-test-summary.json','tested-source-sha256.json','accepted-source-tests-freeze.json','dpi2-accepted-tests.xml','dpi2-accepted-tests.log','visual-verification.json','visual-review.json','legacy-capture-preservation.json','performance-complete.json','performance-comparison.json','performance-comparison.md','active-repeat-comparison.json','active-repeat-comparison.md','protected-verification.json','implementation.diff','postchecks-complete.json')])
paths.update(backup/n for n in ('manifest.json','personal-saves-manifest.json','SHA256SUMS.json'))
for stage in ('before','before-refined','after'):
    for name in ('economy-simulation.json','early-playthrough.json','early-progression.json'):
        p=OUT/stage/name
        if p.is_file():paths.add(p)
for stage in ('before','after'):
    paths.add(OUT/stage/'purchases/results.json')
    paths.update(p for folder in ('active','extended','rapid') for p in (OUT/stage/folder).rglob('*') if p.is_file() and p.suffix in {'.json','.log'})
    paths.update((OUT/'active-repeat'/stage).glob('*.json'))
paths.update((OUT/'final-accepted-tests').glob('*'))
paths.update(ROOT/r['file'] for r in visual['rows'])
records=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths) if p.is_file()]
manifest=OUT/'deliverables-manifest.json';manifest.write_text(json.dumps(dict(files=records,total=len(records),backup_archive_hashes='See backup/SHA256SUMS.json; the large retained archive chain is not copied or rehashed for delivery.'),indent=2),encoding='utf8')
(OUT/'deliverables-manifest.sha256').write_text(sha(manifest)+'  deliverables-manifest.json\n',encoding='ascii')
assert all(sha(ROOT/r['path'])==r['sha256'] for r in records)
print(json.dumps(dict(ok=True,files=len(records),tests=1779,migrations=16,protected=len(protected['protected']),personal=len(personal),changed=len(changed),new=len(new))),flush=True)
