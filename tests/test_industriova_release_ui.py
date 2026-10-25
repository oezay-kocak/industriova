import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt, QPointF, QMimeData
from PySide6.QtGui import QFontDatabase, QFont, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.supply import buy_common_supply_cards
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2, FactoryV2MachineCard
from production_zero.ui.release_board import MACHINE_MIME


def answer_dialog(callback):
    from PySide6.QtCore import QTimer
    from production_zero.ui.release_dialogs import IndustrialDialog
    seen = []
    def answer():
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, IndustrialDialog):
            seen.append(dialog.windowTitle())
            callback(dialog)
    QTimer.singleShot(0, answer)
    return seen


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    for filename in ("bahnschrift.ttf", "segoeui.ttf", "arial.ttf", "consola.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + filename)
    application.setFont(QFont("Bahnschrift", 10))
    return application


@pytest.fixture
def window(app):
    widget = MainWindow(development_mode=False)
    widget._session_state.cash.amount = 1e12
    widget.resize(1366, 768)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def populated_factory(window):
    board = window.findChild(FactoryViewV2)
    board.pause_simulation()
    ids = buy_common_supply_cards(board._state, board._definitions, "machine.processor", 3)
    from production_zero.core.commands import InstallCardInHall,UnlockProductionLine
    board._state.cash.amount+=900  # Fund the purchased second line in this interaction fixture.
    UnlockProductionLine(board._selected_hall_id,board._units[board._selected_hall_id].production_lines[1].line_id,"factory").apply(board._state)
    for i,cid in enumerate(ids):
        InstallCardInHall(board._selected_hall_id,i,cid,"factory").apply(board._state)
    board.refresh_view()
    tabs = window.findChild(QTabWidget, "mainTabs")
    tabs.setCurrentWidget(board)
    QApplication.processEvents()
    return board, ids


def test_retired_navigation_and_global_resources_available(window):
    tabs = window.findChild(QTabWidget, "mainTabs")
    names = {tabs.tabText(index) for index in range(tabs.count())}
    assert not {"Packs", "Market"} & names
    assert {"Resources", "Factory", "Energy", "Freight", "Inventory", "Industrial Supply"} <= names
    window._global_header._resources_global_button.clicked.emit()
    QApplication.processEvents()
    assert window._global_resources.isVisible()
    # Choose a position inside the parent's bounds; reopening clamps overflow.
    window._global_resources.move(250, 100)
    position = window._global_resources.pos()
    window._global_resources.toggle()
    window._global_resources.toggle()
    assert window._global_resources.pos() == position
    window._global_resources.move(window.width(), window.height())
    window._global_resources.toggle()
    window._global_resources.toggle()
    assert window._global_resources.parentWidget().rect().contains(window._global_resources.geometry())
    window._global_resources.drawer.close_button.clicked.emit()
    assert not window._global_resources.isVisible()


def test_single_ctrl_shift_selection_never_removes_machines(window):
    board, ids = populated_factory(window)
    before_cards = set(board._state.cards)
    before_placements = board._state.installed_card_ids()
    QTest.mouseClick(board._slot_widgets[0], Qt.MouseButton.LeftButton)
    assert board._selected_machines == {ids[0]}
    QTest.mouseClick(board._slot_widgets[1], Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
    assert board._selected_machines == set(ids[:2])
    QTest.mouseClick(board._slot_widgets[2], Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    assert board._selected_machines == set(ids[1:])
    assert set(board._state.cards) == before_cards
    assert board._state.installed_card_ids() == before_placements


def test_right_click_cancel_preserves_machine(window, monkeypatch):
    import production_zero.ui.release_board as release_board
    board, ids = populated_factory(window)
    confirmations = []
    monkeypatch.setattr(release_board, "confirm", lambda *args: confirmations.append(args) or False)
    from PySide6.QtCore import QTimer
    from production_zero.ui.game_ui import GameButton
    def choose_sale():
        dialog = QApplication.activeModalWidget()
        next(button for button in dialog.findChildren(GameButton, 'machineContextAction') if button.text() == 'Sell').click()
    QTimer.singleShot(60, choose_sale)
    QTest.mouseClick(board._slot_widgets[0], Qt.MouseButton.RightButton)
    QTest.qWait(90)
    assert ids[0] in board._state.installed_card_ids()
    assert confirmations and "MK1" in confirmations[0][2]


def test_energy_selection_cannot_open_an_empty_recipe_workspace(window, monkeypatch):
    from production_zero.ui.production_board_views import EnergyViewV2
    import production_zero.ui.release_board as release_board
    board = window.findChild(EnergyViewV2)
    cid = buy_common_supply_cards(board._state, board._definitions, "energy.solar_array", 1)[0]
    from production_zero.core.commands import InstallCardInHall
    InstallCardInHall(board._selected_hall_id,0,cid,"energy").apply(board._state)
    board.refresh_view()
    board._selected_machines = {cid}
    messages = []
    monkeypatch.setattr(release_board, "inform", lambda *args: messages.append(args))
    board._release_action(board._configure_selection)
    assert board._drawer_mode is None and messages


def test_group_drop_preserves_identities_and_mk(window):
    import json
    board, ids = populated_factory(window)
    board._selected_machines = set(ids[:2])
    cards_before = dict(board._state.cards)
    # An empty Build Slot participates in the same native drop protocol.
    target = next(widget for widget in board.findChildren(type(board._slot_widgets[0]).__bases__[0]) if getattr(widget, "_release_slot_index", None) == 3)
    mime = QMimeData()
    mime.setData(MACHINE_MIME, json.dumps(board._machine_drag_payload(ids[:2])).encode())
    drop = QDropEvent(QPointF(10, 10), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert board.eventFilter(target, drop)
    hall = board._units[board._selected_hall_id]
    assert [hall.slots[index].card_id for index in (3, 4)] == list(ids[:2])
    assert board._state.cards == cards_before


def test_real_group_upgrade_and_sale_dialogs_preserve_atomic_accounting(window):
    from production_zero.core.mk_upgrades import mk_upgrade_cost
    from production_zero.core.machine_operations import resale_value
    board, ids = populated_factory(window)
    board._selected_machines = set(ids)
    state = board._state
    state.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    for cid in ids:
        state.ensure_machine_production(cid, 'iron', 'recipe.processor.iron').progress_seconds = 2.5
    total = sum(mk_upgrade_cost(state.cards[cid], board._definitions[state.cards[cid].definition_id]) for cid in ids)
    cash = state.cash.amount
    seen = answer_dialog(lambda dialog: dialog.accept_button.click())
    board._upgrade_selection()
    assert seen == ['MK Upgrade']
    assert state.cash.amount == pytest.approx(cash - total)
    assert all(state.cards[cid].mk_level == 2 and state.machine_production[cid].progress_seconds == 2.5 for cid in ids)
    snapshot = dict(state.cards)
    board._selected_machines = set(ids)
    answer_dialog(lambda dialog: dialog.reject_button.click())
    board._sell_selection()
    assert state.cards == snapshot and state.cash.amount == pytest.approx(cash - total)
    proceeds = sum(resale_value(state.cards[cid], board._definitions[state.cards[cid].definition_id]) for cid in ids)
    answer_dialog(lambda dialog: dialog.accept_button.click())
    board._sell_selection()
    assert not set(ids) & state.cards.keys()
    assert state.cash.amount == pytest.approx(cash - total + proceeds)
    assert not set(ids) & state.installed_card_ids()


def test_ui_configuration_copy_pause_and_rectangle_selection(window):
    from PySide6.QtCore import QPoint
    board, ids = populated_factory(window)
    state = board._state
    state.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    for cid in ids[:2]:
        state.ensure_machine_production(cid, 'iron', 'recipe.processor.iron').progress_seconds = 2.5
    board._selected_machines = set(ids[:2])
    board._pause_selection()
    board._copy_selection()
    cards = set(state.cards)
    cash = state.cash.amount
    board._selected_machines = set(ids[1:])
    board._focused_line_id = board._units[board._selected_hall_id].production_lines[1].line_id
    answer_dialog(lambda d: d.accept())
    board._paste_selection()
    new_ids = set(state.cards) - cards
    assert len(new_ids) == 2 and state.cash.amount == cash - 550
    assert all(state.machine_production[cid].selected_production_id == 'recipe.processor.iron' for cid in (*ids[:2], *new_ids))
    assert all(state.cards[cid].paused for cid in (*ids[:2], *new_ids))
    assert not state.cards[ids[2]].paused
    assert state.machine_production[ids[0]].progress_seconds == 2.5
    surface = board._release_selection_surface
    first, last = board._slot_widgets[0], board._slot_widgets[2]
    start = first.mapTo(surface, QPoint(0, 0)) - QPoint(1, 1)
    end = last.mapTo(surface, last.rect().bottomRight()) + QPoint(1, 1)
    QTest.mousePress(surface, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(surface, end)
    QTest.mouseRelease(surface, Qt.MouseButton.LeftButton, pos=end)
    assert board._selected_machines == set(ids)


def test_purchase_dialog_quantity_acquires_inventory_and_counts_owned_machines(window):
    from production_zero.ui.supply_view import SupplyView
    from production_zero.core.supply import common_supply_offers
    view = window.findChild(SupplyView)
    offer = next(offer for offer in common_supply_offers(view._definitions) if offer.definition_id == 'machine.processor')
    state = view._state
    cards = set(state.cards)
    cash, owned = state.cash.amount, view._owned_count(offer)
    totals = []
    def purchase(dialog):
        dialog.quantity.setValue(2)
        totals.append((dialog.total.text(), dialog.total.palette().color(dialog.total.foregroundRole()).name()))
        dialog.accept_button.click()
    seen = answer_dialog(purchase)
    view._buy_offer(offer, 'common')
    assert seen == ['Purchase to inventory']
    assert totals == [(f'TOTAL: ${2 * offer.price_cash:,.2f}', '#18201d')]
    added = set(state.cards) - cards
    assert len(added) == 2 and not added & state.installed_card_ids()
    assert all(state.cards[cid].mk_level == 1 and state.cards[cid].acquisition_cost == offer.price_cash for cid in added)
    assert state.cash.amount == cash - 2 * offer.price_cash
    assert view._owned_count(offer) == owned + 2


@pytest.mark.parametrize("size", [(1366, 768), (1600, 980), (1920, 1080)])
def test_supported_resolution_and_cached_card_rendering(window, size):
    board, ids = populated_factory(window)
    window.resize(*size)
    QApplication.processEvents()
    assert (window.width(), window.height()) == size
    assert window._global_header.geometry().right() < window.centralWidget().width()
    card = board._slot_widgets[0]
    first = card.grab().toImage()
    cached = card._cached_card_pixmap.cacheKey()
    card.grab()
    assert card._cached_card_pixmap.cacheKey() == cached
    assert not first.isNull()
    assert "MK1" in card._meta_text()
