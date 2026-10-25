from copy import deepcopy
from importlib.resources import files
import json
import sqlite3

import pytest

from production_zero.core.commands import (PurchaseHall, PurchaseProductionUnit, BuildFreightFacility,
    UnlockProductionSlot, UnlockProductionLine, ExpandFreightFacility, ExpandInventoryStorage)
from production_zero.core.freight import (FreightFacility, FreightSlot, FREIGHT_FACILITY_START_SLOTS,
    freight_facility_expansion_cost, freight_expansion_problem)
from production_zero.core.infrastructure_prices import (BOARD_LIMITS, RESOURCE_TYPES, expansion_key,
    unit_slot_price, unit_line_price, scaled_expansion_price, production_facility_price)
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.storage_upgrades import (global_storage_base_capacity, global_storage_capacity,
    inventory_storage_multiplier, inventory_storage_upgrade_cost, next_storage_capacity)
from production_zero.data.definitions import load_resource_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore

R = load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')
TYPES = [('factory', None), ('energy', None), *(('resources', k) for k in sorted(RESOURCE_TYPES)),
         *(('freight', k) for k in FREIGHT_FACILITY_START_SLOTS)]


def state():
    s = deserialize_game_state(serialize_game_state(GameState(351)))
    s.cash.amount = 1e12
    s.warehouse_capacity = global_storage_base_capacity(R)
    return s


def buy(s, board, kind):
    if board == 'freight':
        before = set(s.freight.facilities)
        BuildFreightFacility(kind).apply(s)
        return s.freight.facilities[next(k for k in s.freight.facilities if k not in before)]
    limits = BOARD_LIMITS[board]
    before = set(s.production_units(board))
    PurchaseProductionUnit(board, board, board, limits[0], limits[1], 1, limits[2], kind).apply(s)
    return s.production_units(board)[next(k for k in s.production_units(board) if k not in before)]


def clear_type(s, board, kind):
    units = s.freight.facilities if board == 'freight' else s.production_units(board)
    for uid, unit in list(units.items()):
        actual = unit.facility_type if board == 'freight' else unit.specialization
        if board not in {'resources', 'freight'} or actual == kind:
            del units[uid]
    s.infrastructure_tiers.pop(expansion_key(board, kind), None)


@pytest.mark.parametrize('board,kind', TYPES)
def test_new_buildings_scale_slots_and_lines_by_stable_square_tier(board, kind):
    s = state(); clear_type(s, board, kind)
    for tier in (1, 2, 3, 4):
        unit = buy(s, board, kind)
        assert unit.expansion_tier == tier
        if board == 'freight':
            assert freight_facility_expansion_cost(unit, slot_index=7) == 60 * (8 - FREIGHT_FACILITY_START_SLOTS[kind]) * tier ** 2
            assert freight_facility_expansion_cost(unit, slot_index=8) == 900 * tier ** 2
        else:
            start = BOARD_LIMITS[board][2]
            base = {'factory': 40, 'resources': 90, 'energy': 100}[board]
            assert unit_slot_price(unit, 1, start + 1) == base * tier ** 2
            reference = deepcopy(unit); reference.expansion_tier = 1
            assert unit_line_price(unit, 2) == unit_line_price(reference, 2) * tier ** 2


@pytest.mark.parametrize('board,kind', TYPES)
def test_tier_survives_reordering_renaming_sale_and_reload(board, kind):
    s = state(); clear_type(s, board, kind)
    first, second = buy(s, board, kind), buy(s, board, kind)
    units = s.freight.facilities if board == 'freight' else s.production_units(board)
    second.name = 'A renamed building'
    uid = lambda u: u.facility_id if board == 'freight' else u.hall_id
    units.pop(uid(first))
    restored = deserialize_game_state(serialize_game_state(s))
    restored_units = restored.freight.facilities if board == 'freight' else restored.production_units(board)
    assert restored_units[uid(second)].expansion_tier == 2
    rebuilt = buy(restored, board, kind)
    assert rebuilt.expansion_tier == 3
    again = deserialize_game_state(serialize_game_state(restored))
    assert again.infrastructure_tiers[expansion_key(board, kind)] == 3


