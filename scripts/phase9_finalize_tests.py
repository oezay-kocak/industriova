"""Keep the original failed expectation and reconcile its full module rerun."""
from pathlib import Path
import time,json,hashlib,shutil,subprocess,sys
root=Path.cwd();out=root/'artifacts/phase9';dest=out/'final-regression';rerun=out/'tooltip-test-rerun'
deadline=time.monotonic()+900
while True:
 records=json.loads((dest/'results.json').read_text(encoding='utf8')) if (dest/'results.json').exists() else []
 repeated=json.loads((rerun/'results.json').read_text(encoding='utf8')) if (rerun/'results.json').exists() else []
 if len(records)==95 and len(repeated)==1:break
 assert time.monotonic()<deadline,'Owned regression jobs did not finish within 15 minutes.'
 time.sleep(2)
assert all(r['exit_code']==0 for r in repeated)
old=json.loads((out/'source-before-tooltip-test-adjustment-sha256.json').read_text(encoding='utf8'))
new=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert {n for n in new if new[n]!=old[n]}=={'tests/test_factory_ui.py'}
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in new.items())
diagnostic=out/'regression-before-tooltip-test-adjustment';diagnostic.mkdir(exist_ok=True)
shutil.copyfile(dest/'results.json',diagnostic/'results.json')
for extension in ('.txt','.xml'):
 name='test_factory_ui'+extension
 shutil.copyfile(dest/name,diagnostic/name);shutil.copyfile(rerun/name,dest/name)
records=[repeated[0] if r['module']=='test_factory_ui.py' else r for r in records]
assert all(r['exit_code']==0 and r['skipped']==0 for r in records)
(dest/'results.json').write_text(json.dumps(records,indent=2),encoding='utf8')
(dest/'provenance.json').write_text(json.dumps(dict(unchanged_production_source=True,only_test_adjustment='tests/test_factory_ui.py',reason='Elided resource titles retain the full name as a tooltip prefix; P9 also retains the central base price and category. All prior name/elision assertions retained. Complete 217-case module rerun, no deselection.',module_origins={r['module']:('tooltip-test-rerun' if r['module']=='test_factory_ui.py' else 'original full 95-module run') for r in records}),indent=2),encoding='utf8')
print('FINAL REGRESSION',sum(r['tests'] for r in records),len(records),flush=True)
with (out/'postchecks.log').open('w',encoding='utf8') as log:
 result=subprocess.run([sys.executable,'-u','scripts/phase9_postchecks.py'],stdout=log,stderr=subprocess.STDOUT,cwd=root)
assert result.returncode==0,'See postchecks.log and per-job logs'
print('ALL POSTCHECKS FINISHED',flush=True)
