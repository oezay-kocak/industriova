"""Serial P5 proof pipeline; retain every failed run, never overwrite older phases."""
import os, sys, json, subprocess, argparse, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
parser=argparse.ArgumentParser();parser.add_argument('--after-tests',action='store_true');args=parser.parse_args()
def run(name,argv,**environment):
    env=dict(os.environ,LOCALAPPDATA=str(OUT/'validation-appdata'),APPDATA=str(OUT/'validation-appdata'),PYTHONHASHSEED='0',**environment)
    with (OUT/(name+'.log')).open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,*argv],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(name,'exit',result.returncode,flush=True)
    if result.returncode:raise SystemExit(result.returncode)
if not args.after_tests:
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    (OUT/'tested-source-sha256.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
    run('full-suite',['scripts/run_release_tests.py','.', 'artifacts/phase5/first-full-tests','--workers','1','--timeout','600'])
    run('finalize-tests',['scripts/phase5_finalize_tests.py'])
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in frozen.items())
run('dpi2-tests',['-m','pytest','tests/test_phase5_freight_core.py','tests/test_phase5_freight_ui.py',
    'tests/test_phase4_drag_ui.py','tests/test_phase4_slot_permutations.py','-q','--tb=short',
    '--junitxml=artifacts/phase5/dpi2-tests.xml','-o','cache_dir=artifacts/phase5/cache-dpi2',
    '--basetemp=artifacts/phase5/tmp-dpi2'],QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='2')
for stage in ('before','after'):
    source=['--source','artifacts/phase5/before-tree'] if stage=='before' else []
    run('migration-'+stage,['scripts/phase2_migration_audit.py','--out',f'artifacts/phase5/migration-{stage}.json',*source])
    for kind,repeat in (('ui',7),('rapid',7),('active',1),('extended',1)):
        run(stage+'-'+kind,['scripts/phase5_measure.py',stage,kind,'--repeat',str(repeat),*source])
    run(stage+'-inventory',['scripts/phase5_inventory_benchmark.py',stage,*source])
    run(stage+'-drag',['scripts/phase5_drag_benchmark.py',stage,*source])
before=json.loads((OUT/'migration-before.json').read_text(encoding='utf8'));after=json.loads((OUT/'migration-after.json').read_text(encoding='utf8'))
assert before['passed']==after['passed']==16 and before['results']==after['results']
(OUT/'migration-comparison.json').write_text(json.dumps(dict(passed=16,failed=0,identical_payloads=True),indent=2),encoding='utf8')
run('freight-ui-benchmark',['scripts/phase5_freight_benchmark.py'])
run('compare',['scripts/phase5_compare.py'])
for scale in ('1','2'):
    run('final-capture-dpi'+scale,['scripts/phase5_capture.py'],QT_SCALE_FACTOR=scale)
run('visual-dimensions',['scripts/phase5_verify_visual.py'])
run('preserve-legacy',['scripts/phase5_preserve_legacy_outputs.py'])
run('protected',['scripts/phase5_verify_protected.py'])
print('P5 SERIAL VALIDATION COMPLETE',flush=True)
