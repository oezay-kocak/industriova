"""Isolated supplemental native UI fixture; never uses personal AppData saves."""
import os,json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows'
out=Path('artifacts/ui-polish/native');out.mkdir(parents=True,exist_ok=True)
os.environ['LOCALAPPDATA']=str((out/'localappdata').resolve())
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.core.commands import InstallCardInHall
from production_zero.persistence.sqlite_store import SQLiteSaveStore,serialize_game_state
app=QApplication([])
w=MainWindow(development_mode=False,save_store=SQLiteSaveStore(out/'company.sqlite'));w.resize(1366,768)
w.setWindowTitle('Industriova – UI Polish Verification')
boards={b._board_config.board_kind:b for b in w.findChildren(ProductionBoardViewV2)}
for b in boards.values():b.pause_simulation()
if len(w._session_state.cards)==8 and not w._session_state.installed_card_ids():
    w._session_state.cash.amount=20000
    for kind,uid,cid,index in [('resources','site-1','test-drill-common-001',0),('factory','hall-1','test-furnace-common-001',0),('factory','hall-1','test-blast-furnace-common-001',1),('energy','plant-1','test-solar-common-001',0)]:
        boards[kind]._command_bus.dispatch(InstallCardInHall(uid,index,cid,kind))
    for b in boards.values():b.refresh_view()
w.show()
def record():
    w._global_header.refresh()
    p=serialize_game_state(w._session_state)
    p.pop('history',None)
    (out/'observed-state.json').write_text(json.dumps(p),encoding='utf-8')
timer=QTimer();timer.timeout.connect(record);timer.start(500)
record();raise SystemExit(app.exec())
