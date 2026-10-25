"""Sequential A/B measurements with the exact saved source, no test workers."""
import os,sys,json,zipfile,subprocess
from pathlib import Path
root=Path.cwd();out=root/'artifacts/industriova-ui-repair';before=out/'before-source'
with zipfile.ZipFile(root/'artifacts/release-backups/20261018T221255021770Z/working-tree.zip') as z:
    for name in z.namelist():
        if name.startswith('src/'):
            p=before/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
for number,kind in enumerate(('before','after','after','before'),1):
    target=out/f'benchmark-abba-{number}-{kind}.json'
    env=dict(os.environ,PYTHONPATH=str((before if kind=='before' else root)/'src'),PYTHONHASHSEED='0',QT_QPA_PLATFORM='offscreen')
    with (out/f'benchmark-abba-{number}-{kind}.txt').open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,str(root/'scripts/release_benchmark.py'),str(target)],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert result.returncode==0
    print(json.dumps({'run':number,'source':kind,'result':str(target)}),flush=True)
