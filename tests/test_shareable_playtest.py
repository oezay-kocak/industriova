import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from production_zero.core.company_xp import award_contract_company_xp
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.enums import Rarity
from production_zero.persistence.dev_save_store import DevJsonSaveStore
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.event_feed import EventFeedController, EventFeedWidget, FeedEvent
from production_zero.ui.main_window import MainWindow, _create_initial_state


def test_new_company_has_two_common_trucks():
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    state = _create_initial_state(resources, definitions)
    trucks = [card for card in state.cards.values() if card.definition_id == "freight.truck"]
    assert len(trucks) == 2
    assert all(card.rarity == Rarity.COMMON for card in trucks)
    assert not state.freight.assignments


@pytest.mark.parametrize("amount,visible", [(0.5, True), (1, True), (5, True), (9.9, True), (10, True), (75, True)])
def test_xp_notification_threshold_preserves_earned_xp(amount, visible):
    app = QApplication.instance() or QApplication([])
    from production_zero.core.state import GameState
    state = GameState(rng_seed=1)
    feed = EventFeedWidget(state=state)
    controller = EventFeedController(state, feed)
    award_contract_company_xp(state, amount, None, source="test")
    controller.observe()
    feed.flush_pending()
    assert bool(feed.history) is visible
    assert len(feed.history) == 1
    assert feed.history[0].event_type == "xp"
    assert feed.history[0].amount == pytest.approx(amount)
    assert state.company.current_xp == pytest.approx(amount)
    assert not state.communications.messages
    feed.close()


def test_dev_new_game_save_load_and_relaunch(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    store = SQLiteSaveStore(tmp_path / "company.sqlite")
    window = MainWindow(development_mode=True, save_store=store)
    dev = window.findChild(DevToolsView)
    dev._save_store = DevJsonSaveStore(tmp_path / "manual")
    state = window._session_state
    try:
        state.cash.amount = 7777
        state.research.total_earned = 25
        state.communications.add_unlocks(["resource.aluminum"])
        window._event_feed.push(FeedEvent("xp", "Previous company", 50))
        dev._save_game()
        assert store.load("company").cash.amount == 7777
        monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.No)
        dev._new_game()
        assert state.cash.amount == 7777
        monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
        buttons = {button.text(): button for button in dev.findChildren(QPushButton)}
        buttons["NEW GAME"].click()
        assert state.cash.amount == 1250
        assert state.research.total_earned == 0
        assert not state.communications.messages
        assert not window._event_feed.history
        assert store.load("company").cash.amount == 1250
        assert len([card for card in state.cards.values() if card.definition_id == "freight.truck"]) == 2
        buttons["LOAD GAME"].click()
        assert state.cash.amount == 7777
        assert state.research.total_earned == 25
        assert state.communications.messages
    finally:
        window.close()
    reopened = MainWindow(development_mode=True, save_store=store)
    try:
        assert reopened._session_state.cash.amount == 7777
        assert reopened.findChild(DevToolsView) is not None
    finally:
        reopened.close()
