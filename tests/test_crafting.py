from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.commands import AddCard, BuildHall, CommandBus, CraftRarityCard, InstallCardInHall
from production_zero.core.crafting import crafted_bonus_tenths
from production_zero.core.enums import CardKind, Rarity, TradeState
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _card(
    card_id: str,
    rarity: Rarity,
    bonus_tenths: int,
    definition_id: str = "machine.mining_drill.mk1",
    card_kind: CardKind = CardKind.MACHINE,
) -> CardInstance:
    return create_card_instance(card_id, definition_id, card_kind, rarity, bonus_tenths=bonus_tenths)


def test_crafts_five_uncommon_into_targeted_rare_card() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=901)
    bus = CommandBus(state)
    materials = tuple(_card(f"uncommon-{index}", Rarity.UNCOMMON, 30) for index in range(5))
    for card in materials:
        bus.dispatch(AddCard(card))

    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.furnace.mk1", definitions))

    output = next(iter(state.cards.values()))
    assert output.definition_id == "machine.processor.mk1"
    assert output.rarity is Rarity.RARE
    assert output.output_bonus_tenths == 80
    assert output.is_tradeable_by_rarity is True


def test_crafts_five_rare_into_epic_and_five_epic_into_legendary() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=902)
    bus = CommandBus(state)
    rare_materials = tuple(_card(f"rare-{index}", Rarity.RARE, 90) for index in range(5))
    epic_materials = tuple(_card(f"epic-{index}", Rarity.EPIC, 150) for index in range(5))
    for card in (*rare_materials, *epic_materials):
        bus.dispatch(AddCard(card))

    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in rare_materials), "recipe.processor.iron", definitions))
    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in epic_materials), "machine.blast_furnace.mk1", definitions))

    crafted = sorted(state.cards.values(), key=lambda card: card.rarity.value)
    assert {card.rarity for card in crafted} == {Rarity.EPIC, Rarity.LEGENDARY}
    assert next(card for card in crafted if card.rarity is Rarity.EPIC).output_bonus_tenths == 140
    assert next(card for card in crafted if card.rarity is Rarity.LEGENDARY).output_bonus_tenths == 200


def test_common_cards_are_not_rarity_craftable() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=903)
    bus = CommandBus(state)
    materials = tuple(_card(f"common-{index}", Rarity.COMMON, 0) for index in range(5))
    for card in materials:
        bus.dispatch(AddCard(card))

    with pytest.raises(ValueError, match="Common cards cannot be rarity-crafted"):
        bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.furnace.mk1", definitions))


def test_crafting_materials_may_be_different_card_types_but_must_share_rarity() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=904)
    bus = CommandBus(state)
    materials = (
        _card("machine-1", Rarity.RARE, 60, "machine.mining_drill.mk1", CardKind.MACHINE),
        _card("machine-2", Rarity.RARE, 70, "machine.furnace.mk1", CardKind.MACHINE),
        _card("energy-1", Rarity.RARE, 80, "energy.solar_array.mk1", CardKind.ENERGY),
        _card("recipe-1", Rarity.RARE, 90, "recipe.processor.iron", CardKind.RECIPE),
        _card("recipe-2", Rarity.RARE, 100, "recipe.processor.iron", CardKind.RECIPE),
    )
    for card in materials:
        bus.dispatch(AddCard(card))

    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.mining_drill.mk1", definitions))

    output = next(iter(state.cards.values()))
    assert output.rarity is Rarity.EPIC
    assert output.output_bonus_tenths == 130

    bad_state = GameState(rng_seed=905)
    bad_bus = CommandBus(bad_state)
    mixed = (*materials[:4], _card("wrong-rarity", Rarity.EPIC, 110))
    for card in mixed:
        bad_bus.dispatch(AddCard(card))
    with pytest.raises(ValueError, match="same rarity"):
        bad_bus.dispatch(CraftRarityCard(tuple(card.card_id for card in mixed), "machine.mining_drill.mk1", definitions))


def test_relative_bonus_transfer_rounds_to_one_decimal_percent() -> None:
    cards = (
        _card("rare-1", Rarity.RARE, 68),
        _card("rare-2", Rarity.RARE, 68),
        _card("rare-3", Rarity.RARE, 69),
        _card("rare-4", Rarity.RARE, 69),
        _card("rare-5", Rarity.RARE, 69),
    )

    assert crafted_bonus_tenths(cards) == 119


def test_installed_cards_cannot_be_used_for_crafting() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=906)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall("hall-1", "Hall 1", 1)))
    materials = tuple(_card(f"rare-{index}", Rarity.RARE, 70) for index in range(5))
    for card in materials:
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, materials[0].card_id))

    with pytest.raises(ValueError, match="Installed cards cannot be used for crafting"):
        bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.furnace.mk1", definitions))

    assert materials[0].card_id in state.cards


def test_crafting_consumes_stack_materials_and_adds_output_to_inventory() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=907)
    bus = CommandBus(state)
    materials = tuple(_card(f"uncommon-{index}", Rarity.UNCOMMON, 10) for index in range(5))
    for card in materials:
        bus.dispatch(AddCard(card))
    assert state.inventory_card_stacks()[0].quantity == 5

    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.mining_drill.mk1", definitions))

    stacks = state.inventory_card_stacks()
    assert len(stacks) == 1
    assert stacks[0].quantity == 1
    assert stacks[0].first_card.rarity is Rarity.RARE
    assert stacks[0].first_card.definition_id == "machine.extractor.mk1"


def test_non_stackable_materials_are_consumed_individually() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=908)
    bus = CommandBus(state)
    materials = tuple(
        CardInstance(
            f"collectible-{index}",
            "machine.mining_drill.mk1",
            CardKind.MACHINE,
            Rarity.RARE,
            7.4,
            3.7,
            TradeState.COLLECTIBLE_VERIFIED,
            f"token-{index}",
        )
        for index in range(5)
    )
    for card in materials:
        bus.dispatch(AddCard(card))

    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "machine.furnace.mk1", definitions))

    assert len(state.cards) == 1
    assert next(iter(state.cards.values())).rarity is Rarity.EPIC


def test_crafted_card_survives_save_load(tmp_path) -> None:
    definitions = _definitions()
    state = GameState(rng_seed=909)
    bus = CommandBus(state)
    materials = tuple(_card(f"rare-{index}", Rarity.RARE, 100) for index in range(5))
    for card in materials:
        bus.dispatch(AddCard(card))
    bus.dispatch(CraftRarityCard(tuple(card.card_id for card in materials), "recipe.processor.iron", definitions))

    store = SQLiteSaveStore(tmp_path / "save.sqlite3")
    store.initialize()
    store.save("slot-1", state)
    loaded = store.load("slot-1")

    output = next(iter(loaded.cards.values()))
    assert output.definition_id == "recipe.processor.iron"
    assert output.rarity is Rarity.EPIC
    assert output.output_bonus_tenths == 150
