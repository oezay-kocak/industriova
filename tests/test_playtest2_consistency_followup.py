from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QPushButton, QTabBar, QTabWidget

from production_zero.core.commands import AddCash, InstallCardInHall
from production_zero.ui.contracts_view import ContractProductPicker, ContractsView
from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.factory_view import ProductionSelectionTile
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_icons import card_resource_icon_signature
from production_zero.ui.resource_tiles import RESOURCE_TILE_HEIGHT, RESOURCE_TILE_WIDTH, ResourceSelectionTile
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET, Theme
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from tests.test_contract_selection_ui import _card, _view_with_four_products
from tests.test_factory_view_v2 import _state_defs_bus


def _app():
    return QApplication.instance() or QApplication([])


def test_ticker_is_clipped_in_tab_row_and_moves_one_persistent_tape() -> None:
    app = _app()
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(1600, 900)
    window.show()
    app.processEvents()
    tabs = window.findChild(QTabWidget, "mainTabs")
    feed = window.findChild(EventFeedWidget, "eventFeed")
    row = window.findChild(QFrame, "mainNavigationRow")
    navigation = window.findChild(QTabBar, "mainNavigationTabs")
    assert feed.parent() is row and navigation.parent() is row
    assert abs(navigation.y() - feed.y()) <= 4
    ratio = navigation.width() / row.width()
    assert abs(navigation.width() - feed.width()) <= 1
    assert abs(ratio - 0.5) <= 0.005
    assert feed.width() / row.width() >= 0.44
    assert navigation.expanding()
    assert all(navigation.tabText(index) for index in range(navigation.count()))
    assert navigation.property("equalWidthFill") is True
    assert navigation.font().family() == "Bahnschrift"
    assert navigation.font().pixelSize() == 12
    assert navigation.font().weight() == QFont.Weight.Black
    assert navigation.font().stretch() == QFont.Stretch.Condensed
    widths = [navigation.tabRect(index).width() for index in range(navigation.count())]
    assert sum(widths) == navigation.width()
    assert max(widths) - min(widths) <= 24
    assert all(
        navigation.fontMetrics().horizontalAdvance(navigation.tabText(index)) < navigation.tabRect(index).width()
        for index in range(navigation.count())
    )
    assert feed._history_button.isVisible()
    feed.push(FeedEvent("xp", "Company Progress", 24))
    feed.flush_pending()
    QTest.qWait(210)
    assert len(feed._entries)==1 and feed._live_panel.isVisible()
    assert feed._live_panel.parentWidget() is feed
    assert not feed.findChildren(QLabel,'eventFeedTickerEntry')
    window.close()


def test_shared_product_picker_retains_search_and_unavailable_product_states() -> None:
    app = _app()
    from types import SimpleNamespace
    view = _view_with_four_products()
    view._test_window.findChild(QTabWidget, 'mainTabs').setCurrentWidget(view)
    view._test_window.show()
    for _ in range(8):
        app.processEvents()
    products = [SimpleNamespace(resource_id=rid, name=resource.name) for rid, resource in view._resources.items()]
    first = products[0].resource_id
    picker = ContractProductPicker(products, view._resources, {first}, "", view, purpose_label="RESEARCH CATEGORY")
    picker.resize(1200, 600)
    picker.show()
    app.processEvents()
    assert picker.parent() is view
    assert picker.tiles and all(isinstance(tile, ResourceSelectionTile) for tile in picker.tiles)
    assert all(tile.size().width() == RESOURCE_TILE_WIDTH and tile.size().height() == RESOURCE_TILE_HEIGHT for tile in picker.tiles)
    duplicate = next(tile for tile in picker.tiles if tile.property("resourceId") == first)
    assert not duplicate.isEnabled()
    picker.search.setText("definitely-not-a-product")
    app.processEvents()
    assert all(tile.isHidden() for tile in picker.tiles)
    picker.search.clear()
    assert any(not tile.isHidden() for tile in picker.tiles)
    picker.search.setText('iron')
    for _ in range(6):
        app.processEvents()
    visible = [tile for tile in picker.tiles if not tile.isHidden()]
    assert len(visible) >= 2
    assert visible[0].y() == visible[1].y()
    assert visible[1].x() == visible[0].x() + RESOURCE_TILE_WIDTH + picker._grid.horizontalSpacing()
    assert any(label.text() == 'SELECT PRODUCT' for label in picker.findChildren(QLabel))
    assert not view.findChildren(QDialog)


