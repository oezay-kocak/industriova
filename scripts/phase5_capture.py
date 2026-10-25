"""Actual MainWindow boards at three sizes and both Qt scales, isolated saves."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts/phase5/screenshots'/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from dataclasses import replace
from PySide6.QtCore import Qt,QPoint,QEvent
from PySide6.QtWidgets import QApplication,QTabWidget,QWidget
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.drag_feedback import drag_pixmap
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.freight import FreightFacility,OutboundFreightShipment
from production_zero.persistence.sqlite_store import serialize_game_state
from phase0_benchmark import register_fonts
os.environ.update(LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
app=QApplication([]);register_fonts(app);window=MainWindow(development_mode=False)
boards=window.findChildren(ProductionBoardViewV2)
for b in boards:b.pause_simulation()
f=window.findChild(FreightView);s=f._state;d=f._definitions;tabs=window.findChild(QTabWidget,'mainTabs')
def drain():
    for _ in range(4):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
captures=[]
def capture(name,size,widget=window):
    drain();pix=widget.grab();path=out/f'{name}-{size[0]}x{size[1]}.png';assert pix.save(str(path))
    captures.append(dict(file=str(path.relative_to(ROOT)),surface='MainWindow' if widget is window else 'QtPopup',width=pix.width(),height=pix.height(),
                         logical_width=widget.width(),logical_height=widget.height(),scale=float(os.environ.get('QT_SCALE_FACTOR','1'))))
def add(cid,did,i):
    s.cards[cid]=replace(create_card_instance(cid,did,d[did].card_kind,tuple(Rarity)[i%5]),mk_level=i%99+1,acquisition_cost=100+i)
def static_ghost(source,target):
    c=f._slot_interaction
    c.ids=tuple(slot.card_id for slot in s.freight.facilities[f._selected_facility_id].slots[:2])
    from production_zero.core.machine_operations import installed_slot_snapshot
    c.origins=installed_slot_snapshot(s,c.ids);c.origin=source;c.start=QPoint(25,70);c.session=s.cards;c.dragging=True
    c.feedback.start(source,c.start,len(c.ids),ghost=True)
    position=target.mapToGlobal(QPoint(70,90));c.feedback.update_position(position);c.feedback.timer.stop();c._hover(position)
for size in ((1366,768),(1600,980),(1920,1080)):
    window.resize(*size);window.show();drain();assert (window.width(),window.height())==size
    tabs.setCurrentWidget(f)
    s.cash.amount=1e15
    s.ensure_resource('steel').amount=1000
    s.ensure_resource('copper_ore').amount=1000
    for did,kind in [('freight.truck','garage_depot'),('freight.train','rail_station'),('freight.aircraft','airport'),('freight.ship','harbor')]:
        unit=FreightFacility('p5-'+kind,'International '+kind.replace('_',' ').title()+' Long Distance Cargo Terminal 01',kind,slot_count=16)
        s.freight.facilities[unit.facility_id]=unit;f._selected_facility_id=unit.facility_id
        for i,slot in enumerate(unit.slots):
            cid=f'p5-{kind}-{i}';add(cid,did,i);slot.card_id=cid if i%6!=5 else None
        s.cards[unit.slots[1].card_id]=replace(s.cards[unit.slots[1].card_id],mk_level=99,paused=True)
        f._reset_assignment_state();f.refresh();f._restore_slot_scroll((0,0));QTest.qWait(100);drain()
        capture(kind+'-mk-rarity-99',size)
        bar=f._slots_scroll.verticalScrollBar();bar.setValue(bar.maximum());capture(kind+'-last-line-mk',size)
        bar.setValue(0);drain()
        source=next(w for w in f._slot_interaction._cards() if w._freight_destination[1]==0)
        cid=unit.slots[0].card_id
        s.freight.outbound_shipments['p5-busy']=OutboundFreightShipment('p5-busy','market',resource_id='steel',freight_card_id=cid,quantity=20,transport_capacity=30,transport_time_seconds=60,remaining_seconds=40)
        f._show_freight_hover(cid,source);capture(kind+'-busy-theoretical-tooltip',size);f._hide_freight_hover()
        s.freight.outbound_shipments.clear()
        if kind!='garage_depot':continue
        from production_zero.core.freight import FreightAssignment
        from production_zero.core.contracts import ActiveContract,ContractOffer
        s.freight.assignments[cid]=FreightAssignment('steel','market')
        second=unit.slots[1].card_id
        s.freight.assignments[second]=FreightAssignment('copper_ore','market')
        f._selected_vehicles={cid,second};f._slot_interaction.update_selection()
        f._open_assignment_view(cid,(cid,second));capture('route-1-cargo-mixed-group',size)
        f._select_assignment_resource('steel');capture('route-2-target-unselected',size)
        f._route_combo.setCurrentIndex(f._route_combo.findData('contract'));capture('route-2-contract-invalid',size)
        offer=ContractOffer('p5-manual','daily','Accepted selected cargo',{'steel':500},0,0,0)
        s.contracts.active['daily']=ActiveContract(offer)
        f._update_assignment_targets();capture('route-2-contract-valid',size)
        f._route_combo.setCurrentIndex(f._route_combo.findData('market'));capture('route-2-sell-confirm',size)
        from production_zero.core.consortium import ConsortiumService,ConsortiumContract,ConsortiumPersonalReward
        membership=s.consortium.membership()
        team=membership[0] if membership else ConsortiumService(s,d).create('P5 Cargo Partners')
        team.contracts['weekly']=ConsortiumContract('p5-team','weekly','active',0,1e20,{'steel':500},ConsortiumPersonalReward(),0)
        f._route_combo.setCurrentIndex(f._route_combo.findData('consortium'));capture('route-2-consortium-valid',size)
        f._route_combo.showPopup();drain();capture('route-target-options-event-disabled',size,app.activePopupWidget());f._route_combo.hidePopup()
        f._close_assignment_view()
window.close();drain();(out/'captures.json').write_text(json.dumps(captures,indent=2),encoding='utf8')
print(json.dumps(dict(captures=len(captures),out=str(out))),flush=True)
