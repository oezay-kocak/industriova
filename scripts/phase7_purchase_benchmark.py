"""Serial command latency against an explicit source tree; setup outside timing."""
import argparse,json,os,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--source',type=Path,default=ROOT);a=p.parse_args()
OUT=ROOT/'artifacts/phase7'/a.stage/'purchases';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.source.resolve()/'src'));os.environ.update(LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
from production_zero.core.commands import PurchaseHall,UnlockProductionLine,UnlockProductionSlot,BuildFreightFacility,ExpandFreightFacility,BuyCommonSupplyCard,UpgradeMachines
from production_zero.core.state import GameState,FactoryHall
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
D=load_card_definitions(a.source/'src/production_zero/data/game_definitions.json');results={}
for name in ('building','slot','line','freight_building','freight_slot','supply_ship','ship_mk'):
    values=[]
    for repeat in range(21):
        s=deserialize_game_state(serialize_game_state(GameState(197)));s.cash.amount=1e12
        s.halls['h']=FactoryHall('h','Hall',6,max_lines=5)
        s.cards['ship']=create_card_instance('ship','freight.ship',D['freight.ship'].card_kind,Rarity.COMMON)
        command={'building':lambda:PurchaseHall(),'slot':lambda:UnlockProductionSlot('h','h.line-1'),'line':lambda:UnlockProductionLine('h','h.line-3'),
          'freight_building':lambda:BuildFreightFacility('harbor'),'freight_slot':lambda:ExpandFreightFacility('garage-1'),
          'supply_ship':lambda:BuyCommonSupplyCard('freight.ship',D),'ship_mk':lambda:UpgradeMachines(('ship',),D)}[name]()
        start=time.perf_counter();command.apply(s);values.append((time.perf_counter()-start)*1000)
    results[name]=dict(samples_ms=values,median_ms=statistics.median(values),max_ms=max(values))
(OUT/'results.json').write_text(json.dumps(dict(method='21 serial warm in-process samples; synthetic company, setup excluded; commands include quote/validation/debit/commit, no human modal wait',results=results),indent=2),encoding='utf8')
print(json.dumps({n:round(v['median_ms'],4) for n,v in results.items()}),flush=True)
