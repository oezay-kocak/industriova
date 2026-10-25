"""P6 header ownership and existing P5 hover/runtime widget reuse."""
from dataclasses import replace
import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtTest import QTest
from test_ui_interaction_recovery import app, window
from test_phase5_freight_ui import setup
from production_zero.core.freight import FreightFacility
from production_zero.core.freight_statistics import FreightDeliveryStatistics, DeliveryRate
from production_zero.ui.freight_view import FreightFacilityStage
from production_zero.ui.freight_statistics import compact_rate, actual_throughput_text


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_header_values_are_local_and_runtime_keeps_cards(window,size):
    window.resize(*size);f,u,ids,source=setup(window)
    stats=f._state.freight.delivery_statistics;stats.advance(60)
    stats.record(ids[0],u.facility_id,sell=5,contract=7,consortium=11)
    stats.record('other','other-facility',sell=1e9)
    f.refresh_runtime();stage=f._facility_stage
    assert stage.property('deliveryTotal')=='23/min'
    assert stage.property('deliverySell')=='5/min' and stage.property('deliveryContract')=='7/min'
    assert stage.property('deliveryConsortium')=='11/min'
    assert f._runtime_widgets[ids[0]]['card'] is source
    assert '1000000000' not in stage.toolTip() and 'TOTAL: 23 units/min' in stage.toolTip()
    f._show_freight_hover(ids[0],source)
    popup=f._hover_popup
    assert popup._value_labels['ACTUAL THROUGHPUT'].text()=='23.00 units/min'
    assert 'THEORETICAL THROUGHPUT' in popup._value_labels
    previous=popup._value_labels['THEORETICAL THROUGHPUT'].text()
    f._state.cards[ids[0]]=replace(f._state.cards[ids[0]],mk_level=50)
    f.refresh_runtime()
    assert popup._value_labels['ACTUAL THROUGHPUT'].text()=='23.00 units/min'
    assert popup._value_labels['THEORETICAL THROUGHPUT'].text()!=previous
    stats.advance(60);f.refresh_runtime()
    assert stage.property('deliveryTotal')=='0/min'
    assert popup._value_labels['ACTUAL THROUGHPUT'].text()=='0.00 units/min'


def test_facility_switch_shows_own_measurements(window):
    f,u,ids,source=setup(window);second=FreightFacility('other-facility','Garage 02')
    f._state.freight.facilities[second.facility_id]=second
    stats=f._state.freight.delivery_statistics;stats.advance(60)
    stats.record(ids[0],u.facility_id,sell=5);stats.record('other',second.facility_id,sell=9)
    for unit,amount in ((u,'5/min'),(second,'9/min'),(u,'5/min')):
        f._selected_facility_id=unit.facility_id;f.refresh();stage=f._facility_stage
        assert stage.property('deliveryTotal')==amount


def test_warmup_and_unchanged_header_does_not_request_repaint(window):
    f,u,ids,source=setup(window);stage=f._facility_stage
    f._state.freight.delivery_statistics=FreightDeliveryStatistics();stage.refresh_statistics()
    assert stage.property('deliveryTotal')=='0/min' and 'MEASURING' in stage.toolTip()
    assert stage.refresh_statistics() is False
    stats=f._state.freight.delivery_statistics;stats.advance(10);stats.record(ids[0],u.facility_id,sell=2)
    assert stage.refresh_statistics() is True
    assert stage.property('deliveryTotal')=='12/min'
    assert 'MEASURING…' in stage.toolTip()
    assert stage.refresh_statistics() is False
    stats.advance(50);f.refresh_runtime()
    assert 'MEASURING…' not in stage.toolTip()


@pytest.mark.parametrize('amount,expected',[(0,'0/min'),(850,'850/min'),(12500,'12.5K/min'),(1250000,'1.25M/min'),(1e15,'1e+03T/min'),(1e-8,'1e-08/min')])
def test_compact_exact_hover_and_small_values(amount,expected):
    assert compact_rate(amount)==expected
    text=actual_throughput_text(DeliveryRate(amount,0,0,60))
    assert 'units/min' in text and 'MEASURING' not in text


@pytest.mark.parametrize('kind',['garage_depot','rail_station','airport','harbor'])
def test_header_title_fit_and_all_target_columns(app,kind):
    from production_zero.core.state import GameState
    state=GameState(197);unit=FreightFacility('long', 'International '+kind.replace('_',' ').title()+' Long Distance Cargo Terminal 01',kind)
    stage=FreightFacilityStage(unit,state);stage.resize(700,188);stage.show();app.processEvents()
    state.freight.delivery_statistics.advance(60)
    state.freight.delivery_statistics.record('c','long',sell=1.25e9,contract=1e-8,consortium=2.5e6)
    assert stage.refresh_statistics()
    image=stage.grab();assert not image.isNull()
    for target in ('Sell','Contract','Consortium','Total'):assert stage.property('delivery'+target)
    assert '1e-08 units/min' in stage.toolTip()
    stage.close();stage.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)


def test_bounded_delivery_feed_uses_sequence_after_rollover(app):
    from production_zero.core.state import GameState
    from production_zero.core.freight import MarketDeliveryResolution
    from production_zero.ui.event_feed import EventFeedController,EventFeedWidget
    state=GameState(197);feed=EventFeedWidget();controller=EventFeedController(state,feed)
    for i in range(700):
        state.freight.completed_market_deliveries.append(MarketDeliveryResolution(i,str(i),'iron_ore',1,0,1,2,2))
        state.freight.next_market_delivery_sequence=i+1
    assert len(state.freight.completed_market_deliveries)==512
    rows=controller._completed_market_deliveries(650)
    assert len(rows)==50 and rows[0].delivery_id==650 and rows[-1].delivery_id==699
    controller.observe();assert controller._market_delivery_count==700
    assert not controller._completed_market_deliveries(controller._market_delivery_count)
    state.freight.completed_market_deliveries.append(MarketDeliveryResolution(700,'new','iron_ore',1,0,1,2,2))
    state.freight.next_market_delivery_sequence=701
    assert len(controller._completed_market_deliveries(700))==1
    feed.close();feed.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
