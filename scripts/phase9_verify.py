"""Final source freeze, preserved test identities, screenshots and original data."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,struct,difflib,xml.etree.ElementTree as ET
root=Path.cwd();out=root/'artifacts/phase9';backup=Path((out/'backup-location.txt').read_text(encoding='utf8'));base=out/'before-tree'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert all(sha(root/n)==h for n,h in frozen.items())
def cases(folder):
 c=Counter()
 for p in folder.glob('test_*.xml'):
  for t in ET.parse(p).getroot().iter('testcase'):c[t.get('classname'),t.get('name')]+=1
 return c
old=cases(root/'artifacts/phase8/final-regression');new=cases(out/'final-regression')
assert sum(old.values())==1869 and not old-new
reg=json.loads((out/'final-regression/results.json').read_text(encoding='utf8'));dpi=json.loads((out/'dpi2-regression/results.json').read_text(encoding='utf8'))
assert len(reg)==95 and all(x['exit_code']==0 and x['skipped']==0 for x in reg+dpi)
(out/'regression-summary.json').write_text(json.dumps(dict(original_cases=sum(old.values()),retained_cases=sum(old.values()),final_cases=sum(new.values()),new_cases=sum((new-old).values()),modules=len(reg),dpi2_cases=sum(x['tests'] for x in dpi),dpi2_modules=len(dpi),failures=0,skips=0),indent=2),encoding='utf8')
allowed={
 'core/consortium.py','core/simulation.py','ui/contracts_view.py','ui/consortium_view.py','ui/event_feed.py','ui/factory_view.py','ui/factory_view_v2.py','ui/freight_view.py','ui/main_window.py','ui/main_tab_header.py','ui/interaction_polish.py',
}
allowed={'src/production_zero/'+n for n in allowed}|{'tests/'+n for n in ('test_consortium.py','test_consortium_ui.py','test_phase8_contract_balance.py','test_phase8_contract_ui.py','test_industriova_release_integration.py','test_factory_view_v2.py','test_factory_ui.py')}
m=json.loads((backup/'manifest.json').read_text(encoding='utf8'));changed=[];diff=[]
for e in m['entries']:
 p=root/e['path'];assert p.exists(),e['path']
 if sha(p)!=e['sha256']:
  assert e['path'] in allowed,e['path'];changed.append(e['path'])
  diff.extend(difflib.unified_diff((base/e['path']).read_text(encoding='utf8').splitlines(True),p.read_text(encoding='utf8').splitlines(True),fromfile='before/'+e['path'],tofile='after/'+e['path']))
known={e['path'] for e in m['entries']};new_files=[]
for folder in ('src','tests','scripts','docs'):
 for p in (root/folder).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts:continue
  name=p.relative_to(root).as_posix()
  if name not in known:
   assert name.startswith(('scripts/phase9_','docs/industriova-03-phase9-')) or name in ('src/production_zero/core/freight_settlement.py','src/production_zero/ui/resource_prices.py','tests/consortium_freight_fixture.py','tests/test_phase9_freight_only.py','tests/test_phase9_navigation_ui.py'),name
   new_files.append(name)
   if p.suffix in ('.py','.md'):diff.extend(difflib.unified_diff([],p.read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/'+name))
(out/'implementation.diff').write_text(''.join(diff),encoding='utf8')
with ThreadPoolExecutor(max_workers=4) as pool:
 checked=list(pool.map(lambda e:sha(root/e['path'])==e['sha256'],m['protected_builds']))
assert all(checked)
personal=json.loads((backup/'personal-saves-manifest.json').read_text(encoding='utf8'))
assert len(personal)==5 and all(sha(Path(e['original']))==e['sha256'] for e in personal)
# Existing final P8 evidence is retained. Source hashes in its manifest are
# historical by definition and are compared separately against before-tree.
p8=json.loads((root/'artifacts/phase8/delivery-manifest.json').read_text(encoding='utf8'))
entries=p8.get('files',p8.get('entries',[])) if isinstance(p8,dict) else p8
evidence=[]
if isinstance(entries,dict):entries=[dict(path=k,sha256=v) for k,v in entries.items()]
for e in entries:
 name=e.get('path',e.get('file',''))
 if name.startswith('artifacts/phase8/'):
  assert sha(root/name)==e['sha256'],name;evidence.append(name)
report=dict(ok=True,changed_existing=sorted(changed),new_files=sorted(new_files),unchanged_baseline_files=len(m['entries'])-len(changed),protected_build_files=len(checked),personal_saves=5,p8_evidence_files=len(evidence),backup=str(backup),previous_chain_manifest_unchanged=sha(Path(m['previous_manifest']))==m['previous_manifest_sha256'])
assert report['previous_chain_manifest_unchanged']
(out/'protected-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)
