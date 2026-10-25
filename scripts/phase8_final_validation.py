"""Serial final evidence queue; never loads personal saves or builds binaries."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/phase8'
def hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests') for p in sorted((ROOT/folder).rglob('*.py'))
            if '__pycache__' not in p.parts}
resume='--resume' in sys.argv
frozen=hashes()
if resume:
    assert frozen==json.loads((OUT/'final-source-sha256.json').read_text(encoding='utf8'))
else:
    (OUT/'final-source-sha256.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
jobs=[
    ('final-regression',['scripts/phase8_run_tests.py','.','artifacts/phase8/final-regression','--timeout','600','--workers','2'],{}),
    ('before-matched',['scripts/phase8_contract_simulation.py','--source','artifacts/phase8/before-tree','--stage','before-matched'],{}),
    ('after-matched',['scripts/phase8_contract_simulation.py','--stage','after-matched'],{}),
    ('consortium-before-matched',['scripts/phase8_consortium_simulation.py','--source','artifacts/phase8/before-tree','--stage','consortium-before-matched'],{}),
    ('consortium-after-matched',['scripts/phase8_consortium_simulation.py','--stage','consortium-after-matched'],{}),
    ('migration-final',['scripts/phase8_migration_audit.py','--stage','after'],{}),
    ('capture-final-dpi1',['scripts/phase8_capture.py'],{'QT_SCALE_FACTOR':'1'}),
    ('capture-final-dpi2',['scripts/phase8_capture.py'],{'QT_SCALE_FACTOR':'2'}),
    ('dpi2-regression',['scripts/phase8_run_tests.py','.','artifacts/phase8/dpi2-regression','--timeout','600','--workers','2',
        '--module','test_phase8_contract_ui.py','--module','test_phase8_contract_balance.py',
        '--module','test_phase4_drag_ui.py','--module','test_phase5_freight_ui.py',
        '--module','test_phase6_freight_statistics.py','--module','test_phase6_freight_statistics_ui.py',
        '--module','test_phase7_economy.py','--module','test_phase7_economy_ui.py'],{'QT_SCALE_FACTOR':'2'}),
    ('performance-before-matched',['scripts/phase8_benchmark.py','--source','artifacts/phase8/before-tree','--stage','before-matched'],{}),
    ('performance-after-matched',['scripts/phase8_benchmark.py','--stage','after-matched'],{}),
]
records=json.loads((OUT/'final-validation-queue.json').read_text(encoding='utf8')) if resume else []
for name,args,extra in jobs:
    if any(r['name']==name and r['exit_code']==0 for r in records):continue
    assert hashes()==frozen,'Source/tests changed during final validation'
    start=time.time()
    print('START',name,flush=True)
    with (OUT/f'{name}.log').open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,'-u',*args],cwd=ROOT,env=dict(os.environ,**extra),stdout=log,stderr=subprocess.STDOUT)
    row=dict(name=name,exit_code=result.returncode,seconds=time.time()-start)
    records.append(row)
    (OUT/'final-validation-queue.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    print('END',json.dumps(row),flush=True)
    assert result.returncode==0,row
    if name in ('final-regression','dpi2-regression'):
        testrows=json.loads((OUT/name/'results.json').read_text(encoding='utf8'))
        assert all(r['exit_code']==0 and r.get('skipped',0)==0 for r in testrows),name
assert hashes()==frozen
print('FINAL QUEUE COMPLETE',flush=True)
