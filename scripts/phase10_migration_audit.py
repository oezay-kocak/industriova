"""Recheck all sixteen read-only historical copies against final P8 payloads."""
from pathlib import Path
from contextlib import closing
import json,sqlite3,hashlib,sys
root=Path.cwd();sys.path.insert(0,str(root/'src'))
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,STATE_SCHEMA_VERSION
assert STATE_SCHEMA_VERSION==9
out=root/'artifacts/phase10';saved=root/'artifacts/release-backups/20261018T185514851717Z'
old=json.loads((root/'artifacts/phase8/migration-after.json').read_text(encoding='utf8'))['results']
rows=[]
for e in json.loads((saved/'manifest.json').read_text(encoding='utf8'))['saves']:
 p=saved/e['backup']
 if p.suffix not in ('.sqlite','.db'):continue
 with closing(sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:records=db.execute('SELECT slot,state_json FROM saves').fetchall()
 for slot,raw in records:
  value=serialize_game_state(deserialize_game_state(json.loads(raw)))
  digest=hashlib.sha256(json.dumps(value,sort_keys=True).encode('utf8')).hexdigest()
  prior=next(r for r in old if r['source']==e['source'] and r['slot']==slot)
  row=dict(source=e['source'],slot=slot,payload_sha256=digest,entire_payload_equals_final_p8=digest==prior['payload_sha256'],idempotent=serialize_game_state(deserialize_game_state(value))==value)
  rows.append(row);print(slot,row['entire_payload_equals_final_p8'],flush=True)
report=dict(schema=STATE_SCHEMA_VERSION,results=rows,passed=sum(r['entire_payload_equals_final_p8'] and r['idempotent'] for r in rows))
(out/'migration-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
assert len(rows)==report['passed']==16
print('16/16 FULL PAYLOADS MATCH FINAL P8',flush=True)
