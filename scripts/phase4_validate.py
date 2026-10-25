"""Serial P4 checks after the full suite; all outputs isolated from old evidence."""
import os,sys,json,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase4'
parser=argparse.ArgumentParser();parser.add_argument('--resume-after-tests',action='store_true');args=parser.parse_args()
def run(name,argv,**environment):
    env=dict(os.environ,LOCALAPPDATA=str(OUT/'validation-appdata'),APPDATA=str(OUT/'validation-appdata'),PYTHONHASHSEED='0',**environment)
    with (OUT/(name+'.log')).open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,*argv],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(name,'exit',result.returncode,flush=True)
    if result.returncode:raise SystemExit(result.returncode)
if not args.resume_after_tests:
    run('intent-recheck',['scripts/phase4_intent_recheck.py'])
    run('artifact-recheck',['scripts/phase4_artifact_recheck.py'])
    run('finalize-tests',['scripts/phase4_finalize_tests.py','--reruns','artifacts/phase4/final-rechecks','--reruns','artifacts/phase4/intent-rechecks','--reruns','artifacts/phase4/artifact-recheck'])
else:
    assert (OUT/'final-test-summary.json').is_file()
run('dpi2-tests',['-m','pytest','tests/test_phase4_drag_ui.py','tests/test_phase4_slot_permutations.py','-q','--tb=short',
    '--junitxml=artifacts/phase4/dpi2-tests.xml','-o','cache_dir=artifacts/phase4/cache-dpi2','--basetemp=artifacts/phase4/tmp-dpi2'],QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='2')
for stage in ('before','after'):
    source=['--source','artifacts/phase4/before-tree'] if stage=='before' else []
    for kind,repeat in (('ui',7),('rapid',7),('active',1),('extended',1)):
        run(stage+'-'+kind,['scripts/phase4_measure.py',stage,kind,'--repeat',str(repeat),*source])
    run(stage+'-inventory',['scripts/phase4_inventory_benchmark.py',stage,*source])
    run(stage+'-drag',['scripts/phase4_drag_benchmark.py',stage,*source])
run('migration-after',['scripts/phase2_migration_audit.py','--out','artifacts/phase4/migration-after.json'])
before=json.loads((OUT/'migration-before.json').read_text(encoding='utf8'));after=json.loads((OUT/'migration-after.json').read_text(encoding='utf8'))
assert before['passed']==after['passed']==16 and before['results']==after['results']
(OUT/'migration-comparison.json').write_text(json.dumps(dict(passed=16,failed=0,identical_payloads=True),indent=2),encoding='utf8')
run('compare',['scripts/phase4_compare.py'])
for scale in ('1','2'):
    run('capture-dpi'+scale,['scripts/phase4_capture.py'],QT_SCALE_FACTOR=scale)
run('preserve-legacy',['scripts/phase4_preserve_legacy_outputs.py'])
run('protected',['scripts/phase4_verify_protected.py'])
print('P4 SERIAL VALIDATION COMPLETE',flush=True)
