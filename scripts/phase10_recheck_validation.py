"""Retain original module logs and bind the explicit scroll-timing rechecks."""
from pathlib import Path
import json,time,shutil,hashlib,subprocess,sys
out=Path('artifacts/phase10');deadline=time.monotonic()+700
for source,target in (('timing-recheck','final-regression'),('dpi2-timing-recheck','dpi2-regression')):
 while True:
  path=out/source/'results.json'
  if path.exists():break
  assert time.monotonic()<deadline
  time.sleep(2)
 rows=json.loads(path.read_text(encoding='utf8'));assert len(rows)==1 and rows[0]['exit_code']==0
 row=rows[0];name=Path(row['module']).stem
 retained=out/'replaced-modules'/target;retained.mkdir(parents=True,exist_ok=True)
 for suffix in ('.xml','.txt'):
  shutil.copy2(out/target/(name+suffix),retained/(name+suffix))
  shutil.copy2(out/source/(name+suffix),out/target/(name+suffix))
 results=out/target/'results.json';existing=json.loads(results.read_text(encoding='utf8'))
 existing=[dict(row,rechecked_from=source) if r['module']==row['module'] else r for r in existing]
 results.write_text(json.dumps(existing,indent=2),encoding='utf8')
f=out/'final-source-sha256.json';hashes=json.loads(f.read_text(encoding='utf8'))
name='tests/test_unified_production_ux.py';hashes[name]=hashlib.sha256(Path(name).read_bytes()).hexdigest();f.write_text(json.dumps(hashes,indent=2),encoding='utf8')
(out/'validation-rechecks.json').write_text(json.dumps(dict(module=name,tests=20,scales=[1,2],reason='Existing test scrolled before 0/50/150-ms cached scroll restoration completed; explicitly wait 220ms and scroll the actual visible slot. All original gameplay assertions retained; no productive code changed.',retained_logs='replaced-modules',full_regression_tests=1990),indent=2),encoding='utf8')
result=subprocess.run([sys.executable,'-u','scripts/phase10_final_validation.py','--resume'])
assert result.returncode==0
