"""Verify original saves, builds, catalog, prior evidence and frozen final source."""
from pathlib import Path
import hashlib,json,zipfile
root=Path.cwd();out=root/'artifacts/phase10';backup=Path((out/'backup-location.txt').read_text(encoding='utf8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
 return h.hexdigest()
manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'));changed=[];untouched=0
for row in manifest['entries']:
 p=root/row['path']
 if sha(p)==row['sha256']:untouched+=1
 else:changed.append(dict(path=row['path'],before=row['sha256'],after=sha(p)))
allowed_core={'src/production_zero/core/commands.py'}
assert all(not row['path'].startswith('src/production_zero/core/') or row['path'] in allowed_core for row in changed)
assert all(not row['path'].startswith('src/production_zero/data/') for row in changed)
for row in manifest['protected_builds']:assert sha(root/row['path'])==row['sha256'],row['path']
saves=json.loads((backup/'personal-saves-manifest.json').read_text(encoding='utf8'))
for row in saves:assert sha(Path(row['original']))==row['sha256'],row['original']
for name,digest in json.loads((backup/'SHA256SUMS.json').read_text(encoding='utf8')).items():assert sha(backup/name)==digest,name
previous=Path(manifest['previous_manifest']);assert sha(previous)==manifest['previous_manifest_sha256']
for name,digest in manifest['previous_archive_sums'].items():assert sha(previous.parent/name)==digest,name
frozen=json.loads((out/'final-source-sha256.json').read_text(encoding='utf8'))
for name,digest in frozen.items():assert sha(root/name)==digest,name
report=dict(ok=True,original_saves=len(saves),protected_build_files=len(manifest['protected_builds']),
 unchanged_baseline_files=untouched,changed_existing_files=changed,frozen_python_files=len(frozen),
 schema=9,resources_and_recipes_unchanged=True,backup=str(backup))
(out/'protected-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PROTECTED',len(saves),'saves',len(manifest['protected_builds']),'build files',untouched,'baseline files',flush=True)
