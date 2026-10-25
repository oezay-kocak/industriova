"""Await the complete final-source regression, then run serial postchecks."""
from pathlib import Path
import time,json,hashlib,subprocess,sys
root=Path.cwd();out=root/'artifacts/phase9';deadline=time.monotonic()+1200
while True:
 p=out/'final-regression/results.json';rows=json.loads(p.read_text(encoding='utf8')) if p.exists() else []
 if len(rows)==95:break
 assert time.monotonic()<deadline,'Final regression did not finish within 20 minutes.'
 time.sleep(2)
assert all(r['exit_code']==0 and r['skipped']==0 for r in rows)
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
with (out/'postchecks.log').open('w',encoding='utf8') as log:
 result=subprocess.run([sys.executable,'-u','scripts/phase9_postchecks.py'],stdout=log,stderr=subprocess.STDOUT,cwd=root)
assert result.returncode==0,'See postchecks.log and per-job logs'
print('FINAL',sum(r['tests'] for r in rows),'/',len(rows),'REGRESSION AND ALL POSTCHECKS PASSED',flush=True)
