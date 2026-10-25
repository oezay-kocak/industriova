"""Final full source after ULP-safe display: complete regression, DPI and timings."""
from pathlib import Path
import subprocess,sys,os,time,json,shutil
root=Path.cwd();out=root/'artifacts/phase10';deadline=time.monotonic()+1800
modules=['test_phase3_inventory_ui.py','test_phase4_drag_ui.py','test_phase5_freight_ui.py',
 'test_phase6_freight_statistics_ui.py','test_phase7_economy_ui.py','test_ui_polish_interactions.py',
 'test_unified_production_ux.py','test_factory_ui.py']
command=[sys.executable,'-u','scripts/phase8_run_tests.py','.',str(out/'final-cent-dpi2-rest'),'--workers','2','--timeout','600']+sum((['--module',name] for name in modules),[])
with (out/'final-cent-dpi2-rest.log').open('w',encoding='utf8') as log:
 r=subprocess.run(command,env=dict(os.environ,QT_SCALE_FACTOR='2'),stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0
def wait_rows(folder,count):
 while True:
  p=out/folder/'results.json';rows=json.loads(p.read_text(encoding='utf8')) if p.exists() else []
  if len(rows)==count:break
  assert time.monotonic()<deadline
  time.sleep(2)
 assert all(r['exit_code']==0 and r['skipped']==0 for r in rows),[(r['module'],r['exit_code']) for r in rows if r['exit_code']]
 return rows
full=wait_rows('final-cent-regression',97)
first=wait_rows('final-cent-dpi2',3);rest=wait_rows('final-cent-dpi2-rest',8)
for target,sources,rows in (('final-regression',['final-cent-regression'],full),('dpi2-regression',['final-cent-dpi2','final-cent-dpi2-rest'],first+rest)):
 retained=out/'before-cent-safety'/target;retained.mkdir(parents=True,exist_ok=True)
 for p in (out/target).iterdir():
  if p.suffix in ('.xml','.txt') or p.name=='results.json':shutil.copy2(p,retained/p.name)
 for source in sources:
  for p in (out/source).iterdir():
   if p.suffix in ('.xml','.txt'):shutil.copy2(p,out/target/p.name)
 (out/target/'results.json').write_text(json.dumps(sorted(rows,key=lambda r:r['module']),indent=2),encoding='utf8')
(out/'accepted-validation.json').write_text(json.dumps(dict(full_regression_source='final-cent-regression',modules=97,tests=sum(r['tests'] for r in full),dpi2_sources=['final-cent-dpi2','final-cent-dpi2-rest'],dpi2_modules=11,dpi2_tests=sum(r['tests'] for r in first+rest),scope='Complete fresh final regression after the last productive formatter correction. All DPI modules also re-run on this exact final source; earlier failures/logs retained separately.'),indent=2),encoding='utf8')
assert subprocess.run([sys.executable,'-u','scripts/phase10_final_validation.py','--resume']).returncode==0
for stage in ('before','after'):
 cmd=[sys.executable,'-u','scripts/phase10_inventory_benchmark.py','--stage',stage]
 if stage=='before':cmd+=['--source',str(out/'before-tree')]
 with (out/f'inventory-matched-{stage}.log').open('w',encoding='utf8') as log:
  assert subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode==0
for script in ('phase10_preserve_legacy_outputs.py','phase10_verify.py','phase10_evidence.py'):
 with (out/(Path(script).stem+'.log')).open('w',encoding='utf8') as log:
  assert subprocess.run([sys.executable,'-u','scripts/'+script],stdout=log,stderr=subprocess.STDOUT).returncode==0
print('EXACT FINAL SOURCE, ALL REGRESSIONS, DPI AND MATCHED TIMINGS GREEN',flush=True)
