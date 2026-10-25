"""Rerun every affected dialog UI module after the high-DPI label fix."""
import json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase3';FINAL=OUT/'final-tests';DEST=OUT/'dialog-final-tests';DEST.mkdir(exist_ok=True)
modules=('test_factory_ui.py','test_industriova_release_ui.py','test_live_playtest_polish.py','test_phase3_inventory_ui.py','test_playtest2_consistency_followup.py','test_post_audit_ui.py','test_recipe_retirement.py','test_research_interaction_polish.py','test_ui_interaction_recovery.py','test_ui_polish_interactions.py')
results=json.loads((FINAL/'results.json').read_text(encoding='utf8'));indexed={r['module']:r for r in results};updates={}
def check(name,folder,scale):
 folder.mkdir(parents=True,exist_ok=True);stem=Path(name).stem
 assert folder.resolve().is_relative_to(ROOT)
 (folder/'tmp').mkdir(parents=True,exist_ok=True)
 report=folder/(stem+'.xml');log=folder/(stem+'.txt')
 if report.exists():
  suites=list(ET.parse(report).getroot().iter('testsuite'));counts={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
  if not any(counts[k] for k in ('failures','errors','skipped')) and name!='test_phase3_inventory_ui.py':
   result=dict(module=name,exit_code=0,seconds=round(sum(float(s.get('time',0)) for s in suites),2),seconds_source='JUnit suite duration; retained successful dialog recheck',summary=log.read_text(encoding='utf8').strip().splitlines()[-1],**counts,passed=counts['tests'])
   print('REUSE COMPLETE MODULE',name,flush=True);return result
  archive=folder/'previous-attempts'/f'{stem}-{len(list((folder/"previous-attempts").glob(stem+"-*")))}';archive.mkdir(parents=True)
  shutil.copyfile(report,archive/report.name);shutil.copyfile(log,archive/log.name)
 env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR=str(scale),LOCALAPPDATA=str(folder/'appdata'),APPDATA=str(folder/'appdata'))
 start=time.perf_counter();run=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'tests'/name),'-q','--tb=short',f'--junitxml={folder/(stem+".xml")}',f'--basetemp={folder/"tmp"/stem}','-o',f'cache_dir={folder/"cache"/stem}'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=600)
 (folder/(stem+'.txt')).write_text(run.stdout+run.stderr,encoding='utf8');counts={k:0 for k in ('tests','failures','errors','skipped')}
 for suite in ET.parse(folder/(stem+'.xml')).getroot().iter('testsuite'):
  for key in counts:counts[key]+=int(suite.get(key,0))
 result=dict(module=name,exit_code=run.returncode,seconds=round(time.perf_counter()-start,2),summary=run.stdout.strip().splitlines()[-1],**counts,passed=counts['tests']-counts['failures']-counts['errors']-counts['skipped'])
 print(json.dumps(result),flush=True)
 assert result['exit_code']==result['failures']==result['errors']==result['skipped']==0
 assert result['tests']==indexed[name]['tests']
 return result
for name in modules:updates[name]=check(name,DEST,1)
check('test_phase3_inventory_ui.py',DEST/'dpi2',2)
provenance=json.loads((FINAL/'provenance.json').read_text(encoding='utf8'));provenance['high_dpi_dialog_recheck']=list(modules)
for name,result in updates.items():
 indexed[name]=result;provenance['module_sources'][name]=str(DEST)
 for suffix in ('.txt','.xml'):shutil.copyfile(DEST/(Path(name).stem+suffix),FINAL/(Path(name).stem+suffix))
(FINAL/'results.json').write_text(json.dumps(sorted(indexed.values(),key=lambda r:r['module']),indent=2),encoding='utf8')
(FINAL/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf8')
print('DIALOG RECHECK COMPLETE',flush=True)
