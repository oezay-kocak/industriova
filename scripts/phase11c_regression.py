"""Isolated Qt regression, every test module, no skips or selection filters."""
from pathlib import Path
import subprocess,os,json,sys,re
out=Path('artifacts/phase11c/regression');out.mkdir(exist_ok=True)
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1')
results=[]
for p in sorted(Path('tests').glob('test_*.py')):
 cmd=[sys.executable,'-B','-m','pytest',str(p),'-q','-p','no:cacheprovider','--basetemp='+str(out/(p.stem+'-temp'))]
 result=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
 text=result.stdout+result.stderr;(out/(p.stem+'.log')).write_text(text,encoding='utf8')
 results.append(dict(module=str(p),exit_code=result.returncode,passed=sum(int(x) for x in re.findall(r'(\d+) passed',text)),tail=text[-800:]))
 print(p.stem,result.returncode,results[-1]['passed'],flush=True)
 (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
assert all(r['exit_code']==0 for r in results)
print('ALL',len(results),'MODULES',sum(r['passed'] for r in results),'PASSED',flush=True)
