"""Keep the unchanged recipe regression assertions, redirect only its PNG output."""
import os,sys,json,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/phase4/artifact-recheck';out.mkdir(exist_ok=True)
name='test_recipe_retirement';start=time.perf_counter()
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
with (out/(name+'.txt')).open('w',encoding='utf8') as log:
    result=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'tests'/(name+'.py')),'-q','--tb=short',
        f'--junitxml={out/(name+".xml")}','-o',f'cache_dir={out/"cache"}',f'--basetemp={out/"tmp"}'],
        cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
counts={k:0 for k in ('tests','failures','errors','skipped')}
for suite in ET.parse(out/(name+'.xml')).getroot().iter('testsuite'):
    for k in counts:counts[k]+=int(suite.get(k,0))
row=dict(module=name+'.py',exit_code=result.returncode,seconds=round(time.perf_counter()-start,2),**counts)
row['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
(out/'results.json').write_text(json.dumps([row],indent=2),encoding='utf8');print(json.dumps(row),flush=True)
raise SystemExit(result.returncode)
