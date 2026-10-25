"""Identical inventory projections at P1/P2; isolated acquisition timing at P2.

No UI, no personal stores. Python allocation is reported separately from timing.
"""
import argparse,gc,json,statistics,sys,time,tracemalloc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('stage',choices=('before','after'));p.add_argument('--source',type=Path,default=ROOT);args=p.parse_args()
sys.path.insert(0,str(args.source.resolve()/'src'))
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.supply import buy_common_supply_cards,common_card_price
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.session_writer import snapshot_game_state,encode_snapshot
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json')

def fixture(count):
 s=GameState(99);s.cash.amount=1e10
 from dataclasses import replace
 for i in range(count):
  d=D[('machine.processor','energy.solar_array','freight.truck')[i%3]];cid=f'inventory-{i:05d}'
  s.cards[cid]=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),acquisition_cost=common_card_price(d))
 return s

def measure(fn):
 values=[]
 for _ in range(7):
  t=time.perf_counter();fn();values.append((time.perf_counter()-t)*1000)
 return dict(samples_ms=values,median_ms=statistics.median(values),max_ms=max(values))

result=dict(method='7 serial repetitions; same 3-type unplaced inventory; Python tracemalloc separately; UTF8 JSON snapshot',inventory={},acquisition={})
for count in (500,5000,10000):
 s=fixture(count);rows=build_card_inventory_rows(s,D);assert sum(r.quantity for r in rows)==count
 projection=measure(lambda:build_card_inventory_rows(s,D));snapshot=measure(lambda:snapshot_game_state(s))
 payload=encode_snapshot(snapshot_game_state(s));payload_bytes=len(payload.encode('utf8'))
 del s;gc.collect();tracemalloc.start();s=fixture(count);rows=build_card_inventory_rows(s,D);snap=snapshot_game_state(s)
 current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 result['inventory'][count]=dict(projection=projection,snapshot=snapshot,payload_bytes=payload_bytes,python_current_bytes=current,python_peak_bytes=peak,logical_cards=len(s.cards),projection_rows=len(rows))
 del s,rows,snap;gc.collect()
for count in (1,10,100,1000):
 values=[];rejections=[]
 for _ in range(7):
  s=GameState(99);s.cash.amount=1e10;s.freight.facilities.clear()
  t=time.perf_counter()
  try:ids=buy_common_supply_cards(s,D,'machine.processor',count)
  except ValueError as e:rejections.append(str(e))
  else:
   assert len(ids)==count and not s.installed_card_ids();values.append((time.perf_counter()-t)*1000)
 result['acquisition'][count]=dict(samples_ms=values,rejections=rejections,median_ms=statistics.median(values) if values else None,max_ms=max(values) if values else None)
out=ROOT/'artifacts/phase6'/args.stage;out.mkdir(parents=True,exist_ok=True);(out/'inventory-benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
