from dataclasses import replace
from datetime import datetime, timezone
from importlib.resources import files
import json

import pytest

from production_zero.core.research import (
    ResearchState, cooldown_remaining, grant_research_points, node_state,
    purchase_research, research_catalog, research_domains, research_from_dict,
    respec_research, sync_research_clock, validate_catalog,
)
from production_zero.core.modifiers import Modifier, contract_cash_quote, market_sale_price, modifier_bonus
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.resources import create_resource_inventory
from production_zero.core.company import xp_required_for_next_level
from production_zero.core.company_xp import award_contract_company_xp
from production_zero.core.contracts import (
    DAILY, WEEKLY, REGULAR, ContractOffer, accept_contract, initialize_contracts,
    receive_contract_delivery,
)
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.commands import AddCard, AssignFreightCard, CommandBus, InstallFreightCard, SellResource
from production_zero.core.freight import freight_stats
from production_zero.core.analytics import calculate_resource_flows
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore, serialize_game_state, deserialize_game_state


@pytest.fixture(scope="module")
def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


@pytest.fixture
def state():
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    return GameState(rng_seed=19, resources=create_resource_inventory(resources))


def buy(state, *ids):
    for nid in ids:
        purchase_research(state, nid)


def test_catalog_covers_every_canonical_resource_and_recipe_output(definitions):
    trees, nodes = research_catalog()
    domains = research_domains()
    raw = json.loads(files("production_zero.data").joinpath("research_domains.json").read_text(), object_pairs_hook=lambda pairs: pairs)
    assert len(raw) == len(dict(raw)) == 353
    assert len(trees) == 21 and len(nodes) == 645
    assert sum(n.node_type == "major" for n in nodes.values()) == 105
    for definition in definitions.values():
        for option in getattr(definition, "available_production_options", ()):
            assert option.output_resource in domains
            assert set(option.input_resources) <= domains.keys()
    assert {domains[r] for r in ("copper_ore", "copper", "copper_wire")} == {"metals"}
    assert domains["polymer"] == "chemicals" and domains["microchip"] == "electronics"
    for tree in trees.values():
        own = [n for n in nodes.values() if n.tree_id == tree.id]
        assert len(own) == (35 if tree.family == "company" else 29) and sum(n.node_type == "major" for n in own) == 5
        assert tree.icon_resource in domains
        assert all(n.cost == 1 and n.icon_resource in domains for n in own)
        if tree.family == "industry":
            assert all(n.effect_type == "value" for n in own)
            assert all(n.effect_target == tree.id.split(".")[1] if n.effect_scope == "domain" else domains[n.effect_target] == tree.id.split(".")[1] for n in own)


def test_prerequisites_and_bad_catalog_are_validated():
    trees, nodes = research_catalog()
    mid = "industry.metals.s2.major"
    assert len(nodes[mid].prerequisites) == 3
    broken = dict(nodes)
    broken[mid] = replace(nodes[mid], prerequisites=(mid,))
    with pytest.raises(ValueError, match="prerequisite"):
        validate_catalog(trees, broken, research_domains())
    broken[mid] = replace(nodes[mid], effect_type="industry_speed")
    with pytest.raises(ValueError, match="effect"):
        validate_catalog(trees, broken, research_domains())


def test_points_purchase_cost_and_major_gate(state):
    nodes = research_catalog()[1]
    major = "industry.metals.s1.major"
    assert node_state(state.research, nodes[major]) == "unfunded"
    with pytest.raises(ValueError):
        purchase_research(state, major)
    grant_research_points(state, 8, "test")
    with pytest.raises(ValueError):
        purchase_research(state, "industry.metals.s2.major")
    buy(state, major)
    assert state.research.available == 7 and state.research.spent == 1
    with pytest.raises(ValueError):
        purchase_research(state, major)
    # Lane order is free, but every second-row node needs its first-row parent.
    with pytest.raises(ValueError):
        purchase_research(state, "industry.metals.s1.n6")
    for i in (3, 6, 2, 5, 1):
        buy(state, f"industry.metals.s1.n{i}")
    with pytest.raises(ValueError):
        purchase_research(state, "industry.metals.s2.major")
    buy(state, "industry.metals.s1.n4", "industry.metals.s2.major")
    assert state.research.available == 0 and state.research.total_earned == 8
    assert any("Development ready" in label for _, label in state.communications.pending_activity)


def test_level_up_grants_one_per_level_and_no_retroactive_credit(state, definitions):
    amount = sum(xp_required_for_next_level(level) for level in range(1, 4))
    award_contract_company_xp(state, amount, definitions, source="test")
    assert state.company.level == 4 and state.research.total_earned == 3
    award_contract_company_xp(state, 1, definitions, source="test")
    assert state.research.total_earned == 3


