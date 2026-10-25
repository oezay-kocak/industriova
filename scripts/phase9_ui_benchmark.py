"""Matched actual MainWindow navigation plus 500-vehicle Freight stress."""
from pathlib import Path
import argparse,os,sys,runpy,json,time,statistics
root=Path.cwd();p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root);p.add_argument('--stage',required=True);args=p.parse_args()
out=root/'artifacts/phase9/performance'/args.stage;out.mkdir(parents=True,exist_ok=True)
os.environ.update(PHASE8_FORCE_CLOCK='1',QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.argv=['fixture','--source',str(args.source),'--stage','../phase9/'+args.stage]
f=runpy.run_path(str(root/'scripts/phase8_contract_simulation.py'),run_name='fixture')
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QTimer,QEvent
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow,_copy_state
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.core.freight import FreightFacility,FreightAssignment
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.persistence.sqlite_store import serialize_game_state
app=QApplication([]);_load_qa_fonts();w=MainWindow(development_mode=False)
for timer in w.findChildren(QTimer):timer.stop()
s,info=f['company']('late',10)
for rid in f['PRODUCERS']:s.ensure_resource(rid).amount=.001
_copy_state(w._session_state,s);s=w._session_state
boards={v._board_config.board_kind:v for v in w.findChildren(ProductionBoardViewV2)}
for v in boards.values():v.reset_for_state_change()
freight=w.findChild(FreightView);freight.reset_for_state_change()
personal=w.findChild(ContractsView);personal.reset_for_state_change()
conso=w.findChild(ConsortiumView);conso._workspace_signature=None;conso._render_signature=None;conso.refresh()
feed=w.findChild(EventFeedWidget);tabs=w.findChild(QTabWidget,'mainTabs');w.resize(1600,980);w.show()
results={}
def drain():app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def measure(name,fn):
 samples=[]
 for i in range(7):
  begin=time.perf_counter_ns();fn(i);drain();samples.append((time.perf_counter_ns()-begin)/1e6)
 results[name]=dict(samples_ms=samples,median_ms=statistics.median(samples),max_ms=max(samples));print(name,results[name]['median_ms'],flush=True)
drain()
def switch(i):
 for view in [boards['resources'],boards['factory'],boards['energy'],freight,personal,conso]*3+[boards['resources'],boards['factory']]:
  tabs.setCurrentWidget(view);drain()
measure('main.20_tab_switches',switch)
def communication(i):
 feed._show_history();drain()
 if hasattr(feed,'close_panels'):feed.close_panels()
 else:feed._history_panel.close()
 feed._show_inbox();drain()
 if hasattr(feed,'close_panels'):feed.close_panels()
 else:feed._inbox_panel.close()
measure('main.history_inbox_pair',communication)
def global_resources(i):
 w._global_resources.toggle();drain();w._global_resources.toggle()
w._global_resources.drawer._set_inventory_mode(True)
measure('main.global_resources_pair',global_resources)
w._global_resources.toggle();drain()
measure('main.global_prices_353_refresh',lambda i:w._global_resources.drawer.summary.refresh())
w._global_resources.toggle();drain()
for kind,v in boards.items():
 tabs.setCurrentWidget(v);drain();measure('main.'+kind+'_runtime',lambda i,v=v:v.refresh_runtime())
# Identical deliberately oversized facility in both versions, not legal play.
facility=FreightFacility('p9-stress','Large Freight Facility',slot_count=500,line_capacity=500)
s.freight.facilities[facility.facility_id]=facility
for i,slot in enumerate(facility.slots):
 cid=f'p9-truck-{i}';s.cards[cid]=create_card_instance(cid,'freight.truck',f['D']['freight.truck'].card_kind,Rarity.COMMON);slot.card_id=cid
 s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
tabs.setCurrentWidget(freight);freight._select_facility(facility.facility_id);drain()
measure('freight.500_runtime',lambda i:freight.refresh_runtime())
def routes(i):
 from production_zero.core.commands import AssignFreightVehicles
 freight._command_bus.dispatch(AssignFreightVehicles(('p9-truck-0',),'iron_ore' if i%2 else 'coal','market',f['D']))
 freight.refresh_runtime()
measure('freight.route_switch',routes)
measure('main.header_refresh',lambda i:w._global_header.refresh())
measure('main.snapshot_large_freight',lambda i:serialize_game_state(s))
(out/'ui-results.json').write_text(json.dumps(dict(source=str(args.source.resolve()),logical=[w.width(),w.height()],global_stored_rows=len(f['PRODUCERS']),stress_freight_cards=500,results=results,assumptions='Seven serial warm samples including event drain, identical mature fixture, 353 stored products with .001 eligibility stock each, and 500 actual truck cards in one deliberately oversized facility. Offscreen Qt, no FPS claim. Resource row height and visible content area differ with P9 price lines; no smaller data fixtures.'),indent=2),encoding='utf8')
w.close();drain()
