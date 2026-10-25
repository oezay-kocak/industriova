"""Offscreen regression captures and warm/cold Guide timing; never starts the real GUI."""

import os

os.environ['QT_QPA_PLATFORM'] = 'offscreen'



import json

import time

from pathlib import Path



from PySide6.QtCore import QPoint

from PySide6.QtGui import QFontDatabase, QFont

from production_zero.ui.theme import APP_STYLESHEET

from PySide6.QtTest import QTest

from PySide6.QtWidgets import QApplication, QLabel

from production_zero.core.commands import CommandBus, InstallCardInHall, SelectMachineProduction

from production_zero.data.definitions import load_card_definitions, load_resource_definitions

from production_zero.ui.main_window import _create_initial_state

from production_zero.ui.factory_view_v2 import FactoryViewV2

from production_zero.ui.supply_view import SupplyView, SupplyOfferCardFrame

from production_zero.ui.inventory_view import InventoryView





def main():

    app = QApplication.instance() or QApplication([])

    for name in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf", "arial.ttf", "agencyr.ttf"):

        QFontDatabase.addApplicationFont(str(Path("C:/Windows/Fonts") / name))

    app.setFont(QFont("Segoe UI", 10))

    app.setStyleSheet(APP_STYLESHEET)

    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))

    resources = load_resource_definitions(Path('src/production_zero/data/resource_definitions.json'))

    state = _create_initial_state(resources, definitions)

    assert not any(m.selected_production_id for m in state.machine_production.values())

    bus = CommandBus(state)

    output = Path('artifacts/playtest')

    output.mkdir(exist_ok=True)

    view = FactoryViewV2(state, bus, definitions)

    view.pause_simulation()

    view.resize(1500, 950)

    view.show(); app.processEvents()

    timings = []

    for _ in range(3):

        start = time.perf_counter()

        view._open_production_guide(); app.processEvents()

        timings.append(round((time.perf_counter() - start) * 1000, 1))

        view._close_drawer(); app.processEvents()

    view._open_chain_from_hall('copper_wire'); app.processEvents()

    view.grab().save(str(output / 'chain.png'))

    extraction = view._build_chain('copper_wire')

    raw = next(node for nodes in extraction.values() for node in nodes if node['resource_id'] == 'copper_ore')

    assert raw['input_resources'] == {}

    view._close_drawer(); app.processEvents()

    bus.dispatch(InstallCardInHall('hall-1', 0, 'test-drill-common-001'))

    bus.dispatch(SelectMachineProduction('test-drill-common-001', 'resource.copper_ore', 'copper_ore'))

    view.refresh_view(); app.processEvents()

    installed = view._slot_widgets[0]

    installed.hovered.emit('test-drill-common-001'); app.processEvents()

    assert view._selection_hover_popup.isVisible()

    view.grab().save(str(output / 'installed-tooltip.png'))

    view._hide_card_selection_hover()

    state.resources["iron"].amount = 7

    view._set_resources_drawer_open(True)

    view._resource_drawer._set_inventory_mode(True); app.processEvents()

    assert set(view._resource_drawer.summary._items) == {rid for rid, stock in state.resources.items() if stock.amount > 0}

    view.grab().save(str(output / 'stored.png'))

    state.resources["iron"].amount = 0

    view._resource_drawer.refresh()

    assert "iron" not in view._resource_drawer.summary._items

    view.close()



    supply = SupplyView(state, bus, definitions)

    supply.resize(1500, 950); supply.show(); app.processEvents()

    card = next(c for c in supply.findChildren(SupplyOfferCardFrame) if c.isVisible())

    offer_id = card.property('offerId')

    QTest.mouseMove(card, QPoint(40, 80)); QTest.qWait(350)

    assert supply._hover_popup and supply._hover_popup.isVisible()

    for _ in range(3):

        supply.refresh(); app.processEvents()

        assert card.property('offerId') == offer_id and card.isVisible()

    QTest.mouseMove(card._buy_button, card._buy_button.rect().center()); QTest.qWait(350)

    assert supply._hover_card is card and supply._hover_popup.isVisible()

    supply.grab().save(str(output / 'daily-tooltip.png'))

    source = card._source

    state.cash.amount = 100000

    supply._buy_offer(card._supply_data.offer, source); app.processEvents()

    locked = [c for c in supply.findChildren(SupplyOfferCardFrame) if c._source == source and c._state == 'locked']

    assert len(locked) == 3

    assert all(c._buy_button.text() == 'LOCKED\nUNTIL RESET' for c in locked)

    supply._hide_common_hover()

    supply.grab().save(str(output / 'daily-locked.png'))

    supply._show_section(1); app.processEvents()

    supply._buy_quantity.setCurrentIndex(1); app.processEvents()

    common = next(c for c in supply._common_card_pool if c.isVisible())

    assert common._buy_button.text() == "BUY ×4"

    owned_before = len(state.cards)

    cash_before = state.cash.amount

    price = common._supply_data.offer.price_cash

    common._buy_button.click(); app.processEvents()

    assert len(state.cards) == owned_before + 4

    assert state.cash.amount == cash_before - 4 * price

    supply.grab().save(str(output / 'common-buy-four.png'))

    state.cash.amount = price * 3

    supply.refresh()

    assert not common._buy_button.isEnabled()

    supply.close()



    inventory = InventoryView(state, definitions, resources, bus)

    inventory.resize(1500, 950); inventory.show(); app.processEvents()

    inventory._tabs.setCurrentIndex(3); app.processEvents()

    assert inventory._scrap_choice.count() > 0

    assert inventory._scrap_button.isEnabled()

    inventory.grab().save(str(output / 'scrap.png'))

    owned_before = len(state.cards)

    scrap_before = state.scrap.amount

    inventory._scrap_button.click(); app.processEvents()

    assert len(state.cards) == owned_before - 1

    assert state.scrap.amount > scrap_before

    assert 'test-drill-common-001' in state.cards

    inventory.close()

    result = {'guide_open_ms': timings, 'guide_tiles_created': view._guide_tile_create_count,

              'hover_survives_refresh_and_child_transition': True, 'stored_view_complete': True,

              'buy_four_click_and_affordability': True, 'scrap_click': True}

    (output / 'validation.json').write_text(json.dumps(result, indent=2))

    print(json.dumps(result))





if __name__ == '__main__':

    main()