@pytest.mark.parametrize("kind,points", [(DAILY, 1), (WEEKLY, 3), (REGULAR, 0)])
def test_authoritative_contract_completion_grants_once(state, definitions, kind, points):
    state.company.level = 200  # Avoid incidental XP level rewards in this test.
    initialize_contracts(state, definitions)
    original = state.contracts.offers[kind][0]
    offer = replace(original, balance_version=0, requirements={"iron_ore": 2.0, "wheat": 3.0})
    state.contracts.offers[kind] = [offer]
    accept_contract(state, kind, offer.contract_id, definitions)
    receive_contract_delivery(state, offer.contract_id, "iron_ore", 2, definitions)
    assert state.research.total_earned == 0
    receive_contract_delivery(state, offer.contract_id, "wheat", 3, definitions)
    assert state.research.total_earned == points
    receive_contract_delivery(state, offer.contract_id, "wheat", 3, definitions)
    assert state.research.total_earned == points


def test_additive_value_no_recipe_inheritance_and_exact_product(state):
    grant_research_points(state, 20, "test")
    buy(state, "company.general.s1.major", "industry.metals.s1.major", "industry.metals.s1.n1", "industry.metals.s1.n2", "industry.metals.s1.n3", "industry.metals.s1.n6", "industry.chemicals.s1.major", "industry.electronics.s1.major", "industry.electronics.s1.n3", "industry.electronics.s1.n6")
    assert modifier_bonus(state.research, "value", "copper_wire") == pytest.approx(.018)
    assert modifier_bonus(state.research, "value", "copper") == pytest.approx(.018)
    assert modifier_bonus(state.research, "value", "microchip") == pytest.approx(.014)
    assert modifier_bonus(state.research, "value", "cpu") == pytest.approx(.014)
    assert modifier_bonus(state.research, "value", "wheat") == pytest.approx(.005)
    assert modifier_bonus(state.research, "production_speed", "microchip") == 0
    # Exact-product capability remains available to future systems, outside this catalog.
    extra = (Modifier("value", "global", "*", .01), Modifier("value", "domain", "electronics", .02), Modifier("value", "product", "cpu", .003))
    assert modifier_bonus(state.research, "value", "microchip", additional=extra) == pytest.approx(.044)
    assert modifier_bonus(state.research, "value", "cpu", additional=extra) == pytest.approx(.047)


