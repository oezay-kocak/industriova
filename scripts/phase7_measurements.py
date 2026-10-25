"""Serial P7 performance controls, after completed tests and captures."""
import json,os,subprocess,sys,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7'
expected=json.loads((OUT/'tested-source-sha256.json').read_text(encoding='utf8'))
def frozen():
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in expected.items())
frozen();env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',PYTHONHASHSEED='0')
records=[]
for stage,source in [('before',OUT/'before-tree'),('after',ROOT)]:
    jobs=[('purchases',['scripts/phase7_purchase_benchmark.py',stage,'--source',str(source)])]
    jobs += [(kind,['scripts/phase7_measure.py',stage,kind,'--source',str(source)]) for kind in ('active','extended','rapid')]
    for name,args in jobs:
        with (OUT/f'performance-{stage}-{name}.log').open('w',encoding='utf8') as f:
            result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        records.append(dict(stage=stage,kind=name,exit_code=result.returncode))
        print(json.dumps(records[-1]),flush=True)
        assert result.returncode==0,(stage,name)
frozen();(OUT/'performance-complete.json').write_text(json.dumps(dict(ok=True,jobs=records,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),method='Serial before-tree/current controls without concurrent tests, captures or hashing jobs. Active/extended seven samples per action; rapid twenty sequential purchase callbacks per firm. No human modal wait.'),indent=2),encoding='utf8')
