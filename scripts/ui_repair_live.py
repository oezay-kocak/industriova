"""Isolated regular game window for native interaction verification."""
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "windows")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QObject,QEvent
from production_zero.ui.main_window import MainWindow
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.persistence.dev_save_store import serialize_game_state
import json

app=QApplication([])
destination=Path("artifacts/industriova-ui-repair/live")
destination.mkdir(parents=True,exist_ok=True)
window=MainWindow(save_store=SQLiteSaveStore(destination/'game.sqlite'),development_mode=False)
window.setWindowTitle("Industriova – UI Repair Verification")
window.resize(1366,768);window.show()
events=[]
class InputTrace(QObject):
    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseMove,QEvent.Type.MouseButtonRelease,QEvent.Type.DragEnter,QEvent.Type.DragMove,QEvent.Type.Drop):
            if hasattr(watched,'objectName'):
                name=watched.objectName()
                if name in ('freightSlotCard','factoryV2BuildSlot','factoryV2MachineCard'):
                    events.append({'type':event.type().name,'widget':name,'slot':watched.property('slotIndex'),'buttons':event.buttons().value if hasattr(event,'buttons') else None,'spontaneous':event.spontaneous()})
                    del events[:-400]
        return False
trace=InputTrace();app.installEventFilter(trace)
def record():
    (destination/'observed-state.json').write_text(json.dumps(serialize_game_state(window._session_state)),encoding='utf-8')
    tabs=window.findChild(__import__('PySide6.QtWidgets',fromlist=['QTabWidget']).QTabWidget,'mainTabs')
    view=tabs.currentWidget()
    (destination/'interaction.json').write_text(json.dumps({'events':events,'current':tabs.tabText(tabs.currentIndex()),'selected_vehicle':getattr(view,'_selected_vehicle_id',None)}),encoding='utf-8')
timer=QTimer();timer.timeout.connect(record);timer.start(1000)
raise SystemExit(app.exec())
