"""Identical P3 Inventory fixtures and UI measurements before/after P4."""
import argparse, gc, hashlib, json, os, statistics, sys, time, tracemalloc
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser();p.add_argument('stage', choices=('before','after'));p.add_argument('--source',type=Path,default=ROOT);args=p.parse_args()
out=ROOT/'artifacts/phase5'/args.stage;out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(args.source.resolve()/'src'),str(ROOT/'scripts')]
from dataclasses import replace
from production_zero.core.state import GameState
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.commands import CommandBus
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.session_writer import snapshot_game_state,encode_snapshot
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json')
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication,QWidget
from phase0_benchmark import register_fonts,memory
os.environ.update(LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
app=QApplication([]);register_fonts(app)
def drain():
 for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def fixture(count,distinct):
 s=GameState(99);s.cash.amount=1e10
 for i in range(count):
  d=D[('machine.processor','energy.solar_array','freight.truck')[i%3]];cid=f'card-{i:05}'
  s.cards[cid]=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),acquisition_cost=float(i) if distinct else 100.)
 return s
def measure(action,n=7):
 values=[]
 for _ in range(n):
  start=time.perf_counter();action();values.append((time.perf_counter()-start)*1000)
 return dict(samples_ms=values,median_ms=statistics.median(values),max_ms=max(values))
result=dict(method='7 serial repetitions, same 500/5000/10000 three-type fixtures, stacked AND distinct investments; Qt offscreen 1366x768; Python allocations separately, no GPU/FPS claim',fixtures={})
for count in (500,5000,10000):
 for distinct in (False,True):
  s=fixture(count,distinct);rows=build_card_inventory_rows(s,D)
  assert sum(r.quantity for r in rows)==count
  record=dict(cards=count,rows=len(rows),projection=measure(lambda:build_card_inventory_rows(s,D)),snapshot=measure(lambda:snapshot_game_state(s)))
  payload=encode_snapshot(snapshot_game_state(s));record['payload_bytes']=len(payload.encode('utf8'));record['payload_sha256']=hashlib.sha256(payload.encode('utf8')).hexdigest()
  if args.stage in ('before','after'):
   from production_zero.ui.inventory_view import InventoryView,InventoryCardFrame
   cold=[]
   for _ in range(7):
    t=time.perf_counter();v=InventoryView(s,D,command_bus=CommandBus(s),release_mode=True);v.resize(1366,768);v.show();drain();cold.append((time.perf_counter()-t)*1000)
    v.close();v.deleteLater();drain()
   record['cold_open']=dict(samples_ms=cold,median_ms=statistics.median(cold),max_ms=max(cold))
   v=InventoryView(s,D,command_bus=CommandBus(s),release_mode=True);v.resize(1366,768);v.show();drain()
   record['refresh']=measure(lambda:(v.refresh(),drain()))
   bar=v._workspace_scroll.verticalScrollBar()
   record['scroll_pair']=measure(lambda:(bar.setValue(bar.maximum()),drain(),bar.setValue(0),drain()))
   assert set(v._workspace_by_id)==set(s.cards)
   record['card_widgets']=len(v.findChildren(InventoryCardFrame));record['all_widgets']=len(v.findChildren(QWidget))
   record['process_working_set_bytes']=memory()
   assert record['card_widgets']<100
   v.close();v.deleteLater();drain();gc.collect()
   tracemalloc.start();memory_state=fixture(count,distinct);v=InventoryView(memory_state,D,command_bus=CommandBus(memory_state),release_mode=True);v.resize(1366,768);v.show();drain()
   record['python_current_bytes'],record['python_peak_bytes']=tracemalloc.get_traced_memory();tracemalloc.stop()
   v.close();v.deleteLater();drain();del memory_state;gc.collect()
  result['fixtures'][f'{count}-'+('distinct' if distinct else 'stacked')]=record
  print(count,distinct,record.get('card_widgets'),flush=True)
(out/'inventory-ui-benchmark.json').write_text(json.dumps(result,indent=2),encoding='utf8')
