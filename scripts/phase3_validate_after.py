"""Serial final P3 evidence. Preserve prior outputs before repeating this driver."""
import hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase3'
os.environ.update(LOCALAPPDATA=str(OUT/'validation-appdata'),APPDATA=str(OUT/'validation-appdata'),QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1')
def run(script,*args,env=None):
 print('START',script,*args,flush=True)
 subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],cwd=ROOT,env=env,check=True)
run('phase3_finalize_tests.py')
for kind,repetitions in (('ui',7),('rapid',7),('active',1),('extended',1)):
 run('phase3_measure.py','after',kind,'--repeat',repetitions)
run('phase3_inventory_benchmark.py','after')
source=(OUT/'screenshots').resolve();target=(OUT/'screenshots-first-pass').resolve()
assert source.is_relative_to(ROOT) and target.is_relative_to(ROOT)
if source.exists():
 assert not target.exists()
 source.rename(target)
for dpi in (1,2):run('phase3_capture.py',env=dict(os.environ,QT_SCALE_FACTOR=str(dpi)))
run('phase2_migration_audit.py','--out',OUT/'migration-after.json')
before=json.loads((OUT/'migration-before.json').read_text(encoding='utf8'));after=json.loads((OUT/'migration-after.json').read_text(encoding='utf8'))
indexed={(e['source'],e['slot']):e for e in before['results']};comparisons=[]
for e in after['results']:
 b=indexed[(e['source'],e['slot'])]
 comparisons.append(dict(source=e['source'],slot=e['slot'],same_payload=b['payload_sha256']==e['payload_sha256'],before_passed=b['passed'],after_passed=e['passed']))
ok=len(comparisons)==16==len(indexed) and all(e['same_payload'] and e['before_passed'] and e['after_passed'] for e in comparisons)
(OUT/'migration-before-after-comparison.json').write_text(json.dumps(dict(ok=ok,slots=comparisons),indent=2),encoding='utf8');assert ok
run('phase3_compare.py')
run('phase3_preserve_legacy_outputs.py')
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'));entries={e['path']:e for e in manifest['entries']}
with zipfile.ZipFile(backup/'source-baseline.zip') as z:
 for name in z.namelist():assert hashlib.sha256(z.read(name)).hexdigest()==entries[name]['sha256']
(OUT/'source-backup-verification.json').write_text(json.dumps(dict(ok=True,members=len(z.namelist()))),encoding='utf8')
run('phase3_verify_protected.py')
run('phase3_finish_report.py')
run('phase3_verify_protected.py')
protected=json.loads((OUT/'protected-verification.json').read_text(encoding='utf8'))
names=sorted(set(protected['changed_existing_source']+protected['new_files']))
delivery=[dict(path=name,sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()) for name in names]
(OUT/'deliverables-manifest.json').write_text(json.dumps(dict(files=delivery,evidence='artifacts/phase3',no_build=True),indent=2),encoding='utf8')
print('P3 VALIDATION COMPLETE',flush=True)
