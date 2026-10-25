"""Complete affected gesture modules after adding cancelled-intent protection."""
import os,sys,json,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/phase4/intent-rechecks';out.mkdir(exist_ok=True);(out/'tmp').mkdir(exist_ok=True)
rows=[];env=dict(os.environ,QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
for name in ('test_phase4_drag_ui','test_industriova_release_ui','test_phase1_performance','test_ui_interaction_recovery'):
    start=time.perf_counter()
    with (out/(name+'.txt')).open('w',encoding='utf8') as log:
        run=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'tests'/(name+'.py')),'-q','--tb=short',
            f'--junitxml={out/(name+".xml")}','-o',f'cache_dir={out/"cache"/name}',f'--basetemp={out/"tmp"/name}'],
            env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    totals={k:0 for k in ('tests','failures','errors','skipped')}
    for suite in ET.parse(out/(name+'.xml')).getroot().iter('testsuite'):
        for k in totals:totals[k]+=int(suite.get(k,0))
    row=dict(module=name+'.py',exit_code=run.returncode,seconds=round(time.perf_counter()-start,2),**totals)
    row['passed']=totals['tests']-totals['failures']-totals['errors']-totals['skipped'];rows.append(row)
    (out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(row),flush=True)
    if run.returncode:raise SystemExit(run.returncode)
