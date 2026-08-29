from __future__ import annotations

from collections import Counter
from pathlib import Path

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AcceptContract, AddCard, AddCash, AddResource, AssignFreightCard, CommandBus, CraftRarityCard, DeliverAvailableToContract, InstallFreightCard, RecycleCards
from production_zero.core.contracts import DAILY, WEEKLY, initialize_contracts
from production_zero.core.definitions import EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility, expand_freight_facility
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, GENERAL_PACK_CATEGORY_WEIGHTS, _candidate_definitions, grant_pack, open_pack, pack_category_pool_counts
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _install_freight_fleet(state: GameState, bus: CommandBus, definitions) -> None:
    for facility_type in ("rail_station", "harbor", "airport"):
        build_freight_facility(state.freight, facility_type)
    facility_ids = {
        facility.facility_type: facility_id
        for facility_id, facility in state.freight.facilities.items()
    }
    assignments = [
        ("steel", "market"),
        ("iron", "market"),
        ("iron_ore", "market"),
        ("coal", "market"),
        ("copper", "market"),
        ("copper_ore", "market"),
        ("iron_ore", "contract"),
        ("coal", "contract"),
        ("copper", "contract"),
        ("iron", "contract"),
        ("copper_ore", "contract"),
        ("steel", "contract"),
    ]
    assignment_index = 0
    for index in range(3):
        for facility_id, definition_id in (
            (facility_ids["airport"], "freight.aircraft.class1"),
            (facility_ids["garage_depot"], "freight.truck.class1"),
            (facility_ids["harbor"], "freight.ship.class1"),
            (facility_ids["rail_station"], "freight.train.class1"),
        ):
            facility = state.freight.facilities[facility_id]
            while len(facility.slots) <= index:
                expand_freight_facility(facility)
            card = create_card_instance(f"{facility_id}-{index}", definition_id, CardKind.FREIGHT, Rarity.COMMON)
            bus.dispatch(AddCard(card))
            bus.dispatch(InstallFreightCard(facility_id, index, card.card_id, definitions))
            resource_id, destination = assignments[assignment_index]
            assignment_index += 1
            bus.dispatch(AssignFreightCard(card.card_id, resource_id, destination))


def _deliver_until_settled(state: GameState, bus: CommandBus, definitions, kind: str, attempts: int = 8) -> None:
    engine = SimulationEngine(definitions)
    for _ in range(attempts):
        if kind not in state.contracts.active or state.contracts.active[kind].status == "completed":
            return
        bus.dispatch(DeliverAvailableToContract(kind, definitions))
        if not state.freight.outbound_shipments:
            return
        engine.advance_time(state, 420)


def test_daily_mini_pack_opens_three_independent_cards_with_valid_rarity_bonuses() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=801)
    pack_id = grant_pack(state, DAILY_MINI_PACK, "test")

    cards = open_pack(state, definitions, pack_id)

    assert len(cards) == 3
    assert state.packs.unopened == []
    assert state.packs.last_opened_cards == list(cards)
    assert all(card.card_id in state.cards for card in cards)
    assert all(_bonus_in_rarity_range(card.rarity, card.output_bonus_tenths) for card in cards)


def test_general_pack_pool_and_daily_mini_can_include_freight_cards() -> None:
    definitions = _definitions()
    candidates = _candidate_definitions(definitions, "general")

    assert any(isinstance(definition, FreightDefinition) for definition in candidates)
    assert any(definition.card_kind is CardKind.FREIGHT for definition in candidates)
    assert any(definition.card_kind is CardKind.MACHINE for definition in candidates)
    assert any(definition.card_kind is CardKind.RECIPE for definition in candidates)


def test_general_pack_pool_contains_each_reward_category_once() -> None:
    definitions = _definitions()
    candidates = _candidate_definitions(definitions, "general")
    counts = pack_category_pool_counts(definitions, "general")

    assert counts[CardKind.MACHINE] > 0
    assert counts[CardKind.ENERGY] > 0
    assert counts[CardKind.RECIPE] > 0
    assert counts[CardKind.FREIGHT] > 0
    assert len({definition.definition_id for definition in candidates}) == len(candidates)


