"""Final full-suite proof after the visually detected popup correction."""
import os,sys,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
assert json.loads((OUT/'visual-verification.json').read_text(encoding='utf8'))['captures']==114
for name in ('first-full-tests','final-tests','final-test-summary.json','tested-source-sha256.json',
             'tested-source-at-suite-launch-sha256.json','test-source-reconciliation.json',
             'full-suite.log','finalize-tests.log','dpi2-tests.xml','dpi2-tests.log',
             'protected-verification.json','implementation.diff','legacy-test-captures',
             'legacy-capture-preservation.json','recipe-retirement-captures'):
    source=OUT/name;target=OUT/('before-popup-fix-'+name)
    if source.exists():
        assert source.resolve().is_relative_to(OUT.resolve()) and target.resolve().is_relative_to(OUT.resolve())
        assert not target.exists(),target
        source.rename(target)
source=OUT/'after/freight-ui';target=OUT/'after/freight-ui-before-popup-fix'
assert source.resolve().is_relative_to(OUT.resolve()) and target.resolve().is_relative_to(OUT.resolve())
assert not target.exists();source.rename(target)
frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests') for p in (ROOT/folder).rglob('*')
        if p.is_file() and '__pycache__' not in str(p)}
(OUT/'tested-source-sha256.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
def run(name,args,**extra):
    env=dict(os.environ,LOCALAPPDATA=str(OUT/'final-validation-appdata'),APPDATA=str(OUT/'final-validation-appdata'),PYTHONHASHSEED='0',QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1')
    env.update(extra)
    with (OUT/(name+'.log')).open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(name,'exit',result.returncode,flush=True)
    assert result.returncode==0,name
run('full-suite',['scripts/phase5_run_tests.py','.', 'artifacts/phase5/first-full-tests','--workers','2','--timeout','600'])
run('finalize-tests',['scripts/phase5_finalize_tests.py'])
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in frozen.items())
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
