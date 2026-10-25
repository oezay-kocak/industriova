"""Serial final regression and comparable P1 measurement/capture pipeline."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase1'
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',PYTHONHASHSEED='0',LOCALAPPDATA=str(OUT/'test-appdata'),APPDATA=str(OUT/'test-appdata'))
def run(name,*args,extra=None):
    print('START',name,flush=True)
    with (OUT/(name+'.log')).open('w',encoding='utf8') as stream:
        subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env| (extra or {}),stdout=stream,stderr=subprocess.STDOUT,check=True)
    print('DONE',name,flush=True)
test_output=OUT/(sys.argv[sys.argv.index('--test-output')+1] if '--test-output' in sys.argv else 'final-tests')
if '--resume' not in sys.argv:
    run(test_output.name,'scripts/run_release_tests.py',ROOT,test_output,'--timeout',600,'--workers',1)
tests=json.loads((test_output/'results.json').read_text())
baseline=json.loads((ROOT/'artifacts/phase0/regression/results.json').read_text())
by_name={row['module']:row for row in tests}
assert all(row['exit_code']==0 and row.get('skipped')==0 for row in tests), 'Regression failed; measurements not started'
assert all(by_name[row['module']]['tests']==row['tests'] for row in baseline), 'Original case counts changed'
summary=dict(modules=len(tests),tests=sum(r['tests'] for r in tests),failures=0,skipped=0,module_seconds=sum(r['seconds'] for r in tests))
(OUT/'final-test-summary.json').write_text(json.dumps(summary,indent=2))
print('TESTS',json.dumps(summary),flush=True)
before=OUT/'before-tree'
if '--after-only' not in sys.argv:
    for kind,repeats in (('active',1),('extended',1),('rapid',7)):
        run('measure-before-'+kind,'scripts/phase1_measure.py','before',kind,'--source',before,'--repeat',repeats)
for kind,repeats in (('ui',7),('actions',1),('rapid',7),('active',1),('extended',1)):
    run('measure-after-'+kind,'scripts/phase1_measure.py','after',kind,'--repeat',repeats)
for scale in ('1','2'):
    run('capture-after-dpi'+scale,'scripts/phase1_capture.py','after',extra={'QT_SCALE_FACTOR':scale})
run('comparison','scripts/phase1_compare.py')
run('visual-comparison','scripts/phase1_visual_compare.py')
run('protected-verification-final','scripts/phase1_verify_protected.py')
print('COMPLETE',flush=True)
