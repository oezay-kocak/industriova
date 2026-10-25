"""Isolated real Qt widget screenshots for the final three polish changes."""
import os,json,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget,QFrame,QComboBox
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.core.freight import build_freight_facility
from production_zero.ui.research_hover import ResearchHover
from production_zero.core.research import research_domains
from production_zero.tools.ui_contact_sheet import _load_qa_fonts

app=QApplication([]);_load_qa_fonts();w=MainWindow(development_mode=False,charts_enabled=False);w.show();QTest.qWait(60)
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
tabs=w.findChild(QTabWidget,'mainTabs')
def show(name):
    tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name));QTest.qWait(45);return tabs.currentWidget()
f=show('Freight');facilities={kind:build_freight_facility(f._state.freight,kind).facility_id for kind in ('garage_depot','rail_station','airport','harbor')}
v=show('Contracts');v._state.production_progress.unlocked_production_ids.add('recipe.processor.steel');v._state.ensure_resource('steel').amount=1;v.refresh()
out=Path(sys.argv[1])/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True);metrics=[]
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(50)
    for kind,uid in facilities.items():
        f=show('Freight');f._selected_facility_id=uid;f.refresh();QTest.qWait(80)
        w.grab().save(str(out/f'freight-{kind}-{width}x{height}.png'))
    v=show('Contracts');w.grab().save(str(out/f'contracts-{width}x{height}.png'))
    metrics.append({'size':[width,height],'cards':[{'kind':c.property('kind'),'height':c.height(),'products_height':c.findChild(QFrame,'contractRequirements').height(),'rewards_height':c.findChild(QFrame,'contractRewards').height()} for c in v.findChildren(QFrame,'contractCard')]})
    r=show('Research');domains=research_domains();domain=max(set(domains.values()),key=lambda d:list(domains.values()).count(d));tid='industry.'+domain
    popup=ResearchHover(w);popup.display(r.navigation_buttons[tid],w._session_state,tid);QTest.qWait(40)
    w.grab().save(str(out/f'research-icons-{width}x{height}.png'));popup.grab().save(str(out/f'research-panel-{width}x{height}.png'));popup.close();popup.deleteLater()
v=show('Contracts')
for card in v.findChildren(QFrame,'contractCard'):
    used=set()
    for combo in card.findChildren(QComboBox,'contractProductSelect'):
        i=next(i for i in range(1,combo.count()) if combo.itemData(i) not in used);used.add(combo.itemData(i));combo.setCurrentIndex(i)
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(40);w.grab().save(str(out/f'contracts-selected-{width}x{height}.png'))
for kind,controls in tuple(v._selection_controls.items()):controls['accept'].click()
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(40);w.grab().save(str(out/f'contracts-active-{width}x{height}.png'))
w.close();(out/'layout-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8');print(out)
