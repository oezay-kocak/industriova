"""Serial final captures in all requested size/DPI configurations."""
from pathlib import Path
import os,sys,subprocess,json
out=Path('artifacts/phase10');rows=[]
for stage,scale in (('before',2),('after',1),('after',2)):
 command=[sys.executable,'-u','scripts/phase10_capture.py','--stage',stage]
 if stage=='before':command+=['--source',str(out/'before-tree')]
 with (out/f'capture-{stage}-dpi{scale}.log').open('w',encoding='utf8') as log:
  r=subprocess.run(command,env=dict(os.environ,QT_SCALE_FACTOR=str(scale)),stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(stage=stage,scale=scale,exit_code=r.returncode))
 (out/'capture-queue.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 assert r.returncode==0
 print(stage,scale,'DONE',flush=True)
