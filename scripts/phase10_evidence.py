"""Count retained test identities, migration results and real PNG artifacts."""
from pathlib import Path
from collections import Counter
import json,hashlib,struct,xml.etree.ElementTree as ET
root=Path.cwd();out=root/'artifacts/phase10'
def cases(folder):
 return Counter((t.get('classname'),t.get('name')) for p in folder.glob('*.xml') for t in ET.parse(p).getroot().iter('testcase'))
baseline=cases(root/'artifacts/phase9/final-regression');final=cases(out/'final-regression')
assert sum(baseline.values())==1938 and not baseline-final
rows=json.loads((out/'final-regression/results.json').read_text(encoding='utf8'))
dpi=json.loads((out/'dpi2-regression/results.json').read_text(encoding='utf8'))
assert len(rows)==97 and all(r['exit_code']==0 and r['skipped']==0 for r in rows+dpi)
images=[]
for p in sorted((out/'screenshots').rglob('captures.json')):
 images.extend(json.loads(p.read_text(encoding='utf8'))['captures'])
for folder in ('price-screenshots','resource-screenshots'):
 for p in sorted((out/folder).rglob('captures.json')):
  images.extend(json.loads(p.read_text(encoding='utf8')))
for row in images:
 p=root/row['file'];data=p.read_bytes();size=list(struct.unpack('>II',data[16:24]));assert size==row['pixels']
 assert hashlib.sha256(data).hexdigest()==row['sha256']
 assert row['pixels']==[v*row['scale'] for v in row['logical']],row
report=dict(regression_tests=sum(r['tests'] for r in rows),modules=len(rows),old_test_identities_retained=sum(baseline.values()),new_test_identities=sum((final-baseline).values()),dpi2_tests=sum(r['tests'] for r in dpi),dpi2_modules=len(dpi),captured_images=len(images),png_hashes_and_dimensions_verified=True)
(out/'regression-summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(out/'image-manifest.json').write_text(json.dumps(images,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
