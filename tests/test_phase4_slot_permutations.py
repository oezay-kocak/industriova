"""P4 permutations are prevalidated against the complete resulting placement."""
from dataclasses import replace
from importlib.resources import files
import itertools
import pytest
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.commands import CommandBus, MoveMachines, MoveFreightVehicles
from production_zero.core.state import GameState, FactoryHall, MachineProductionState
from production_zero.core.freight import FreightFacility, FreightAssignment, OutboundFreightShipment
from production_zero.core.machine_operations import installed_slot_snapshot, plan_slot_permutation
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.data.definitions import load_card_definitions


@pytest.fixture
def definitions():
    return load_card_definitions(files('production_zero.data') / 'game_definitions.json')


def fixture(definitions, board='factory', size=10, occupied=None):
    state = GameState(rng_seed=197)
    did = {'factory': 'machine.processor', 'resources': 'machine.extractor',
           'energy': 'energy.solar_array', 'freight': 'freight.truck'}[board]
    if board == 'freight':
        state.freight.facilities.clear()
        unit = FreightFacility('a', 'a', slot_count=size)
        state.freight.facilities['a'] = unit
    else:
        unit = FactoryHall('a', 'a', size, board_kind=board, max_lines=1,
                           max_slots_per_line=size, start_unlocked_lines=1, start_slots_per_line=size)
        state.production_units(board)['a'] = unit
    for i in range(size if occupied is None else occupied):
        cid = f'c{i}'
        state.cards[cid] = replace(create_card_instance(cid, did, definitions[did].card_kind, Rarity.LEGENDARY),
                                  mk_level=50, acquisition_cost=123.45+i, upgrade_investment=50+i, paused=bool(i % 2))
        unit.slots[i].card_id = cid
        if board == 'freight':
            state.freight.assignments[cid] = FreightAssignment('iron_ore', 'market')
        else:
            state.machine_production[cid] = MachineProductionState(cid, 'iron', 'recipe.processor.iron', 2.5+i)
    return state, unit


def command(state, defs, board, ids, indexes, unit='a', **kwargs):
    if board == 'freight':
        return MoveFreightVehicles(tuple(ids), unit, tuple(indexes), defs, **kwargs)
    return MoveMachines(tuple(ids), board, unit, tuple(indexes), **kwargs)


@pytest.mark.parametrize('board', ['factory', 'resources', 'energy', 'freight'])
@pytest.mark.parametrize('count', [1, 2, 5, 10])
def test_full_occupied_swap_keeps_instances_cycles_cash_routes_and_roundtrip(definitions, board, count):
    s, u = fixture(definitions, board, 20)
    before = serialize_game_state(s)
    cards = dict(s.cards)
    bus = CommandBus(s)
    bus.dispatch(command(s, definitions, board, [f'c{i}' for i in range(count)], range(10, 10+count)))
    assert [slot.card_id for slot in u.slots[:count]] == [f'c{i}' for i in range(10, 10+count)]
    assert [slot.card_id for slot in u.slots[10:10+count]] == [f'c{i}' for i in range(count)]
    assert all(s.cards[cid] is card for cid, card in cards.items())
    after = serialize_game_state(s)
    for key in ('cards', 'cash', 'machine_production', 'history'):
        assert after[key] == before[key]
    assert after['freight']['assignments'] == before['freight']['assignments']
    assert after['freight']['outbound_shipments'] == before['freight']['outbound_shipments']
    loaded = deserialize_game_state(after)
    assert serialize_game_state(deserialize_game_state(serialize_game_state(loaded))) == serialize_game_state(loaded)
    if board == 'freight':
        assert [slot.card_id for slot in loaded.freight.facilities['a'].slots] == [slot.card_id for slot in u.slots]
    else:
        assert [slot.card_id for slot in loaded.production_units(board)['a'].slots] == [slot.card_id for slot in u.slots]


@pytest.mark.parametrize('board', ['factory', 'freight'])
@pytest.mark.parametrize('targets,expected', [((1,2), ['c2','c0','c1','c3',None,None]),
    ((1,4), [None,'c0','c2','c3','c1',None]), ((4,5), [None,None,'c2','c3','c0','c1']),
    ((1,0), ['c1','c0','c2','c3',None,None]), ((0,1), ['c0','c1','c2','c3',None,None])])
def test_overlapping_paths_closed_cycles_and_empty_endpoints(definitions, board, targets, expected):
    s, u = fixture(definitions, board, 6, occupied=4)
    command(s, definitions, board, ('c0','c1'), targets).apply(s)
    assert [slot.card_id for slot in u.slots] == expected


@pytest.mark.parametrize('board', ['factory', 'freight'])
@pytest.mark.parametrize('case', ['duplicate-id','duplicate-target','missing','negative','bool','unowned',
                                  'duplicate-origin','stale','locked-origin','missing-unit','unknown-counterpart'])
def test_rejected_group_is_whole_state_and_bus_history_atomic(definitions, board, case):
    s, u = fixture(definitions, board)
    ids, targets, uid, kwargs = ('c0','c1'), (5,6), 'a', {}
    if case == 'duplicate-id': ids = ('c0','c0')
    if case == 'duplicate-target': targets = (5,5)
    if case == 'missing': targets = (5,99)
    if case == 'negative': targets = (5,-1)
    if case == 'bool': targets = (5,True)
    if case == 'unowned': s.cards.pop('c1')
    if case == 'duplicate-origin': u.slots[9].card_id = 'c1'
    if case == 'stale':
        kwargs['expected_origins'] = installed_slot_snapshot(s, ids)
        u.slots[0].card_id, u.slots[2].card_id = u.slots[2].card_id, u.slots[0].card_id
    if case == 'locked-origin':
        if board == 'freight': u.slots.pop(1)
        else: u.production_lines[0].slot_indexes.remove(1)
    if case == 'missing-unit': uid = 'gone'
    if case == 'unknown-counterpart': u.slots[6].card_id = 'unowned'
    before = serialize_game_state(s)
    bus = CommandBus(s)
    with pytest.raises(ValueError): bus.dispatch(command(s, definitions, board, ids, targets, uid, **kwargs))
    assert serialize_game_state(s) == before and not bus.history


