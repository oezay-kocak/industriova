import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QSpinBox, QTabWidget, QWidget

from production_zero.core.freight import FreightFacility
from production_zero.core.state import FactoryHall
from production_zero.persistence.sqlite_store import serialize_game_state
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.ui.factory_view_v2 import FactoryV2HallStage, ProductionBoardViewV2
from production_zero.ui.freight_view import FreightFacilityStage, FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET
from production_zero.tools.ui_contact_sheet import _load_qa_fonts


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    app.setStyleSheet(APP_STYLESHEET)
    return app


@pytest.fixture
def window(app):
    window = MainWindow(development_mode=False)
    for timer in window.findChildren(QTimer):
        timer.stop()
    state = window._session_state
    state.cash.amount = 1e9
    state.cards.clear()
    state.machine_production.clear()
    for unit in (*state.all_production_units(), *state.freight.facilities.values()):
        for slot in unit.slots:
            slot.card_id = None
    for stock in state.resources.values():
        stock.amount = 0
    for view in window.findChildren(ProductionBoardViewV2):
        view.reset_for_state_change()
    window.findChild(FreightView).reset_for_state_change()
    window._global_header.refresh()
    window.resize(1366, 850)
    window.show()
    app.processEvents()
    yield window
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def board(window, kind):
    if kind == "freight":
        return window.findChild(FreightView)
    return next(v for v in window.findChildren(ProductionBoardViewV2) if v._board_config.board_kind == kind)


def tabs(window):
    return window.findChild(QTabWidget, "mainTabs")


def test_supply_is_immediately_after_freight_in_both_navigation_bars(window):
    pages = tabs(window)
    names = [pages.tabText(i) for i in range(pages.count())]
    assert names[names.index("Freight") + 1] == "Industrial Supply"
    assert [pages._navigation_bar.tabText(i) for i in range(pages._navigation_bar.count())] == names


def test_factory_supply_category_contains_all_three_machine_families(window):
    supply = window.findChild(SupplyView)
    selector = supply._type_filter
    assert selector.categories == ("All", "Resources", "Energy", "Factory", "Freight")
    selector.buttons["Factory"].click()
    assert {d.definition_id for d in supply._filtered_common_data} == {
        "machine.processor", "machine.fabricator", "machine.assembler",
    }
    assert not any(supply.findChildren(QPushButton, "supplyCategory" + name) for name in ("Processing", "Fabrication", "Assembly"))


@pytest.mark.parametrize("kind,category", (("factory", "Factory"), ("resources", "Resources"), ("energy", "Energy"), ("freight", "Freight")))
def test_empty_card_picker_opens_correct_common_supply_category(window, app, kind, category):
    view = board(window, kind)
    pages = tabs(window)
    pages.setCurrentWidget(view)
    if kind == "freight":
        view._open_drawer(0)
    else:
        view._on_slot_clicked(0)
    app.processEvents()
    button = view.findChild(QPushButton, "openIndustrialSupplyButton")
    assert button is not None and button.isVisible()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    app.processEvents()
    supply = window.findChild(SupplyView)
    assert pages.currentWidget() is supply
    assert supply._stack.currentWidget() is supply._common_page
    assert supply._type_filter.currentText() == category
    assert supply._filtered_common_data
    assert all(supply._supply_category(d.definition) == category for d in supply._filtered_common_data)
    assert not window._session_state.cards


@pytest.mark.parametrize("category", ("Factory", "Resources", "Energy", "Freight", "All"))
def test_open_common_supply_clears_daily_page_and_stale_filter(window, category):
    supply = window.findChild(SupplyView)
    supply._type_filter.setCurrentText("Energy")
    supply._show_section(0)
    before = serialize_game_state(window._session_state)
    supply.show_common(category)
    assert supply._stack.currentWidget() is supply._common_page
    assert supply._type_filter.currentText() == category
    assert serialize_game_state(window._session_state) == before


