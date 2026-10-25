"""Independent sources and read-only personal saves; bind the retained P8 chain."""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing
import hashlib,json,sqlite3,zipfile,shutil
root=Path.cwd();out=root/'artifacts/phase10';dest=out/('backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));dest.mkdir()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
previous=Path((root/'artifacts/phase9/backup-location.txt').read_text(encoding='utf8'))
entries=[]
paths=[p for folder in ('src','tests','scripts','docs','assets','data') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [p for p in root.iterdir() if p.is_file()]
with zipfile.ZipFile(dest/'source-baseline.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
 for p in sorted(paths):
  name=p.relative_to(root).as_posix();archive.write(p,name);entries.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
print('SOURCES SAVED',len(entries),flush=True)
personal=[]
for i,e in enumerate(json.loads((previous/'personal-saves-manifest.json').read_text(encoding='utf8'))):
 p=Path(e['original']);raw=dest/f'personal-{i}-raw.sqlite';copy=dest/f'personal-{i}-consistent.sqlite';shutil.copyfile(p,raw)
 with closing(sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(copy)) as target:
  source.backup(target);integrity=target.execute('PRAGMA integrity_check').fetchone()[0];assert integrity=='ok'
 assert sha(p)==sha(raw)
 personal.append(dict(original=str(p),sha256=sha(p),raw=str(raw),consistent=str(copy),integrity=integrity))
print('FIVE PERSONAL SAVES VERIFIED',flush=True)
protected=[]
for folder in ('build','dist'):
 for p in (root/folder).rglob('*'):
  if p.is_file():protected.append(dict(path=p.relative_to(root).as_posix(),sha256=sha(p)))
manifest=dict(entries=entries,protected_builds=protected,previous_manifest=str(previous/'manifest.json'),previous_manifest_sha256=sha(previous/'manifest.json'),previous_archive_sums=json.loads((previous/'SHA256SUMS.json').read_text(encoding='utf8')),restore='Extract source-baseline.zip into a NEW directory and verify SHA256. Retain P9 backup chain for all prior dirty state, artifacts and builds. Personal saves restore only on explicit request; originals were opened read-only. P10 backup scope is relevant sources/tests/configuration/docs/assets plus five personal saves; build/dist protected separately.')
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');(dest/'personal-saves-manifest.json').write_text(json.dumps(personal,indent=2),encoding='utf8')
with zipfile.ZipFile(dest/'source-baseline.zip') as z:
 assert z.testzip() is None;z.extractall(out/'before-tree')
for e in entries:assert sha(out/'before-tree'/e['path'])==e['sha256']
(dest/'SHA256SUMS.json').write_text(json.dumps({p.name:sha(p) for p in dest.iterdir() if p.is_file()},indent=2),encoding='utf8')
(out/'backup-location.txt').write_text(str(dest),encoding='utf8')
print('BACKUP VERIFIED',json.dumps(dict(files=len(entries),build_files=len(protected),backup=str(dest))),flush=True)
