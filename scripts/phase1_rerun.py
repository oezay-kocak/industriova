"""Rerun complete failed modules; retain original attempts and exact case counts."""
import json,os,subprocess,sys,time
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase1';DEST=OUT/'final-reruns';DEST.mkdir(exist_ok=True)
if sys.argv[1]=='merge':
    path=OUT/'final-tests/results.json';rows=json.loads(path.read_text());updates={r['module']:r for r in json.loads((DEST/'results.json').read_text())}
    for row in rows:
        if row['module'] in updates:
            assert row['tests']==updates[row['module']]['tests']
            row.update(updates[row['module']])
            row['evidence']='artifacts/phase1/final-reruns/'+Path(row['module']).stem+'.txt'
            row['rerun']=True
    path.write_text(json.dumps(rows,indent=2));print('merged',list(updates));raise SystemExit()
results=[]
for name in sys.argv[1:]:
    stem=Path(name).stem;report=DEST/(stem+'.xml');log=DEST/(stem+'.txt')
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONPATH=str(ROOT/'src'),LOCALAPPDATA=str(OUT/'test-appdata'),APPDATA=str(OUT/'test-appdata'))
    start=time.perf_counter()
    with log.open('w',encoding='utf8') as stream:
        completed=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'tests'/name),'-q','--tb=short','--junitxml='+str(report),'--basetemp='+str(DEST/'tmp'/stem),'-o','cache_dir='+str(DEST/'cache'/stem)],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
    suites=list(ET.parse(report).getroot().iter('testsuite'))
    row=dict(module=name,exit_code=completed.returncode,seconds=round(time.perf_counter()-start,2),summary=log.read_text(encoding='utf8').splitlines()[-1],**{key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')})
    row['passed']=row['tests']-row['failures']-row['errors']-row['skipped'];results.append(row);print(row,flush=True)
    (DEST/'results.json').write_text(json.dumps(results,indent=2))
if any(row['exit_code'] for row in results):raise SystemExit(1)
