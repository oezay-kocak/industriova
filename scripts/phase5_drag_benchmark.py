"""P0-sized real/synthetic selection surfaces; callbacks, events, paints separated."""
import argparse,os,sys,json,time,statistics,types
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--source',type=Path,default=Path.cwd());args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1] if Path(__file__).parent.name=='scripts' else Path.cwd()
out=ROOT/'artifacts/phase5'/args.stage/'drag';out.mkdir(parents=True,exist_ok=True)
source=args.source.resolve();sys.path[:0]=[str(source/'src'),str(source/'scripts')]
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
path=source/'scripts/phase0_benchmark.py';m=types.ModuleType('phase0_benchmark');m.__file__=str(path)
sys.modules[m.__name__]=m
exec(compile(path.read_text(encoding='utf8').replace("OUT = ROOT / 'artifacts/phase0'",f'OUT = Path({str(out)!r})'),str(path),'exec'),m.__dict__)
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import QPoint,QPointF,Qt,QEvent
from PySide6.QtGui import QMouseEvent,QPixmap
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.core.commands import CommandBus,MoveMachines
class App(QApplication):
    def notify(self,obj,event):
        if event.type()==QEvent.Type.Paint:self.paints+=1
        return super().notify(obj,event)
app=App([]);app.paints=0;m.register_fonts(app)
results={}
def measured(name,action,events=False):
    callbacks=[];totals=[];paints=[]
    for _ in range(7):
        app.paints=0;start=time.perf_counter();action();callbacks.append((time.perf_counter()-start)*1000)
        if events:app.processEvents()
        totals.append((time.perf_counter()-start)*1000);paints.append(app.paints)
    results[name]=dict(callback_ms=callbacks,total_ms=totals,paint_counts=paints,median_ms=statistics.median(totals),max_ms=max(totals))
    print(name,results[name]['median_ms'],flush=True)
for count in (10,50,100,500):
    state=m.board_fixture(count,selected_hall=True);bus=CommandBus(state)
    b=FactoryViewV2(state,bus,m.D);b.pause_simulation();b.resize(1366,768);b.show();app.processEvents()
    ids=tuple(state.cards);unit=next(iter(state.halls.values()));surface=b._release_selection_surface
    results[str(count)+'.fixture']=dict(cards=count,widgets=len(b.findChildren(QWidget)),slots=len(b._slot_widgets),synthetic=count>50)
    measured(f'{count}.shift',lambda:(b._select_slot(0,Qt.KeyboardModifier.NoModifier),b._select_slot(count-1,Qt.KeyboardModifier.ShiftModifier)),True)
    event=QMouseEvent(QEvent.Type.MouseMove,QPointF(20,20),QPointF(20,20),Qt.MouseButton.NoButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
    measured(f'{count}.1000_idle_filter',lambda:[b.eventFilter(surface,event) for _ in range(1000)])
    measured(f'{count}.render',lambda:b.render(QPixmap(b.size())))
    # Identical empty-move and selected-cycle semantics in both versions.
    cycleids=ids[:min(5,count)];targets=tuple(range(1,len(cycleids)))+(0,)
    def cycle():
        current=tuple(unit.slots[i].card_id for i in range(len(cycleids)))
        MoveMachines(current,'factory',unit.hall_id,targets).apply(state)
    measured(f'{count}.drop_commit_cycle',cycle)
    measured(f'{count}.100_move_burst',lambda:[cycle() for _ in range(100)])
    if hasattr(b,'_machine_feedback'):
        b.refresh_view();app.processEvents()
        sourcewidget=b._slot_widgets[0];b._selected_machines=set(cycleids)
        b._machine_drag_data=b._machine_drag_payload(tuple(unit.slots[i].card_id for i in range(len(cycleids))))
        b._machine_feedback.start(sourcewidget,QPoint(20,80));position=sourcewidget.mapToGlobal(QPoint(30,90))
        def hover():
            for _ in range(100):b._machine_feedback.update_position(position);b._machine_hover(position)
        measured(f'{count}.100_drag_moves',hover,True)
        b._cancel_machine_drag()
        def swaps():
            for _ in range(100):MoveMachines((unit.slots[0].card_id,),'factory',unit.hall_id,(count-1,)).apply(state)
        measured(f'{count}.100_occupied_swaps',swaps)
    b.close();b.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
from production_zero.ui.freight_view import FreightView
from production_zero.core.freight import FreightFacility
for count in (10,50,100,500):
    state=m.state();state.cards.clear();state.freight.facilities.clear()
    unit=FreightFacility('drag-freight','Drag freight',slot_count=count);state.freight.facilities[unit.facility_id]=unit
    for i,slot in enumerate(unit.slots):
        cid=f'vehicle-{i}';state.cards[cid]=m.create_card_instance(cid,'freight.truck',m.CardKind.FREIGHT,m.Rarity.COMMON);slot.card_id=cid
    f=FreightView(state,CommandBus(state),m.D,m.R);f.resize(1366,768);f.show();app.processEvents()
    c=f._slot_interaction;sourcewidget=next(w for w in c._cards() if w._freight_vehicle=='vehicle-0')
    position=sourcewidget.mapToGlobal(QPoint(60,100));f._selected_vehicles={'vehicle-0'}
    press=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(25,70),QPointF(sourcewidget.mapToGlobal(QPoint(25,70))),Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    c.eventFilter(sourcewidget,press)
    start=QMouseEvent(QEvent.Type.MouseMove,QPointF(60,100),QPointF(position),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    c.eventFilter(sourcewidget,start)
    def moves():
        for i in range(100):
            local=QPoint(60+i%12,100+i%8);globalpos=sourcewidget.mapToGlobal(local)
            event=QMouseEvent(QEvent.Type.MouseMove,QPointF(local),QPointF(globalpos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            c.eventFilter(sourcewidget,event)
    measured(f'freight.{count}.100_pointer_moves',moves,True)
    results[f'freight.{count}.fixture']=dict(cards=count,widgets=len(f.findChildren(QWidget)),synthetic=True,
        ghost=hasattr(c,'feedback') and c.feedback.ghost is not None)
    c._finish_pointer_drag();f.close();f.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
(out/'measurements.json').write_text(json.dumps(results,indent=2),encoding='utf8')
