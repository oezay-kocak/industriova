"""Refresh the six retype-dialog captures after its local contrast correction."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];scale=int(os.environ.get('QT_SCALE_FACTOR','1'));OUT=ROOT/f'artifacts/phase7/screenshots/dpi{scale}'
sys.path.insert(0,str(ROOT/'src'));os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'retype-appdata'),APPDATA=str(OUT/'retype-appdata'))
from PySide6.QtWidgets import QApplication,QComboBox,QTabWidget
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtGui import QFontDatabase
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2
app=QApplication([])
for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','arial.ttf','agencyr.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
w=MainWindow(development_mode=False)
for timer in w.findChildren(QTimer):timer.stop()
b=w.findChild(ResourcesViewV2);w.findChild(QTabWidget,'mainTabs').setCurrentWidget(b)
rows=json.loads((OUT/'captures.json').read_text(encoding='utf8'))
for size in ((1366,768),(1600,980),(1920,1080)):
    w.resize(*size);w.show();app.processEvents()
    def capture():
        dialog=QApplication.activeModalWidget();combo=dialog.findChild(QComboBox,'resourceSiteType');combo.setCurrentIndex(combo.findData('machine.agriculture'));app.processEvents()
        pix=dialog.grab();path=OUT/f'resource-paid-type-change-{size[0]}x{size[1]}.png';assert pix.save(str(path))
        row=next(r for r in rows if r['file']==path.relative_to(ROOT).as_posix());row.update(logical_size=[dialog.width(),dialog.height()],pixels=[pix.width(),pix.height()])
        dialog.reject()
    QTimer.singleShot(80,capture);b._rename_building()
(OUT/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf8');w.close();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
print(json.dumps(dict(scale=scale,refreshed=3)),flush=True)
