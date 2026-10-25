"""P5: own-production unlocks and XP at the actual Freight settlement boundary."""
from importlib.resources import files
import json
import sqlite3

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCash, AssignFreightCard, InstallFreightCard, SellResource, SellMachines
from production_zero.core.company import xp_required_for_next_level
from production_zero.core.company_xp import award_market_sale_xp
from production_zero.core.contracts import ActiveContract, ContractOffer, REGULAR
from production_zero.core.enums import Rarity
from production_zero.core.freight import OutboundFreightShipment
from production_zero.core.modifiers import market_sale_price
from production_zero.core.progression import (initial_production_ids, initialize_production_progress,
    production_options, record_lifetime_production, unlock_requirements_for, update_production_unlocks)
from production_zero.core.resources import create_resource_inventory
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import GAME_RULESET, SQLiteSaveStore, serialize_game_state, deserialize_game_state

D = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
R = load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')
OPTIONS = {o.output_resource: o for o in production_options(D)}
PRODUCTS = [o for o in OPTIONS.values() if o.input_resources]


def fresh():
    s = GameState(351, resources=create_resource_inventory(R))
    initialize_production_progress(s, D)
    return s


def truck(s):
    s.cards['truck'] = create_card_instance('truck', 'freight.truck', D['freight.truck'].card_kind, Rarity.COMMON)
    InstallFreightCard('garage-1', 0, 'truck', D).apply(s)
    AssignFreightCard('truck', 'iron_ore', 'market').apply(s)


def xp_total(s):
    return sum(xp_required_for_next_level(i) for i in range(1, s.company.level)) + s.company.current_xp


@pytest.mark.parametrize('level', (1, 25, 100))
def test_every_primary_is_free_and_level_alone_unlocks_no_product(level):
    s = fresh(); s.company.level = level
    update_production_unlocks(s, D)
    assert len(OPTIONS) == 353 and len(PRODUCTS) == 304
    assert len(initial_production_ids()) == 49
    assert s.production_progress.unlocked_production_ids == {o.production_id for o in OPTIONS.values() if not o.input_resources}


@pytest.mark.parametrize('option', PRODUCTS, ids=lambda o: o.output_resource)
def test_every_product_requires_100_own_units_of_each_direct_input_at_level_one(option):
    s = fresh()
    # Make each input's ancestors reachable, but leave the direct inputs below
    # the target's threshold. This exercises the real graph rather than levels.
    def ancestors(rid):
        for parent in OPTIONS[rid].input_resources:
            ancestors(parent)
            s.production_progress.lifetime_produced[parent] = 100
    for rid in option.input_resources: ancestors(rid)
    update_production_unlocks(s, D)
    for rid in option.input_resources:
        s.production_progress.lifetime_produced[rid] = 99
    update_production_unlocks(s, D)
    # A transitive ancestor may itself be a direct input, so reset the earned
    # set to the reachable prerequisites before checking the exact boundary.
    s.production_progress.unlocked_production_ids.discard(option.production_id)
    assert {r.quantity for r in unlock_requirements_for(option)} == {100}
    before_stocks = s.resource_snapshot()
    for index, rid in enumerate(option.input_resources):
        record_lifetime_production(s, {rid: 1}, D)
        assert (option.production_id in s.production_progress.unlocked_production_ids) == (index == len(option.input_resources) - 1)
    assert s.company.level == 1 and not s.company_xp_progress.xp_by_source
    assert s.resource_snapshot() == before_stocks
    # Unlocks survive spending/selling every input and never emit a second time.
    earned = tuple(s.production_progress.pending_unlock_ids)
    assert not record_lifetime_production(s, {}, D)
    assert tuple(s.production_progress.pending_unlock_ids) == earned


def test_entire_graph_can_be_traversed_from_roots_without_any_level_up():
    s = fresh(); produced = set()
    while len(produced) < len(OPTIONS):
        available = [o for o in OPTIONS.values() if o.production_id in s.production_progress.unlocked_production_ids and o.output_resource not in produced]
        assert available, 'Production graph is softlocked.'
        for option in available:
            record_lifetime_production(s, {option.output_resource: 100}, D)
            produced.add(option.output_resource)
    assert len(s.production_progress.unlocked_production_ids) == 353 and s.company.level == 1


