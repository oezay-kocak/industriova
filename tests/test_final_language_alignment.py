from release_test_support import legacy_component
"""Behavior and rendered contrast coverage for the final, scoped UI pass."""
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QTabWidget

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.packs_view import PacksView
from production_zero.ui.theme import Theme
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView
from production_zero.core.commands import AddResource, SetResourceCapacity
from production_zero.core.simulation import SimulationEngine
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from test_factory_ui import _app, _add_freight_inventory_card, _install_freight_from_drawer


@pytest.fixture
def window():
    app = _app()
    w = MainWindow()
    w.findChild(FactoryViewV2).pause_simulation()
    w.resize(1366, 768)
    w.show()
    app.processEvents()
    yield w
    w.close()
    w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def cargo(window):
    g = window.findChild(FreightView)
    window.findChild(QTabWidget, 'mainTabs').setCurrentWidget(g)
    _add_freight_inventory_card(g, 'final-truck', 'freight.truck')
    _install_freight_from_drawer(g, 0, 'final-truck')
    for stock in g._state.resources.values():
        stock.amount = 0
    g._open_assignment_view('final-truck')
    return g


def tiles(g):
    return {t.property('resourceId'): t for t in g.findChildren(QFrame, 'freightAssignmentResourceTile')}


def test_owned_cargo_filters_live_stock_and_preserves_search(window):
    g = cargo(window)
    assert not tiles(g)
    assert g.findChild(QLabel, 'emptyStateTitle').text() == 'NO CARGO AVAILABLE'
    g._state.ensure_resource('steel').amount = 0.25
    g._state.ensure_resource('iron_ore').amount = 10
    g._state.ensure_resource('coal').amount = -1
    g.refresh_runtime()
    assert set(tiles(g)) == {'steel', 'iron_ore'}
    steel = tiles(g)['steel']
    assert steel.findChild(QLabel, 'freightAssignmentTileStock').text() == '0.25 STORED'
    search = g.findChild(QLineEdit, 'freightAssignmentSearch')
    search.setText('STEEL')
    assert tiles(g) == {'steel': steel}
    g._state.resources['steel'].amount = 0
    g.refresh_runtime()
    assert not tiles(g)
    assert g.findChild(QLabel, 'emptyStateTitle').text() == 'NO AVAILABLE CARGO'
    assert g.findChild(QLineEdit, 'freightAssignmentSearch') is search
    assert search.text() == 'STEEL'
    g._select_assignment_resource('steel')
    assert 'final-truck' not in g._state.freight.assignments
    g._state.resources['steel'].amount = 3
    g.refresh_runtime()
    assert set(tiles(g)) == {'steel'}
    search.clear()
    g._set_assignment_category_filter('Energy')
    assert not tiles(g)
    assert g.findChild(QLabel, 'emptyStateTitle').text() == 'NO AVAILABLE CARGO'


def test_cargo_then_target_confirm_and_zero_stock_route_survives_save(window):
    g = cargo(window)
    g._state.ensure_resource('steel').amount = 3
    g.refresh_runtime()
    tiles(g)['steel'].selected.emit('steel')
    assert 'final-truck' not in g._state.freight.assignments
    assert g._route_dialog.isVisible()
    g._choose_assignment_destination('market')
    g._confirm_assignment()
    assert g._assignment_card_id is None
    assert not g.findChildren(QFrame, 'freightAssignmentResourceTile')
    assert g.findChild(QPushButton, 'freightApplyMarketAssignmentButton') is None
    assignment = g._state.freight.assignments['final-truck']
    assert (assignment.resource_id, assignment.destination_kind) == ('steel', 'market')
    g._open_assignment_view('final-truck')
    assert tiles(g)['steel'].property('selected') is True
    g._state.resources['steel'].amount = 0
    g.refresh_runtime()
    assert g._state.freight.assignments['final-truck'] == assignment
    loaded = deserialize_game_state(serialize_game_state(g._state))
    assert loaded.freight.assignments['final-truck'] == assignment
    from production_zero.core.commands import CommandBus
    bus = CommandBus(loaded)
    bus.dispatch(SetResourceCapacity('steel', 100))
    bus.dispatch(AddResource('steel', 10))
    SimulationEngine(g._definitions).advance_time(loaded, 1)
    assert loaded.resources['steel'].amount == 0
    assert loaded.freight.assignments['final-truck'] == assignment


