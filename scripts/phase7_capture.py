"""Real P7 window/dialog screenshots in isolated offscreen companies."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];scale=int(os.environ.get('QT_SCALE_FACTOR','1'))
OUT=ROOT/f'artifacts/phase7/screenshots/dpi{scale}';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
sys.path.insert(0,str(ROOT/'src'))
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication,QTabWidget,QComboBox,QScrollArea
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.freight_upgrade import upgrade_vehicles
from production_zero.core.freight import FreightFacility,FREIGHT_FACILITY_START_SLOTS
from production_zero.core.commands import ExpandFreightFacility,InstallFreightCard
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.supply import common_supply_offers
app=QApplication([])
for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','arial.ttf','agencyr.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
w=MainWindow(development_mode=False);s=w._session_state;s.cash.amount=1e12
for timer in w.findChildren(QTimer):timer.stop()
tabs=w.findChild(QTabWidget,'mainTabs');rows=[];size=None
def drain():
    for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def shot(name,target=None):
    drain();target=target or w;pix=target.grab();path=OUT/f'{name}-{size[0]}x{size[1]}.png';assert pix.save(str(path))
    rows.append(dict(file=path.relative_to(ROOT).as_posix(),logical_size=[target.width(),target.height()],pixels=[pix.width(),pix.height()],scale=scale))
def modal(name,action,prepare=None):
    def capture():
        dialog=QApplication.activeModalWidget();assert dialog
        if prepare:prepare(dialog)
        shot(name,dialog);dialog.reject()
    QTimer.singleShot(80,capture);action()
for size in ((1366,768),(1600,980),(1920,1080)):
    w.resize(*size);w.show();drain()
    for b in w.findChildren(ProductionBoardViewV2):
        tabs.setCurrentWidget(b);b.refresh_view();shot(b._board_config.board_kind+'-start-slot-prices')
        scroll=b.findChild(QScrollArea,'factoryV2Scroll')
        if scroll:scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        shot(b._board_config.board_kind+'-line-price')
    resource=w.findChild(ResourcesViewV2);tabs.setCurrentWidget(resource)
    modal('resource-type-build-quotes',resource._purchase_hall,lambda d:d.options['machine.drilling'].click())
    def choose(dialog):
        combo=dialog.findChild(QComboBox,'resourceSiteType');combo.setCurrentIndex(combo.findData('machine.agriculture'))
    modal('resource-paid-type-change',resource._rename_building,choose)
    f=w.findChild(FreightView);tabs.setCurrentWidget(f)
    modal('freight-four-build-quotes',f._build_facility,lambda d:d.options['harbor'].click())
    for kind,did in [('garage_depot','freight.truck'),('rail_station','freight.train'),('airport','freight.aircraft'),('harbor','freight.ship')]:
        u=FreightFacility('p7-'+kind,kind.replace('_',' ').title()+' 01',kind,slot_count=FREIGHT_FACILITY_START_SLOTS[kind]);s.freight.facilities[u.facility_id]=u
        f._selected_facility_id=u.facility_id;f.refresh();shot(kind+'-slots')
        ExpandFreightFacility(u.facility_id,8,900).apply(s);f.refresh();drain()
        from PySide6.QtWidgets import QWidget
        second=next(c for c in f.findChildren(QWidget,'freightSlotCard') if c.property('slotIndex')==8)
        f._slots_scroll.ensureWidgetVisible(second);shot(kind+'-independent-line-and-locked-gaps')
        cid='p7-'+did;s.cards[cid]=create_card_instance(cid,did,f._definitions[did].card_kind,Rarity.COMMON)
        InstallFreightCard(u.facility_id,0,cid,f._definitions).apply(s);f.refresh()
        if kind=='harbor':
            source=f._runtime_widgets[cid]['card'];f._show_freight_hover(cid,source);shot('ship-new-throughput');f._hide_freight_hover()
            modal('ship-mk-price',lambda:upgrade_vehicles(f,(cid,)))
    supply=w.findChild(SupplyView);tabs.setCurrentWidget(supply)
    offer=next(o for o in common_supply_offers(supply._definitions) if o.definition_id=='freight.ship')
    modal('ship-common-price',lambda:supply._purchase_dialog(offer,'common').exec())
    from production_zero.core.supply import refresh_supply
    refresh_supply(s,supply._definitions)
    daily=next((o for o in s.supply.freight_daily_offers if o.definition_id=='freight.ship'),None)
    if daily:modal('ship-daily-price',lambda:supply._purchase_dialog(daily,'daily_freight').exec())
    # Large but attainable facility quotes use the same existing controls.
    b=next(b for b in w.findChildren(ProductionBoardViewV2) if b._board_config.board_kind=='factory')
    from production_zero.core.state import FactoryHall
    for i in range(2,10):s.halls[f'large-{i}']=FactoryHall(f'large-{i}',f'Hall {i}',3,max_lines=5,start_unlocked_lines=1)
    tabs.setCurrentWidget(b);b.refresh_view();shot('factory-large-building-price')
(OUT/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
w.close();drain();print(json.dumps(dict(scale=scale,captures=len(rows))),flush=True)
