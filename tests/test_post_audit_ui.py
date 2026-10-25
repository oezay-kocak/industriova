from __future__ import annotations
from release_test_support import legacy_component
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QWheelEvent
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QTabWidget
from shiboken6 import isValid
from production_zero.ui.factory_view_v2 import FactoryViewV2, FactoryCommandDeckWidget
from production_zero.ui.market_view import MarketView
from production_zero.ui.supply_view import SupplyView, SupplyOfferCardFrame
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.theme import Theme
from production_zero.tools import ui_contact_sheet

@pytest.fixture
def window(monkeypatch):
    # Even an old shell environment cannot select the retired implementation.
    monkeypatch.setenv('PRODUCTION_ZERO_FACTORY_VIEW_V2', '0')
    app = QApplication.instance() or QApplication([])
    ui_contact_sheet._load_qa_fonts()
    view = ui_contact_sheet.MainWindow()
    view.findChild(FactoryViewV2).pause_simulation()
    yield view
    view.close()
    view.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

def settle():
    for _ in range(8):
        QApplication.processEvents()

def test_product_and_offscreen_router_have_one_factory(window):
    tabs = window.findChild(QTabWidget, 'mainTabs')
    assert type(tabs.widget(1)) is FactoryViewV2
    assert type(window._global_header) is FactoryCommandDeckWidget
    assert window.findChild(QFrame, 'factoryHallCommandBoard') is None
    from production_zero.ui import factory_view
    assert not hasattr(factory_view, 'FactoryView')

@pytest.mark.parametrize('size', [(1366,768),(1600,980),(1920,1080)])
def test_actual_native_window_fits_every_tab(window,size):
    window.resize(*size)
    window.show()
    tabs = window.findChild(QTabWidget, 'mainTabs')
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        settle()
        assert (window.width(),window.height()) == size, tabs.tabText(index)

@pytest.mark.parametrize('size', [(1366,768),(1600,980)])
def test_daily_supply_readable_purchase_geometry(window,size):
    view = window.findChild(SupplyView)
    window.findChild(QTabWidget,'mainTabs').setCurrentWidget(view)
    window.resize(*size)
    window.show()
    settle()
    cards = view.findChildren(SupplyOfferCardFrame)
    daily = [card for card in cards if card._source in {'freight_daily','machine_daily'}]
    assert len(daily) == 8
    for card in daily:
        assert card.width() >= 80 and card.height() >= 106
        assert card.rect().contains(card._buy_button.geometry())
        assert card.rect().contains(card._price_label.geometry())
        assert not card._price_label.geometry().intersects(card._buy_button.geometry())
        assert card._price_label.width() >= card._price_label.fontMetrics().horizontalAdvance(card._price_label.text())
    for grid in view._daily_gallery_layouts:
        assert {(grid.getItemPosition(i)[0],grid.getItemPosition(i)[1]) for i in range(grid.count())} == {(0,0),(0,1),(0,2),(0,3)}
    assert view._daily_scroll.horizontalScrollBar().maximum() == 0
    assert view._daily_scroll.verticalScrollBar().maximum() == 0
    assert view._daily_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert view._daily_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    for gallery in view._daily_offer_galleries:
        assert gallery.horizontalScrollBar().maximum() == 0
        assert gallery.verticalScrollBar().maximum() == 0
    wheel = QWheelEvent(
        QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate, False,
    )
    assert view.eventFilter(view._daily_scroll.viewport(), wheel) is True
    assert view._daily_scroll.verticalScrollBar().value() == 0

def test_market_tick_preserves_control_identity_focus_and_selection(window):
    view = legacy_component(window, MarketView)
    window.findChild(QTabWidget,'mainTabs').setCurrentWidget(view)
    window.resize(1366,768)
    window.show()
    settle()
    chips = view.findChildren(QPushButton,'marketFilterChip')
    chip = next(c for c in chips if c.text() == 'PROCESSING')
    chip.click()
    chip.setFocus(Qt.FocusReason.TabFocusReason)
    for _ in range(3):
        view.refresh()
        QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        settle()
        assert all(isValid(c) for c in chips)
        assert view.findChildren(QPushButton,'marketFilterChip') == chips
        assert QApplication.focusWidget() is chip
        assert chip.property('active') is True
        assert view._stage_filter.currentText() == 'Processing'

@pytest.mark.parametrize('size,expected', [((1366,768),84),((1600,980),116)])
def test_contracts_header_responds_to_actual_tab_height(window,size,expected):
    view = window.findChild(ContractsView)
    window.findChild(QTabWidget,'mainTabs').setCurrentWidget(view)
    window.resize(*size)
    window.show()
    settle()
    assert view._header.height() == expected
    assert (view.height() < 650) == (expected == 84)

def test_current_guide_passive_tokens_are_neutral(window):
    factory = window.findChild(FactoryViewV2)
    factory._open_production_guide()
    assert factory.findChild(QFrame,'secondaryViewHeader') is not None
    for token in (Theme.GUIDE_CHASSIS_LIGHT,Theme.GUIDE_CHASSIS_MID,Theme.GUIDE_CHASSIS_DARK,
                  Theme.GUIDE_HEADER_START,Theme.GUIDE_HEADER_MID,Theme.GUIDE_HEADER_END):
        c = QColor(token)
        assert max(c.red(),c.green(),c.blue()) - min(c.red(),c.green(),c.blue()) <= 15
