"""Current boards and honest side-by-side references at each supported scale."""
import os,json,shutil
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget,QWidget
from production_zero.ui.main_window import MainWindow
from production_zero.ui.game_ui.widgets import GameButton
from capture_industriova_release import seed
app=QApplication([])
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
_load_qa_fonts()
scale=os.environ.get('QT_SCALE_FACTOR','1');out=Path('artifacts/industriova-ui-repair/visuals')/('dpi'+scale);out.mkdir(parents=True,exist_ok=True)
measurements=[]
for size in ((1366,768),(1600,980),(1920,1080)):
    w=MainWindow(development_mode=False);w.resize(*size);w.show();app.processEvents();seed(w)
    tabs=w.findChild(QTabWidget,'mainTabs')
    for name in ('Resources','Factory','Energy','Freight'):
        tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name))
        for _ in range(10):app.processEvents()
        w.grab().save(str(out/f'{name}_{size[0]}x{size[1]}.png'))
        toolbar=tabs.currentWidget().findChild(QWidget,'productionSelectionToolbar')
        if toolbar:
            buttons=toolbar.findChildren(GameButton)
            measurements.append({'size':size,'board':name,'scale':scale,'toolbar_height':toolbar.height(),'buttons':[(b._text,b.x(),b.y(),b.width(),b.height()) for b in buttons]})
    w.close();w.deleteLater();app.processEvents()
(out/'measurements.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
if scale=='1':
    for size in ((1366,768),(1600,980),(1920,1080)):
        label=f'{size[0]}x{size[1]}'
        shutil.copyfile(f'artifacts/human_review_followup/factory_reference_{label}.png',out/f'accepted_Factory_{label}.png')
        shutil.copyfile(f'artifacts/industriova-stabilization/visuals/Factory_{label}.png',out/f'before_Factory_{label}.png')
    rows=''.join(f'<h2>{x} × {y}</h2><div><figure><img src="dpi1/accepted_Factory_{x}x{y}.png"><figcaption>Akzeptierte Referenz</figcaption></figure><figure><img src="dpi1/before_Factory_{x}x{y}.png"><figcaption>dev1 vor Reparatur</figcaption></figure><figure><img src="dpi1/Factory_{x}x{y}.png"><figcaption>Reparatur 100%</figcaption></figure><figure><img src="dpi2/Factory_{x}x{y}.png"><figcaption>Reparatur 200%</figcaption></figure></div>' for x,y in ((1366,768),(1600,980),(1920,1080)))
    (out.parent/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>UI-Vergleich Industriova</title><style>body{background:#111;color:#eee;font:16px sans-serif}div{display:grid;grid-template-columns:1fr 1fr}figure{margin:8px}img{width:100%}</style><h1>Aktionsleiste – echte Screenshots</h1><p>Referenz und Reparatur verwenden unterschiedliche Spielzustände. Verglichen werden Anordnung, Höhe und sichtbarer Linienraum.</p>'+rows,encoding='utf-8')
print(json.dumps({'screenshots':12,'scale':scale,'destination':str(out)}))
