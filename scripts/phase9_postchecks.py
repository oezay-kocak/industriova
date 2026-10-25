"""Run final DPI, economic and matched performance jobs sequentially."""
from pathlib import Path
import os,sys,json,subprocess,hashlib
root=Path.cwd();out=root/'artifacts/phase9'
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
reg=json.loads((out/'final-regression/results.json').read_text(encoding='utf8'))
assert len(reg)==95 and all(r['exit_code']==0 and r['skipped']==0 for r in reg)
modules=['test_phase4_drag_ui.py','test_phase5_freight_ui.py','test_phase6_freight_statistics_ui.py','test_phase7_economy_ui.py','test_phase8_contract_ui.py','test_phase9_freight_only.py','test_phase9_navigation_ui.py','test_consortium_ui.py']
jobs=[('dpi2',["scripts/phase8_run_tests.py",".","artifacts/phase9/dpi2-regression","--workers","2","--timeout","600"]+sum((['--module',m] for m in modules),[]),{'QT_SCALE_FACTOR':'2'}),
 ('consortium-final',['scripts/phase9_consortium_simulation.py','--stage','consortium-final','--source','.'],{}),
 ('contracts-before',['scripts/phase9_contract_benchmark.py','--source','artifacts/phase9/before-tree','--stage','before'],{}),
 ('contracts-after',['scripts/phase9_contract_benchmark.py','--source','.','--stage','after'],{}),
 ('ui-before',['scripts/phase9_ui_benchmark.py','--source','artifacts/phase9/before-tree','--stage','before'],{}),
 ('ui-after',['scripts/phase9_ui_benchmark.py','--source','.','--stage','after'],{}),
 ('migration-final',['scripts/phase9_migration_audit.py'],{})]
records=[]
for name,args,env in jobs:
 with (out/(name+'-final.log')).open('w',encoding='utf8') as log:
  result=subprocess.run([sys.executable,'-u',*args],cwd=root,env=dict(os.environ,QT_SCALE_FACTOR='1',**env) if 'QT_SCALE_FACTOR' not in env else dict(os.environ,**env),stdout=log,stderr=subprocess.STDOUT)
 records.append(dict(job=name,exit_code=result.returncode));(out/'postchecks.json').write_text(json.dumps(records,indent=2),encoding='utf8');print(name,result.returncode,flush=True)
 assert result.returncode==0,name
 if name=='dpi2':
  r=json.loads((out/'dpi2-regression/results.json').read_text(encoding='utf8'));assert len(r)==len(modules) and all(x['exit_code']==0 and x['skipped']==0 for x in r)
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
