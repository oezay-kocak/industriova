"""Repeated Qt-window clicks, normal funds, no installation commands."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_ui_interaction_recovery import board,click,install
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2,FactoryV2LockedLine
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app=QApplication([]);results=[]
for size in ((1366,768),(1600,980),(1920,1080)):
    for repetition in range(3):
        w=MainWindow(development_mode=False);w.resize(*size);w.show();QTest.qWait(30)
        for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
        for name in ('Resources','Factory','Energy'):
            b=board(w,name);cid=install(w,b)
            results.append({'size':size,'repeat':repetition,'step':name+' Build Slot → install','card':cid,'passed':True})
        b=board(w,'Factory');line=b.findChild(FactoryV2LockedLine)
        b._factory_v2_scroll.ensureWidgetVisible(line._unlock_button,0,0);QTest.qWait(60)
        cash=b._state.cash.amount;click(w,line._unlock_button)
        assert b._units[b._selected_hall_id].production_lines[2].unlocked
        assert b._state.cash.amount==cash-750
        results.append({'size':size,'repeat':repetition,'step':'Unlock Line 3','passed':True})
        w.close();w.deleteLater();QTest.qWait(20)
        w=MainWindow(development_mode=False);w.resize(*size);w.show();QTest.qWait(30)
        b=board(w,'Factory');b.pause_simulation();click(w,b._build_hall_button)
        assert len(b._units)==2 and b._state.cash.amount==250
        results.append({'size':size,'repeat':repetition,'step':'Build Hall','passed':True})
        w.close();w.deleteLater();QTest.qWait(20)
out=Path('artifacts/industriova-ui-repair')/('repeated-dpi'+os.environ.get('QT_SCALE_FACTOR','1')+'.json')
out.write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps({'paths':len(results),'passed':sum(r['passed'] for r in results),'scale':os.environ.get('QT_SCALE_FACTOR','1')}))
