"""Retain the preparatory suite, then run the frozen P5 proof once serially."""
import os,sys,time,json,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
deadline=time.monotonic()+1800
while time.monotonic()<deadline:
    path=OUT/'first-full-tests/results.json'
    records=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    if len(records)==87 and (OUT/'finalize-tests.log').exists():break
    time.sleep(10)
else:raise SystemExit('Preparatory suite has not completed; outputs preserved.')
time.sleep(2)
preserve=subprocess.run([sys.executable,'scripts/phase5_preserve_legacy_outputs.py'],cwd=ROOT)
assert preserve.returncode==0
for name in ('first-full-tests','final-tests','tested-source-sha256.json','full-suite.log','finalize-tests.log','screenshots',
             'legacy-test-captures','legacy-capture-preservation.json','recipe-retirement-captures'):
    path=OUT/name
    if path.exists():
        target=OUT/('before-board-reuse-'+name)
        assert not target.exists(),target
        shutil.move(str(path),str(target))
env=dict(os.environ,QT_SCALE_FACTOR='1',LOCALAPPDATA=str(OUT/'validation-appdata'),APPDATA=str(OUT/'validation-appdata'))
result=subprocess.run([sys.executable,'-u','scripts/phase5_validate.py'],cwd=ROOT,env=env)
print('Frozen P5 validation exit',result.returncode,flush=True)
raise SystemExit(result.returncode)
