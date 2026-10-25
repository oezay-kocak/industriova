"""P7 measured per-resource deliveries and presentation-only building order."""
from copy import deepcopy
import json
import pytest
from production_zero.core.freight_statistics import FreightDeliveryStatistics
from production_zero.core.building_order import ordered_building_ids
from production_zero.core.commands import ReorderBuildings
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.freight import FreightFacility
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore
from test_phase6_freight_statistics import definitions, company, depart, complete


@pytest.mark.parametrize('at', [0, .1, 29.999, 59.999, 60, 599.9])
@pytest.mark.parametrize('elapsed', [0, .1, 30, 59, 60, 61, 600, 1e9])
def test_resource_window_normalization_expiry_and_roundtrip(at, elapsed):
    stats = FreightDeliveryStatistics()
    stats.advance(at)
    stats.record('c', 'f', resource_id='iron_ore', sell=3, contract=4, consortium=5)
    stats.record_resource('iron_ore', event=2)
    stats.record('d', 'g', resource_id='coal', sell=99)
    stats.advance(elapsed)
    loaded = FreightDeliveryStatistics.from_snapshot(json.loads(json.dumps(stats.snapshot())))
    assert loaded.snapshot() == stats.snapshot()
    for rid in ['iron_ore', 'coal', 'absent']:
        assert loaded.resource_rate(rid) == stats.resource_rate(rid)
    rate = stats.resource_rate('iron_ore')
    duration = min(60, at + elapsed)
    factor = 60 / duration if duration else 0
    present = int(at + elapsed) - 60 < int(at)
    assert rate.total == pytest.approx(14 * factor if present else 0)
    assert rate.measuring == (duration < 60)
    if elapsed >= 600:
        assert not stats.resource_buckets


@pytest.mark.parametrize('target', ['market', 'contract', 'consortium'])
def test_real_completion_resource_attribution_exactly_once(definitions, target):
    from test_freight import _set_active_contract
    from production_zero.core.consortium import ConsortiumService, ConsortiumContract, ConsortiumPersonalReward
    s, u = company(definitions)
    uid = None
    if target == 'contract':
        _set_active_contract(s, 'daily', 'p7', 'iron_ore', 13)
        uid = 'p7'
    if target == 'consortium':
        team = ConsortiumService(s, definitions).create('Resource attribution')
        team.contracts['weekly'] = ConsortiumContract('p7', 'weekly', 'active', 0, 1e20, {'iron_ore':13}, ConsortiumPersonalReward(), 0)
        uid = f'{team.consortium_id}|weekly|p7'
    shipment = depart(s, definitions, target, 40, uid)
    assert s.freight.delivery_statistics.resource_rate('iron_ore').total == 0
    engine = complete(s, definitions, shipment)
    rate = s.freight.delivery_statistics.resource_rate('iron_ore')
    owner = s.freight.delivery_statistics.rate(card_id='truck-0')
    assert rate == owner
    assert rate.total == 40
    if target != 'market':
        assert rate.sell == 27
        assert (rate.contract if target == 'contract' else rate.consortium) == 13
    engine._complete_outbound_shipments(s, (shipment,))
    assert s.freight.delivery_statistics.resource_rate('iron_ore') == rate
    loaded = deserialize_game_state(serialize_game_state(s))
    assert loaded.freight.delivery_statistics.resource_rate('iron_ore') == rate


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1])
def test_invalid_resource_values_rejected_without_recording(bad):
    stats = FreightDeliveryStatistics()
    before = stats.snapshot()
    for key in ['sell', 'contract', 'consortium', 'event', 'at_seconds']:
        with pytest.raises(ValueError): stats.record_resource('iron_ore', **{key: bad})
        assert stats.snapshot() == before


def test_resource_history_is_bounded_and_aggregates_identical_arrivals():
    stats = FreightDeliveryStatistics()
    for _ in range(2000):
        stats.advance(.5)
        stats.record('v', 'f', resource_id='iron_ore', sell=1)
        stats.record('v', 'f', resource_id='iron_ore', contract=2)
    assert len(stats.resource_buckets) <= 600
    # The current half-full second is included; the boundary second is excluded.
    assert stats.resource_rate('iron_ore').total == 357
    assert stats.resource_rate('iron_ore') == stats.rate(card_id='v')
    assert stats.resource_rate('coal').total == 0


def test_shared_physical_contract_arrival_counts_resource_only_once(definitions):
    from test_freight import _set_active_contract
    s, u = company(definitions)
    quantities = {'regular':20, 'daily':13, 'weekly':7}
    for kind, quantity in quantities.items():
        _set_active_contract(s, kind, kind, 'iron_ore', quantity)
    shipment = depart(s, definitions, 'contract', 40)
    shipment.contract_allocations = dict(quantities)
    complete(s, definitions, shipment)
    assert s.freight.delivery_statistics.resource_rate('iron_ore').contract == 40
    assert s.freight.delivery_statistics.resource_rate('iron_ore').total == 40


def test_old_offline_arrival_expires_from_resource_window(definitions):
    from production_zero.core.simulation import SimulationEngine
    s,u=company(definitions)
    depart(s,definitions,quantity=40); u.paused=True
    SimulationEngine(definitions).advance_time(s,1000)
    assert s.freight.delivery_statistics.resource_rate('iron_ore').total == 0
    assert not s.freight.delivery_statistics.resource_buckets


@pytest.mark.parametrize('kind', ['resources', 'factory', 'freight'])
def test_order_is_persistent_and_does_not_change_economics(kind, tmp_path):
    s = GameState(1)
    units = s.freight.facilities if kind == 'freight' else s.production_units(kind)
    units.clear()
    for i in range(3):
        uid = f'building-{i}'
        units[uid] = FreightFacility(uid, uid, 'garage_depot') if kind == 'freight' else FactoryHall(uid, uid, i)
    before = serialize_game_state(s)
    ids = tuple(reversed(units))
    ReorderBuildings(kind, ids).apply(s)
    after = serialize_game_state(s)
    expected = deepcopy(before)
    expected['building_order'] = {kind: list(ids)}
    assert after == expected
    assert tuple(units) == tuple(before['freight']['facilities'] if kind == 'freight' else before['resource_sites' if kind == 'resources' else 'halls'])
    store = SQLiteSaveStore(tmp_path / 'order.sqlite'); store.initialize(); store.save('p7', s)
    loaded = store.load('p7')
    assert ordered_building_ids(loaded, kind, units) == ids
    # Sold IDs disappear; new buildings append without disturbing remaining order.
    assert ordered_building_ids(loaded, kind, ('building-0', 'new', 'building-2')) == ('building-2', 'building-0', 'new')
    before = serialize_game_state(s)
    for bad in [(), ids[:-1], (ids[0],)*3, ('unknown',)+ids[1:]]:
        with pytest.raises(ValueError): ReorderBuildings(kind, bad).apply(s)
        assert serialize_game_state(s) == before