def test_market_dispatch_and_payout_use_research_snapshot(state, definitions):
    grant_research_points(state, 2, "test")
    buy(state, "industry.metals.s1.major", "company.freight.s1.major")
    bus = CommandBus(state)
    truck = create_card_instance("research-truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(truck))
    bus.dispatch(InstallFreightCard("garage-1", 0, truck.card_id, definitions))
    bus.dispatch(AssignFreightCard(truck.card_id, "copper", "market"))
    state.ensure_resource("copper").amount = 100
    base = state.market.ensure_resource("copper").current_price
    assert market_sale_price(state, "copper") == pytest.approx(base * 1.005)
    bus.dispatch(SellResource("copper", 10, definitions))
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.market_price == pytest.approx(base * 1.005)
    assert shipment.transport_capacity == pytest.approx(freight_stats(truck, definitions[truck.definition_id]).capacity * 1.005)
    respec_research(state, now=100)
    assert market_sale_price(state, "copper") == base
    engine = SimulationEngine(definitions)
    engine.advance_time(state, shipment.remaining_seconds)
    assert state.cash.amount == pytest.approx(shipment.quantity * base * 1.005)


def test_multi_product_contract_quote_acceptance_and_payout(state, definitions):
    grant_research_points(state, 3, "test")
    buy(state, "industry.metals.s1.major", "company.general.s1.major", "company.contracts.s1.major")
    state.company.level = 200
    initialize_contracts(state, definitions)
    requirements = {"copper": 10, "microchip": 20, "wheat": 30}
    prices = {rid: state.market.ensure_resource(rid).current_price for rid in requirements}
    expected = 10 * prices["copper"] * 1.015 + (20 * prices["microchip"] + 30 * prices["wheat"]) * 1.01
    assert contract_cash_quote(state, requirements) == pytest.approx(expected)
    state.contracts.active.pop(DAILY, None)
    offer = replace(state.contracts.offers[DAILY][0], balance_version=0, requirements=requirements, reward_cash=round(expected*1.2, 2))
    state.contracts.offers[DAILY] = [offer]
    accept_contract(state, DAILY, offer.contract_id, definitions)
    active = state.contracts.active[DAILY]
    assert active.offer.requirements == requirements
    assert active.offer.reward_cash == round(expected*1.2, 2)
    respec_research(state, now=100)
    for rid, amount in requirements.items():
        receive_contract_delivery(state, offer.contract_id, rid, amount, definitions)
    assert state.cash.amount == round(expected*1.2, 2)


def test_respec_refund_cooldown_reallocation_and_clock_rollback(state):
    grant_research_points(state, 3, "test")
    buy(state, "company.general.s1.major", "company.storage.s1.major")
    base_capacity = state.warehouse_capacity
    assert state.storage_capacity == pytest.approx(base_capacity * 1.01)
    assert respec_research(state, now=1000) == 2
    assert state.research.total_earned == state.research.available == 3
    assert state.storage_capacity == base_capacity
    assert modifier_bonus(state.research, "value", "copper") == 0
    assert cooldown_remaining(state.research, 1000) == 86_400
    buy(state, "company.general.s1.major")
    with pytest.raises(ValueError, match="cooling"):
        respec_research(state, now=999)
    sync_research_clock(state, now=87_400)
    assert cooldown_remaining(state.research, 1) == 0
    before = len(state.communications.pending_activity)
    sync_research_clock(state, now=87_401)
    assert len(state.communications.pending_activity) == before
    assert respec_research(state, now=87_401) == 1


def test_sqlite_roundtrip_does_not_compound_storage_and_old_save_zero(state, tmp_path):
    grant_research_points(state, 12, "test")
    buy(state, "company.storage.s1.major")
    respec_research(state, now=100)
    buy(state, "company.storage.s1.major", "industry.aerospace.s1.major")
    state.research.saved_allocations["Future"] = tuple(state.research.unlocked_node_ids)
    store = SQLiteSaveStore(tmp_path / "research.sqlite")
    store.initialize()
    capacity = state.storage_capacity
    for _ in range(3):
        store.save("test", state)
        state = store.load("test")
        assert state.storage_capacity == capacity
        assert state.research.total_earned == 12 and state.research.available == 10
        assert state.research.respec_available_at == 86_500
        assert state.research.saved_allocations["Future"]
    payload = serialize_game_state(state)
    del payload["research"]
    migrated = deserialize_game_state(payload)
    assert migrated.research == ResearchState()


def test_removed_nodes_refunded_and_invalid_saves_rejected():
    state = research_from_dict(dict(total_earned=5, unlocked_node_ids=["removed.node", "industry.metals.s2.major"]))
    assert state.available == 5 and not state.unlocked_node_ids
    for payload in ([], dict(saved_allocations={"bad": "not a list"}), dict(total_earned=-1), dict(total_earned=0, unlocked_node_ids=["company.general.s1.major"]), dict(total_earned=2, respec_available_at=float("nan"))):
        with pytest.raises(ValueError):
            research_from_dict(payload)


def test_global_speed_scales_input_and_output_rates_together(state, definitions):
    state.halls["test"] = FactoryHall("test", "Test", 6)
    for i, did in enumerate(("machine.extractor", "machine.processor", "machine.fabricator", "machine.assembler")):
        card = create_card_instance(f"m{i}", did, CardKind.MACHINE, Rarity.COMMON)
        state.cards[card.card_id] = card
        state.halls["test"].slots[i].card_id = card.card_id
        option = definitions[did].available_production_options[0]
        state.ensure_machine_production(card.card_id, option.output_resource, option.production_id)
    before = calculate_resource_flows(state, definitions)
    grant_research_points(state, 1, "test")
    buy(state, "company.production.s1.major")
    after = calculate_resource_flows(state, definitions)
    for rid, flow in before.items():
        assert after[rid].produced_per_minute == pytest.approx(flow.produced_per_minute * 1.005)
        assert after[rid].consumed_per_minute == pytest.approx(flow.consumed_per_minute * 1.005)


def test_energy_generation_preview_and_tick_match(state, definitions):
    card = create_card_instance("sun", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)
    state.cards[card.card_id] = card
    state.energy_plants["power"] = FactoryHall("power", "Power", 6)
    state.energy_plants["power"].slots[0].card_id = card.card_id
    now = datetime(2026, 1, 1)
    engine = SimulationEngine(definitions, utc_now=lambda: now)
    base = engine.preview_tick(state).gross_power
    grant_research_points(state, 1, "test")
    buy(state, "company.energy.s1.major")
    assert engine.preview_tick(state).gross_power == pytest.approx(base * 1.005)
    assert engine.advance_time(state, 1).gross_power == pytest.approx(base * 1.005)
    assert state.research.utc_high_water_timestamp == now.replace(tzinfo=timezone.utc).timestamp()


def test_global_cycle_bonus_changes_runtime_for_both_stages_without_quantity_drift(state, definitions):
    tuned = dict(definitions)
    for did, output, inputs in (("machine.extractor", "iron_ore", {}), ("machine.processor", "iron", {"iron_ore": 1})):
        tuned[did] = replace(definitions[did], base_output_per_tick=1, base_power_draw=0,
                             cycle_seconds=100, output_resource=output, input_resources=inputs, production_options=())
    state.halls["test"] = FactoryHall("test", "Test", 6)
    state.ensure_resource("iron_ore").amount = 100
    for index, did in enumerate(("machine.extractor", "machine.processor")):
        card = create_card_instance(f"runtime-{index}", did, CardKind.MACHINE, Rarity.COMMON)
        state.cards[card.card_id] = card
        state.halls["test"].slots[index].card_id = card.card_id
        option = tuned[did].available_production_options[0]
        state.ensure_machine_production(card.card_id, option.output_resource, option.production_id)
    grant_research_points(state, 1, "test")
    buy(state, "company.production.s1.major")
    totals = SimulationEngine(tuned, utc_now=lambda: 100).advance_time(state, 99.55)
    assert totals.outputs == {"iron_ore": 1, "iron": 1}
    assert totals.inputs == {"iron_ore": 1}
    assert state.ensure_resource("iron_ore").amount == 100


def test_respec_preserves_goods_above_reduced_capacity(state):
    grant_research_points(state, 1, "test")
    buy(state, "company.storage.s1.major")
    state.store_resource("copper", state.storage_capacity)
    before = state.used_storage
    respec_research(state, now=100)
    assert state.used_storage == before > state.storage_capacity
    assert state.available_storage == 0 and state.store_resource("wheat", 1) == 0


def test_every_section_has_three_strict_lanes_and_pure_industry_content():
    trees, nodes = research_catalog()
    for tree in trees.values():
        for section in range(1, 6):
            prefix = f"{tree.id}.s{section}"
            major = nodes[prefix + ".major"]
            expected = tuple(f"{tree.id}.s{section - 1}.n{i}" for i in (4, 5, 6)) if section > 1 else ()
            assert major.prerequisites == expected
            if tree.family == "industry" and section == 5:
                assert major.effect_scope == "domain"
                continue
            for lane in (1, 2, 3):
                assert nodes[f"{prefix}.n{lane}"].prerequisites == (major.id,)
                assert nodes[f"{prefix}.n{lane + 3}"].prerequisites == (f"{prefix}.n{lane}",)
            if tree.family == "industry":
                for node in (nodes[prefix + ".major"], *(nodes[f"{prefix}.n{i}"] for i in range(1, 7))):
                    assert node.effect_scope == "domain" and node.effect_type == "value"
                    assert node.effect_target == tree.id.split(".")[1]
                    if node.node_type == "small":
                        assert node.effect_value == .002


def test_legacy_paid_specialization_migrates_without_point_or_ownership_loss(state, tmp_path):
    original_ids = {"industry.forestry.s1.major", "industry.forestry.s1.n6"}
    state.research = research_from_dict(dict(version=1, total_earned=12, unlocked_node_ids=sorted(original_ids)))
    store = SQLiteSaveStore(tmp_path / "legacy-research.sqlite")
    store.initialize()
    for _ in range(3):
        assert state.research.unlocked_node_ids == original_ids
        assert state.research.legacy_lane_node_ids == {"industry.forestry.s1.n6"}
        assert (state.research.total_earned, state.research.spent, state.research.available) == (12, 2, 10)
        assert modifier_bonus(state.research, "value", "timber") == pytest.approx(.007)
        assert modifier_bonus(state.research, "value", "lumber") == pytest.approx(.007)
        assert node_state(state.research, research_catalog()[1]["industry.forestry.s1.n4"]) == "locked"
        store.save("test", state)
        state = store.load("test")
    respec_research(state, now=100)
    assert state.research.available == 12 and not state.research.legacy_lane_node_ids
    buy(state, "industry.forestry.s1.major")
    with pytest.raises(ValueError):
        purchase_research(state, "industry.forestry.s1.n6")


def test_complete_v1_allocation_preserves_surviving_paid_ids_and_refunds_retired_cluster():
    ids = list(research_catalog()[1])
    retired = [f"{tid}.s5.n{i}" for tid in research_catalog()[0] if tid.startswith("industry.") for i in range(1, 7)]
    migrated = research_from_dict(dict(version=1, total_earned=800, unlocked_node_ids=ids + retired))
    assert migrated.unlocked_node_ids == set(ids)
    assert migrated.available == 155 and not migrated.legacy_lane_node_ids


def test_v2_does_not_grandfather_new_invalid_lane_allocations():
    migrated = research_from_dict(dict(version=2, total_earned=4, unlocked_node_ids=[
        "industry.forestry.s1.major", "industry.forestry.s1.n6"]))
    assert migrated.unlocked_node_ids == {"industry.forestry.s1.major"}
    assert migrated.available == 3 and not migrated.legacy_lane_node_ids