@pytest.mark.parametrize("source", ("machine_daily", "freight_daily"))
def test_daily_dialog_has_no_quantity_controls_and_buys_exactly_one(window, source):
    supply = window.findChild(SupplyView)
    state = window._session_state
    offer = getattr(state.supply, source + "_offers")[0]
    dialog = supply._purchase_dialog(offer, source)
    dialog.show()
    assert dialog.quantity is None and dialog.max_button is None
    assert dialog.findChildren(QSpinBox) == []
    assert dialog.findChild(QPushButton, "purchaseMax") is None
    before_cash, before_cards = state.cash.amount, set(state.cards)
    supply._commit_purchase(dialog)
    acquired = set(state.cards) - before_cards
    assert len(acquired) == 1
    assert state.cards[acquired.pop()].rarity == offer.rarity
    assert state.cash.amount == before_cash - offer.price_cash
    after = serialize_game_state(state)
    try:
        supply._commit_purchase(dialog)
    except ValueError:
        pass
    assert serialize_game_state(state) == after


@pytest.mark.parametrize("source", ("machine_daily", "freight_daily"))
@pytest.mark.parametrize("case", ("no_cash", "expired", "cancel"))
def test_daily_fixed_quantity_preserves_purchase_guards(window, source, case):
    supply = window.findChild(SupplyView)
    state = window._session_state
    offer = getattr(state.supply, source + "_offers")[0]
    dialog = supply._purchase_dialog(offer, source)
    if case == "no_cash":
        state.cash.amount = 0
    elif case == "expired":
        dialog.offer = replace(offer, offer_id=offer.offer_id + "-expired")
    before = serialize_game_state(state)
    if case == "cancel":
        dialog.reject()
    else:
        with pytest.raises(ValueError):
            supply._commit_purchase(dialog)
    assert serialize_game_state(state) == before


@pytest.mark.parametrize("quantity", (1, 7, 100))
def test_common_supply_keeps_quantity_and_max(window, quantity):
    supply = window.findChild(SupplyView)
    state = window._session_state
    offer = next(o for o in supply._common_offers if o.definition_id == "machine.processor")
    dialog = supply._purchase_dialog(offer, "common")
    assert dialog.quantity is not None and dialog.max_button is not None
    dialog.max_button.click()
    assert dialog.quantity.value() == dialog.quantity.maximum()
    dialog.quantity.setValue(quantity)
    before_cash = state.cash.amount
    supply._commit_purchase(dialog)
    assert len(state.cards) == quantity
    assert state.cash.amount == before_cash - quantity * offer.price_cash


def button_pixel(button):
    image = QImage(button.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    button.render(image)
    return image.pixelColor(button.width() // 2, button.height() // 4)


def test_inbox_alternates_actual_grey_and_yellow_surfaces_without_state_changes(window, app):
    feed = window.findChild(EventFeedWidget)
    state = window._session_state
    state.communications.messages.clear()
    feed.refresh_communications()
    history = button_pixel(feed._history_button)
    state.communications.add_unlocks(["resource.iron_ore"])
    feed.refresh_communications()
    feed._inbox_attention.stop()
    before = serialize_game_state(state)
    colors = []
    for _ in range(4):
        colors.append(button_pixel(feed._inbox_button))
        feed._pulse_inbox()
    grey = next(c for c in colors if abs(c.red() - c.blue()) < 45)
    yellow = next(c for c in colors if c.red() - c.blue() > 100 and c.green() - c.blue() > 80)
    assert colors[0] == colors[2] and colors[1] == colors[3] and colors[0] != colors[1]
    assert grey != yellow
    assert serialize_game_state(state) == before
    assert button_pixel(feed._history_button) == history
    feed._show_inbox()
    app.processEvents()
    assert not feed._inbox_attention.isActive() and not feed._inbox_button.property("unread")
    assert not feed._inbox_button.property("attentionPhase")


@pytest.mark.parametrize("kind", ("resources", "factory", "energy", "freight"))
def test_building_list_navigation_does_not_rename(window, app, monkeypatch, kind):
    view = board(window, kind)
    called = []
    monkeypatch.setattr("production_zero.ui.interaction_polish.rename_building", lambda *args: called.append(args))
    if kind == "freight":
        state_units = view._state.freight.facilities
        state_units["other"] = FreightFacility("other", "Other")
        view.refresh()
        tree = view._facility_tree
    else:
        state_units = view._units
        state_units["other"] = FactoryHall("other", "Other", 3, board_kind=kind)
        view._refresh_hall_tree()
        tree = view._hall_tree
    pages = tabs(window)
    pages.setCurrentWidget(view)
    app.processEvents()
    item = next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == "other")
    rect = tree.visualItemRect(item)
    QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(rect.left() + 30, rect.top() + 10))
    app.processEvents()
    assert not called
    assert (view._selected_facility_id if kind == "freight" else view._selected_hall_id) == "other"


