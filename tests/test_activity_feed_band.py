"""Three clipped, paced blocks and fixed three-second aggregation windows."""
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QWidget
from PySide6.QtTest import QTest
from production_zero.ui.event_feed import (EventFeedWidget, FeedEvent, AGGREGATION_SECONDS,
    DISPLAY_INTERVAL_SECONDS, SLIDE_DURATION_MS, PENDING_LIMIT, HISTORY_LIMIT)
from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import serialize_game_state


@pytest.fixture
def band(monkeypatch):
    import production_zero.ui.event_feed as module
    app=QApplication.instance() or QApplication([])
    clock=[100.0]; monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    host=QWidget(); host.resize(900,320)
    feed=EventFeedWidget(host); feed.move(0,0); feed.resize(900,34)
    host.show(); app.processEvents(); feed._timer.stop()
    yield app,clock,host,feed
    host.close(); host.deleteLater()
    QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()


def settle(feed):
    for entry in feed._entries+list(feed._departing): entry._slide.setCurrentTime(SLIDE_DURATION_MS)


@pytest.mark.parametrize('kind', ['cash','xp','rp','delivery','unlock','pack','contract','research','level_up','daily_activity'])
def test_every_type_waits_three_seconds_and_merges_across_sources(band,kind):
    app,clock,host,f=band
    for i in range(100):
        f.push(FeedEvent(kind,f'Source {i}',i+1,group_key=str(i),resource_id=f'resource-{i}'))
    assert AGGREGATION_SECONDS==3 and len(f._pending)==1 and not f.history and not f._entries
    clock[0]+=2.999; f._tick(); assert not f.history
    clock[0]+=.001; f._tick(); settle(f)
    assert len(f.history)==1 and len(f._entries)==1
    event=f.history[0]
    assert event.amount==5050 and event.count==100 and event.resource_id=='' and event.group_key==''
    assert f._entries[0].event.amount==5050


def test_boundary_arrival_begins_next_fixed_window_without_starvation(band):
    app,clock,host,f=band
    for i in range(31):
        clock[0]=100+i*.1
        f.push(FeedEvent('cash','Sales',1))
    assert len(f.history)==1 and f.history[0].amount==30
    assert f._pending['cash'].amount==1 and f._pending['cash'].created_at==103
    clock[0]=106; f._tick()
    assert sum(e.amount for e in f.history)==31