def test_general_pack_uses_category_weights_instead_of_flat_definition_pool() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=811)
    category_counts: Counter[CardKind] = Counter()
    pack_count = 1200

    for _ in range(pack_count):
        pack_id = grant_pack(state, FULL_PACK, "distribution-test")
        cards = open_pack(state, definitions, pack_id, "general")
        category_counts.update(card.card_kind for card in cards)

    total_cards = pack_count * 6
    expected = {
        card_kind: weight / 100.0
        for card_kind, weight in GENERAL_PACK_CATEGORY_WEIGHTS
    }
    actual = {
        card_kind: category_counts[card_kind] / total_cards
        for card_kind in expected
    }

    assert actual[CardKind.RECIPE] < 0.32
    assert abs(actual[CardKind.MACHINE] - expected[CardKind.MACHINE]) < 0.04
    assert abs(actual[CardKind.RECIPE] - expected[CardKind.RECIPE]) < 0.04
    assert abs(actual[CardKind.ENERGY] - expected[CardKind.ENERGY]) < 0.04
    assert abs(actual[CardKind.FREIGHT] - expected[CardKind.FREIGHT]) < 0.04


def test_general_daily_mini_uses_same_broad_general_category_weights() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=812)
    category_counts: Counter[CardKind] = Counter()

    for _ in range(300):
        pack_id = grant_pack(state, DAILY_MINI_PACK, "daily-distribution-test")
        cards = open_pack(state, definitions, pack_id, "recipes")
        category_counts.update(card.card_kind for card in cards)

    assert set(category_counts) == {CardKind.MACHINE, CardKind.ENERGY, CardKind.RECIPE, CardKind.FREIGHT}
    assert category_counts[CardKind.RECIPE] < sum(category_counts.values()) * 0.4


def test_specialized_pack_categories_keep_their_focused_pools() -> None:
    definitions = _definitions()

    assert all(isinstance(definition, MachineDefinition) for definition in _candidate_definitions(definitions, "extraction"))
    assert all(definition.machine_type.value == "extractor" for definition in _candidate_definitions(definitions, "extraction"))
    assert all(isinstance(definition, MachineDefinition) for definition in _candidate_definitions(definitions, "processing"))
    assert all(definition.machine_type.value == "processor" for definition in _candidate_definitions(definitions, "processing"))
    assert all(isinstance(definition, EnergyDefinition) for definition in _candidate_definitions(definitions, "energy"))
    assert all(isinstance(definition, RecipeDefinition) for definition in _candidate_definitions(definitions, "recipes"))
    assert all(isinstance(definition, FreightDefinition) for definition in _candidate_definitions(definitions, "freight"))


def test_full_pack_has_guaranteed_slots_and_category_filtering() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=802)
    pack_id = grant_pack(state, FULL_PACK, "test")

    cards = open_pack(state, definitions, pack_id, "energy")

    assert [card.rarity for card in cards[:4]] == [Rarity.COMMON] * 4
    assert cards[4].rarity is Rarity.UNCOMMON
    assert cards[5].rarity in {Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY}
    assert {card.card_kind for card in cards} == {CardKind.ENERGY}


def test_freight_full_pack_contains_only_freight_cards_with_existing_full_pack_slot_rules() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=807)
    pack_id = grant_pack(state, FULL_PACK, "test")

    cards = open_pack(state, definitions, pack_id, "freight")

    assert [card.rarity for card in cards[:4]] == [Rarity.COMMON] * 4
    assert cards[4].rarity is Rarity.UNCOMMON
    assert cards[5].rarity in {Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY}
    assert {card.card_kind for card in cards} == {CardKind.FREIGHT}
    assert all(isinstance(definitions[card.definition_id], FreightDefinition) for card in cards)
    assert all(definitions[card.definition_id].class_label == "Class I" for card in cards)
    assert all(card.card_id in state.cards for card in cards)
    assert all(_bonus_in_rarity_range(card.rarity, card.output_bonus_tenths) for card in cards)


def test_freight_card_from_pack_can_be_installed_and_recycled() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=808)
    bus = CommandBus(state)
    pack_id = grant_pack(state, FULL_PACK, "test")
    cards = open_pack(state, definitions, pack_id, "freight")
    card = cards[0]
    definition = definitions[card.definition_id]
    assert isinstance(definition, FreightDefinition)
    if definition.facility_id != "garage_depot":
        facility = build_freight_facility(state.freight, definition.facility_id)
        facility_id = facility.facility_id
    else:
        facility_id = "garage-1"

    bus.dispatch(InstallFreightCard(facility_id, 0, card.card_id, definitions))

    assert state.freight.facilities[facility_id].slots[0].card_id == card.card_id

    another_card = next(candidate for candidate in cards[1:] if candidate.card_id in state.cards)
    expected_scrap = 1 if another_card.rarity is Rarity.COMMON else 3
    bus.dispatch(RecycleCards((another_card.card_id,)))

    assert another_card.card_id not in state.cards
    assert state.scrap.amount == expected_scrap


