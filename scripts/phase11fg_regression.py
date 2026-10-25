"""Run the full suite in isolated per-module Qt processes, retaining all logs."""
from pathlib import Path
import subprocess,os,json,sys,re
root=Path(__file__).resolve().parents[1];out=root/'artifacts/phase11fg/regression';out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1',LOCALAPPDATA=str(out/'isolated-appdata'))
results=[]
previous=json.loads((out/'results.json').read_text()) if (out/'results.json').exists() else []
only_failed='--failed' in sys.argv
paths=sorted((root/'tests').glob('test_*.py'))
if only_failed:paths=[p for p in paths if any(Path(r['module']).name==p.name and r['exit_code']!=0 for r in previous)]
for p in paths:
    cmd=[sys.executable,'-B','-m','pytest',str(p),'-q','-p','no:cacheprovider','--basetemp='+str(out/(p.stem+'-temp'))]
    result=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
    output=result.stdout+result.stderr;(out/(p.stem+'.log')).write_text(output,encoding='utf8')
    row=dict(module=str(p.relative_to(root)),exit_code=result.returncode,passed=sum(int(x) for x in re.findall(r'(\d+) passed',output)),failed=sum(int(x) for x in re.findall(r'(\d+) failed',output)),tail=output[-1200:])
    results.append(row)
    print(p.stem,result.returncode,row['passed'],row['failed'],flush=True)
    (out/('rerun.json' if only_failed else 'results.json')).write_text(json.dumps(results,indent=2),encoding='utf8')
assert all(r['exit_code']==0 for r in results)
print('ALL',len(results),'MODULES',sum(r['passed'] for r in results),'PASSED',flush=True)
