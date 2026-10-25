"""Freeze accepted P10 sources/reports/evidence, excluding diagnostic runs."""
from pathlib import Path
import json,hashlib,difflib
root=Path.cwd();out=root/'artifacts/phase10';backup=Path((out/'backup-location.txt').read_text(encoding='utf8'))
def read(name):return json.loads((out/name).read_text(encoding='utf8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
assert read('protected-verification.json')['ok']
assert read('migration-audit.json')['passed']==16
assert read('regression-summary.json')['regression_tests']==1994
assert read('accepted-validation.json')['tests']==1994
assert all(r['exit_code']==0 for r in read('postchecks.json'))
for scale in (1,2):assert read(f'click-roundtrip-dpi{scale}/result.json')['ok']
source=read('final-source-sha256.json')
for name,digest in source.items():assert sha(root/name)==digest,name
for name,digest in read('visual-review.json')['file_sha256'].items():assert sha(root/name)==digest,name
baseline=json.loads((backup/'manifest.json').read_text(encoding='utf8'));old={r['path']:r for r in baseline['entries']};diff=[]
changed=[]
for folder in ('src','tests','scripts','docs'):
 for p in (root/folder).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.md'):continue
  name=p.relative_to(root).as_posix()
  if sha(p)==old.get(name,{}).get('sha256'):continue
  previous=out/'before-tree'/name
  diff.extend(difflib.unified_diff(previous.read_text(encoding='utf-8-sig').splitlines(True) if previous.exists() else [],p.read_text(encoding='utf-8-sig').splitlines(True),fromfile='P9/'+name,tofile='P10/'+name))
  changed.append(name)
(out/'implementation.diff').write_text(''.join(diff),encoding='utf8')
completion=dict(status='complete',regression_tests=1994,modules=97,dpi2_tests=518,dpi2_modules=11,migrations=16,schema=9,
 personal_saves_unchanged=5,build_files_unchanged=4083,new_build=False,native_windows_hand_acceptance='open',
 visual_review='17 real images viewed; 342 captures checked for hashes/dimensions',
 economy='49 raw resources, 353 chains, 76 engine strategies; no price/recipe changes',
 pointer_roundtrips=[1,2],
 missing_input='The ten user-reference screenshots mentioned in the text were not attached; textual requirements and existing UI were used.')
(out/'completion-final.json').write_text(json.dumps(completion,indent=2),encoding='utf8')
files=set(changed)|set(source)
files.update(p.relative_to(root).as_posix() for p in (root/'scripts').glob('phase10_*.py'))
files.update(p.relative_to(root).as_posix() for p in out.glob('*.json') if p.name not in {'delivery-manifest.json'})
files.add((out/'implementation.diff').relative_to(root).as_posix())
for folder in ('final-regression','dpi2-regression'):
 files.update(p.relative_to(root).as_posix() for p in (out/folder).iterdir() if p.is_file() and (p.suffix in ('.txt','.xml') or p.name=='results.json'))
for name in ('before','after'):
 files.update((out/'performance'/name/p).relative_to(root).as_posix() for p in ('results.json','inventory-matched.json'))
for row in read('image-manifest.json'):files.add(row['file'])
for scale in (1,2):files.add((out/f'click-roundtrip-dpi{scale}/result.json').relative_to(root).as_posix())
for folder in ('screenshots','price-screenshots','resource-screenshots'):
 files.update(p.relative_to(root).as_posix() for p in (out/folder).rglob('captures.json'))
files.update((backup/name).relative_to(root).as_posix() for name in ('manifest.json','personal-saves-manifest.json','SHA256SUMS.json','source-baseline.zip'))
entries=[dict(path=name,bytes=(root/name).stat().st_size,sha256=sha(root/name)) for name in sorted(files)]
(out/'delivery-manifest.json').write_text(json.dumps(dict(files=entries,count=len(entries),completion=completion,scope='Final complete fresh regression and DPI batches after last productive fix. Diagnostic/old intermediate test runs remain on disk but are not accepted tests or performance measurements.'),indent=2),encoding='utf8')
print('DELIVERED',len(entries),'PINNED FILES; P10 COMPLETE',flush=True)
