"""Seed only a deliberately incompatible legacy save; Industriova stays fresh."""
import json,sqlite3,hashlib
from pathlib import Path
out=Path('artifacts/dev3/native');out.mkdir(parents=True,exist_ok=True)
legacy=out/'Production Zero/saves/company.sqlite';legacy.parent.mkdir(parents=True,exist_ok=True)
assert not legacy.exists() and not (out/'Industriova/saves/company.sqlite').exists()
payload={'state_schema_version':999,'cash':{'amount':999999999},'company':{'level':99,'current_xp':888888},'resources':{'coal':{'amount':777777}},'cards':{'legacy-only-machine':{'mk_level':99,'rarity':'legendary'}}}
with sqlite3.connect(legacy) as db:
    db.execute('create table saves(slot text primary key,state_json text not null)')
    db.execute('insert into saves values (?,?)',('company',json.dumps(payload)))
before={'path':str(legacy.resolve()),'sha256':hashlib.sha256(legacy.read_bytes()).hexdigest(),'bytes':legacy.stat().st_size}
(out/'legacy-before.json').write_text(json.dumps(before,indent=2));print(json.dumps(before))
