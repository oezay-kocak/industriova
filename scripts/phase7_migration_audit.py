"""Sixteen historical backup rows, full payload comparison across the P7 boundary."""
import argparse, hashlib, json, sqlite3, sys
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import faulthandler
faulthandler.dump_traceback_later(45,repeat=True)
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--stage',choices=('before','after'),required=True);p.add_argument('--source',type=Path,default=ROOT);args=p.parse_args()
sys.path.insert(0,str(args.source.resolve()/'src'))
from production_zero.persistence.sqlite_store import deserialize_game_state,serialize_game_state
OUT=ROOT/'artifacts/phase7';backup=ROOT/'artifacts/release-backups/20261018T185514851717Z'
manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'))
baseline=json.loads((OUT/'migration-before.json').read_text(encoding='utf8')) if args.stage=='after' else None
p6=json.loads((ROOT/'artifacts/phase6/migration-audit.json').read_text(encoding='utf8'))
rows=[]
for entry in manifest['saves']:
    path=backup/entry['backup']
    if path.suffix not in {'.sqlite','.db'}:continue
    print('reading',path.name,flush=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:records=db.execute('SELECT slot,state_json FROM saves').fetchall()
    for slot,raw in records:
        new=serialize_game_state(deserialize_game_state(json.loads(raw)))
        digest=hashlib.sha256(json.dumps(new,sort_keys=True).encode('utf8')).hexdigest()
        checks={'idempotent':serialize_game_state(deserialize_game_state(new))==new}
        if args.stage=='before':
            expected=next(r for r in p6['results'] if r['source']==entry['source'] and r['slot']==slot)
            checks['full_payload_matches_final_p6']=digest==expected['payload_sha256']
        else:
            old=next(r for r in baseline['results'] if r['source']==entry['source'] and r['slot']==slot)
            compatible=deepcopy(new);compatible['state_schema_version']=7;compatible.pop('infrastructure_pricing_version')
            for fid,facility in compatible['freight']['facilities'].items():
                owned=facility.pop('purchased_slot_indexes')
                checks['all_legacy_slots_retained_'+fid]=owned==list(range(old['legacy_slot_counts'][fid]))
            # The only changed business quote is an unpurchased Ship Daily offer.
            # Keep exact old quotes for this comparison; all other fields must match.
            changes=[]
            for key,offers in compatible.get('supply',{}).items():
                if not isinstance(offers,list):continue
                old_offers=old['ship_offers']
                for offer in offers:
                    if not isinstance(offer,dict) or offer.get('definition_id')!='freight.ship':continue
                    previous=old_offers[offer['offer_id']]
                    if offer.get('price_cash')!=previous.get('price_cash'):
                        assert not offer.get('purchased',False)
                        changes.append(dict(offer_id=offer['offer_id'],old=previous.get('price_cash'),new=offer.get('price_cash')))
                        offer['price_cash']=previous.get('price_cash')
            checks['entire_business_payload_preserved_except_pending_ship_quote']=hashlib.sha256(json.dumps(compatible,sort_keys=True).encode('utf8')).hexdigest()==old['payload_sha256']
        rows.append(dict(source=entry['source'],slot=slot,checks=checks,passed=all(checks.values()),payload_sha256=digest,**({'legacy_slot_counts':{fid:len(u['slots']) for fid,u in new['freight']['facilities'].items()},'ship_offers':{o['offer_id']:o for offers in new.get('supply',{}).values() if isinstance(offers,list) for o in offers if isinstance(o,dict) and o.get('definition_id')=='freight.ship'}} if args.stage=='before' else {'pending_ship_requotes':changes})))
report=dict(results=rows,passed=sum(r['passed'] for r in rows),failed=sum(not r['passed'] for r in rows))
(OUT/f'migration-{args.stage}.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
for r in rows:
    if not r['passed']:print(json.dumps({k:v for k,v in r.items() if k!='payload'}))
assert len(rows)==16 and report['failed']==0
