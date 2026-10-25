from dataclasses import replace
from importlib.resources import files

import pytest

from production_zero.core.research import (
    ResearchState, research_catalog, research_domains, specialization_catalog,
    purchase_research, purchase_specialization, specialization_state, grant_research_points,
    respec_research, cooldown_remaining, research_from_dict, research_to_dict,
)
from production_zero.core.modifiers import modifier_bonus, market_sale_price, contract_cash_quote
from production_zero.core.state import GameState
from production_zero.core.resources import create_resource_inventory
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


@pytest.fixture
def state():
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    return GameState(rng_seed=19, resources=create_resource_inventory(resources))


def unlock(state, tree="industry.electronics", through=5):
    grant_research_points(state, 60, "test")
    for node in research_catalog()[1].values():
        if node.tree_id == tree and node.row <= (through - 1) * 3:
            purchase_research(state, node.id)


def select(state, number, product="microchip", tree="industry.electronics"):
    purchase_specialization(state, f"{tree}.specialization.{number}", product)


def test_catalog_has_four_optional_side_slots_at_majors_two_to_five():
    trees, nodes = research_catalog()
    slots = specialization_catalog()
    assert len(slots) == 60 and len(nodes) == 645
    for tree in trees.values():
        own = [n for n in nodes.values() if n.tree_id == tree.id]
        side = [s for s in slots.values() if s.tree_id == tree.id]
        assert sum(n.node_type == "major" for n in own) == 5
        if tree.family == "company":
            assert len(own) == 35 and not side
            continue
        assert len(own) == 29 and len(side) == 4
        assert {n.row // 3 for n in own if n.node_type == "small"} == {0, 1, 2, 3}
        assert all(n.effect_scope == "domain" for n in own)
        for i, slot in enumerate(side, 1):
            assert slot.id == f"{tree.id}.specialization.{i}"
            assert slot.major_node_id == f"{tree.id}.s{i + 1}.major"
            assert slot.cost == 1 and slot.value_bonus == .01
        assert not any(set(n.prerequisites) & slots.keys() for n in own)


def test_locked_invalid_domain_unknown_and_insufficient_rp_are_atomic(state):
    slot = specialization_catalog()["industry.electronics.specialization.1"]
    assert specialization_state(state.research, slot) == "locked"
    for sid, rid in ((slot.id, "microchip"), ("missing.slot", "microchip")):
        with pytest.raises(ValueError):
            purchase_specialization(state, sid, rid)
    unlock(state, through=2)
    before = research_to_dict(state.research)
    for rid in ("copper_wire", "missing_product"):
        with pytest.raises(ValueError, match="domain"):
            purchase_specialization(state, slot.id, rid)
        assert research_to_dict(state.research) == before
    state.research.total_earned = state.research.spent
    assert specialization_state(state.research, slot) == "unfunded"
    with pytest.raises(ValueError):
        select(state, 1)
    assert state.research.available == 0 and not state.research.specializations


@pytest.mark.parametrize("products", [("microchip",) * 4, ("microchip", "cpu", "ai_accelerator", "server_components")])
def test_duplicate_and_distinct_selections_cost_one_and_lock_until_respec(state, products):
    unlock(state)
    assert not state.research.specializations  # All Majors are reachable without any specialization.
    before = state.research.available
    activity = len(state.communications.pending_activity)
    for index, product in enumerate(products, 1):
        select(state, index, product)
        assert state.research.available == before - index
        assert state.research.specializations[f"industry.electronics.specialization.{index}"] == product
        with pytest.raises(ValueError, match="Full Respec"):
            select(state, index, "cpu")
    assert len(state.communications.pending_activity) == activity + 4
    assert not state.communications.messages


def test_four_duplicate_exact_product_effects_are_additive_and_economic_only(state):
    unlock(state)
    purchase_research(state, "company.general.s1.major")
    base = modifier_bonus(state.research, "value", "microchip")
    assert base == pytest.approx(.098 + .005)
    for i in range(1, 5):
        select(state, i)
        assert modifier_bonus(state.research, "value", "microchip") == pytest.approx(base + i * .01)
        assert modifier_bonus(state.research, "value", "cpu") == pytest.approx(base)
        assert modifier_bonus(state.research, "value", "copper_wire") == pytest.approx(.005)
    # Neither inputs nor products consuming Microchips inherit specialization.
    for rid in ("silicon", "semiconductor_die", "industrial_computer"):
        assert modifier_bonus(state.research, "value", rid) == pytest.approx(base)
    for effect in ("production_speed", "energy_output", "storage_capacity", "freight_capacity"):
        assert modifier_bonus(state.research, effect, "microchip") == 0


def test_market_and_mixed_contract_use_matching_product_contribution(state):
    unlock(state)
    purchase_research(state, "company.general.s1.major")
    purchase_research(state, "company.contracts.s1.major")
    prices = {rid: state.market.ensure_resource(rid).current_price for rid in ("microchip", "cpu", "copper")}
    requirements = {"microchip": 10, "cpu": 20, "copper": 30}
    before = contract_cash_quote(state, requirements)
    select(state, 1)
    select(state, 2)
    assert market_sale_price(state, "microchip") == pytest.approx(prices["microchip"] * 1.123)
    assert market_sale_price(state, "cpu") == pytest.approx(prices["cpu"] * 1.103)
    assert market_sale_price(state, "copper") == pytest.approx(prices["copper"] * 1.005)
    assert contract_cash_quote(state, requirements) == pytest.approx(before + prices["microchip"] * 10 * .02)


def test_actual_market_shipment_and_contract_snapshots_survive_respec(state):
    from production_zero.core.cards import create_card_instance
    from production_zero.core.enums import CardKind, Rarity
    from production_zero.core.commands import AddCard, AssignFreightCard, CommandBus, InstallFreightCard, SellResource
    from production_zero.core.contracts import DAILY, accept_contract, initialize_contracts, receive_contract_delivery
    from production_zero.core.simulation import SimulationEngine
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    unlock(state)
    select(state, 1)
    bus = CommandBus(state)
    truck = create_card_instance("special-truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(truck))
    bus.dispatch(InstallFreightCard("garage-1", 0, truck.card_id, definitions))
    bus.dispatch(AssignFreightCard(truck.card_id, "microchip", "market"))
    state.ensure_resource("microchip").amount = 100
    price = market_sale_price(state, "microchip")
    bus.dispatch(SellResource("microchip", 10, definitions))
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.market_price == price
    state.company.level = 200
    initialize_contracts(state, definitions)
    requirements = {"microchip": 10, "cpu": 20, "copper": 30}
    expected = round(contract_cash_quote(state, requirements)*1.2, 2)
    state.contracts.active.pop(DAILY, None)
    offer = replace(state.contracts.offers[DAILY][0], balance_version=0, requirements=requirements, reward_cash=round(expected, 2))
    state.contracts.offers[DAILY] = [offer]
    accept_contract(state, DAILY, offer.contract_id, definitions)
    assert state.contracts.active[DAILY].offer.reward_cash == expected
    respec_research(state, now=100)
    assert market_sale_price(state, "microchip") < price
    # Finish the mixed Contract before arrival: normal freight prioritizes open
    # Contract requirements over Market payout, independently of Research.
    for rid, amount in requirements.items():
        receive_contract_delivery(state, offer.contract_id, rid, amount, definitions)
    assert state.cash.amount == expected
    SimulationEngine(definitions).advance_time(state, shipment.remaining_seconds)
    assert state.cash.amount == pytest.approx(shipment.quantity * price + expected)


def test_sqlite_selection_refund_and_cooldown(state, tmp_path):
    unlock(state)
    for i in range(1, 5):
        select(state, i)
    store = SQLiteSaveStore(tmp_path / "specialization.sqlite")
    store.initialize()
    ids = dict(state.research.specializations)
    for _ in range(3):
        store.save("test", state)
        state = store.load("test")
        assert state.research.specializations == ids
        assert state.research.available == 27 and state.research.spent == 33
    assert respec_research(state, now=100) == 33
    assert not state.research.specializations and state.research.available == state.research.total_earned == 60
    assert modifier_bonus(state.research, "value", "microchip") == 0
    assert cooldown_remaining(state.research, now=100) == 86400
    # The existing cooldown limits resets, not ordinary/specialization purchases.
    for node in research_catalog()[1].values():
        if node.tree_id == "industry.electronics" and node.row <= 3:
            purchase_research(state, node.id)
    select(state, 1)
    with pytest.raises(ValueError, match="cooling"):
        respec_research(state, now=100)
    store.save("test", state)
    loaded = store.load("test")
    assert loaded.research.specializations == state.research.specializations
    assert loaded.research.respec_available_at == 86500


@pytest.mark.parametrize("version", [1, 2])
def test_old_save_without_slots_refunds_retired_tail_and_preserves_major(state, version):
    unlock(state)
    payload = research_to_dict(state.research)
    payload["version"] = version
    del payload["specializations"]
    payload["unlocked_node_ids"] += [f"industry.electronics.s5.n{i}" for i in range(1, 7)]
    migrated = research_from_dict(payload)
    assert migrated.unlocked_node_ids == state.research.unlocked_node_ids
    assert not migrated.specializations and migrated.total_earned == 60
    assert migrated.available == 31


@pytest.mark.parametrize("replacement", ["retired_product", "copper", None])
def test_invalid_specialization_refunds_safely(state, replacement):
    unlock(state)
    select(state, 1)
    select(state, 2)
    payload = research_to_dict(state.research)
    if replacement is None:
        payload["specializations"]["retired.slot"] = payload["specializations"].pop("industry.electronics.specialization.1")
    else:
        payload["specializations"]["industry.electronics.specialization.1"] = replacement
    loaded = research_from_dict(payload)
    assert loaded.specializations == {"industry.electronics.specialization.2": "microchip"}
    assert loaded.total_earned == 60 and loaded.available == 30


def test_oil_gas_four_products_allow_four_repeats(state):
    assert sum(domain == "oil_gas" for domain in research_domains().values()) == 4
    unlock(state, tree="industry.oil_gas")
    for i in range(1, 5):
        select(state, i, "crude_oil", "industry.oil_gas")
    assert modifier_bonus(state.research, "value", "crude_oil") == pytest.approx(.138)
    assert modifier_bonus(state.research, "value", "natural_gas") == pytest.approx(.098)