def test_immediate_market_route_keeps_transit_lock_and_contract_priority(window):
    from production_zero.core.contracts import DAILY
    from test_freight import _set_active_contract
    g = cargo(window)
    g._state.ensure_resource('steel').amount = 10
    _set_active_contract(g._state, DAILY, 'final-delivery', 'steel', 6)
    g._select_assignment_resource('steel')
    g._choose_assignment_destination('market')
    g._confirm_assignment()
    engine = SimulationEngine(g._definitions)
    engine.advance_time(g._state, 1)
    g._state.ensure_resource('copper_ore').amount = 5
    g._open_assignment_view('final-truck')
    assert g._assignment_card_is_busy()
    assert all(tile.isEnabled() for tile in tiles(g).values())
    original = next(iter(g._state.freight.outbound_shipments.values()))
    g._select_assignment_resource('copper_ore')
    assert g._state.freight.assignments['final-truck'].resource_id == 'steel'
    g._confirm_assignment()
    assert g._state.freight.assignments['final-truck'].resource_id == 'copper_ore'
    assert original.resource_id == 'steel' and original.quantity == 10
    engine.advance_time(g._state, 60)
    g.refresh_runtime()
    assert original.shipment_id not in g._state.freight.outbound_shipments
    delivery = g._state.freight.completed_market_deliveries[-1]
    assert (delivery.delivered_amount, delivery.contract_amount, delivery.market_amount) == (10, 0, 10)
    assert g._state.contracts.active[DAILY].status == 'active'
    assert g._state.contracts.active[DAILY].delivered == {}


@pytest.mark.parametrize('resource,count', [('bauxite', 1), ('iron', 3)])
def test_used_in_compact_action_and_secondary_contrast(window, resource, count):
    f = window.findChild(FactoryViewV2)
    f._open_chain_from_guide(resource)
    _app().processEvents()
    action = f.findChild(QPushButton, 'guideUsedInOpenButton')
    assert action.text() == f"USED IN\n{count} {'PRODUCT' if count == 1 else 'PRODUCTS'}  >"
    assert (action.width(), action.height()) == (142, 68)
    title = f.findChild(QLabel, 'sectionLabel')
    assert title.palette().color(QPalette.ColorRole.WindowText).name() == Theme.TEXT
    canvas = f.findChild(ZoomPanGraphicsView, 'chainInspectorCanvas')
    assert canvas is not None and canvas.content_widget is not None
    box = canvas.content_widget.findChild(QFrame, 'chainResourceBox')
    assert box is not None
    assert box.findChild(QLabel, 'chainResourceName').palette().color(QPalette.ColorRole.WindowText).name() == Theme.TEXT
    shell = next(p for p in f.findChildren(QFrame) if p.property('secondaryShell'))
    image = shell.grab().toImage()
    assert image.pixelColor(image.width() // 2, 5).lightnessF() > 0.6


def test_packs_empty_canvas_is_light_and_text_is_dark(window):
    p = legacy_component(window, PacksView)
    window.findChild(QTabWidget, 'mainTabs').setCurrentWidget(p)
    p.refresh(force=True)
    _app().processEvents()
    title = p.findChild(QLabel, 'emptyStateTitle')
    assert title is not None and title.text() == 'NO UNOPENED PACKS'
    assert title.palette().color(QPalette.ColorRole.WindowText).name() == Theme.TEXT_ON_LIGHT_PRIMARY
    point = p._pack_scroll.viewport().mapTo(p, QPoint(10, 10))
    image = p.grab().toImage()
    assert image.pixelColor(point).lightnessF() > 0.6
