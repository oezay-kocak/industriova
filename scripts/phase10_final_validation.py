"""Wait for final regression/captures, then serial high-DPI and matched timings."""
from pathlib import Path
import time,json,subprocess,sys,os,hashlib
root=Path.cwd();out=root/'artifacts/phase10';deadline=time.monotonic()+1800
while True:
 path=out/'final-regression/results.json';rows=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
 capture=out/'capture-queue.json';images=json.loads(capture.read_text(encoding='utf8')) if capture.exists() else []
 if len(rows)==97 and len(images)==3:break
 assert time.monotonic()<deadline
 time.sleep(2)
assert all(r['exit_code']==0 and r['skipped']==0 for r in rows),[(r['module'],r['exit_code']) for r in rows if r['exit_code']]
assert all(r['exit_code']==0 for r in images)
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==sha for p,sha in frozen.items())
jobs=[]
modules=['test_phase10_polish_ui.py','test_phase3_inventory_ui.py','test_phase4_drag_ui.py',
 'test_phase5_freight_ui.py','test_phase6_freight_statistics_ui.py','test_phase7_economy_ui.py',
 'test_phase9_navigation_ui.py','test_ui_polish_interactions.py','test_unified_production_ux.py','test_factory_ui.py']
commands=[('dpi2',[sys.executable,'-u','scripts/phase8_run_tests.py','.',str(out/'dpi2-regression'),'--workers','2','--timeout','600']+sum((['--module',name] for name in modules),[]),dict(os.environ,QT_SCALE_FACTOR='2')),
 ('before-benchmark',[sys.executable,'-u','scripts/phase10_benchmark.py','--source',str(out/'before-tree'),'--stage','before'],dict(os.environ)),
 ('after-benchmark',[sys.executable,'-u','scripts/phase10_benchmark.py','--stage','after'],dict(os.environ))]
for name,command,environment in commands:
 if name=='dpi2' and '--resume' in sys.argv:
  from types import SimpleNamespace
  result=SimpleNamespace(returncode=0)
 else:
  with (out/f'{name}.log').open('w',encoding='utf8') as log:
   result=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
 if name=='dpi2':
  dpi=json.loads((out/'dpi2-regression/results.json').read_text(encoding='utf8'))
  assert set(modules)<={r['module'] for r in dpi} and all(r['exit_code']==0 and not r['skipped'] for r in dpi)
 jobs.append(dict(job=name,exit_code=result.returncode))
 (out/'postchecks.json').write_text(json.dumps(jobs,indent=2),encoding='utf8')
 assert result.returncode==0,name
 print(name,'DONE',flush=True)
print('ALL FINAL CHECKS PASSED',flush=True)
