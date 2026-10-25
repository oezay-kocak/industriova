"""Populated real Global Resources price rows, separately from empty active flow."""
from pathlib import Path
import os,sys,json,hashlib
root=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase10/resource-screenshots/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'src'));os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
app=QApplication([]);_load_qa_fonts();rows=[]
for width,height in ((1366,768),(1600,980),(1920,1080)):
 w=MainWindow(development_mode=False)
 for timer in w.findChildren(QTimer):timer.stop()
 for rid in w._global_header._resource_definitions:w._session_state.ensure_resource(rid).amount=1
 w.resize(width,height);w.show();app.processEvents();w._global_resources.toggle();w._global_resources.drawer._set_inventory_mode(True)
 for _ in range(4):app.processEvents()
 path=out/f'global-resources-prices-{width}x{height}.png';pix=w.grab();assert pix.save(str(path))
 rows.append(dict(file=path.relative_to(root).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),logical=[w.width(),w.height()],pixels=[pix.width(),pix.height()],scale=scale))
 w.close();app.processEvents()
(out/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('CAPTURED',len(rows),'populated resource views',scale,flush=True)