@pytest.mark.parametrize("kind", ("resources", "factory", "energy", "freight"))
def test_only_pencil_opens_rename_dialog_and_saves_name(window, app, kind):
    view = board(window, kind)
    tabs(window).setCurrentWidget(view)
    app.processEvents()
    stage = view.findChild(FreightFacilityStage if kind == "freight" else FactoryV2HallStage)
    unexpected = []
    def close_unexpected():
        dialog = QApplication.activeModalWidget()
        if dialog:
            unexpected.append(dialog)
            dialog.reject()
    QTimer.singleShot(0, close_unexpected)
    QTest.mouseClick(stage, Qt.MouseButton.LeftButton, pos=QPoint(55, 28))
    app.processEvents()
    assert not unexpected
    def rename():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, IndustrialDialog)
        dialog.findChild(QLineEdit, "buildingNameInput").setText("Renamed via pencil")
        dialog.accept_button.click()
    QTimer.singleShot(0, rename)
    stage._rename_filter.pencil.click()
    unit = (view._state.freight.facilities[view._selected_facility_id] if kind == "freight" else view._units[view._selected_hall_id])
    assert unit.name == "Renamed via pencil"


@pytest.mark.parametrize("width", (1180, 1366, 1920))
def test_storage_font_and_geometry_stay_stable_while_amounts_change(window, app, width):
    window.resize(width, 850)
    state = window._session_state
    state.warehouse_capacity = 100_000_000
    header = window._global_header
    label = header.findChild(QLabel, "factoryV2StorageValue")
    frames = []
    for amount in (0, 69_999, 70_000, 70_001, 99_999, 100_000, 999_999, 1_000_000, 9_999_999, 0):
        state.ensure_resource("iron_ore").amount = amount
        header.refresh()
        for _ in range(3):
            app.processEvents()
        frames.append((label.font().pixelSize(), label.geometry()))
        assert label.fontMetrics().horizontalAdvance(label.text()) <= label.width()
        assert f"{amount:,.0f}" in label.toolTip()
    assert all(frame == frames[0] for frame in frames)


@pytest.mark.parametrize("source", ("machine_daily", "freight_daily"))
def test_unaffordable_daily_dialog_keeps_fixed_total_and_disables_purchase(window, source):
    supply = window.findChild(SupplyView)
    state = window._session_state
    state.cash.amount = 0
    offer = getattr(state.supply, source + "_offers")[0]
    dialog = supply._purchase_dialog(offer, source)
    assert dialog.quantity is None and not dialog.accept_button.isEnabled()
    assert f"${offer.price_cash:,.2f}" in dialog.total.text()
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        supply._commit_purchase(dialog)
    assert serialize_game_state(state) == before


def test_inbox_timer_changes_phase_without_changing_game_state(window):
    feed = window.findChild(EventFeedWidget)
    state = window._session_state
    state.communications.messages.clear()
    state.communications.add_unlocks(["resource.iron_ore"])
    feed.refresh_communications()
    before = serialize_game_state(state)
    initial = feed._inbox_button.property("attentionPhase")
    QTest.qWait(feed._inbox_attention.interval() + 80)
    assert feed._inbox_button.property("attentionPhase") != initial
    assert serialize_game_state(state) == before
