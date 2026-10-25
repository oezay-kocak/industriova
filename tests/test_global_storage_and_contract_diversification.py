from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AcceptContract, AddCard, AddResource, BuildHall, CommandBus, ConsumeResource, ExpandInventoryStorage, InstallCardInHall, SelectMachineProduction
from production_zero.core.contracts import CONTRACT_REQUIREMENT_COUNTS, DAILY, REGULAR, WEEKLY, contract_requirements_for_products, contract_requirements_for_selection, generate_contract_offers, initialize_contracts
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.market import market_price_for
from production_zero.core.progression import initialize_production_progress
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.core.storage_upgrades import global_storage_base_capacity
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


CARD_DEFINITIONS = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
RESOURCE_DEFINITIONS = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))


def _eligible_state(count: int) -> GameState:
    state = GameState(rng_seed=2201, warehouse_capacity=10_000)
    initialize_production_progress(state, CARD_DEFINITIONS)
    for resource_id in ("iron_ore", "coal", "copper_ore", "bauxite")[:count]:
        state.ensure_resource(resource_id).amount = 1
    from tests.contract_capacity_fixture import provide_capacity
    provide_capacity(state,CARD_DEFINITIONS)
    return state


def test_global_storage_counts_only_physical_resources_and_shares_space() -> None:
    state = GameState(rng_seed=2200, warehouse_capacity=10)
    bus = CommandBus(state)
    state.cash.amount = 999
    state.company.current_xp = 250
    state.energy.generated = 100
    bus.dispatch(AddResource("coal", 7))
    bus.dispatch(AddResource("iron_ore", 7))

    assert state.used_storage == 10
    assert state.resources["coal"].amount == 7
    assert state.resources["iron_ore"].amount == 3
    assert state.available_storage == 0
    bus.dispatch(ConsumeResource("coal", 2))
    assert state.available_storage == 2
    assert state.used_storage == 8


def test_storage_upgrade_increases_one_global_capacity_without_deleting_goods() -> None:
    state = GameState(rng_seed=2202, warehouse_capacity=global_storage_base_capacity(RESOURCE_DEFINITIONS))
    state.cash.amount = 10_000
    state.ensure_resource("coal").amount = 80
    before = state.warehouse_capacity

    CommandBus(state).dispatch(ExpandInventoryStorage(RESOURCE_DEFINITIONS))

    assert state.warehouse_capacity > before
    assert state.resources["coal"].amount == 80


def test_full_shared_storage_blocks_transaction_without_consuming_inputs() -> None:
    state = GameState(rng_seed=2203, warehouse_capacity=10)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall("hall-1", "Hall", 2)))
    state.ensure_resource("copper").amount = 2
    state.ensure_resource("coal").amount = 8
    for card in (
        create_card_instance("fabricator", "machine.fabricator", CardKind.MACHINE, Rarity.COMMON),
        create_card_instance("solar", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "fabricator"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar"))
    bus.dispatch(SelectMachineProduction("fabricator", "recipe.fabricator.copper_wire", "copper_wire"))

    totals = SimulationEngine(CARD_DEFINITIONS).advance_time(state, 6)

    assert totals.outputs == {}
    assert state.resources["copper"].amount == 2
    assert state.resources["coal"].amount == 8
    assert state.ensure_resource("copper_wire").amount == 0
    assert state.machine_production["fabricator"].is_storage_full


def test_legacy_over_capacity_migration_preserves_inventory_and_blocks_growth() -> None:
    legacy = GameState(rng_seed=2204)
    legacy.ensure_resource("coal").capacity = 4
    legacy.ensure_resource("coal").amount = 7
    payload = serialize_game_state(legacy)
    payload.pop("warehouse_capacity")
    payload["state_schema_version"] = 2

    loaded = deserialize_game_state(payload)

    assert loaded.warehouse_capacity == 4
    assert loaded.resources["coal"].amount == 7
    assert loaded.store_resource("iron_ore", 1) == 0
    assert loaded.used_storage == 7


@pytest.mark.parametrize("kind,count", [(REGULAR, 2), (DAILY, 3), (WEEKLY, 4)])
def test_contract_acceptance_materializes_exact_unique_requirement_count(kind: str, count: int) -> None:
    state = _eligible_state(count)
    initialize_contracts(state, CARD_DEFINITIONS)
    offer = state.contracts.offers[kind][0]
    selected = "iron_ore"
    from production_zero.core.contracts import contract_work_xp_quote, contract_requirements_for_selection
    expected_xp = contract_work_xp_quote(state, CARD_DEFINITIONS, kind, contract_requirements_for_selection(state, offer, CARD_DEFINITIONS, selected))

    explicit=tuple(contract_requirements_for_selection(state,offer,CARD_DEFINITIONS,selected))
    CommandBus(state).dispatch(AcceptContract(kind, offer.contract_id, CARD_DEFINITIONS, selected_resource_ids=explicit))

    accepted = state.contracts.active[kind].offer
    assert len(accepted.requirements) == count == CONTRACT_REQUIREMENT_COUNTS[kind]
    assert len(set(accepted.requirements)) == count
    assert accepted.reward_xp == expected_xp
    assert accepted.reward_cash == round(sum(
        market_price_for(state.market, resource_id) * amount
        for resource_id, amount in accepted.requirements.items()
    ) * {REGULAR:1.,DAILY:1.2,WEEKLY:1.4}[kind], 2)


def test_contract_requirements_are_scaled_independently_and_exclude_ineligible_products() -> None:
    state = _eligible_state(4)
    offer = generate_contract_offers(state.rng_seed, WEEKLY, 0, state=state, definitions=CARD_DEFINITIONS)[0]
    requirements = contract_requirements_for_selection(state, offer, CARD_DEFINITIONS, "iron_ore")

    assert len(set(requirements)) == 4
    assert all(amount > 0 for amount in requirements.values())
    assert "steel" not in requirements


def test_contract_with_insufficient_unique_candidates_is_unavailable_without_duplicates() -> None:
    state = _eligible_state(1)
    offer = generate_contract_offers(state.rng_seed, REGULAR, 0, state=state, definitions=CARD_DEFINITIONS)[0]

    with pytest.raises(ValueError, match="requires 2 eligible unique products; only 1 available"):
        contract_requirements_for_selection(state, offer, CARD_DEFINITIONS, "iron_ore")


def test_backend_rejects_duplicate_explicit_contract_products() -> None:
    state = _eligible_state(4)
    offer = generate_contract_offers(state.rng_seed, REGULAR, 0, state=state, definitions=CARD_DEFINITIONS)[0]

    with pytest.raises(ValueError, match="must be unique"):
        contract_requirements_for_products(state, offer, CARD_DEFINITIONS, ("coal", "coal"))
