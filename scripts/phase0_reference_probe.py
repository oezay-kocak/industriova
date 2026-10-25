"""Visually verified reference captures and visible production-ranking updates."""
import json,time,statistics
from phase0_benchmark import D,OUT,state,register_fonts
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import QEvent,QTimer
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.services.local import LocalLeaderboardService
from production_zero.core.commands import CommandBus
class App(QApplication):
    paints=0
    def notify(self,receiver,event):
        if event.type()==QEvent.Type.Paint:self.paints+=1
        return super().notify(receiver,event)
app=App([]);register_fonts(app)
def drain():
    for _ in range(5):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
s=state();b=FactoryViewV2(s,CommandBus(s),D);b.pause_simulation();b.resize(1366,768);b.show();drain()
b._open_production_guide();drain();b.grab().save(str(OUT/'production-guide.png'))
b._open_unlock_tree();drain();b.grab().save(str(OUT/'unlock-tree.png'))
u=b._cached_unlock_tree_panel
from phase0_benchmark import memory
before=memory()
for _ in range(10):u.refresh_state();drain()
after=memory();baseline_nodes=len(u._node_items);baseline_items=len(u.canvas.scene().items())
b.close();b.deleteLater();drain()
lb=LeaderboardView(LocalLeaderboardService(s));lb.resize(1366,768);lb.show();lb._set_ranking_index(2);drain()
rows=[];previous=lb._production_own_layout.itemAt(0).widget()
for i in range(10):
    s.production_progress.lifetime_produced['iron_ore']=i+1;app.paints=0;t=time.perf_counter();lb.refresh()
    callback=(time.perf_counter()-t)*1000;new=lb._production_own_layout.itemAt(0).widget();drain()
    rows.append({'callback_ms':callback,'including_events_ms':(time.perf_counter()-t)*1000,'replaced':new is not previous,'paint_events':app.paints})
    previous=new
lb.grab().save(str(OUT/'leaderboard-production.png'))
(OUT/'reference-probe.json').write_text(json.dumps({'ranking_tab_visible':lb._tabs.currentIndex()==2,
     'changed_production_refresh':rows,'unlock_ten_refreshes':{'working_set_before':before,'working_set_after':after,
       'nodes':baseline_nodes,'scene_items':baseline_items}},indent=2),encoding='utf8')
lb.close();print('Reference captures and visible ranking probe complete')
