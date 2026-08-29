from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddIndustrialScrap, BuildHall, CommandBus, InstallCardInHall, UpgradeCardMk
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.mk_upgrades import mk_upgrade_scrap_cost, next_mk_definition
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _drill(card_id: str, rarity: Rarity = Rarity.RARE, bonus_tenths: int = 94):
    return create_card_instance(
        card_id,
        "machine.mining_drill.mk1",
        CardKind.MACHINE,
        rarity,
        bonus_tenths=bonus_tenths,
    )


def test_mk_upgrade_moves_mk1_to_mk2_and_preserves_rarity_and_bonus() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1001)
    bus = CommandBus(state)
    card = _drill("drill-rare", Rarity.RARE, 94)
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(mk_upgrade_scrap_cost(1, 2)))

    bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    upgraded = next(iter(state.cards.values()))
    assert upgraded.definition_id == "machine.extractor.mk2"
    assert upgraded.rarity is Rarity.RARE
    assert upgraded.output_bonus_tenths == 94
    assert upgraded.power_bonus_tenths == 47
    assert upgraded.is_tradeable_by_rarity is True
    assert state.scrap.amount == 0


def test_mk_upgrade_uses_next_available_definition_and_new_base_values() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1002)
    bus = CommandBus(state)
    card = create_card_instance("mk2", "machine.mining_drill.mk2", CardKind.MACHINE, Rarity.UNCOMMON, bonus_tenths=30)
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(mk_upgrade_scrap_cost(2, 3)))

    assert next_mk_definition(card, definitions).definition_id == "machine.extractor.mk3"
    bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    upgraded = next(iter(state.cards.values()))
    assert upgraded.definition_id == "machine.extractor.mk3"
    assert definitions[upgraded.definition_id].base_output_per_tick == 60
    assert upgraded.output_bonus_tenths == 30


def test_mk_upgrade_requires_enough_scrap() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1003)
    bus = CommandBus(state)
    card = _drill("drill")
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(mk_upgrade_scrap_cost(1, 2) - 1))

    with pytest.raises(ValueError, match="Insufficient Industrial Scrap"):
        bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    assert state.cards[card.card_id].definition_id == "machine.mining_drill.mk1"


def test_installed_cards_cannot_be_mk_upgraded() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1004)
    bus = CommandBus(state)
    card = _drill("installed")
    bus.dispatch(BuildHall(FactoryHall("hall-1", "Hall 1", 1)))
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(100))
    bus.dispatch(InstallCardInHall("hall-1", 0, card.card_id))

    with pytest.raises(ValueError, match="Installed cards cannot be MK-upgraded"):
        bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    assert state.cards[card.card_id].definition_id == "machine.mining_drill.mk1"


def test_mk_upgrade_requires_next_definition() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1005)
    bus = CommandBus(state)
    card = create_card_instance("furnace", "machine.furnace.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=70)
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(100))

    with pytest.raises(ValueError, match="Max MK"):
        bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    assert state.cards[card.card_id].definition_id == "machine.furnace.mk1"


def test_mk_upgrade_consumes_one_card_from_stack_and_output_restacks() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1006)
    bus = CommandBus(state)
    cards = tuple(_drill(f"drill-{index}", Rarity.RARE, 80) for index in range(2))
    for card in cards:
        bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(100))
    assert state.inventory_card_stacks()[0].quantity == 2

    bus.dispatch(UpgradeCardMk(cards[0].card_id, definitions))

    stacks_by_definition = {
        stack.first_card.definition_id: stack.quantity
        for stack in state.inventory_card_stacks()
    }
    assert stacks_by_definition == {
        "machine.mining_drill.mk1": 1,
        "machine.extractor.mk2": 1,
    }


def test_mk_upgrade_survives_save_load(tmp_path) -> None:
    definitions = _definitions()
    state = GameState(rng_seed=1007)
    bus = CommandBus(state)
    card = _drill("save-drill", Rarity.EPIC, 140)
    bus.dispatch(AddCard(card))
    bus.dispatch(AddIndustrialScrap(100))
    bus.dispatch(UpgradeCardMk(card.card_id, definitions))

    store = SQLiteSaveStore(tmp_path / "save.sqlite3")
    store.initialize()
    store.save("slot-1", state)
    loaded = store.load("slot-1")

    upgraded = next(iter(loaded.cards.values()))
    assert upgraded.definition_id == "machine.extractor.mk2"
    assert upgraded.rarity is Rarity.EPIC
    assert upgraded.output_bonus_tenths == 140
    assert loaded.scrap.amount == 60