def test_legacy_purchase_hall_command_uses_same_tiers():
    s = state(); s.halls.clear(); s.infrastructure_tiers.pop('factory', None)
    for tier in (1, 2, 3):
        PurchaseHall().apply(s)
        unit = next(reversed(s.halls.values()))
        assert unit.expansion_tier == tier
        before = s.cash.amount
        UnlockProductionSlot(unit.hall_id, unit.production_lines[0].line_id, 'factory', 40 * tier ** 2).apply(s)
        assert before - s.cash.amount == 40 * tier ** 2


@pytest.mark.parametrize('board,kind', TYPES)
def test_other_building_types_do_not_raise_this_types_tier(board, kind):
    s = state(); clear_type(s, board, kind)
    if board == 'resources':
        other = next(k for k in RESOURCE_TYPES if k != kind)
        buy(s, board, other); buy(s, board, other)
    elif board == 'freight':
        other = next(k for k in FREIGHT_FACILITY_START_SLOTS if k != kind)
        buy(s, board, other); buy(s, board, other)
    else:
        buy(s, 'resources', 'machine.drilling')
    assert buy(s, board, kind).expansion_tier == 1


@pytest.mark.parametrize('kind', tuple(FREIGHT_FACILITY_START_SLOTS))
@pytest.mark.parametrize('tier', (1, 2, 5))
def test_freight_requires_full_preceding_line_and_quotes_match_debits(kind, tier):
    s = state()
    unit = FreightFacility('test', 'Test', kind, FREIGHT_FACILITY_START_SLOTS[kind], expansion_tier=tier)
    s.freight.facilities = {'test': unit}
    before = serialize_game_state(s)
    with pytest.raises(ValueError, match='Complete all slots'):
        ExpandFreightFacility('test', 8, 900 * tier ** 2).apply(s)
    assert serialize_game_state(s) == before
    for target in range(len(unit.slots), 8):
        price = freight_facility_expansion_cost(unit, slot_index=target)
        cash = s.cash.amount
        ExpandFreightFacility('test', target, price).apply(s)
        assert cash - s.cash.amount == price
    assert not freight_expansion_problem(unit, 8)
    for line in (1, 2, 3):
        target = line * 8
        next_line = freight_facility_expansion_cost(unit, slot_index=target)
        assert next_line > freight_facility_expansion_cost(unit, slot_index=target - 1)
        ExpandFreightFacility('test', target, next_line).apply(s)
        for slot in range(target + 1, target + 8):
            ExpandFreightFacility('test', slot, freight_facility_expansion_cost(unit, slot_index=slot)).apply(s)


@pytest.mark.parametrize('capacity', (8, 16, 32, 64))
def test_last_slot_always_costs_less_than_next_freight_line(capacity):
    unit = FreightFacility('x', 'X', slot_count=3, line_capacity=capacity, expansion_tier=3)
    for line in range(1, 10):
        assert freight_facility_expansion_cost(unit, slot_index=line * capacity - 1) < freight_facility_expansion_cost(unit, slot_index=line * capacity)


def test_legacy_sparse_lines_are_preserved_and_can_fill_their_paid_slots():
    s = state(); unit = s.freight.facilities['garage-1']
    unit.slots = [FreightSlot(i) for i in range(17)]
    unit.slot_count = 17; unit.purchased_slot_indexes = {0, 1, 2, 8, 16}
    old = serialize_game_state(s); old['infrastructure_pricing_version'] = 1
    loaded = deserialize_game_state(old); unit = loaded.freight.facilities['garage-1']
    assert set(unit.unlocked_slot_indexes()) == {0, 1, 2, 8, 16}
    ExpandFreightFacility('garage-1', 9).apply(loaded)
    assert 9 in unit.unlocked_slot_indexes()
    with pytest.raises(ValueError):
        ExpandFreightFacility('garage-1', 24).apply(loaded)


@pytest.mark.parametrize('level', (0, 1, 2, 5, 10, 20))
def test_storage_growth_matches_preview_and_keeps_goods(level):
    s = state(); s.inventory_storage_level = level
    s.warehouse_capacity = global_storage_capacity(R, level)
    s.ensure_resource('coal').amount = 99
    before, cash = s.storage_capacity, s.cash.amount
    preview = next_storage_capacity(s, R)
    ExpandInventoryStorage(R, level, inventory_storage_upgrade_cost(level)).apply(s)
    assert s.storage_capacity == pytest.approx(before * 1.25)
    assert s.storage_capacity == pytest.approx(preview)
    assert s.resources['coal'].amount == 99
    assert cash - s.cash.amount == inventory_storage_upgrade_cost(level)


