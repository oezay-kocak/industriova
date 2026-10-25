"""Fresh funds, visible controls, real timer: picker stays open across unlock."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_ui_interaction_recovery import board,click,install
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.factory_view import ProductionSelectionTile
from production_zero.ui.game_ui.widgets import GameButton
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app=QApplication([]);w=MainWindow(development_mode=False);w.resize(1366,768);w.show();QTest.qWait(50)
out=Path('artifacts/industriova-ui-repair');results=[]
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
r=board(w,'Resources');rid=install(w,r);click(w,r._slot_widgets[0]);click(w,next(c for c in r.findChildren(GameButton) if c._text=='Recipe'))
click(w,next(c for c in r.findChildren(ProductionSelectionTile) if c.property('productionId')=='resource.iron_ore'))
e=board(w,'Energy');eid=install(w,e)
f=board(w,'Factory');cid=install(w,f);click(w,f._slot_widgets[0]);click(w,next(c for c in f.findChildren(GameButton) if c._text=='Recipe'))
initial=[c.property('productionId') for c in f.findChildren(ProductionSelectionTile) if c.isEnabled()]
assert 'recipe.processor.iron' not in initial
host=f._production_selection_grid_host;f.resume_simulation()
for seconds in range(1,86):
    QTest.qWait(1000)
    iron=next((c for c in f.findChildren(ProductionSelectionTile) if c.property('productionId')=='recipe.processor.iron' and c.isEnabled()),None)
    if iron is not None:
        results.append({'step':'open picker receives natural Iron unlock','seconds':seconds,'cash':f._state.cash.amount,'lifetime':f._state.production_progress.lifetime_produced.copy(),'same_host':f._production_selection_grid_host is host})
        click(w,iron);break
else:raise AssertionError('Iron did not appear in the open picker')
before=f._state.resources['iron'].amount;QTest.qWait(12000);f.pause_simulation()
assert f._state.resources['iron'].amount>before
assert f._state.cash.amount==1250
results.append({'step':'real Factory production','iron_delta':f._state.resources['iron'].amount-before,'recipe':f._state.machine_production[cid].selected_production_id,'starter_resource':rid,'starter_energy':eid})
w.grab().save(str(out/'natural-unlock-production.png'));w.close()
(out/'natural-unlock.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results))
