"""Identical P9/P10 fixtures; run serially without tests or capture processes."""
from pathlib import Path
import argparse,os,sys,time,json,statistics,tempfile
from dataclasses import replace
root=Path.cwd();p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root);p.add_argument('--stage',required=True);args=p.parse_args()
out=root/'artifacts/phase10/performance'/args.stage;out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(args.source.resolve()/'src'),str(root/'tests'),str(root)]
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QTimer
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.freight_view import FreightView
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.core.commands import CommandBus,BuyCommonSupplyCard
from production_zero.core.state import GameState
from production_zero.core.freight import FreightFacility
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.persistence.sqlite_store import serialize_game_state,SQLiteSaveStore
from production_zero.persistence.session_writer import snapshot_game_state
D=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json');R=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
app=QApplication([]);_load_qa_fonts();results={};geometry={}
def measure(name,operation):
 samples=[]
 for _ in range(7):
  start=time.perf_counter();operation();samples.append((time.perf_counter()-start)*1000)
 results[name]=dict(median_ms=statistics.median(samples),max_ms=max(samples),samples_ms=samples)
 print(name,round(statistics.median(samples),3),flush=True)
for count in (500,5000,10000):
 s=GameState(1);s.cash.amount=1e12;bus=CommandBus(s);bus.dispatch(BuyCommonSupplyCard('machine.processor',D,count))
 s.cards={f'inventory-{index}':replace(card,card_id=f'inventory-{index}',acquisition_cost=1000+index*.01) for index,card in enumerate(s.cards.values())}
 inv=InventoryView(s,D,command_bus=bus,release_mode=True);inv.resize(1100,650);inv.show();app.processEvents()
 measure(f'inventory.{count}.refresh',lambda:(inv.refresh(),app.processEvents()))
 def scroll():
  bar=inv._workspace_scroll.verticalScrollBar();bar.setValue(bar.maximum() if bar.value()==0 else 0);app.processEvents()
 measure(f'inventory.{count}.scroll',scroll)
 geometry[str(count)]=dict(rows=len(inv._workspace_rows),pool=len(inv._workspace_pool))
 inv.close();inv.deleteLater();app.processEvents()
w=MainWindow(development_mode=False);s=w._session_state
for timer in w.findChildren(QTimer):timer.stop()
# Same one-site baseline in both performance fixtures; the authorized three-site
# genesis difference is audited separately, rather than changing sample size.
s.resource_sites={k:v for k,v in s.resource_sites.items() if k=='site-1'}
w.resize(1366,768);w.show();app.processEvents();tabs=w.findChild(QTabWidget,'mainTabs');supply=w.findChild(SupplyView);freight=w.findChild(FreightView);feed=w.findChild(EventFeedWidget)
def tabcycle():
 for _ in range(2):
  for index in range(tabs.count()):tabs.setCurrentIndex(index);app.processEvents()
measure('main.20_tab_switches',tabcycle)
tabs.setCurrentWidget(supply);supply._show_section(1)
def categories():
 for value in ('Resources','Energy','Freight')+ (('Processing','Fabrication','Assembly','All') if hasattr(supply._type_filter,'buttons') else ('Factory',)):
  supply._type_filter.setCurrentText(value);app.processEvents()
measure('supply.all_categories_cycle',categories)
def shared_categories():
 for value in ('Resources','Energy','Freight'):
  supply._type_filter.setCurrentText(value);app.processEvents()
measure('supply.three_shared_categories',shared_categories)
for rid,definition in R.items():s.ensure_resource(rid).amount=.001
w._global_resources.drawer._set_inventory_mode(True)
def resources():w._global_resources.toggle();app.processEvents();w._global_resources.toggle();app.processEvents()
measure('resources.353_open_close',resources)
def communication():feed._show_history();app.processEvents();feed.close_panels();feed._show_inbox();app.processEvents();feed.close_panels()
measure('history_inbox.open_close',communication)
measure('header.refresh',w._global_header.refresh)
def storage_dialog():
 from production_zero.ui.release_dialogs import IndustrialDialog
 dialog=IndustrialDialog('Storage expansion','Additional storage capacity: 18,820 units\nCurrent capacity: 75,280 → 94,100 units\nCost: $250.00',w,accept_text='YES – EXPAND')
 dialog.show();app.processEvents();dialog.reject();dialog.deleteLater();app.processEvents()
measure('storage_dialog.open_cancel',storage_dialog)
for index in range(500):
 cid=f'bench-truck-{index}';s.cards[cid]=create_card_instance(cid,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON)
facility=FreightFacility('bench','Benchmark Garage',slot_count=500,purchased_slot_indexes=set(range(500)))
for index,slot in enumerate(facility.slots):slot.card_id=f'bench-truck-{index}'
s.freight.facilities[facility.facility_id]=facility;tabs.setCurrentWidget(freight);freight._select_facility(facility.facility_id)
measure('freight.500_runtime',freight.refresh_runtime)
def route():
 freight._open_assignment_view('bench-truck-0');freight._select_assignment_resource('iron_ore')
 if hasattr(freight,'_route_dialog'):freight._route_dialog.reject()
 freight._close_assignment_view();app.processEvents()
measure('freight.resource_target_cancel',route)
measure('snapshot.500',lambda:snapshot_game_state(s))
measure('serialize.500',lambda:serialize_game_state(s))
payload=serialize_game_state(s);store=SQLiteSaveStore(out/'benchmark.sqlite');store.initialize()
measure('save.500',lambda:store.save('benchmark',s));measure('load.500',lambda:store.load('benchmark'))
w.close();app.processEvents()
(out/'results.json').write_text(json.dumps(dict(results=results,inventory=geometry,payload_bytes=len(json.dumps(payload).encode()),assumptions='Seven serial samples, real Qt offscreen widgets at 1366x768/100%, same exact card IDs/counts/stock and one-site fixture. Synthetic 500-slot Freight stress. Supply category cycle explicitly includes seven P10 versus four P9 categories; not normalized as equal work. No FPS/native latency claim.'),indent=2),encoding='utf8')