def test_three_horizontal_blocks_slide_right_and_never_leave_band_parent(band):
    app,clock,host,f=band
    for kind in ['cash','xp','rp']:
        f.push(FeedEvent(kind,kind,10)); f.flush_pending()
        settle(f); clock[0]+=DISPLAY_INTERVAL_SECONDS
    assert len(f._entries)==3
    assert [e.event.event_type for e in f._entries]==['rp','xp','cash']
    original=f._entries[:]
    f.push(FeedEvent('unlock','New product')); f.flush_pending()
    incoming=f._entries[0]
    assert incoming.x()<0 and len(f._departing)==1
    for entry in f._entries+f._departing:
        assert entry.parentWidget() is f._live_panel
        entry._slide.setCurrentTime(SLIDE_DURATION_MS//2)
    assert incoming.x()<=0 and original[-1].x()>original[-2].x()
    settle(f)
    assert len(f._entries)==3 and not f._departing
    assert [e.event.event_type for e in f._entries]==['unlock','rp','xp']
    assert all(e.y()==0 and f._live_panel.rect().contains(e.geometry()) for e in f._entries)
    assert f._live_panel.parentWidget() is f and f.rect().contains(f._live_panel.geometry())
    assert not host.findChildren(QWidget,'activityFeedStack')


@pytest.mark.parametrize('width',[360,480,660,800,1000])
def test_resize_and_clipping_keep_three_readable_slots_inside_reserved_rectangle(band,width):
    app,clock,host,f=band
    f.move_communication_buttons(QHBoxLayout(QWidget(host)))
    for kind in ['cash','xp','rp']:
        f.push(FeedEvent(kind,'A long message with many words',1e15)); f.flush_pending()
        clock[0]+=DISPLAY_INTERVAL_SECONDS; settle(f)
    f.resize(width,34); app.processEvents(); settle(f)
    assert len(f._entries)==3
    assert all(e.parentWidget() is f._live_panel and f._live_panel.rect().contains(e.geometry()) for e in f._entries)
    assert f._live_panel.width()<=width
    for i,entry in enumerate(f._entries):
        for other in f._entries[i+1:]: assert not entry.geometry().intersects(other.geometry())
        assert entry.toolTip() and entry.findChild(QLabel,'eventFeedAmount').text()


def test_ready_summaries_merge_under_load_without_speeding_up_or_losing_amounts(band):
    app,clock,host,f=band
    expected={kind:0 for kind in ['cash','xp','rp','delivery','unlock','pack','contract','research','level_up']}
    shown={kind:0 for kind in expected}
    original_present=f._present_next
    def present(now):
        before=f._entries[0] if f._entries else None
        original_present(now)
        if f._entries and f._entries[0] is not before:
            event=f._entries[0].event; shown[event.event_type]+=event.amount
        settle(f)
    f._present_next=present
    previous=clock[0]
    for tick in range(100):
        clock[0]=100+tick*.25
        for kind in expected:
            f.push(FeedEvent(kind,f'truck-{tick}',1)); expected[kind]+=1
        previous_entry=f._entries[0] if f._entries else None
        f._tick()
        if f._entries and f._entries[0] is not previous_entry:
            assert clock[0]-previous>=DISPLAY_INTERVAL_SECONDS
            previous=clock[0]
        assert len(f._pending)<=9 and len(f._ready)<=9 and len(f._entries)<=3
    f.flush_pending()
    for _ in range(12):
        clock[0]+=DISPLAY_INTERVAL_SECONDS; f._tick()
    assert shown==expected and not f._pending and not f._ready


def test_idle_messages_stay_until_replaced_and_clear_resets_queue_and_animation(band):
    app,clock,host,f=band
    for kind in ['cash','xp','rp','unlock','pack']:
        f.push(FeedEvent(kind,kind,10)); f.flush_pending()
        clock[0]+=DISPLAY_INTERVAL_SECONDS; f._tick()
    assert f._departing
    f.clear_events()
    assert not f._pending and not f._ready and not f._entries and not f._departing and not f.history
    clock[0]+=10000; f._tick(); assert not f._entries
    f.push(FeedEvent('cash','First new reward',5)); f.flush_pending(); settle(f)
    clock[0]+=10000; f._tick()
    assert len(f._entries)==1 and f._entries[0].event.amount==5


def test_unrecognized_types_have_bounded_pending_and_ready_summaries(band):
    app,clock,host,f=band
    total=0
    for wave in range(3):
        for i in range(100):
            f.push(FeedEvent(f'future-{wave}-{i}','Future activity',1)); total+=1
        f.flush_pending()
        assert len(f._pending)<=PENDING_LIMIT and len(f._ready)<=PENDING_LIMIT
    assert len(f.history)<=HISTORY_LIMIT
    assert sum(e.amount for e in f._ready.values())+sum(e.event.amount for e in f._entries)==total


def test_feed_display_never_mutates_game_state(band):
    app,clock,host,f=band
    s=GameState(42); f._state=s
    before=serialize_game_state(s)
    for i in range(100): f.push(FeedEvent('cash','Sales',1)); f.push(FeedEvent('xp','XP',.25))
    clock[0]+=3; f._tick(); clock[0]+=DISPLAY_INTERVAL_SECONDS; f._tick(); settle(f)
    assert serialize_game_state(s)==before


def test_hundred_completed_deliveries_become_one_cash_and_one_xp_summary(band):
    from production_zero.core.freight import MarketDeliveryResolution
    from production_zero.ui.event_feed import EventFeedController
    app,clock,host,f=band
    s=GameState(42); f._state=s
    c=EventFeedController(s,f)
    for i in range(100):
        s.freight.completed_market_deliveries.append(MarketDeliveryResolution(
            delivery_id=i,shipment_id=f'truck-{i}',resource_id=f'resource-{i}',
            delivered_amount=10,contract_amount=0,market_amount=10,market_price=10,market_earnings=100))
        s.freight.next_market_delivery_sequence=i+1
        s.cash.add(100); s.statistics.record_earnings(100)
    s.company.current_xp+=500
    c.observe()
    assert len(f._pending)==2 and not f.history
    assert f._pending['cash'].amount==10000 and f._pending['cash'].count==100
    clock[0]+=3; f._tick()
    assert {e.event_type:e.amount for e in f.history}=={'cash':10000,'xp':500}
    old=f.history
    c.observe();clock[0]+=3;f._tick();assert f.history==old


def test_queued_window_merging_does_not_rewrite_past_history(band):
    app,clock,host,f=band
    f.push(FeedEvent('cash','Income',1)); f.push(FeedEvent('xp','XP',5)); f.flush_pending()
    original=f.history
    # Hold display, while a second XP window merges with the waiting XP block.
    f._next_display_at=1000
    f.push(FeedEvent('xp','XP',7)); clock[0]+=3; f._tick()
    assert f._ready['xp'].amount==12
    assert original[0].amount==5 and original[1].amount==1
    assert [e.amount for e in f.history if e.event_type=='xp']==[7,5]
