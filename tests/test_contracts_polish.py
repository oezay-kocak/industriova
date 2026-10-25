import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from dataclasses import replace
from pathlib import Path
import pytest
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton, QScrollArea, QTabWidget
from production_zero.core.commands import CommandBus, AcceptContract, CancelContract
from production_zero.core.contracts import initialize_contracts, receive_contract_delivery, DAY_SECONDS, WEEK_SECONDS, refresh_contracts
from production_zero.core.state import GameState
from production_zero.ui.main_window import MainWindow
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.theme import APP_STYLESHEET


def _complete_card_selection(card):
    used = set()
    for selector in card.findChildren(QComboBox, 'contractProductSelect'):
        index = next(index for index in range(1, selector.count()) if selector.itemData(index) not in used)
        used.add(selector.itemData(index))
        selector.setCurrentIndex(index)


@pytest.mark.parametrize('kind,period', [('regular', None), ('daily', DAY_SECONDS), ('weekly', WEEK_SECONDS)])
def test_cancel_releases_category_but_completion_locks_until_reset(kind, period):
    from production_zero.core.contracts import ActiveContract, ContractOffer
    state = GameState(rng_seed=132)
    initialize_contracts(state)
    first = ContractOffer("first-" + kind, kind, "First", {"steel": 10}, 200, 50, 0)
    state.contracts.active[kind] = ActiveContract(first)
    state.contracts.offers[kind] = [first]
    bus = CommandBus(state)
    receive_contract_delivery(state, first.contract_id, "steel", 3)
    before = state.cash.amount
    bus.dispatch(CancelContract(kind))
    assert state.cash.amount == before and kind not in state.contracts.active
    second = replace(first, contract_id="second-" + kind)
    state.contracts.offers[kind] = [second]
    bus.dispatch(AcceptContract(kind, second.contract_id))
    receive_contract_delivery(state, first.contract_id, "steel", 10)
    assert state.contracts.active[kind].delivered == {}
    quoted = state.contracts.active[kind].offer.reward_cash
    receive_contract_delivery(state, second.contract_id, "steel", 10)
    assert state.cash.amount == before + quoted
    assert state.packs.unopened == []
    if period:
        assert state.contracts.active[kind].status == "completed"
        with pytest.raises(ValueError):
            bus.dispatch(CancelContract(kind))
        refresh_contracts(state, now_utc=state.company_xp_progress.utc_high_water_timestamp + period)
        assert kind not in state.contracts.active  # no definitions/eligible products in this isolated fixture
    else:
        assert kind not in state.contracts.active
        assert len(state.contracts.offers[kind]) == 1


@pytest.mark.parametrize('size', [(1366, 768), (1600, 900), (1920, 1080)])
def test_full_window_automatic_contracts_fit_and_cancel(size):
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    window = MainWindow()
    try:
        view = window.findChild(ContractsView)
        window.findChild(QTabWidget, "mainTabs").setCurrentWidget(view)
        window.resize(*size)
        window.show()
        for _ in range(8):
            app.processEvents()
        scroll = view.findChild(QScrollArea, "contractsBoardScroll")
        assert (window.width(), window.height()) == size
        assert scroll.horizontalScrollBar().maximum() == 0
        cards = view.findChildren(QFrame, "contractCard")
        assert len(cards) == 3
        for card in cards:
            assert card.geometry().bottom() <= card.parentWidget().height()
            for button in card.findChildren(QPushButton):
                assert button.mapTo(card, button.rect().bottomRight()).y() < card.height()
        active = view._state.contracts.active
        assert not active
        from tests.contract_acceptance_fixture import accept_fixture
        for kind in ('regular', 'daily'):
            accept_fixture(view._state, view._definitions, kind)
        view.refresh()
        assert {"regular", "daily"} <= active.keys()
        assert len(view.findChildren(QPushButton, "cancelContractButton")) == 2
        assert not view.findChildren(QPushButton, "deliverContractButton")
        for kind in ("regular", "daily"):
            previous = active[kind].offer
            card = next(card for card in view.findChildren(QFrame, "contractCard") if card.property("kind") == kind)
            card.findChild(QPushButton, "cancelContractButton").click()
            assert kind not in active
            assert view._state.contracts.offers[kind][0].requirements == {}
            assert view._state.cash.amount == 1250
        folder = Path("artifacts/contracts-polish")
        folder.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(folder / f"automatic-{size[0]}x{size[1]}.png"))
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_cancel_preserves_in_transit_goods_and_other_shipments():
    from production_zero.core.freight import OutboundFreightShipment
    state = GameState(rng_seed=132)
    initialize_contracts(state)
    offer = replace(state.contracts.offers['daily'][0], requirements={'steel': 10}, production_value_budget=None)
    state.contracts.offers['daily'][0] = offer
    bus = CommandBus(state)
    bus.dispatch(AcceptContract('daily', offer.contract_id))
    shipment = OutboundFreightShipment('cancelled-load', 'contract', offer.contract_id, 'steel', 5, remaining_seconds=20)
    other = OutboundFreightShipment('other-load', 'contract', 'other-contract', 'steel', 7)
    state.freight.outbound_shipments = {item.shipment_id: item for item in (shipment, other)}
    bus.dispatch(CancelContract('daily'))
    assert shipment.destination_kind == 'market'
    assert shipment.target_id is None
    assert shipment.quantity == 5 and shipment.remaining_seconds == 20 and shipment.active
    assert shipment.market_price == state.market.ensure_resource('steel').current_price
    assert other.destination_kind == 'contract' and other.target_id == 'other-contract'


@pytest.mark.parametrize('kind,outcome', [(kind, outcome) for kind in ('regular', 'daily', 'weekly') for outcome in ('cancel', 'expire', 'complete') if (kind, outcome) != ('regular', 'expire')])
def test_contract_feed_requires_real_completion(kind, outcome):
    from production_zero.ui.event_feed import EventFeedController
    class RecordingFeed:
        def __init__(self):
            self.events = []
        def push(self, event):
            self.events.append(event)
    state = GameState(rng_seed=132)
    initialize_contracts(state)
    offer = replace(state.contracts.offers[kind][0], requirements={'steel': 10}, production_value_budget=None)
    state.contracts.offers[kind][0] = offer
    bus = CommandBus(state)
    bus.dispatch(AcceptContract(kind, offer.contract_id))
    accepted_cash = state.contracts.active[kind].offer.reward_cash
    feed = RecordingFeed()
    controller = EventFeedController(state, feed)
    before = (state.cash.amount, state.company.current_xp, len(state.packs.unopened))
    if outcome == 'cancel':
        bus.dispatch(CancelContract(kind))
    elif outcome == 'expire':
        period = DAY_SECONDS if kind == 'daily' else WEEK_SECONDS
        refresh_contracts(state, now_utc=state.company_xp_progress.utc_high_water_timestamp + period)
    else:
        receive_contract_delivery(state, offer.contract_id, 'steel', 10)
    controller.observe()
    events = list(feed.events)
    controller.observe()
    assert feed.events == events  # Completion feedback is emitted once.
    if outcome != 'complete':
        assert feed.events == []
        assert (state.cash.amount, state.company.current_xp, len(state.packs.unopened)) == before
        assert kind not in state.contracts.active
    else:
        assert sum(event.label == 'Contract completed' for event in events) == 1
        assert sum(event.amount for event in events if event.event_type == 'cash') == accepted_cash
        assert sum(event.amount for event in events if event.event_type == 'xp') == offer.reward_xp
        assert not any(event.event_type == 'pack' for event in events)