@pytest.mark.parametrize('board', ['factory','resources','energy','freight'])
def test_cross_facility_swap_validates_both_directions(definitions, board):
    s, a = fixture(definitions, board, 4)
    if board == 'freight':
        b = FreightFacility('b', 'b', slot_count=4); s.freight.facilities['b'] = b
    else:
        b = FactoryHall('b','b',4,board_kind=board); s.production_units(board)['b'] = b
    a.slots[2].card_id = None; b.slots[0].card_id = 'c2'
    command(s, definitions, board, ('c0',), (0,), 'b').apply(s)
    assert a.slots[0].card_id == 'c2' and b.slots[0].card_id == 'c0'


@pytest.mark.parametrize('case', ['reverse-energy','reverse-freight','mixed-final-site','fixed-site','whole-site'])
def test_compatibility_uses_complete_final_state(definitions, case):
    board = 'freight' if case == 'reverse-freight' else 'energy' if case == 'reverse-energy' else 'resources'
    s, a = fixture(definitions, board, 4)
    if board == 'freight':
        # Forward move is legal; only the displaced train's reverse move fails.
        b = FreightFacility('b','b',slot_count=4); s.freight.facilities['b'] = b
        did = 'freight.train'
    else:
        b = FactoryHall('b','b',4,board_kind=board); s.production_units(board)['b'] = b
        did = 'machine.processor' if board == 'energy' else 'machine.drilling'
    s.cards['other'] = create_card_instance('other',did,definitions[did].card_kind,Rarity.COMMON)
    b.slots[0].card_id = 'other'
    if case == 'fixed-site': b.specialization = did
    before = serialize_game_state(s)
    ids, targets = (('c0','c1','c2','c3'),(0,1,2,3)) if case == 'whole-site' else (('c0',),(0,))
    if case == 'whole-site':
        command(s, definitions, board, ids, targets, 'b').apply(s)
        assert a.specialization == 'machine.drilling' and b.specialization == 'machine.extractor'
    else:
        with pytest.raises(ValueError): command(s, definitions, board, ids, targets, 'b').apply(s)
        assert serialize_game_state(s) == before


@pytest.mark.parametrize('busy', ['c0','c1','c5','c6'])
@pytest.mark.parametrize('remaining,quantity', [(30,0),(0,12),(30,12)])
def test_busy_sources_and_displaced_reserved_cargo_reject_entire_freight_group(definitions,busy,remaining,quantity):
    s, u = fixture(definitions,'freight')
    s.freight.outbound_shipments['reserved'] = OutboundFreightShipment('reserved','market',resource_id='iron_ore',
        quantity=quantity,freight_card_id=busy,remaining_seconds=remaining,transport_capacity=40,market_price=7)
    before = serialize_game_state(s)
    with pytest.raises(ValueError, match='reserved delivery'):
        command(s,definitions,'freight',('c0','c1'),(5,6)).apply(s)
    assert serialize_game_state(s) == before


def test_exhaustive_small_slot_assignments_are_bijections(definitions):
    # All injective two-card mappings over a full four-slot board, including
    # both overlaps, self-edges, cycles and all empty endpoint combinations.
    for occupied in (2,3,4):
        for targets in itertools.permutations(range(4),2):
            s,u = fixture(definitions,'factory',4,occupied=occupied)
            command(s,definitions,'factory',('c0','c1'),targets).apply(s)
            assert u.slots[targets[0]].card_id == 'c0' and u.slots[targets[1]].card_id == 'c1'
            assert sorted(slot.card_id for slot in u.slots if slot.card_id) == sorted(s.cards)


@pytest.mark.parametrize('board',['factory','resources','energy','freight'])
def test_sqlite_save_load_repeats_exact_permutation_and_all_nonplacement_state(definitions,board,tmp_path):
    from production_zero.persistence.sqlite_store import SQLiteSaveStore
    s,u=fixture(definitions,board,10)
    before=serialize_game_state(s)
    command(s,definitions,board,('c0','c1','c2'),(2,3,4)).apply(s)
    after=serialize_game_state(s)
    def without_placement(payload):
        import copy
        payload=copy.deepcopy(payload)
        for name in ('halls','resource_sites','energy_plants'):
            for unit in payload[name].values():
                unit.pop('specialization',None)
                for slot in unit['slots']:slot['card_id']=None
        for unit in payload['freight']['facilities'].values():
            for slot in unit['slots']:slot['card_id']=None
        return payload
    assert without_placement(before)==without_placement(after)
    store=SQLiteSaveStore(tmp_path/'permutation.sqlite');store.initialize()
    for _ in range(3):
        store.save('p4',s);s=store.load('p4')
    loaded_unit=s.freight.facilities['a'] if board=='freight' else s.production_units(board)['a']
    assert [slot.card_id for slot in loaded_unit.slots]==[slot.card_id for slot in u.slots]
    assert without_placement(serialize_game_state(s))==without_placement(serialize_game_state(deserialize_game_state(after)))