def test_stock_cash_and_sales_cannot_substitute_for_own_production():
    s = fresh(); s.ensure_resource('iron_ore').amount = 10000
    AddCash(100000).apply(s)
    award_market_sale_xp(s, 100000, D)
    update_production_unlocks(s, D)
    assert 'recipe.processor.iron' not in s.production_progress.unlocked_production_ids
    assert s.production_progress.lifetime_produced == {}


def test_actual_sale_grants_fractional_xp_at_arrival_once_and_roundtrips_in_transit():
    s = fresh(); truck(s); s.ensure_resource('iron_ore').amount = .125
    SellResource('iron_ore', .125, D).apply(s)
    shipment = next(iter(s.freight.outbound_shipments.values()))
    engine = SimulationEngine(D, utc_now=lambda: 1000000)
    engine.advance_time(s, 59)
    assert not s.cash.amount and not s.company_xp_progress.xp_by_source
    s = deserialize_game_state(serialize_game_state(s))
    engine.advance_time(s, 1)
    assert s.cash.amount == .125 and xp_total(s) == pytest.approx(.0125)
    assert s.company_xp_progress.xp_by_source == {'market_sales': pytest.approx(.0125)}
    assert not s.freight.outbound_shipments
    restored = deserialize_game_state(serialize_game_state(s))
    engine.advance_time(restored, 600)
    assert restored.cash.amount == s.cash.amount and xp_total(restored) == xp_total(s)
    shipment.active = False; shipment.remaining_seconds = 0; shipment.economic_processed = True
    engine._complete_outbound_shipments(restored, [shipment])
    assert restored.cash.amount == s.cash.amount and xp_total(restored) == xp_total(s)


@pytest.mark.parametrize('destination', ('market', 'contract', 'consortium'))
def test_settlement_retry_never_duplicates_sale_xp(destination):
    s = fresh()
    shipment = OutboundFreightShipment('one', destination, target_id='missing', resource_id='iron_ore',
        quantity=25, market_price=1, active=False, remaining_seconds=0)
    engine = SimulationEngine(D, utc_now=lambda: 1000000)
    engine._complete_outbound_shipments(s, [shipment])
    assert s.cash.amount == 25 and xp_total(s) == 2.5
    for _ in range(5): engine._complete_outbound_shipments(s, [shipment])
    assert s.cash.amount == 25 and xp_total(s) == 2.5


@pytest.mark.parametrize('quantity', (40, 60))
def test_contract_reward_is_separate_and_only_real_surplus_sale_gets_market_xp(quantity):
    s = fresh()
    offer = ContractOffer('contract', REGULAR, 'Test contract', {'iron_ore': 40}, 1000, 150, 0)
    s.contracts.active[REGULAR] = ActiveContract(offer)
    shipment = OutboundFreightShipment('delivery', 'contract', target_id='contract', resource_id='iron_ore',
        quantity=quantity, market_price=1, active=False, remaining_seconds=0)
    SimulationEngine(D, utc_now=lambda: 1000000)._complete_outbound_shipments(s, [shipment])
    assert s.cash.amount == 1000 + quantity - 40
    assert s.company_xp_progress.xp_by_source['regular_contracts'] == 150
    assert s.company_xp_progress.xp_by_source.get('market_sales', 0) == (quantity - 40) * .1


def test_research_bonus_changes_actual_revenue_and_matching_sale_xp():
    from production_zero.core.research import research_catalog
    s = fresh(); truck(s); s.ensure_resource('iron_ore').amount = 20
    s.research.unlocked_node_ids = {k for k, n in research_catalog()[1].items() if n.effect_type == 'value'}
    quoted = market_sale_price(s, 'iron_ore') * 20
    assert quoted > 20
    SellResource('iron_ore', 20, D).apply(s)
    # A later bonus change must not reprice already dispatched market cargo.
    s.research.unlocked_node_ids.clear()
    SimulationEngine(D, utc_now=lambda: 1000000).advance_time(s, 60)
    assert s.cash.amount == pytest.approx(quoted)
    assert xp_total(s) == pytest.approx(quoted * .1)


def test_cash_grants_card_sales_and_idle_time_grant_no_market_xp():
    s = fresh(); s.cash.amount = 1000
    s.cards['spare'] = create_card_instance('spare', 'machine.processor', D['machine.processor'].card_kind, Rarity.COMMON)
    AddCash(100000).apply(s); SellMachines(('spare',), D).apply(s)
    SimulationEngine(D, utc_now=lambda: 1000000).advance_time(s, 600)
    assert not s.company_xp_progress.xp_by_source and xp_total(s) == 0


