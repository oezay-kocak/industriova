"""Pin final P9 code, report and accepted evidence; exclude transient AppData."""
from pathlib import Path
import hashlib,json
root=Path.cwd();out=root/'artifacts/phase9'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
assert all(sha(root/n)==h for n,h in frozen.items())
paths={root/n for n in frozen};paths.update((root/'scripts').glob('phase9_*.py'));paths.add(root/'docs/industriova-03-phase9-ui-consortium-report.md')
for folder in ('final-regression','dpi2-regression'):
 paths.update((out/folder).glob('*.xml'));paths.update((out/folder).glob('*.txt'));paths.update((out/folder).glob('*.json'))
for folder in ('screenshots','popups'):
 for scale in (1,2):paths.update((out/folder/f'dpi{scale}').glob('*.png'));paths.add(out/folder/f'dpi{scale}/captures.json')
for stage in ('before','after'):
 for name in ('results.json','ui-results.json'):paths.add(out/'performance'/stage/name)
for name in ('consortium-before/consortium-balance-simulation.json','consortium-final/consortium-balance-simulation.json','economic-comparison.json','performance-comparison.json','migration-audit.json','ship-allocation-proof.json','visual-review.json','protected-verification.json','regression-summary.json','final-source-sha256.json','implementation.diff','legacy-capture-preservation.json','backup-location.txt','backup-final.log','postchecks.json','postchecks.log','validation-final-source.log','header-tooltip-fix.json','final-navigation-coverage.json','source-before-header-tooltip-fix-sha256.json','source-before-all-tab-entry-coverage-sha256.json','completion-final.json'):
 paths.add(out/name)
for name in ('dpi2-final.log','consortium-final-final.log','contracts-before-final.log','contracts-after-final.log','ui-before-final.log','ui-after-final.log','migration-final-final.log','consortium-before.log','capture-final-dpi1.log','capture-final-dpi2.log','popups-dpi1.log','popups-dpi2.log'):paths.add(out/name)
backup=Path((out/'backup-location.txt').read_text(encoding='utf8'))
for name in ('manifest.json','personal-saves-manifest.json','SHA256SUMS.json'):paths.add(backup/name)
records=[]
for p in sorted(paths):
 assert p.is_file(),p;records.append(dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
(out/'delivery-manifest.json').write_text(json.dumps(dict(files=records,count=len(records),final_test_cases=1938,final_modules=95,source_frozen=True,excluded='Personal AppData copies, tmp/cache, intermediate diagnostics and incomplete initial archive scan. Retained backup ZIP integrity is bound by SHA256SUMS.json; existing P8 chain remains at its recorded paths.'),indent=2),encoding='utf8')
print('DELIVERY',len(records),'files',flush=True)
