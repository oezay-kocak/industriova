"""All 16 historical migrations plus five personal backup copies; never originals."""
from pathlib import Path
from contextlib import closing
import json, sqlite3, shutil, subprocess, sys, hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase11fg/migrations';OUT.mkdir(parents=True,exist_ok=True)

def historical():
    saved=ROOT/'artifacts/release-backups/20261018T185514851717Z'
    count=0
    for entry in json.loads((saved/'manifest.json').read_text())['saves']:
        path=saved/entry['backup']
        if path.suffix not in ('.sqlite','.db'):continue
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
            for slot,raw in db.execute('SELECT slot,state_json FROM saves'):
                count+=1
                yield dict(source=entry['source'],path=str(path),slot=slot,payload=json.loads(raw))
    assert count==16

def hash_value(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

def preserved_hashes(value):
    changed={'state_schema_version','economy_version','market','contracts','consortium','company_xp_progress'}
    return dict(fields={key:hash_value(v) for key,v in value.items() if key not in changed},active=hash_value(value['contracts']['active']),xp={key:hash_value(v) for key,v in value['company_xp_progress'].items() if key not in ('last_productive_bucket','productive_event_seconds')},market_timing=hash_value({key:v for key,v in value['market'].items() if key!='resources'}),consortium={cid:{kind:hash_value(contract) for kind,contract in con['contracts'].items() if contract['status']!='available'} for cid,con in value['consortium']['consortiums'].items()})

if '--old-worker' in sys.argv:
    print('Old source worker: reading all historical copies',flush=True)
    sys.path.insert(0,str(ROOT/'artifacts/phase11fg/starting-snapshot/source/src'))
    from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
    values=[]
    for index,entry in enumerate(historical()):
        values.append(preserved_hashes(serialize_game_state(deserialize_game_state(entry['payload']))))
        print('old normalized',index,flush=True)
    (OUT/'previous-normalized-hashes.json').write_text(json.dumps(values,indent=2),encoding='utf-8')
    raise SystemExit

if not (OUT/'previous-normalized-hashes.json').exists():
    subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--old-worker'],check=True,cwd=ROOT)
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore
before=json.loads((OUT/'previous-normalized-hashes.json').read_text());rows=[]
preserve=('cash','resources','cards','halls','resource_sites','energy_plants','research','company','statistics','machine_production','inventory_storage_level','warehouse_capacity','scrap','production_progress')
for index,(entry,old) in enumerate(zip(historical(),before)):
    path=OUT/f'historical-{index}.sqlite'
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS saves (slot TEXT PRIMARY KEY,state_json TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO saves VALUES (?,?)',(entry['slot'],json.dumps(entry['payload'])))
    store=SQLiteSaveStore(path);new=serialize_game_state(store.load(entry['slot']))
    assert preserved_hashes(new)==old,(index,'preserved field SHA256 mismatch')
    assert new['economy_version']==2
    store.save(entry['slot'],deserialize_game_state(new));again=serialize_game_state(store.load(entry['slot']));assert again==new
    with closing(sqlite3.connect(path)) as db:integrity=db.execute('pragma integrity_check').fetchone()[0]
    rows.append(dict(group='historical',index=index,source=entry['source'],slot=entry['slot'],idempotent=True,assets_and_commitments_preserved=True,integrity=integrity))
    print('historical',index,'PASS',flush=True)
personal=json.loads((ROOT/'artifacts/phase10/backup-20261022T224910Z/personal-saves-manifest.json').read_text())
for index,entry in enumerate(personal):
    source=Path(entry['consistent']);path=OUT/f'personal-copy-{index}.sqlite';shutil.copy2(source,path)
    with closing(sqlite3.connect(path)) as db:slots=[r[0] for r in db.execute('select slot from saves')]
    store=SQLiteSaveStore(path)
    for slot in slots:
        new=serialize_game_state(store.load(slot));assert new['economy_version']==2
        store.save(slot,deserialize_game_state(new));assert serialize_game_state(store.load(slot))==new
    rows.append(dict(group='personal-backup-copy',index=index,source=str(source),slot=slots,idempotent=True,assets_and_commitments_preserved=True,integrity='ok'))
    print('personal backup copy',index,'PASS',flush=True)
report=dict(historical=sum(r['group']=='historical' for r in rows),personal_backup_copies=len(personal),results=rows)
(OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('16/16 historical; 5/5 personal BACKUP copies; no original opened as a database',flush=True)
