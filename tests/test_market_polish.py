import inspect
import os
from html import escape
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QScrollArea
from production_zero.core.market import MARKET_EVENTS, active_market_event
from production_zero.core.state import GameState
from production_zero.data.definitions import load_resource_definitions
from production_zero.ui.market_view import MarketTableDelegate, MarketView
from production_zero.ui.theme import APP_STYLESHEET


@pytest.fixture
def market():
    app = QApplication.instance() or QApplication([])
    fonts = [QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{name}") for name in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf")]
    previous = app.styleSheet()
    app.setStyleSheet(APP_STYLESHEET)
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    view = MarketView(GameState(rng_seed=411), resources)
    view.resize(1366, 768)
    view.show()
    app.processEvents()
    yield view
    view.close()
    view.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.setStyleSheet(previous)
    for font in fonts:
        if font >= 0:
            QFontDatabase.removeApplicationFont(font)


def test_default_stage_and_event_tooltip_refresh(market):
    assert market._stage_filter.currentText() == "Primary Production"
    assert market.findChild(QFrame, "marketEventPanel") is None
    for event in MARKET_EVENTS[:2]:
        market._state.market.active_event_id = event.event_id
        market.refresh()
        info = market._header._event_info
        assert escape(event.name) in info
        for resource_id in active_market_event(market._state.market).affected_resources:
            assert escape(market._resources[resource_id].name) in info
    count = market._proxy_model.rowCount()
    market._stage_filter.setCurrentText("All")
    assert market._proxy_model.rowCount() > count


def test_assembly_stage_uses_authoritative_production_metadata(market):
    market._stage_filter.setCurrentText("Assembly")
    assembly_ids = {
        market._proxy_model.index(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(market._proxy_model.rowCount())
    }

    assert assembly_ids
    assert "nuclear_fuel_assembly" in assembly_ids
    assert "construction_frames" in assembly_ids
    assert "steel" not in assembly_ids


@pytest.mark.parametrize("size", [(1366, 768), (1920, 1080)])
def test_market_compact_geometry_and_offscreen_render(market, size):
    market.resize(*size)
    for _ in range(4):
        QApplication.processEvents()
    filters = market.findChild(QScrollArea, "marketFilterScroll")
    assert filters.widget().width() <= filters.viewport().width()
    assert market._market_table.verticalHeader().defaultSectionSize() == 64
    folder = Path("artifacts/market-polish")
    folder.mkdir(parents=True, exist_ok=True)
    assert market.grab().save(str(folder / f"overview-{size[0]}.png"))
    for value in (40, 42, 39, 44, 49, 47, 52):
        market._state.history.append("market.price.steel", value)
    market._state.market.ensure_resource("steel").current_price = 52
    market._show_detail("steel")
    QApplication.processEvents()
    assert market._detail_price.property("change") == "positive"
    assert market._detail_chart.height() >= market._stack.height() * 0.65
    assert market._detail_summary_layout.rowCount() == 2
    assert market.grab().save(str(folder / f"detail-{size[0]}.png"))
    market._state.history.append("market.price.steel", 30)
    market._state.market.ensure_resource("steel").current_price = 30
    market.refresh()
    assert market._detail_price.property("change") == "negative"
    assert market._detail_change.property("change") == "negative"
    market._show_overview()
    assert market._stage_filter.currentText() == "Primary Production"


def test_market_rows_mount_resource_icons_in_compact_industrial_wells(market):
    delegate = market._market_table.itemDelegate()
    source = inspect.getsource(MarketTableDelegate.paint)

    assert isinstance(delegate, MarketTableDelegate)
    assert delegate.sizeHint(None, market._lane_model.index(0, 0)).height() == 64
    assert "icon_well = QRectF" in source
    assert "icon_recess = icon_well.adjusted" in source
    assert 'QColor("#d2d4ce")' in source


def test_lanes_preserve_filter_sort_clicks_and_share_scroll(market):
    from PySide6.QtCore import Qt
    market._stage_filter.setCurrentText("All")
    table = market._market_table
    lanes = table.model()
    source = market._proxy_model
    assert lanes.columnCount() == 2
    assert lanes.rowCount() == (source.rowCount() + 1) // 2
    for sorting in ("Name", "Price", "24h Change"):
        market._sort.setCurrentText(sorting)
        actual = [lanes.index(row, column).data(Qt.ItemDataRole.UserRole)
                  for row in range(lanes.rowCount()) for column in range(2)
                  if lanes.index(row, column).data(Qt.ItemDataRole.UserRole)]
        expected = [source.index(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(source.rowCount())]
        assert actual == expected
    QApplication.processEvents()
    left, right = lanes.index(2, 0), lanes.index(2, 1)
    before = [table.visualRect(index).top() for index in (left, right)]
    table.verticalScrollBar().setValue(2)
    after = [table.visualRect(index).top() for index in (left, right)]
    assert before[0] == before[1]
    assert after[0] == after[1] < before[0]
    assert table.visualRect(left).right() < table.visualRect(right).left()
    for index in (left, right):
        expected_id = index.data(Qt.ItemDataRole.UserRole)
        table.clicked.emit(index)
        assert market._selected_resource_id == expected_id
        assert market._stack.currentIndex() == 1
        market._show_overview()
    market._search.setText("Iron Ore")
    assert source.rowCount() == 1
    assert lanes.rowCount() == 1
    empty = lanes.index(0, 1)
    assert not (lanes.flags(empty) & Qt.ItemFlag.ItemIsSelectable)
    table.clicked.emit(empty)
    assert market._stack.currentIndex() == 0
    market._search.setText("no matching resource xyz")
    assert lanes.rowCount() == 0


def test_event_hover_is_embedded_styled_and_updates(market):
    from PySide6.QtCore import QEvent, Qt
    header = market._header
    anchor = header._event_value[0]
    popup = header._event_popup
    market._state.market.active_event_id = next(event.event_id for event in MARKET_EVENTS if event.name == 'Industrial Boom')
    market.refresh()
    QApplication.sendEvent(anchor, QEvent(QEvent.Type.Enter))
    QApplication.processEvents()
    assert popup.isVisible()
    assert not popup.isWindow()
    assert not anchor.toolTip()
    assert popup.parentWidget() is market
    assert market.rect().contains(popup.geometry())
    assert popup.title.text() == 'INDUSTRIAL BOOM'
    assert popup.resources.palette().color(popup.resources.foregroundRole()).lightness() > 150
    for resource_id in active_market_event(market._state.market).affected_resources:
        assert escape(market._resources[resource_id].name) in popup.resources.text()
    folder = Path('artifacts/market-polish')
    folder.mkdir(parents=True, exist_ok=True)
    assert market.grab().save(str(folder / 'industrial-boom-hover.png'))
    market._state.market.active_event_id = next(event.event_id for event in MARKET_EVENTS if event.name != 'Industrial Boom')
    market.refresh()
    assert popup.title.text() == active_market_event(market._state.market).name.upper()
    assert market.rect().contains(popup.geometry())
    QApplication.sendEvent(anchor, QEvent(QEvent.Type.Leave))
    assert not popup.isVisible()
