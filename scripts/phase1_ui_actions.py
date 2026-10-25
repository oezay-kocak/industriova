"""Post-confirmation UI workloads, identical against both saved source trees.

Uses the Phase-0 legal 50-slot halls and actual view callbacks; fixture resets
and modal human waiting are outside the measured interval. No personal store.
"""
import json,statistics,time
from phase0_benchmark import D,OUT,board_fixture,register_fonts
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QEvent,QTimer
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.core.state import FactoryHall
from production_zero.core.commands import ConfigureMachines
from production_zero.core.production_templates import quote_templates,PurchaseTemplates
from production_zero.ui import release_board

app=QApplication([]);register_fonts(app,stylesheet=False)
release_board.confirm=lambda *a,**kw:True
results={}
def drain():
    for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)

for count in (50,500):
    window=MainWindow(development_mode=False,charts_enabled=False)
    window.resize(1366,768);window.show()
    for timer in window.findChildren(QTimer):timer.stop()
    state=window._session_state;board=window.findChild(FactoryViewV2)
    window.findChild(QTabWidget,'mainTabs').setCurrentWidget(board)
    bus=board._command_bus
    for action in ('sale20','mk4','slots7','recipe20','copy_paste10'):
        values=[];delays=[];transactions=[]
        for repeat in range(7):
            fixture=board_fixture(count)
            for name in ('cards','halls','machine_production'):
                collection=getattr(state,name);collection.clear();collection.update(getattr(fixture,name))
            state.cash.amount=1e12
            hid=next(iter(state.halls));hall=state.halls[hid]
            board._selected_hall_id=hid;board._selected_machines=set()
            cid=hall.slots[0].card_id
            option=next(o for o in D['machine.processor'].available_production_options if o.output_resource=='iron')
            state.production_progress.unlocked_production_ids.add(option.production_id)
            if action=='slots7':
                hall=FactoryHall(hid,'Slot target',6,max_lines=5);state.halls[hid]=hall
            if action=='copy_paste10':
                for slot in hall.slots[-10:]:slot.card_id=None
                board._selected_machines={s.card_id for s in hall.slots[:10]}
            board.refresh_view();drain()
            history=len(bus.history);cards=len(state.cards)
            def operation():
                if action=='sale20':
                    ids=[s.card_id for s in hall.slots[:20]]
                    for card_id in ids:
                        board._selected_machines={card_id};board._sell_selection()
                elif action=='mk4':
                    for _ in range(4):board._upgrade_selection(cid)
                elif action=='slots7':
                    for _ in range(7):board._unlock_slot(hall.production_lines[0].line_id)
                elif action=='recipe20':
                    for _ in range(20):
                        bus.dispatch(ConfigureMachines((cid,),option.production_id,D));board.refresh_view()
                else:
                    board._copy_selection();templates=board._configuration_clipboard
                    assert len(templates)==10
                    line=hall.production_lines[-1].line_id
                    price=quote_templates(state,D,templates,'factory',hid,line)[2]
                    bus.dispatch(PurchaseTemplates(templates,'factory',hid,line,D,price));board.refresh_view()
            start=time.perf_counter()
            QTimer.singleShot(0,lambda t=start:delays.append((time.perf_counter()-t)*1000))
            operation();drain();values.append((time.perf_counter()-start)*1000)
            transactions.append(len(bus.history)-history)
            assert transactions[-1]==dict(sale20=20,mk4=4,slots7=7,recipe20=20,copy_paste10=1)[action]
            if action=='sale20':assert len(state.cards)==cards-20
            elif action=='mk4':assert state.cards[cid].mk_level==5
            elif action=='slots7':assert len(hall.production_lines[0].slot_indexes)==10
            elif action=='recipe20':assert state.machine_production[cid].selected_production_id==option.production_id
            else:assert len(state.cards)==cards+10
        results[f'{count}.{action}']=dict(samples_ms=values,median_ms=statistics.median(values),max_ms=max(values),queued_event_delays_ms=delays,transactions=transactions)
        print(count,action,round(statistics.median(values),2),flush=True)
    window.close();window.deleteLater();drain()
(OUT/'ui-actions.json').write_text(json.dumps(results,indent=2),encoding='utf8')
