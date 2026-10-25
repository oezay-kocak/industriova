"""Actual MainWindow boards at three sizes and both Qt scales, isolated saves."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts/phase4/screenshots'/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True)
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
    captures.append(dict(file=str(path.relative_to(ROOT)),width=pix.width(),height=pix.height(),
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
    for b in boards:
        did={'factory':'machine.processor','resources':'machine.extractor','energy':'energy.solar_array'}[b._board_config.board_kind]
        unit=b._units[b._selected_hall_id]
        for n,line in enumerate(unit.production_lines):
            line.unlocked=True;line.slot_indexes=list(range(n*unit.max_slots_per_line,(n+1)*unit.max_slots_per_line))
        unit.slot_count=sum(len(line.slot_indexes) for line in unit.production_lines if line.unlocked)
        for i,slot in enumerate(unit.slots):
            cid=f'visual-{b._board_config.board_kind}-{i}';add(cid,did,i);slot.card_id=cid if i%7!=6 else None
        tabs.setCurrentWidget(b);b.refresh_view();b._restore_factory_scroll((0,0))
        b._selected_machines={slot.card_id for slot in unit.slots[:2]};b._update_selection_visuals();QTest.qWait(100);drain()
        b._machine_feedback.highlight(b._slot_widgets[2],'swap');capture(b._board_config.board_kind+'-selected-swap',size)
        source=b._slot_widgets[0];pix=drag_pixmap(source,2);assert pix.save(str(out/f'{b._board_config.board_kind}-drag-preview-{size[0]}.png'))
        b._machine_feedback.highlight();bar=b._factory_v2_scroll.verticalScrollBar();bar.setValue(bar.maximum());capture(b._board_config.board_kind+'-last-line',size)
    tabs.setCurrentWidget(f)
    for did,kind in [('freight.truck','garage_depot'),('freight.train','rail_station'),('freight.aircraft','airport'),('freight.ship','harbor')]:
        unit=FreightFacility('visual-'+kind,'International '+kind.replace('_',' ').title()+' 01',kind,slot_count=16)
        s.freight.facilities[unit.facility_id]=unit;f._selected_facility_id=unit.facility_id
        for i,slot in enumerate(unit.slots):
            cid=f'visual-{kind}-{i}';add(cid,did,i);slot.card_id=cid if i%6!=5 else None
        f.refresh();f._restore_slot_scroll((0,0))
        f._selected_vehicles={unit.slots[i].card_id for i in (0,1)};f._slot_interaction.update_selection();QTest.qWait(100);drain()
        cards=f._slot_interaction._cards();source=next(w for w in cards if w._freight_destination[1]==0);target=next(w for w in cards if w._freight_destination[1]==2)
        before=serialize_game_state(s);static_ghost(source,target);capture(kind+'-group-ghost',size);assert serialize_game_state(s)==before
        f._slot_interaction._finish_pointer_drag()
        if kind=='garage_depot':
            s.freight.outbound_shipments['visual-busy']=OutboundFreightShipment('visual-busy','market',freight_card_id=unit.slots[2].card_id,quantity=20,remaining_seconds=40)
            static_ghost(source,target);capture('freight-busy-invalid',size);f._slot_interaction._finish_pointer_drag();s.freight.outbound_shipments.clear()
        bar=f._slots_scroll.verticalScrollBar();bar.setValue(bar.maximum());capture(kind+'-last-line',size)
window.close();drain();(out/'captures.json').write_text(json.dumps(captures,indent=2),encoding='utf8')
print(json.dumps(dict(captures=len(captures),out=str(out))),flush=True)
