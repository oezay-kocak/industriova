"""Resume only post-suite checks; the complete passing final module proofs stay intact."""
import os,sys,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
summary=json.loads((OUT/'final-test-summary.json').read_text(encoding='utf8'))
assert summary['tests']==summary['passed']==1595 and summary['modules']==87
frozen=json.loads((OUT/'tested-source-sha256.json').read_text(encoding='utf8'))
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in frozen.items())
def run(name,args,**extra):
    env=dict(os.environ,LOCALAPPDATA=str(OUT/'final-validation-appdata'),APPDATA=str(OUT/'final-validation-appdata'),PYTHONHASHSEED='0',QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1')
    env.update(extra)
    with (OUT/(name+'.log')).open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(name,'exit',result.returncode,flush=True);assert result.returncode==0,name
run('dpi2-tests',['-m','pytest','tests/test_phase5_freight_core.py','tests/test_phase5_freight_ui.py',
    'tests/test_phase4_drag_ui.py','tests/test_phase4_slot_permutations.py','-q','--tb=short',
    '--junitxml=artifacts/phase5/dpi2-tests.xml','-o','cache_dir=artifacts/phase5/cache-final-dpi2',
    '--basetemp=artifacts/phase5/tmp-final-dpi2'],QT_SCALE_FACTOR='2')
for stage in ('before','after'):
    source=['--source','artifacts/phase5/before-tree'] if stage=='before' else []
    run('backend-'+stage,['scripts/phase5_backend_inventory_benchmark.py',stage,*source])
run('freight-ui-benchmark-final',['scripts/phase5_freight_benchmark.py'])
run('preserve-legacy-final',['scripts/phase5_preserve_legacy_outputs.py'])
run('protected-final',['scripts/phase5_verify_protected.py'])
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in frozen.items())
(OUT/'final-method.json').write_text(json.dumps(dict(full_suite_workers=2,isolated_appdata_per_module=True,performance_runs_serial=True,
    unaffected_controls='P0/P1/P2/P3/P4 after-control workloads completed before the final local combo-popup colors. Those paths never build the assignment popup. New P5 Freight timings repeated after the color correction; all raw first attempts retained.',
    source_unchanged_through_final_suite_and_checks=True),indent=2),encoding='utf8')
print('P5 FINAL VALIDATION COMPLETE',flush=True)