def test_fulfilled_consortium_contract_grants_its_reward_without_market_xp():
    from test_consortium import created, start
    from consortium_freight_fixture import freight_contribute
    from production_zero.core.consortium import CONSORTIUM_DAILY, COMPLETED
    s, api, consortium = created()
    contract = start(api, consortium, CONSORTIUM_DAILY)
    for rid, amount in contract.requirements.items():
        s.ensure_resource(rid).amount = amount
        freight_contribute(api, consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, rid, amount)
    assert contract.status == COMPLETED
    assert s.company_xp_progress.xp_by_source['consortium_daily'] > 0
    assert s.company_xp_progress.xp_by_source.get('market_sales', 0) == 0


def test_sales_are_linear_uncapped_and_award_level_research_points():
    s = fresh(); split = fresh()
    award_market_sale_xp(s, 30000, D)
    for _ in range(300): award_market_sale_xp(split, 100, D)
    assert xp_total(s) == xp_total(split) == 3000
    assert s.company.level == split.company.level > 1
    assert s.research.total_earned == split.research.total_earned == s.company.level - 1
    for _ in range(10): award_market_sale_xp(s, 30000, D)
    assert s.company_xp_progress.xp_by_source['market_sales'] == 33000
    assert 'continuity' not in s.company_xp_progress.xp_by_source


@pytest.mark.parametrize('earnings', (-1, float('nan'), float('inf')))
def test_invalid_sale_xp_does_not_mutate_state(earnings):
    s = fresh(); before = serialize_game_state(s)
    with pytest.raises(ValueError): award_market_sale_xp(s, earnings, D)
    assert serialize_game_state(s) == before


@pytest.mark.parametrize('dt', (.25, 1, 6, 60, 120))
def test_online_offline_and_save_reload_give_same_sale_xp(dt):
    def run(step, reload):
        s = fresh(); truck(s); s.ensure_resource('iron_ore').amount = 1000
        from production_zero.core.commands import AssignFreightCard
        AssignFreightCard('truck', 'iron_ore', 'market').apply(s)
        clock = [1000000.]; engine = SimulationEngine(D, utc_now=lambda: clock[0])
        for index in range(round(240 / step)):
            clock[0] += step; engine.advance_time(s, step)
            if reload and index + 1 == round(120 / step): s = deserialize_game_state(serialize_game_state(s))
        return s.cash.amount, xp_total(s), s.company_xp_progress.xp_by_source, s.resources['iron_ore'].amount
    assert run(dt, False) == run(1, False)
    assert run(dt, True) == run(1, False)


@pytest.mark.parametrize('ruleset', (None, 'old-test', 'future-test'))
def test_other_test_versions_are_rejected_before_reading_state(ruleset):
    payload = {'game_ruleset': ruleset}
    with pytest.raises(ValueError, match='new company'): deserialize_game_state(payload)


def test_previous_database_is_rejected_without_migration_backup_or_overwrite(tmp_path):
    store = SQLiteSaveStore(tmp_path / 'previous.sqlite'); store.initialize()
    old = serialize_game_state(fresh()); old.pop('game_ruleset')
    old['state_schema_version'] = 8
    text = json.dumps(old); store.save_payload('company', text)
    with pytest.raises(ValueError, match='new company'): store.load('company')
    with sqlite3.connect(tmp_path / 'previous.sqlite') as connection:
        assert connection.execute('SELECT state_json FROM saves WHERE slot=?', ('company',)).fetchone()[0] == text
    assert list(tmp_path.glob('*.sqlite')) == [tmp_path / 'previous.sqlite']


def test_current_save_keeps_sales_xp_and_unlocks_without_granting_xp_again(tmp_path):
    s = fresh(); award_market_sale_xp(s, 750, D)
    record_lifetime_production(s, {'iron_ore': 100}, D)
    store = SQLiteSaveStore(tmp_path / 'current.sqlite'); store.initialize(); store.save('company', s)
    for _ in range(3):
        s = store.load('company'); store.save('company', s)
        assert xp_total(s) == 75 and s.production_progress.lifetime_produced == {'iron_ore': 100}
        assert 'recipe.processor.iron' in s.production_progress.unlocked_production_ids
        assert serialize_game_state(s)['game_ruleset'] == GAME_RULESET
