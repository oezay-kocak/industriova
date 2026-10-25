"""Finish serial verification once the already running module suite ends."""
import json,time,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase4'
while True:
    rows=json.loads((OUT/'first-full-tests/results.json').read_text(encoding='utf8'))
    if len(rows)==85:break
    time.sleep(2)
assert all(row['exit_code']==0 for row in rows)
for name in ('phase4_recheck.py','phase4_validate.py','phase4_finish_report.py'):
    print('START',name,flush=True)
    result=subprocess.run([sys.executable,'-u',str(ROOT/'scripts'/name)],cwd=ROOT)
    if result.returncode:raise SystemExit(result.returncode)
print('P4 CHECKS AND REPORT COMPLETE',flush=True)
