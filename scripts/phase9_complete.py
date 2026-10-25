"""Finish evidence only after all serial validation jobs have completed."""
from pathlib import Path
import time,subprocess,sys,json,difflib
root=Path.cwd();out=root/'artifacts/phase9';deadline=time.monotonic()+2400
while True:
 log=(out/'validation-final-source.log').read_text(encoding='utf8')
 if 'REGRESSION AND ALL POSTCHECKS PASSED' in log:break
 assert 'Traceback (most recent call last)' not in log,log[-2000:]
 assert time.monotonic()<deadline,'Validation still pending after 40 minutes.'
 time.sleep(3)
for script in ('phase9_preserve_legacy_outputs.py','phase9_evidence_summary.py','phase9_visual_review.py','phase9_verify.py','phase9_write_report.py'):
 with (out/(script.removesuffix('.py')+'.log')).open('w',encoding='utf8') as log:
  result=subprocess.run([sys.executable,'-u','scripts/'+script],cwd=root,stdout=log,stderr=subprocess.STDOUT)
 print(script,result.returncode,flush=True);assert result.returncode==0,script
report=root/'docs/industriova-03-phase9-ui-consortium-report.md'
p=out/'protected-verification.json';verified=json.loads(p.read_text(encoding='utf8'));verified['new_files'].append('docs/'+report.name);verified['new_files']=sorted(set(verified['new_files']));verified['report_written_after_protection']=True;p.write_text(json.dumps(verified,indent=2),encoding='utf8')
# verify.py includes an already existing report in its new-file diff. Replace
# that suffix with the just-rendered final report rather than duplicating it.
diffpath=out/'implementation.diff';diff=diffpath.read_text(encoding='utf8');marker='--- /dev/null\n+++ after/docs/'+report.name
if marker in diff:diff=diff[:diff.index(marker)]
diff+=''.join(difflib.unified_diff([],report.read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/docs/'+report.name));diffpath.write_text(diff,encoding='utf8')
result=subprocess.run([sys.executable,'-u','scripts/phase9_delivery_manifest.py'],cwd=root);assert result.returncode==0
print('P9 COMPLETE: report, protected originals, manifest',flush=True)
