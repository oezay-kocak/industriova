"""Run the source or packaged application twice in isolated test storage."""
from pathlib import Path
import os,sys,subprocess,json,tempfile
ROOT=Path(__file__).resolve().parents[1]
packaged='--exe' in sys.argv
out=Path(tempfile.mkdtemp(prefix='exe-smoke-' if packaged else 'source-smoke-',dir=ROOT/'artifacts/phase11fg'))
if packaged:
    command=[str(ROOT/'dist/economy-rebalance-test/Industriova_0.3_Economy_Rebalance_Test/Industriova_0.3_Economy_Rebalance_Test.exe')]
else:
    command=[sys.executable,'-B','-c',"import runpy;runpy.run_path('scripts/economy_test_smoke_hook.py');from production_zero.app.__main__ import main;raise SystemExit(main())"]
results=[]
for number in (1,2):
    env=dict(os.environ,LOCALAPPDATA=str(out/'appdata'),QT_QPA_PLATFORM='offscreen',INDUSTRIOVA_ECONOMY_SMOKE_ROOT=str(out),INDUSTRIOVA_ECONOMY_SMOKE_PASS=str(number),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
    (out/f'stdout-{number}.txt').write_text(result.stdout,encoding='utf-8');(out/f'stderr-{number}.txt').write_text(result.stderr,encoding='utf-8')
    assert result.returncode==0,(number,result.returncode,result.stderr,(out/f'error-{number}.txt').read_text() if (out/f'error-{number}.txt').exists() else '')
    report=json.loads((out/f'pass-{number}.json').read_text());assert report['frozen']==packaged
    results.append(report);print('PASS',number,'packaged',packaged,flush=True)
(out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
(ROOT/'artifacts/phase11fg'/('exe-smoke.json' if packaged else 'source-smoke.json')).write_text(json.dumps(dict(folder=str(out),results=results),indent=2),encoding='utf-8')
