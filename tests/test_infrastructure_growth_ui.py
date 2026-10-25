"""Building expansion quotes and storage confirmations through the real widgets."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabWidget, QWidget

from test_ui_interaction_recovery import app, window, board
from test_infrastructure_growth import buy
from production_zero.core.commands import ExpandFreightFacility, ExpandInventoryStorage
from production_zero.core.freight import freight_facility_expansion_cost
from production_zero.core.infrastructure_prices import unit_slot_price, unit_line_price
from production_zero.core.storage_upgrades import next_storage_capacity, inventory_storage_upgrade_cost
from production_zero.persistence.sqlite_store import serialize_game_state
from production_zero.ui.factory_view_v2 import FactoryV2LockedSlot, FactoryV2LockedLine
from production_zero.ui.freight_view import FreightView
from production_zero.ui.game_ui import GameButton


@pytest.mark.parametrize('name,kind', [('Factory', None), ('Energy', None),
    ('Resources', 'machine.extractor'), ('Resources', 'machine.drilling'), ('Resources', 'machine.agriculture')])
def test_later_building_slot_and_line_quotes_match_debits(window, name, kind):
    b = board(window, name); s = b._state; s.cash.amount = 1e12
    buy(s, name.lower(), kind)
    unit = buy(s, name.lower(), kind)
    assert unit.expansion_tier >= 2
    b._selected_hall_id = unit.hall_id; b.refresh_view(); QTest.qWait(10)
    slot = next(w for w in b.findChildren(FactoryV2LockedSlot) if w.isVisible()
                and w.property('slotNumber') == unit.start_slots_per_line + 1)
    quote = unit_slot_price(unit, 1, unit.start_slots_per_line + 1)
    assert slot.property('unlockCost') == quote
    cash = s.cash.amount; QTest.mouseClick(slot, Qt.MouseButton.LeftButton)
    assert cash - s.cash.amount == quote
    line = next(w for w in b.findChildren(FactoryV2LockedLine) if w.isVisible())
    quote = unit_line_price(unit, 2)
    assert line.property('unlockCost') == quote
    cash = s.cash.amount; line._unlock_button.click()
    assert cash - s.cash.amount == quote and unit.production_lines[1].unlocked


@pytest.mark.parametrize('kind', ['garage_depot', 'rail_station', 'airport', 'harbor'])
def test_later_freight_building_prices_and_runtime_line_guard(window, kind):
    f = window.findChild(FreightView); s = f._state; s.cash.amount = 1e12
    buy(s, 'freight', kind); unit = buy(s, 'freight', kind)
    f._selected_facility_id = unit.facility_id
    window.findChild(QTabWidget, 'mainTabs').setCurrentWidget(f); f.refresh(); QTest.qWait(10)
    line_button = next(w for w in f.findChildren(GameButton, 'unlockFreightLineButton') if w.isVisible())
    assert not line_button.isEnabled()
    target = len(unit.slots)
    slot = next(w for w in f.findChildren(QWidget, 'freightSlotCard') if w.isVisible()
                and w.property('slotIndex') == target)
    quote = freight_facility_expansion_cost(unit, slot_index=target)
    assert slot.property('unlockCost') == quote
    cash = s.cash.amount; QTest.mouseClick(slot, Qt.MouseButton.LeftButton); QTest.qWait(10)
    assert cash - s.cash.amount == quote
    for index in range(len(unit.slots), unit.line_capacity):
        ExpandFreightFacility(unit.facility_id, index).apply(s)
    f.refresh_runtime()
    line_button = next(w for w in f.findChildren(GameButton, 'unlockFreightLineButton') if w.isVisible())
    quote = freight_facility_expansion_cost(unit, slot_index=unit.line_capacity)
    assert line_button.isEnabled() and line_button.property('unlockCost') == quote
    s.cash.amount = quote - 1; f.refresh_runtime(); assert not line_button.isEnabled()
    s.cash.amount = quote; f.refresh_runtime(); assert line_button.isEnabled()
    line_button.click(); assert s.cash.amount == 0 and unit.line_capacity in unit.unlocked_slot_indexes()


@pytest.mark.parametrize('decision', ['buy', 'cancel', 'stale', 'no_cash'])
def test_storage_confirmation_matches_growth_including_research(window, monkeypatch, decision):
    from production_zero.core.research import research_catalog
    h = window._global_header; s = h._state; s.cash.amount = 1e12
    s.research.unlocked_node_ids.add(next(k for k, n in research_catalog()[1].items() if n.effect_type == 'storage_capacity'))
    s.warehouse_capacity += 1234
    for _ in range(2): ExpandInventoryStorage(h._resource_definitions).apply(s)
    current = s.storage_capacity; expected = next_storage_capacity(s, h._resource_definitions)
    level = s.inventory_storage_level; cost = inventory_storage_upgrade_cost(level)
    if decision == 'no_cash': s.cash.amount = 0
    before = serialize_game_state(s); notices = []
    monkeypatch.setattr('production_zero.ui.release_dialogs.inform', lambda *args: notices.append(args))
    def confirm(parent, title, text, *args):
        assert f'{current:,.0f} → {expected:,.0f} units' in text
        assert f'{expected-current:,.0f} units' in text and f'${cost:,.2f}' in text
        if decision == 'stale': ExpandInventoryStorage(h._resource_definitions).apply(s)
        return decision != 'cancel'
    monkeypatch.setattr('production_zero.ui.release_dialogs.confirm', confirm)
    h._expand_resource_storage()
    if decision == 'buy':
        assert s.storage_capacity == pytest.approx(expected)
        assert before['cash']['amount'] - s.cash.amount == cost
    elif decision in {'cancel', 'no_cash'}:
        assert serialize_game_state(s) == before
    else:
        assert s.inventory_storage_level == level + 1 and s.storage_capacity == pytest.approx(expected)
    assert bool(notices) == (decision in {'stale', 'no_cash'})


def test_storage_numeric_limit_is_reported_without_confirmation_or_spending(window, monkeypatch):
    h = window._global_header; s = h._state
    s.inventory_storage_level = 10000; s.cash.amount = 1e12
    before = serialize_game_state(s); notices = []
    monkeypatch.setattr('production_zero.ui.release_dialogs.inform', lambda *args: notices.append(args))
    monkeypatch.setattr('production_zero.ui.release_dialogs.confirm', lambda *args: pytest.fail('Invalid quote must not be offered.'))
    h._expand_resource_storage()
    assert serialize_game_state(s) == before
    assert notices and 'numeric range' in notices[-1][-1]
