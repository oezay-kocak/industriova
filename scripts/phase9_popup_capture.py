"""Capture actual separate Qt Popup surfaces; MainWindow.grab excludes them."""
from pathlib import Path
import os,json,hashlib
root=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase9/popups/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QEvent
from production_zero.ui.main_window import MainWindow
from production_zero.ui.event_feed import EventFeedWidget,FeedEvent
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
app=QApplication([]);_load_qa_fonts();rows=[]
for width,height in ((1366,768),(1600,980),(1920,1080)):
 w=MainWindow(development_mode=False)
 for timer in w.findChildren(QTimer):timer.stop()
 w.resize(width,height);w.show();app.processEvents()
 feed=w.findChild(EventFeedWidget)
 def grab(name,panel):
  app.processEvents();p=out/f'{name}-{width}x{height}.png';pix=panel.grab();assert pix.save(str(p))
  rows.append(dict(file=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),window=[width,height],logical=[panel.width(),panel.height()],pixels=[pix.width(),pix.height()],scale=scale,global_position=[panel.x(),panel.y()],method='Actual separate Qt Popup.grab; no compositing or native desktop capture.'))
 feed.push(FeedEvent('contract','CONSORTIUM FREIGHT DELIVERY COMPLETED',12345));feed.flush_pending();feed._show_history();grab('history-popup',feed._history_panel);feed.close_panels()
 w._session_state.communications.messages.clear();feed._show_inbox();grab('inbox-empty-popup',feed._inbox_panel);feed.close_panels()
 w._session_state.communications.add_unlocks(['resource.iron_ore','production.steel']);feed._show_inbox();grab('inbox-filled-popup',feed._inbox_panel);feed.close_panels()
 w.close();app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
(out/'captures.json').write_text(json.dumps(dict(captures=rows),indent=2),encoding='utf8')
print('ACTUAL POPUPS',len(rows),scale,flush=True)
