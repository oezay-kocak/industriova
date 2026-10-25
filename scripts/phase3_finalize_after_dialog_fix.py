"""Fresh final-source measurements/captures, then one complete protection check."""
import difflib,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase3'
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(OUT/'validation-appdata'),APPDATA=str(OUT/'validation-appdata'))
def run(script,*args,env=None):
 print('START',script,*args,flush=True)
 subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],cwd=ROOT,env=env,check=True)
def preserve(source_name,destination_name):
 source=(OUT/source_name).resolve();destination=(OUT/destination_name).resolve()
 assert source.is_relative_to(ROOT) and destination.is_relative_to(ROOT) and not destination.exists()
 source.rename(destination)
assert 'high_dpi_dialog_recheck' in json.loads((OUT/'final-tests/provenance.json').read_text(encoding='utf8'))
preserve('after','after-before-dpi-fix')
preserve('screenshots','screenshots-before-dpi-fix')
preserve('comparison.json','comparison-before-dpi-fix.json')
preserve('comparison-tables.md','comparison-tables-before-dpi-fix.md')
for kind,repetitions in (('ui',7),('rapid',7),('active',1),('extended',1)):
 run('phase3_measure.py','after',kind,'--repeat',repetitions)
run('phase3_inventory_benchmark.py','after')
for dpi in (1,2):run('phase3_capture.py',env=dict(os.environ,QT_SCALE_FACTOR=str(dpi)))
run('phase3_compare.py')
run('phase3_preserve_legacy_outputs.py')
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'))
bad=[]
for e in manifest['entries']:
 path=ROOT/e['path']
 if path.parent==ROOT/'artifacts' and path.suffix=='.png' and hashlib.sha256(path.read_bytes()).hexdigest()!=e['sha256']:bad.append(e['path'])
assert not bad,bad
run('phase3_verify_protected.py')
run('phase3_finish_report.py')
protected=json.loads((OUT/'protected-verification.json').read_text(encoding='utf8'))
report_name='docs/industriova-03-phase3-inventory-ui-report.md'
if report_name not in protected['new_files']:
 protected['new_files'].append(report_name)
 with (OUT/'implementation.diff').open('a',encoding='utf8') as diff:
  diff.writelines(difflib.unified_diff([],(ROOT/report_name).read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/'+report_name))
 (OUT/'protected-verification.json').write_text(json.dumps(protected,indent=2),encoding='utf8')
names=sorted(set(protected['changed_existing_source']+protected['new_files']))
delivery=[dict(path=name,sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()) for name in names]
(OUT/'deliverables-manifest.json').write_text(json.dumps(dict(files=delivery,evidence='artifacts/phase3',no_build=True),indent=2),encoding='utf8')
print('P3 FINAL VALIDATION COMPLETE',flush=True)
