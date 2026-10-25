"""Rerun whole modules started before the final productive edit, plus failures."""
import os,sys,json,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase4';first=OUT/'first-full-tests'
rows=json.loads((first/'results.json').read_text(encoding='utf8'));assert len(rows)==85
source_files=[ROOT/'src/production_zero'/name for name in ('core/machine_operations.py','core/freight.py','core/commands.py',
    'ui/release_board.py','ui/factory_view.py','ui/factory_view_v2.py','ui/freight_drag.py','ui/freight_view.py','ui/drag_feedback.py')]
freeze=max(p.stat().st_mtime for p in source_files)
rerun=OUT/'final-rechecks';rerun.mkdir(exist_ok=True);(rerun/'tmp').mkdir(exist_ok=True)
env=dict(os.environ,LOCALAPPDATA=str(OUT/'recheck-appdata'),APPDATA=str(OUT/'recheck-appdata'),QT_QPA_PLATFORM='offscreen')
results=[]
for row in rows:
    report=first/(Path(row['module']).stem+'.txt')
    started=report.stat().st_mtime-row['seconds']
    if started>freeze and row['exit_code']==0:continue
    stem=Path(row['module']).stem;start=time.perf_counter()
    command=[sys.executable,'-m','pytest',str(ROOT/'tests'/row['module']),'-q','--tb=short',f'--junitxml={rerun/(stem+".xml")}',
        '-o',f'cache_dir={rerun/"cache"/stem}',f'--basetemp={rerun/"tmp"/stem}']
    with (rerun/(stem+'.txt')).open('w',encoding='utf8') as log:
        run=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    suites=ET.parse(rerun/(stem+'.xml')).getroot().iter('testsuite');counts={key:0 for key in ('tests','failures','errors','skipped')}
    for suite in suites:
        for key in counts:counts[key]+=int(suite.get(key,0))
    entry=dict(module=row['module'],exit_code=run.returncode,seconds=round(time.perf_counter()-start,2),**counts)
    entry['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped'];results.append(entry)
    (rerun/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(entry),flush=True)
    if run.returncode:raise SystemExit(run.returncode)
(rerun/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('Complete module rechecks finished',flush=True)