def test_supply_x4_shows_and_charges_total_price_with_matching_affordability() -> None:
    app = _app()
    window=MainWindow();window.resize(1366,768);window.show()
    supply=window.findChild(SupplyView)
    window.findChild(QTabWidget,"mainTabs").setCurrentWidget(supply)
    supply._show_section(1);supply._type_filter.setCurrentText("Energy")
    supply._bus.dispatch(AddCash(100_000));supply.refresh();app.processEvents()
    card=next(c for c in supply.findChildren(QFrame,"commonSupplyCard") if c.isVisible())
    offer=card._supply_data.offer;price=offer.price_cash
    assert not supply.findChildren(QPushButton,"supplyFilterChip")
    assert card.findChild(QLabel,"supplyCardPrice").text()==f"${price:.2f}"
    # Card affordability is per copy; quantity/MAX belongs exclusively to the dialog.
    for cash,maximum in ((price*4-1,3),(price*4,4),(price,1),(price-1,0)):
        supply._state.cash.amount=cash;supply._refresh_common_purchase_buttons()
        assert card._buy_button.isEnabled()==bool(maximum)
        dialog=supply._purchase_dialog(offer,"common");dialog.max_button.click()
        assert dialog.quantity.value()==maximum
        assert dialog.total.text()==f"TOTAL: ${maximum*price:,.2f}"
        assert dialog.accept_button.isEnabled()==bool(maximum)
        dialog.deleteLater()
    supply._state.cash.amount=price*4;supply.refresh();app.processEvents()
    before=set(supply._state.cards);slots=supply._state.installed_card_ids()
    from PySide6.QtCore import QTimer
    from production_zero.ui.release_dialogs import IndustrialDialog
    def buy_four():
        dialog=app.activeModalWidget();assert isinstance(dialog,IndustrialDialog)
        dialog.quantity.setValue(4);dialog.accept_button.click()
    QTimer.singleShot(0,buy_four);card._buy_button.click()
    added=set(supply._state.cards)-before
    assert len(added)==4 and supply._state.cash.amount==0
    assert supply._state.installed_card_ids()==slots and not added&slots
    window.close()


def test_drilling_picker_offers_both_primary_resources_without_level_gates() -> None:
    app = _app()
    state, definitions, bus = _state_defs_bus()
    view = FactoryViewV2(state, bus, definitions)
    options = view._production_picker_options(definitions["machine.drilling"])
    tiles = [
        ProductionSelectionTile(
            option, "", "Oil & Gas",
            locked_reason=view._locked_production_reason(option),
        )
        for option in options
    ]
    by_resource = {tile.property("resourceId"): tile for tile in tiles}
    assert by_resource["crude_oil"].isEnabled()
    assert by_resource["natural_gas"].isEnabled()
    assert "LEVEL" not in by_resource["natural_gas"].findChild(QLabel, "productionTileCurrent").text()
    assert len(tiles) == 2


def test_energy_pack_icons_are_canonical_and_reveal_backdrop_is_neutral() -> None:
    _, definitions, _ = _state_defs_bus()
    coal = card_resource_icon_signature(definitions["energy.coal_power_plant"], "energy.coal_power_plant")
    gas = card_resource_icon_signature(definitions["energy.gas_power_plant"], "energy.gas_power_plant")
    assert coal[:2] == ("coal_chunk", "coal")
    assert gas[:2] == ("flame", "gas")
    assert "QWidget#packResultPage QWidget#packsCanvasViewport" in APP_STYLESHEET
    assert "stop:0 #d8d8cf" in APP_STYLESHEET
