"""Selected-board runtime and Supply refresh against a marked 500-card fixture."""
import os,json
from pathlib import Path
from time import perf_counter
from statistics import median
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.supply_view import SupplyView
from production_zero.core.state import FactoryHall
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind,Rarity
app=QApplication([]);w=MainWindow(development_mode=False);w.resize(1366,768);w.show();app.processEvents()
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
state=w._session_state
for h in range(10):
    unit=FactoryHall('perf-'+str(h),'Perf '+str(h),50,max_lines=5,max_slots_per_line=10,start_unlocked_lines=5,start_slots_per_line=10)
    state.halls[unit.hall_id]=unit
    for i,slot in enumerate(unit.slots):
        cid='perf-'+str(h)+'-'+str(i);state.cards[cid]=create_card_instance(cid,'machine.processor',CardKind.MACHINE,Rarity.COMMON);slot.card_id=cid
view=w.findChild(SupplyView);tabs=w.findChild(QTabWidget,'mainTabs');tabs.setCurrentWidget(view);app.processEvents()
def measure(fn):
    values=[]
    for _ in range(9):
        start=perf_counter();fn();app.processEvents();values.append((perf_counter()-start)*1000)
    return median(values[2:])
result={'fixture':'500 installed processors; ordinary selected Supply; no personal saves','supply_refresh_ms':measure(view.refresh)}
w.close();print(json.dumps(result))
