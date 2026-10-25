"""Finish reports and delivery only after the exact-final-source queue succeeds."""
from pathlib import Path
import json,time,subprocess,sys,os
out=Path('artifacts/phase10');deadline=time.monotonic()+2400
while True:
 p=out/'cent-final-validation.log'
 if p.exists() and 'EXACT FINAL SOURCE, ALL REGRESSIONS, DPI AND MATCHED TIMINGS GREEN' in p.read_text(encoding='utf8'):break
 assert time.monotonic()<deadline
 time.sleep(2)
accepted=json.loads((out/'accepted-validation.json').read_text(encoding='utf8'))
assert accepted['tests']==1994 and accepted['dpi2_tests']==518
for scale in (1,2):
 with (out/f'click-roundtrip-dpi{scale}.log').open('w',encoding='utf8') as log:
  result=subprocess.run([sys.executable,'-u','scripts/phase10_click_roundtrip.py'],env=dict(os.environ,QT_SCALE_FACTOR=str(scale)),stdout=log,stderr=subprocess.STDOUT,timeout=120)
  assert result.returncode==0
for script in ('phase10_write_report.py','phase10_deliver.py'):
 result=subprocess.run([sys.executable,'-u','scripts/'+script])
 assert result.returncode==0,script
print('P10 COMPLETE; NO BUILD CREATED',flush=True)
