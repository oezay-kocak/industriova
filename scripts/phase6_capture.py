"""P6 actual MainWindow captures; synthetic company, no personal saves."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=ROOT/f'artifacts/phase6/screenshots/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from dataclasses import replace
from PySide6.QtCore import QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication,QTabWidget
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.freight import FreightFacility
from production_zero.core.freight_statistics import FreightDeliveryStatistics
app=QApplication([])
for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','arial.ttf','agencyr.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
window=MainWindow(development_mode=False)
for board in window.findChildren(ProductionBoardViewV2):board.pause_simulation()
f=window.findChild(FreightView);s=f._state;d=f._definitions;tabs=window.findChild(QTabWidget,'mainTabs');rows=[]
def drain():
    for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def capture(name,size):
    drain();pix=window.grab();path=out/f'{name}-{size[0]}x{size[1]}.png';assert pix.save(str(path))
    assert (window.width(),window.height())==size
    stage=f._facility_stage
    rows.append(dict(file=path.relative_to(ROOT).as_posix(),width=pix.width(),height=pix.height(),logical_width=window.width(),logical_height=window.height(),scale=scale,
        facility=f._selected_facility_id,header_geometry=[stage.x(),stage.y(),stage.width(),stage.height()],
        values={key:stage.property('delivery'+key) for key in ('Sell','Contract','Consortium','Total')},
        tooltip=f._hover_popup._value_labels['ACTUAL THROUGHPUT'].text() if f._hover_popup and f._hover_popup.isVisible() else None))
for size in ((1366,768),(1600,980),(1920,1080)):
    window.resize(*size);window.show();tabs.setCurrentWidget(f);drain()
    for did,kind in [('freight.truck','garage_depot'),('freight.train','rail_station'),('freight.aircraft','airport'),('freight.ship','harbor')]:
        s.freight.facilities.clear();s.freight.outbound_shipments.clear();s.freight.assignments.clear()
        unit=FreightFacility('p6-'+kind,kind.replace('_',' ').title()+' Long Distance Cargo Terminal 01',kind,slot_count=16)
        s.freight.facilities[unit.facility_id]=unit
        for i,slot in enumerate(unit.slots):
            cid=f'p6-{kind}-{i}';s.cards[cid]=create_card_instance(cid,did,d[did].card_kind,Rarity.COMMON);slot.card_id=cid
        f._selected_facility_id=unit.facility_id;s.freight.delivery_statistics=FreightDeliveryStatistics();f.refresh();drain()
        capture(kind+'-empty-warmup',size)
        stats=s.freight.delivery_statistics;stats.advance(10);stats.record(unit.slots[0].card_id,unit.facility_id,sell=.002)
        f.refresh_runtime();source=f._runtime_widgets[unit.slots[0].card_id]['card'];f._show_freight_hover(unit.slots[0].card_id,source)
        capture(kind+'-low-warmup-mk1-tooltip',size);f._hide_freight_hover()
        stats.advance(50)
        stats.record(unit.slots[0].card_id,unit.facility_id,sell=12500,contract=650,consortium=320)
        stats.record(unit.slots[1].card_id,unit.facility_id,sell=1.25e9,contract=1.25e6,consortium=320000)
        cid=unit.slots[0].card_id;s.cards[cid]=replace(s.cards[cid],mk_level=50,rarity=Rarity.LEGENDARY,output_bonus_percent=30,paused=True)
        f.refresh_runtime();f._show_freight_hover(cid,source)
        capture(kind+'-high-mixed-paused-mk50-tooltip',size);f._hide_freight_hover()
        stats.advance(60);f.refresh_runtime();capture(kind+'-idle-zero',size)
    s.freight.facilities.clear();s.freight.delivery_statistics=FreightDeliveryStatistics();s.freight.delivery_statistics.advance(60)
    for n in range(20):
        unit=FreightFacility(f'garage-{n+1}',f'Garage {n+1:02d}',slot_count=8);s.freight.facilities[unit.facility_id]=unit
        for i,slot in enumerate(unit.slots):
            cid=f'p6-large-{n}-{i}';s.cards[cid]=create_card_instance(cid,'freight.truck',d['freight.truck'].card_kind,Rarity.COMMON);slot.card_id=cid
            s.freight.delivery_statistics.record(cid,unit.facility_id,sell=(n+1)*100,contract=50,consortium=25)
    f._selected_facility_id='garage-20';f.refresh();capture('20-facilities-isolated-header',size)
(out/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
window.close();drain();print(json.dumps({'captures':len(rows),'scale':scale}),flush=True)
