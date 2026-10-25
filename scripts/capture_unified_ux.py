"""Actual Qt renders at supported logical sizes; test fixtures are explicitly isolated."""
import os,sys,json,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget,QDialog
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.interaction_polish import BuildingChoiceDialog
from production_zero.core.commands import InstallCardInHall,InstallFreightCard
from production_zero.core.machine_operations import SITE_TYPES
from production_zero.core.freight import FREIGHT_FACILITY_TYPES,freight_facility_build_cost
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
app=QApplication([]);_load_qa_fonts()
out=Path(sys.argv[1])/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True)
w=MainWindow(development_mode=False,charts_enabled=False);w.show();QTest.qWait(60)
tabs=w.findChild(QTabWidget,'mainTabs');boards={b._board_config.board_kind:b for b in w.findChildren(ProductionBoardViewV2)}
for b in boards.values():b.pause_simulation()
state=w._session_state;state.cash.amount=20000
bus=boards['factory']._command_bus
for kind,uid,cid in [('resources','site-1','test-drill-common-001'),('factory','hall-1','test-furnace-common-001'),('energy','plant-1','test-solar-common-001')]:
    bus.dispatch(InstallCardInHall(uid,0,cid,kind));boards[kind].refresh_view()
freight=w.findChild(FreightView)
for i,cid in enumerate(('starter-truck-common-001','starter-truck-common-002')):bus.dispatch(InstallFreightCard('garage-1',i,cid,freight._definitions))
freight.refresh();metrics=[]
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(50)
    for name in ('Resources','Factory','Energy','Freight','Contracts'):
        tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name));QTest.qWait(45)
        current=tabs.currentWidget()
        if name in ('Resources','Factory','Energy'):
            scroll=current._factory_v2_scroll;scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());QTest.qWait(20)
        w.grab().save(str(out/f'{name.lower()}-{width}x{height}.png'))
    tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)=='Factory'));QTest.qWait(20)
    b=boards['factory'];start=time.perf_counter()
    for _ in range(50):b.refresh_runtime()
    metrics.append({'size':[width,height],'runtime_refresh_ms':(time.perf_counter()-start)*20})
    if width!=1366:continue
    def capture_actions():
        d=QApplication.activeModalWidget()
        if d is not None:d.grab().save(str(out/'machine-actions.png'));d.reject()
    QTimer.singleShot(50,capture_actions);b._card_actions('test-furnace-common-001')
    for title,choices,filename in [('BUILD SITE',[(k,n,b._definitions[k],1000) for k,n in SITE_TYPES.items()],'build-site.png'),('BUILD FACILITY',[(k,FREIGHT_FACILITY_TYPES[k],freight._definitions[did],freight_facility_build_cost(state.freight,k)) for k,did in [('garage_depot','freight.truck'),('rail_station','freight.train'),('airport','freight.aircraft'),('harbor','freight.ship')]],'build-facility.png')]:
        d=BuildingChoiceDialog(w,title,choices,state.cash.amount);d.show();QTest.qWait(30);d.grab().save(str(out/filename))
        next(iter(d.options.values())).click();QTest.qWait(20);d.grab().save(str(out/filename.replace('.png','-selected.png')));d.close();d.deleteLater()
    try:
        from production_zero.ui.research_hover import ResearchHover
    except ImportError:continue
    tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)=='Research'));QTest.qWait(30)
    from production_zero.core.research import research_domains
    domains=research_domains();domain=max(set(domains.values()),key=lambda x:list(domains.values()).count(x));tid='industry.'+domain
    r=tabs.currentWidget();popup=ResearchHover(w);popup.display(r.navigation_buttons[tid],state,tid);QTest.qWait(35)
    w.grab().save(str(out/'research-largest-hover.png'));popup.grab().save(str(out/'research-hover-panel.png'));popup.close();popup.deleteLater()
w.close();(out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8');print(out)