def test_successive_storage_gains_increase_and_prices_stay_on_existing_schedule():
    base = global_storage_base_capacity(R)
    assert [inventory_storage_upgrade_cost(i) for i in range(3)] == [250, 2000, 6750]
    gains = [global_storage_capacity(R, i + 1) - global_storage_capacity(R, i) for i in range(25)]
    assert gains[0] == base * .25
    assert all(b > a for a, b in zip(gains, gains[1:]))


@pytest.mark.parametrize('level', (0, 1, 2, 5, 10))
def test_old_storage_migrates_once_and_preserves_extra_capacity(level):
    s = state(); base = global_storage_base_capacity(R)
    s.inventory_storage_level = level
    s.warehouse_capacity = base * (1 + .25 * level) + 1234
    s.ensure_resource('coal').amount = 200000
    payload = serialize_game_state(s); payload['infrastructure_pricing_version'] = 1
    restored = deserialize_game_state(payload)
    assert restored.warehouse_capacity == pytest.approx(global_storage_capacity(R, level) + 1234)
    assert restored.resources['coal'].amount == 200000
    expected = serialize_game_state(restored)
    for _ in range(3):
        restored = deserialize_game_state(serialize_game_state(restored))
        assert serialize_game_state(restored) == expected


def test_old_building_tiers_use_numeric_ids_not_dictionary_or_name_order():
    s = state(); s.halls = {f'hall-{i}': FactoryHall(f'hall-{i}', f'Name {20-i}', 3) for i in (10, 2, 1)}
    payload = serialize_game_state(s); payload['infrastructure_pricing_version'] = 1
    payload.pop('infrastructure_tiers')
    for unit in payload['halls'].values():
        unit.pop('expansion_tier')
    restored = deserialize_game_state(payload)
    assert {k: u.expansion_tier for k, u in restored.halls.items()} == {'hall-1': 1, 'hall-2': 2, 'hall-10': 3}


@pytest.mark.parametrize('case', ('stale_slot', 'stale_line', 'no_cash', 'storage_overflow', 'storage_stale'))
def test_failed_purchases_do_not_change_money_tiers_or_slots(case):
    s = state(); unit = buy(s, 'factory', None)
    if case == 'stale_slot':
        command = UnlockProductionSlot(unit.hall_id, unit.production_lines[0].line_id, 'factory', 41)
    elif case == 'stale_line':
        command = UnlockProductionLine(unit.hall_id, unit.production_lines[1].line_id, 'factory', 901)
    elif case == 'no_cash':
        s.cash.amount = 0
        command = PurchaseHall()
    elif case == 'storage_stale':
        command = ExpandInventoryStorage(R, 100, 250)
    else:
        s.inventory_storage_level = 10000
        command = ExpandInventoryStorage(R)
    before = serialize_game_state(s)
    with pytest.raises(ValueError):
        command.apply(s)
    assert serialize_game_state(s) == before


@pytest.mark.parametrize('tier', (0, -1, True, 1.5))
def test_invalid_tiers_are_rejected(tier):
    with pytest.raises(ValueError):
        scaled_expansion_price(40, tier)
    with pytest.raises(ValueError):
        FactoryHall('x', 'X', 3, expansion_tier=tier)


def test_infrastructure_upgrade_has_a_readable_database_backup(tmp_path):
    s = state(); s.inventory_storage_level = 3
    s.warehouse_capacity = global_storage_base_capacity(R) * 1.75
    payload = serialize_game_state(s); payload['infrastructure_pricing_version'] = 1
    path = tmp_path / 'company.sqlite'; store = SQLiteSaveStore(path); store.initialize()
    store.save_payload('company', json.dumps(payload))
    restored = store.load('company')
    backup = tmp_path / 'company.pre-infrastructure-v2.sqlite'
    assert backup.exists()
    with sqlite3.connect(backup) as connection:
        assert json.loads(connection.execute('SELECT state_json FROM saves WHERE slot=?', ('company',)).fetchone()[0]) == payload
    store.save('company', restored)
    assert serialize_game_state(store.load('company')) == serialize_game_state(restored)
