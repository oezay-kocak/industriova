"""Render actual Qt widgets for visual comparison at three sizes and two DPIs."""
import os,json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.interaction_polish import BuildingChoiceDialog
from production_zero.ui.game_ui import GameButton
from production_zero.core.machine_operations import SITE_TYPES
from production_zero.core.freight import FREIGHT_FACILITY_TYPES,freight_facility_build_cost
from production_zero.core.commands import InstallCardInHall,InstallFreightCard
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
app=QApplication([]);_load_qa_fonts()
out=Path('artifacts/ui-polish/visuals')/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True)
w=MainWindow(development_mode=False,charts_enabled=False);w.show()
tabs=w.findChild(QTabWidget,'mainTabs')
boards={b._board_config.board_kind:b for b in w.findChildren(ProductionBoardViewV2)}
for b in boards.values():b.pause_simulation()
state=w._session_state;state.cash.amount=20000 # explicit supplemental visual fixture
bus=boards['factory']._command_bus
for board,uid,cid in [('resources','site-1','test-drill-common-001'),('factory','hall-1','test-furnace-common-001'),('energy','plant-1','test-solar-common-001')]:
    bus.dispatch(InstallCardInHall(uid,0,cid,board));boards[board].refresh_view()
f=w.findChild(FreightView);bus.dispatch(InstallFreightCard('garage-1',0,'starter-truck-common-001',f._definitions));f.refresh()
measurements=[]
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(70)
    for name in ('Resources','Factory','Energy','Freight','Contracts'):
        tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name));QTest.qWait(50)
        w.grab().save(str(out/f'{name.lower()}-{width}x{height}.png'))
    if width!=1366:continue
    tabs.setCurrentIndex(0);QTest.qWait(30)
    w._global_resources.toggle();QTest.qWait(40);w.grab().save(str(out/'resources-overlay.png'));w._global_resources.grab().save(str(out/'overlay-panel.png'));w._global_resources.hide()
    w.findChild(GameButton,'globalResourcesButton').grab().save(str(out/'resources-button.png'))
    b=boards['resources'];card=b._slot_widgets[0];card.grab().save(str(out/'upgrade-card.png'))
    from production_zero.core.machine_operations import resale_value
    value=resale_value(state.cards['test-drill-common-001'],b._definitions['machine.extractor'])
    d=IndustrialDialog('Maschinen verkaufen',f'Extractor MK1 · common · ${value:,.2f}\n\n1 Maschine wird entfernt.\nErlös: ${value:,.2f}',w,accept_text='JA – Verkaufen')
    d.show();QTest.qWait(40);d.grab().save(str(out/'machine-sale.png'));d.close()
    d=IndustrialDialog('MACHINE PURCHASE','Solar Array MK1 · common\n5 compatible free slots. Machines are installed automatically.',w,accept_text='JA – Kaufen',quantity=5,price=180)
    d.quantity.setValue(5);d.show();QTest.qWait(40);d.grab().save(str(out/'machine-purchase.png'));d.close()
    for title,choices,file in [('BUILD SITE',[(k,n,b._definitions[k],1000) for k,n in SITE_TYPES.items()],'build-site.png'),('BUILD FACILITY',[(k,FREIGHT_FACILITY_TYPES[k],f._definitions[did],freight_facility_build_cost(state.freight,k)) for k,did in [('garage_depot','freight.truck'),('rail_station','freight.train'),('airport','freight.aircraft'),('harbor','freight.ship')]],'build-facility.png')]:
        d=BuildingChoiceDialog(w,title,choices,state.cash.amount);d.show();QTest.qWait(40);d.grab().save(str(out/file))
        measurements.append({'dialog':title,'width':d.width(),'options':[{'type':k,'rect':(v.mapTo(d,v.rect().topLeft()).x(),v.mapTo(d,v.rect().topLeft()).y(),v.width(),v.height())} for k,v in d.options.items()]})
        QTest.mouseClick(next(iter(d.options.values())),__import__('PySide6.QtCore',fromlist=['Qt']).Qt.MouseButton.LeftButton);QTest.qWait(20)
        d.grab().save(str(out/file.replace('.png','-selected.png')));d.close()
w.close();(out/'measurements.json').write_text(json.dumps(measurements,indent=2));print(out)
