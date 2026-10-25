"""Explicit release fixtures; no production behavior is replaced."""
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.freight import build_freight_facility


def purchase_state(*args, **kwargs):
    state = GameState(*args, **kwargs)
    state.halls['purchase-factory'] = FactoryHall('purchase-factory', 'Factory', 10)
    state.energy_plants['purchase-energy'] = FactoryHall('purchase-energy', 'Energy', 10, board_kind='energy')
    for family in ('extractor', 'drilling', 'agriculture'):
        key = 'purchase-' + family
        state.resource_sites[key] = FactoryHall(key, family, 10, specialization='machine.' + family, board_kind='resources')
    for facility in ('rail_station', 'airport', 'harbor'):
        build_freight_facility(state.freight, facility)
    return state


def legacy_component(window, cls):
    """Mount a retained legacy component explicitly for compatibility-only QA.

    Retired tabs are never created by the application. Inventory ships its card
    workspace; this harness explicitly mounts its old component for retained QA.
    """
    from PySide6.QtWidgets import QTabWidget
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.inventory_view import InventoryView
    from production_zero.ui.market_view import MarketView
    from production_zero.data.definitions import load_resource_definitions
    from importlib.resources import files
    board = window.findChild(FactoryViewV2)
    resources = load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')
    existing = next((view for view in window.findChildren(cls)
        if not (cls is InventoryView and view._release_mode)), None)
    if existing is not None:
        return existing
    if cls is InventoryView:
        view = cls(board._state, board._definitions, resources,
                   board._command_bus, release_mode=False)
    elif cls is MarketView:
        view = cls(board._state, resources)
    else:
        view = cls(board._state, board._command_bus, board._definitions)
    window.findChild(QTabWidget, 'mainTabs').addTab(view, 'Compatibility QA')
    from PySide6.QtWidgets import QWidget
    view.ensurePolished()
    for child in view.findChildren(QWidget):
        child.ensurePolished()
    return view
