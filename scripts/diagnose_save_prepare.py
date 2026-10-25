"""Read-only inventory and consistent copies for save-state diagnosis."""
import hashlib,json,sqlite3
from pathlib import Path
from contextlib import closing

root=Path.cwd();out=root/'artifacts/industriova-save-state-diagnosis'
out.mkdir(parents=True,exist_ok=True)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
protected={str(p.relative_to(root)):digest(p) for folder in ('src','tests') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
protected[str(Path('dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip'))]=digest(root/'dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip')
(out/'protected-files-before.json').write_text(json.dumps(protected,indent=2))
inventory=[]
for base in [Path.home() / 'AppData/Local/Production Zero/saves',Path.home() / 'AppData/Roaming/Production Zero/saves',Path.home()/'Production Zero/saves',Path.home() / 'AppData/Local/Industriova/saves']:
    if not base.exists():continue
    for p in base.rglob('*'):
        if p.is_file():
            item={'path':str(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':digest(p)}
            if p.suffix=='.sqlite':
                with closing(sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)) as db:
                    item['integrity']=db.execute('pragma integrity_check').fetchone()[0]
                    item['slots']=[{'slot':r[0],'bytes':r[1]} for r in db.execute('select slot,length(state_json) from saves')]
            inventory.append(item)
(out/'personal-inventory-before.json').write_text(json.dumps(inventory,indent=2))
personal=Path.home() / 'AppData/Local/Production Zero/saves/company.sqlite'
legacy=personal.with_name('company.pre-industriova-v5.sqlite')
for case,source in [('B-legacy',legacy),('C-user',personal)]:
    folder=out/case;folder.mkdir(exist_ok=True)
    target=folder/'company.sqlite'
    assert not target.exists(),target
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as db,closing(sqlite3.connect(target)) as copied:
        db.backup(copied)
        assert copied.execute('pragma integrity_check').fetchone()[0]=='ok'
    (folder/'origin.json').write_text(json.dumps({'source':str(source),'copy':str(target),'sha256':digest(target)},indent=2))
print(json.dumps({'inventory':inventory,'protected_files':len(protected),'output':str(out)},indent=2))
