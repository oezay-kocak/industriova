"""Precise fractional-price examples in the real Production Guide."""
from pathlib import Path
import os,sys,json,hashlib
root=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase10/price-screenshots/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'src'));os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
from PySide6.QtWidgets import QApplication,QTabWidget,QLineEdit,QLabel
from PySide6.QtCore import QTimer,QEvent
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.factory_view import ProductionGuideTile
from production_zero.ui.resource_prices import base_price_text
app=QApplication([]);_load_qa_fonts();rows=[]
for width,height in ((1366,768),(1600,980),(1920,1080)):
 w=MainWindow(development_mode=False)
 for timer in w.findChildren(QTimer):timer.stop()
 view=next(v for v in w.findChildren(ProductionBoardViewV2) if v._board_config.board_kind=='factory')
 w.resize(width,height);w.show();w.findChild(QTabWidget,'mainTabs').setCurrentWidget(view);view._open_production_guide();app.processEvents()
 search=view.findChild(QLineEdit,'productionGuideSearchInput')
 for rid in ('ai_accelerator','ai_server','autonomous_control_system','lumber'):
  search.setText(rid)
  for _ in range(3):app.processEvents()
  tile=next(t for t in view.findChildren(ProductionGuideTile) if t.isVisible() and t.property('resourceId')==rid)
  label=tile.findChild(QLabel,'productionGuideTileCategory')
  assert label.text()==base_price_text(rid,compact=True)
  assert label.fontMetrics().horizontalAdvance(label.text())<=label.width(),(rid,label.text(),label.width())
  path=out/f'{rid}-{width}x{height}.png';pix=w.grab();assert pix.save(str(path))
  rows.append(dict(file=path.relative_to(root).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),price=label.text(),logical=[w.width(),w.height()],pixels=[pix.width(),pix.height()],scale=scale))
 w.close();app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
(out/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('VERIFIED',len(rows),'fractional price screenshots',scale,flush=True)
