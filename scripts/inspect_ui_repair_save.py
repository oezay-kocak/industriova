"""Read-only assertions on isolated source/EXE playtest saves."""
import sys,json,sqlite3
from pathlib import Path
path=Path(sys.argv[1]).resolve();out=Path(sys.argv[2])
with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
    assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    data=json.loads(db.execute("select state_json from saves where slot='company'").fetchone()[0])
cards=data['cards'];freight=data['freight']
summary={'integrity':'ok','tick':data['tick'],'cash':data['cash']['amount'],'cards':len(cards),'schema':data['state_schema_version'],
         'halls':list(data['halls']),'lifetime_produced':data['production_progress']['lifetime_produced'],
         'freight_slots':[(fid,s['index'],s['card_id']) for fid,f in freight['facilities'].items() for s in f['slots']],
         'mk':{cid:c['mk_level'] for cid,c in cards.items() if c.get('mk_level',1)>1},'assignments':freight['assignments'],
         'active_shipments':freight['outbound_shipments'],
         'paused_cards':[cid for cid,c in cards.items() if c.get('paused',False)]}
out.write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