def test_freight_cards_from_packs_are_rarity_crafting_compatible() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=809)
    bus = CommandBus(state)

    while len([card for card in state.cards.values() if card.card_kind is CardKind.FREIGHT and card.rarity is Rarity.UNCOMMON]) < 5:
        pack_id = grant_pack(state, FULL_PACK, "test")
        open_pack(state, definitions, pack_id, "freight")

    materials = tuple(
        card for card in state.cards.values()
        if card.card_kind is CardKind.FREIGHT and card.rarity is Rarity.UNCOMMON
    )[:5]
    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "freight.truck.class1", definitions))

    crafted = next(card for card in state.cards.values() if card.definition_id == "freight.truck.class1" and card.rarity is Rarity.RARE)
    assert crafted.card_kind is CardKind.FREIGHT
    assert crafted.is_tradeable_by_rarity is True
    assert all(card.card_id not in state.cards for card in materials)


def test_pack_opening_is_deterministic_for_seed_pack_and_category() -> None:
    definitions = _definitions()
    first = GameState(rng_seed=803)
    second = GameState(rng_seed=803)
    first_pack = grant_pack(first, FULL_PACK, "test")
    second_pack = grant_pack(second, FULL_PACK, "test")

    first_cards = open_pack(first, definitions, first_pack, "processing")
    second_cards = open_pack(second, definitions, second_pack, "processing")

    assert [
        (card.definition_id, card.rarity, card.output_bonus_tenths)
        for card in first_cards
    ] == [
        (card.definition_id, card.rarity, card.output_bonus_tenths)
        for card in second_cards
    ]


def test_opened_pack_cards_enter_inventory_stacks() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=804)
    pack_id = grant_pack(state, FULL_PACK, "test")

    open_pack(state, definitions, pack_id, "processing")

    stacks = state.inventory_card_stacks()
    assert sum(stack.quantity for stack in stacks) == 6
    assert any(stack.quantity == 4 for stack in stacks)


def test_freight_pack_cards_survive_save_load(tmp_path) -> None:
    definitions = _definitions()
    state = GameState(rng_seed=810)
    pack_id = grant_pack(state, FULL_PACK, "test")
    cards = open_pack(state, definitions, pack_id, "freight")
    card = cards[0]

    store = SQLiteSaveStore(tmp_path / "save.sqlite3")
    store.initialize()
    store.save("slot-1", state)
    loaded = store.load("slot-1")

    loaded_card = loaded.cards[card.card_id]
    assert loaded_card.definition_id == card.definition_id
    assert loaded_card.card_kind is CardKind.FREIGHT
    assert loaded_card.rarity is card.rarity
    assert loaded_card.output_bonus_tenths == card.output_bonus_tenths
    assert isinstance(definitions[loaded_card.definition_id], FreightDefinition)


def test_daily_and_weekly_contracts_grant_pack_rewards() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=805)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)

    daily_offer = state.contracts.offers[DAILY][0]
    _fund_contract_requirements(state, bus, daily_offer.requirements)
    bus.dispatch(AcceptContract(DAILY, daily_offer.contract_id))
    _deliver_until_settled(state, bus, definitions, DAILY)

    weekly_offer = state.contracts.offers[WEEKLY][0]
    _fund_contract_requirements(state, bus, weekly_offer.requirements)
    bus.dispatch(AcceptContract(WEEKLY, weekly_offer.contract_id))
    _deliver_until_settled(state, bus, definitions, WEEKLY)

    assert [pack.pack_type for pack in state.packs.unopened] == [DAILY_MINI_PACK, FULL_PACK]


def test_title_milestone_grants_three_full_packs() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=806)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)
    state.company.level = 9
    state.company.current_xp = state.company.xp_to_next_level - 10
    offer = state.contracts.offers[DAILY][0]
    _fund_contract_requirements(state, bus, offer.requirements)

    bus.dispatch(AcceptContract(DAILY, offer.contract_id))
    _deliver_until_settled(state, bus, definitions, DAILY)

    assert state.company.level >= 10
    assert [pack.pack_type for pack in state.packs.unopened].count(FULL_PACK) == 3


def _fund_contract_requirements(state: GameState, bus: CommandBus, requirements: dict[str, float]) -> None:
    for resource_id, amount in requirements.items():
        stock = state.ensure_resource(resource_id)
        stock.capacity = max(stock.capacity, amount)
        bus.dispatch(AddResource(resource_id, amount))


def _bonus_in_rarity_range(rarity: Rarity, bonus_tenths: int) -> bool:
    ranges = {
        Rarity.COMMON: (0, 0),
        Rarity.UNCOMMON: (10, 50),
        Rarity.RARE: (60, 100),
        Rarity.EPIC: (110, 150),
        Rarity.LEGENDARY: (160, 200),
    }
    lower, upper = ranges[rarity]
    return lower <= bonus_tenths <= upper
