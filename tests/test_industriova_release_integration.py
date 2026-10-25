from dataclasses import replace
from importlib.resources import files
import json

import pytest
from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AssignFreightCard, CommandBus, InstallFreightCard, PurchaseProductionUnit, InstallCardInHall
from production_zero.core.contracts import ContractOffer, ActiveContract, refresh_contracts
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility, FreightAssignment, start_outbound_shipment_for_card
from production_zero.core.machine_operations import pause_machines, configure_machines, copy_configuration, paste_configuration, resale_value
from production_zero.core.market import BASE_MARKET_PRICES, LEGACY_BASE_MARKET_PRICES, market_price_for, advance_market_time
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState, FactoryHall, HallSlot, MachineProductionState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore
from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot, SessionWriter


@pytest.fixture
def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def freight_company(definitions):
    state = GameState(rng_seed=12)
    state.warehouse_capacity = 1e6
    card = create_card_instance("truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    state.cards[card.card_id] = card
    facility = build_freight_facility(state.freight, "garage_depot")
    InstallFreightCard(facility.facility_id, 0, card.card_id, definitions).apply(state)
    state.ensure_resource("iron_ore").amount = 1000
    return state, card


def test_fixed_sale_does_not_also_deliver_to_contract(definitions):
    state, card = freight_company(definitions)
    state.freight.assignments[card.card_id] = FreightAssignment("iron_ore", "market")
    offer = ContractOffer("test-contract", "regular", "Test", {"iron_ore": 1000}, 200, 20, 0)
    state.contracts.active["regular"] = ActiveContract(offer)
    engine = SimulationEngine(definitions)
    engine.advance_time(state, 0.)
    shipment = next(iter(state.freight.outbound_shipments.values()))
    quantity = shipment.quantity
    before_cash = state.cash.amount
    engine.advance_time(state, 60.)
    assert state.cash.amount - before_cash == pytest.approx(quantity * BASE_MARKET_PRICES["iron_ore"])
    assert state.contracts.active["regular"].delivered == {}


def test_route_change_preserves_inflight_goods_and_applies_after_arrival(definitions):
    state, card = freight_company(definitions)
    AssignFreightCard(card.card_id, "iron_ore", "market").apply(state)
    engine = SimulationEngine(definitions)
    engine.advance_time(state, 0.)
    before = serialize_game_state(state)["freight"]["outbound_shipments"]
    AssignFreightCard(card.card_id, "coal", "contract").apply(state)
    assert serialize_game_state(state)["freight"]["outbound_shipments"] == before
    engine.advance_time(state, 60.)
    assert state.cash.amount > 0
    assert state.freight.assignments[card.card_id] == FreightAssignment("coal", "contract")


def test_paused_freight_finishes_reserved_trip_without_loading_again(definitions):
    state, card = freight_company(definitions)
    AssignFreightCard(card.card_id, "iron_ore", "market").apply(state)
    engine = SimulationEngine(definitions)
    engine.advance_time(state, 0.)
    remaining_stock = state.resources["iron_ore"].amount
    pause_machines(state, (card.card_id,), True)
    engine.advance_time(state, 60.)
    assert not state.freight.outbound_shipments
    assert state.resources["iron_ore"].amount == remaining_stock
    assert state.cash.amount > 0


def test_resource_site_rejects_wrong_family_without_losing_card(definitions):
    state = GameState(rng_seed=1)
    state.resource_sites["site"] = FactoryHall("site", "Mining", 3, board_kind="resources", specialization="machine.extractor")
    card = create_card_instance("drilling", "machine.drilling", CardKind.MACHINE, Rarity.COMMON)
    state.cards[card.card_id] = card
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        InstallCardInHall("site", 0, card.card_id, "resources").apply(state)
    assert serialize_game_state(state) == before


def test_overfull_warehouse_rejects_partial_recipe_without_consuming_inputs(definitions):
    state = GameState(rng_seed=1)
    state.warehouse_capacity = 1.
    card = create_card_instance("processor", "machine.processor", CardKind.MACHINE, Rarity.COMMON)
    definition = definitions[card.definition_id]
    recipe = definition.available_production_options[0]
    state.cards[card.card_id] = card
    state.halls["h"] = FactoryHall("h", "Hall", 1, slots=[HallSlot(0, card.card_id)])
    state.machine_production[card.card_id] = MachineProductionState(card.card_id, recipe.output_resource, recipe.production_id)
    for rid in recipe.input_resources:
        state.ensure_resource(rid).amount = 10000.
    before = state.resource_snapshot()
    SimulationEngine(definitions).advance_time(state, 60.)
    assert state.machine_production[card.card_id].status == "storage_full"
    assert all(state.resources[rid].amount == amount for rid, amount in before.items())


def test_copy_paste_changes_configuration_only_and_invalid_group_is_atomic(definitions):
    state = GameState(rng_seed=2)
    state.production_progress.unlocked_production_ids.update(o.production_id for d in definitions.values() if isinstance(d, MachineDefinition) for o in d.available_production_options)
    for cid, did in (("a", "machine.processor"), ("b", "machine.processor"), ("c", "machine.assembler")):
        state.cards[cid] = create_card_instance(cid, did, CardKind.MACHINE, Rarity.COMMON)
    recipe = definitions["machine.processor"].available_production_options[0]
    state.machine_production["a"] = MachineProductionState("a", recipe.output_resource, recipe.production_id)
    copied = copy_configuration(state, ("a",))
    cash, cards = state.cash.amount, dict(state.cards)
    paste_configuration(state, definitions, ("b",), copied)
    assert state.machine_production["b"].selected_production_id == recipe.production_id
    assert state.cash.amount == cash and state.cards == cards
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        paste_configuration(state, definitions, ("b", "c"), copied * 2)
    assert serialize_game_state(state) == before


def test_eleventh_hall_uses_existing_quote_and_cash_validation():
    state = GameState(rng_seed=3)
    state.cash.amount = 1e12
    for index in range(10):
        state.halls[str(index)] = FactoryHall(str(index), "Hall", 6)
    from production_zero.core.infrastructure_prices import facility_price
    original_halls = serialize_game_state(state)['halls']
    cash = state.cash.amount
    PurchaseProductionUnit("factory", "Hall", "hall", 5, 10, 2, 3).apply(state)
    assert len(state.halls) == 11
    assert state.cash.amount == cash - facility_price('factory', 10)
    assert all(serialize_game_state(state)['halls'][hid] == data for hid, data in original_halls.items())
    state.cash.amount = 0
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        PurchaseProductionUnit("factory", "Hall", "hall", 5, 10, 2, 3).apply(state)
    assert serialize_game_state(state) == before


def test_prices_remain_fixed_and_processing_has_positive_input_value_margin(definitions):
    state = GameState(rng_seed=3)
    before = {rid: market_price_for(state.market, rid) for rid in BASE_MARKET_PRICES}
    advance_market_time(state.market, 1e7, state.rng_seed)
    assert before == {rid: market_price_for(state.market, rid) for rid in BASE_MARKET_PRICES}
    for definition in definitions.values():
        if not isinstance(definition, MachineDefinition):
            continue
        for recipe in definition.available_production_options:
            if not recipe.input_resources:
                assert BASE_MARKET_PRICES[recipe.output_resource] == LEGACY_BASE_MARKET_PRICES[recipe.output_resource]
                continue
            revenue = BASE_MARKET_PRICES[recipe.output_resource] * recipe.output_amount_for(definition)
            inputs = sum(BASE_MARKET_PRICES[rid] * n for rid, n in recipe.input_resources.items())
            assert revenue > inputs


def test_freight_hierarchy_has_substantial_effective_throughput_growth(definitions):
    rates = [definitions[did].base_capacity / definitions[did].base_transport_time_seconds for did in ("freight.truck", "freight.train", "freight.aircraft", "freight.ship")]
    assert rates[1]>=rates[0]*4 and rates[2]>=rates[1]*3 and rates[3]==pytest.approx(rates[2]*3)


@pytest.mark.parametrize("level", [1, 2, 10, 50, 99])
def test_fuel_and_power_scale_together_and_fuel_ratio_is_two_plants(definitions, level):
    from production_zero.core.mk_upgrades import mk_factor
    state = GameState(rng_seed=1)
    state.warehouse_capacity = 1e9
    card = replace(create_card_instance("coal-plant", "energy.coal_power_plant", CardKind.ENERGY, Rarity.COMMON), mk_level=level)
    state.cards[card.card_id] = card
    state.energy_plants["p"] = FactoryHall("p", "Power", 1, board_kind="energy", slots=[HallSlot(0, card.card_id)])
    state.ensure_resource("coal").amount = 100000
    totals = SimulationEngine(definitions).advance_time(state, 60.)
    assert totals.inputs["coal"] == pytest.approx(60 * mk_factor(level))
    assert totals.gross_power == pytest.approx(60 * mk_factor(level))
    source = definitions["machine.extractor"]
    recipe = next(p for p in source.available_production_options if p.output_resource == "coal")
    assert recipe.output_amount_for(source) * 60 / recipe.cycle_seconds_for(source) == 2 * definitions["energy.coal_power_plant"].fuel_consumption_per_minute


def test_snapshot_encoder_preserves_prefix_and_commit_order(tmp_path):
    state = GameState(rng_seed=6)
    state.history.append("cash", 42.)
    snap = snapshot_game_state(state)
    state.history.append("cash", 99.)
    assert json.loads(encode_snapshot(snap))["history"]["cash"]["values"] == [42.]
    store = SQLiteSaveStore(tmp_path / "company.sqlite")
    store.initialize()
    writer = SessionWriter(store)
    try:
        writer.submit(snap)
        writer.submit(snapshot_game_state(state))
        assert writer.poll(wait=True) is None
        assert store.load("company").history.series["cash"].values == [42., 99.]
    finally:
        writer.shutdown()


def test_legacy_sqlite_is_backed_up_before_migration(tmp_path):
    import sqlite3
    from contextlib import closing
    state = GameState(rng_seed=9)
    state.cards["legacy"] = create_card_instance("legacy", "machine.extractor", CardKind.MACHINE, Rarity.RARE)
    payload = serialize_game_state(state)
    payload["state_schema_version"] = 4
    payload["cards"]["legacy"]["definition_id"] = "machine.extractor.mk3"
    payload["cards"]["legacy"].pop("mk_level")
    store = SQLiteSaveStore(tmp_path / "company.sqlite")
    store.initialize()
    original = json.dumps(payload)
    store.save_payload("company", original)
    migrated = store.load("company")
    assert migrated.cards["legacy"].mk_level == 3
    with closing(sqlite3.connect(tmp_path / "company.pre-industriova-v5.sqlite")) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT state_json FROM saves WHERE slot='company'").fetchone()[0] == original


def test_release_commands_record_success_and_reject_failed_batch_without_history(definitions):
    from production_zero.core.commands import UpgradeMachines, PauseMachines
    state = GameState(rng_seed=4)
    state.cash.amount = 1e9
    state.cards["valid"] = create_card_instance("valid", "machine.processor", CardKind.MACHINE, Rarity.COMMON)
    state.cards["maxed"] = replace(state.cards["valid"], card_id="maxed", mk_level=99)
    bus = CommandBus(state)
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        bus.dispatch(UpgradeMachines(("valid", "maxed"), definitions))
    assert serialize_game_state(state) == before and not bus.history
    bus.dispatch(PauseMachines(("valid",), True))
    bus.dispatch(UpgradeMachines(("valid",), definitions))
    assert len(bus.history) == 2 and state.cards["valid"].mk_level == 2 and state.cards["valid"].paused


def test_consortrium_reserved_cargo_is_counted_once_without_second_stock_debit(definitions):
    from production_zero.core.consortium import ConsortiumService
    state, card = freight_company(definitions)
    service = ConsortiumService(state, definitions)
    from tests.contract_capacity_fixture import provide_capacity
    provide_capacity(state,definitions)
    group = service.create("Release QA", "open", 1)
    state.company.level = 200
    state.production_progress.unlocked_production_ids.update(p.production_id for d in definitions.values() if isinstance(d, MachineDefinition) for p in d.available_production_options)
    for definition in definitions.values():
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                state.ensure_resource(option.output_resource).amount = max(1., state.ensure_resource(option.output_resource).amount)
    candidates = service.contract_candidates(group.consortium_id, "daily")
    contract = service.start_contract(group.consortium_id, service.current_company_id, "daily", tuple(candidates[:3]))
    rid = next(iter(contract.requirements))
    state.ensure_resource(rid).amount = 0.
    amount = min(1., contract.requirements[rid])
    from consortium_freight_fixture import freight_receive
    state.ensure_resource(rid).amount = amount
    delivered = freight_receive(service,group.consortium_id, "daily", contract.contract_id, rid, amount, "reserved-123")
    assert delivered == amount
    assert state.resources[rid].amount == 0.
    assert freight_receive(service,group.consortium_id, "daily", contract.contract_id, rid, amount, "reserved-123") == 0.
    assert contract.delivered[rid] == amount


def test_repeated_contract_dispatch_does_not_reserve_the_same_requirement_twice(definitions):
    from production_zero.core.contracts import ActiveContract, ContractOffer, DAILY, deliver_available_to_contract
    from production_zero.core.commands import AssignFreightCard
    state, card = freight_company(definitions)
    from production_zero.core.contracts import initialize_contracts
    initialize_contracts(state, definitions)
    state.contracts.active[DAILY] = ActiveContract(ContractOffer('dispatch-once', DAILY, 'Dispatch', {'steel': 5}, 50, 10, 0))
    state.contracts.offers[DAILY] = [state.contracts.active[DAILY].offer]
    CommandBus(state).dispatch(AssignFreightCard(card.card_id, 'steel', 'contract'))
    state.ensure_resource('steel').amount = 50
    first = deliver_available_to_contract(state, DAILY, definitions)
    second = deliver_available_to_contract(state, DAILY, definitions)
    assert first == {'steel': 5} and second == {}
    assert state.resources['steel'].amount == 45
    assert sum(s.quantity for s in state.freight.outbound_shipments.values()) == 5


def test_last_freight_building_sale_is_rejected_atomically():
    from production_zero.core.commands import SellFreightBuilding
    state = GameState(rng_seed=1)
    before = serialize_game_state(state)
    bus = CommandBus(state)
    with pytest.raises(ValueError, match='Keep one'):
        bus.dispatch(SellFreightBuilding('garage-1'))
    assert serialize_game_state(state) == before and bus.history == ()
