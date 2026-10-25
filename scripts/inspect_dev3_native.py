"""Read-only save proofs for actual compiled EXE sessions."""
import json,sqlite3,hashlib,sys
from pathlib import Path
out=Path('artifacts/dev3/native');legacy=out/'Production Zero/saves/company.sqlite'
before=json.loads((out/'legacy-before.json').read_text())
assert hashlib.sha256(legacy.read_bytes()).hexdigest()==before['sha256']
assert not list(legacy.parent.glob('*pre-industriova*'))
path=out/'Industriova/saves/company.sqlite'
with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
    assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    p=json.loads(db.execute("select state_json from saves where slot='company'").fetchone()[0])
assert 'legacy-only-machine' not in p['cards']
result={k:p[k] for k in ('tick','cash','company','cards','resources','halls','resource_sites','energy_plants','freight','state_schema_version','contracts')}
result['legacy_unchanged']=True;result['database']=str(path.resolve());result['integrity']='ok'
(out/(sys.argv[1]+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'stage':sys.argv[1],'tick':p['tick'],'cash':p['cash'],'cards':len(p['cards']),'legacy_unchanged':True,'manual_backup_exists':(out/'Industriova/saves/dev/dev_save.json').exists()}))
