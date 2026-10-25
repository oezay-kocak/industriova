"""Retain the full original run and rerun complete failed modules after fixes."""
import json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase3';FIRST=OUT/'first-full-tests';FINAL=OUT/'final-tests';RETRY=OUT/'reruns'
results=json.loads((FIRST/'results.json').read_text(encoding='utf8'));assert len(results)==len(list((ROOT/'tests').glob('test_*.py')))
FINAL.mkdir(exist_ok=False);RETRY.mkdir(exist_ok=True)
forced={'test_factory_ui.py','test_card_rendering_audit.py'}
initial_failed=[r['module'] for r in results if r['exit_code']]
provenance={r['module']:str(FIRST) for r in results}
for i,r in enumerate(results):
 if not r['exit_code'] and r['module'] not in forced:continue
 path=ROOT/'tests'/r['module'];stem=path.stem
 env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'rerun-appdata'),APPDATA=str(OUT/'rerun-appdata'))
 command=[sys.executable,'-m','pytest',str(path),'-q','--tb=short',f'--junitxml={RETRY/(stem+".xml")}',f'--basetemp={RETRY/"tmp"/stem}','-o',f'cache_dir={RETRY/"cache"/stem}']
 start=time.perf_counter();run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=600)
 (RETRY/(stem+'.txt')).write_text(run.stdout+run.stderr,encoding='utf8')
 counts={k:0 for k in ('tests','failures','errors','skipped')}
 for suite in ET.parse(RETRY/(stem+'.xml')).getroot().iter('testsuite'):
  for k in counts:counts[k]+=int(suite.get(k,0))
 assert counts['tests']==r['tests'];counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
 results[i]=dict(module=r['module'],exit_code=run.returncode,seconds=round(time.perf_counter()-start,2),summary=run.stdout.strip().splitlines()[-1],**counts)
 provenance[r['module']]=str(RETRY);print(json.dumps(results[i]),flush=True)
for r in results:
 for suffix in ('.txt','.xml'):
  shutil.copyfile(Path(provenance[r['module']])/(Path(r['module']).stem+suffix),FINAL/(Path(r['module']).stem+suffix))
(FINAL/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');(FINAL/'provenance.json').write_text(json.dumps(dict(initial_failed=initial_failed,forced_after_dialog_cleanup=sorted(forced),module_sources=provenance),indent=2),encoding='utf8')
assert all(r['exit_code']==0 and r['failures']==r['errors']==r['skipped']==0 for r in results)
print(json.dumps(dict(modules=len(results),tests=sum(r['tests'] for r in results),rerun_modules=initial_failed,ok=True)),flush=True)
