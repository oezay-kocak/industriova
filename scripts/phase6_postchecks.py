"""Serial P6 acceptance. Run only after the frozen complete suite passes."""
import os,sys,subprocess,json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase6';BASE=OUT/'before-tree'
def verify_frozen():
    expected=json.loads((OUT/'tested-source-sha256.json').read_text(encoding='utf8'))['sha256']
    actual={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert expected==actual,'Source/tests changed after full-suite freeze'
verify_frozen()
results=json.loads((OUT/'final-tests/results.json').read_text(encoding='utf8'))
# Runner returns a list of complete per-module records.
assert isinstance(results,list)
baseline=json.loads((ROOT/'artifacts/phase5/first-full-tests/results.json').read_text(encoding='utf8'))
old={r['module']:r for r in baseline};new={r['module']:r for r in results}
assert len(old)==87 and sum(r['tests'] for r in old.values())==1595
assert len(new)==89
assert all(new[name]['tests']==row['tests'] for name,row in old.items())
assert all(r['exit_code']==0 and r['passed']==r['tests'] and not any(r[k] for k in ('failures','errors','skipped')) for r in results)
summary=dict(tests=sum(r['tests'] for r in results),passed=sum(r['passed'] for r in results),modules=len(results),retained_baseline_tests=1595,
             added_tests=sum(r['tests'] for name,r in new.items() if name not in old),failures=0,errors=0,skipped=0,workers=2,isolated_appdata_per_module=True,
             summed_module_seconds=sum(r['seconds'] for r in results),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'final-test-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONHASHSEED='0',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(OUT/'post-appdata'),APPDATA=str(OUT/'post-appdata'))
def run(label,args,extra=None):
    child_env=dict(env);child_env.update(extra or {})
    with (OUT/f'{label}.log').open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=child_env,stdout=log,stderr=subprocess.STDOUT)
    print(label,result.returncode,flush=True);assert result.returncode==0,label
run('dpi2-tests',['-m','pytest',*[f'tests/{name}' for name in ('test_phase4_slot_permutations.py','test_phase4_drag_ui.py','test_phase5_freight_core.py','test_phase5_freight_ui.py','test_phase6_freight_statistics.py','test_phase6_freight_statistics_ui.py')],'-q','--tb=short',f'--junitxml={OUT}/dpi2-tests.xml','-o',f'cache_dir={OUT}/dpi2-cache',f'--basetemp={OUT}/dpi2-temp'],{'QT_SCALE_FACTOR':'2'})
run('visual-verification',['scripts/phase6_verify_visual.py'])
run('legacy-reference-preservation',['scripts/phase6_preserve_legacy_outputs.py'])
for stage,source in (('before',BASE),('after',ROOT)):
    run(f'{stage}-freight-final',['scripts/phase6_benchmark.py',stage+'-final','--source',source])
    for kind,repeats in (('ui',7),('rapid',7),('active',1),('extended',1)):
        run(f'{stage}-{kind}-control',['scripts/phase6_measure.py',stage,kind,'--source',source,'--repeat',repeats])
    for script in ('inventory_benchmark','backend_inventory_benchmark','drag_benchmark','freight_ui_benchmark'):
        run(f'{stage}-{script}',['scripts/phase6_'+script+'.py',stage,'--source',source])
run('stress',['scripts/phase6_stress.py'])
run('comparison',['scripts/phase6_compare.py'])
verify_frozen()
(OUT/'postchecks-complete.json').write_text(json.dumps(dict(ok=True,source_tests_frozen=True,method='All performance workloads serial, no concurrent tests or builds. Same pre-change source baseline and fixtures. DPI2 test rerun is additional and not counted twice.',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2),encoding='utf8')
print(json.dumps(summary),flush=True)
