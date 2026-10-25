"""Confirmed-purchase callback bursts with the real MainWindow subscribers.

Measures work after a user confirmation, excluding human/modal waiting time.
"""
import json,time,statistics
from phase0_benchmark import D,OUT,RESULT,board_fixture,save,profile,register_fonts
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QTimer
from production_zero.ui.main_window import MainWindow
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.core.commands import SellMachines
app=QApplication([])
register_fonts(app,stylesheet=False)  # MainWindow owns the real application style.
for count in (50,500):
    w=MainWindow(development_mode=False,charts_enabled=False);w.resize(1366,768);w.show();app.processEvents()
    for timer in w.findChildren(QTimer):timer.stop()
    s=w._session_state;fixture=board_fixture(count)
    for attr in ('cards','halls','resource_sites','energy_plants','machine_production'):
        collection=getattr(s,attr);collection.clear();collection.update(getattr(fixture,attr))
    s.cash.amount=1e18;last=s.halls[list(s.halls)[-1]]
    # Keep all original cards; twenty become unplaced, making legal free slots.
    for slot in last.slots[-20:]:slot.card_id=None
    for board in w.findChildren(ProductionBoardViewV2):
        if board._board_config.board_kind=='factory':board._selected_hall_id=next(iter(s.halls))
    # Resources/Energy need their ordinary empty initial buildings for UI headers.
    from production_zero.core.state import FactoryHall
    s.resource_sites['resources']=FactoryHall('resources','Resources',1,board_kind='resources',max_lines=3,start_unlocked_lines=1,start_slots_per_line=1)
    s.energy_plants['energy']=FactoryHall('energy','Energy',1,board_kind='energy',max_lines=3,max_slots_per_line=5,start_unlocked_lines=1,start_slots_per_line=1)
    for board in w.findChildren(ProductionBoardViewV2):board._selected_hall_id=next(iter(board._units))
    supply=w.findChild(SupplyView);w.findChild(QTabWidget,'mainTabs').setCurrentWidget(supply);app.processEvents()
    samples=[];delays=[];before_ids=set(s.cards)
    for _ in range(20):
        start=time.perf_counter();QTimer.singleShot(0,lambda t=start:delays.append((time.perf_counter()-t)*1000))
        supply._buy_common('machine.processor');app.processEvents();samples.append((time.perf_counter()-start)*1000)
    acquired=tuple(set(s.cards)-before_ids)
    assert len(acquired)==20
    RESULT['measurements'][f'rapid_ui.{count}.20_individual_purchases']={
       'samples_ms':samples,'median_ms':statistics.median(samples),'max_ms':max(samples),'total_ms':sum(samples),
       'queued_event_delays_ms':delays,'includes_event_drain':True,'acquired':len(acquired)}
    SellMachines(acquired,D).apply(s)
    profile(f'rapid-ui-{count}',lambda:supply._buy_common('machine.processor'))
    # This app has no save_store; closing does not write a personal save.
    w.close();w.deleteLater();app.processEvents();save('rapid-ui-baseline')
    print(json.dumps(RESULT['measurements'][f'rapid_ui.{count}.20_individual_purchases']),flush=True)
