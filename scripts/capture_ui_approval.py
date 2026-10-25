"""Headless actual Qt captures of the final dev6 UI changes."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget,QFrame
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2,FactoryV2LockedLine
from production_zero.tools.ui_contact_sheet import _load_qa_fonts

app=QApplication([]);_load_qa_fonts();w=MainWindow(development_mode=False,charts_enabled=False);w.show();QTest.qWait(60)
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
tabs=w.findChild(QTabWidget,'mainTabs');out=Path(sys.argv[1])/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True);metrics=[]
for width,height in [(1366,768),(1600,980),(1920,1080)]:
    w.resize(width,height);QTest.qWait(45)
    for name in ('Resources','Factory','Energy','Freight','Contracts'):
        tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name));QTest.qWait(80);v=tabs.currentWidget()
        if isinstance(v,ProductionBoardViewV2):v._factory_v2_scroll.verticalScrollBar().setValue(0);QTest.qWait(20)
        w.grab().save(str(out/f'{name.lower()}-{width}x{height}.png'))
        if isinstance(v,ProductionBoardViewV2):
            v._factory_v2_scroll.verticalScrollBar().setValue(v._factory_v2_scroll.verticalScrollBar().maximum());QTest.qWait(20)
            w.grab().save(str(out/f'{name.lower()}-expansion-{width}x{height}.png'))
            metrics.append({'board':name,'size':[width,height],'visible_expansions':len(v.findChildren(FactoryV2LockedLine))})
w.close();(out/'layout-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8');print(out)
