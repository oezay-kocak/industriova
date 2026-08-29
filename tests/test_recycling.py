from __future__ import annotations

import pytest

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.commands import AddCard, BuildHall, CommandBus, InstallCardInHall, RecycleCards
from production_zero.core.enums import CardKind, Rarity, TradeState
from production_zero.core.recycling import SCRAP_VALUES, scrap_value_for_card
from production_zero.core.state import FactoryHall, GameState


def _drill(card_id: str, rarity: Rarity, bonus_tenths: int) -> CardInstance:
    return create_card_instance(
        card_id,
        "machine.mining_drill.mk1",
        CardKind.MACHINE,
        rarity,
        bonus_tenths=bonus_tenths,
    )


def test_recycling_each_rarity_grants_expected_scrap() -> None:
    state = GameState(rng_seed=601)
    bus = CommandBus(state)
    cards = (
        _drill("common", Rarity.COMMON, 0),
        _drill("uncommon", Rarity.UNCOMMON, 10),
        _drill("rare", Rarity.RARE, 60),
        _drill("epic", Rarity.EPIC, 110),
        _drill("legendary", Rarity.LEGENDARY, 160),
    )
    for card in cards:
        bus.dispatch(AddCard(card))

    bus.dispatch(RecycleCards(tuple(card.card_id for card in cards)))

    assert state.cards == {}
    assert state.scrap.amount == sum(SCRAP_VALUES[card.rarity] for card in cards)
    assert state.history.values_for("industrial_scrap") == (169.0,)


def test_recycling_scrap_value_ignores_bonus_value() -> None:
    low = _drill("rare-low", Rarity.RARE, 60)
    high = _drill("rare-high", Rarity.RARE, 100)

    assert scrap_value_for_card(low) == 10
    assert scrap_value_for_card(high) == 10


def test_stack_recycling_removes_selected_quantity_only() -> None:
    state = GameState(rng_seed=602)
    bus = CommandBus(state)
    cards = tuple(_drill(f"drill-{index}", Rarity.COMMON, 0) for index in range(3))
    for card in cards:
        bus.dispatch(AddCard(card))

    bus.dispatch(RecycleCards((cards[0].card_id, cards[1].card_id)))

    assert state.scrap.amount == 2
    assert tuple(state.cards) == (cards[2].card_id,)
    assert state.inventory_card_stacks()[0].quantity == 1


def test_installed_cards_cannot_be_recycled() -> None:
    state = GameState(rng_seed=603)
    bus = CommandBus(state)
    card = _drill("installed", Rarity.COMMON, 0)
    bus.dispatch(BuildHall(FactoryHall("hall-1", "Hall 1", 1)))
    bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, card.card_id))

    with pytest.raises(ValueError, match="Installed cards cannot be recycled"):
        bus.dispatch(RecycleCards((card.card_id,)))

    assert card.card_id in state.cards
    assert state.scrap.amount == 0


def test_non_stackable_cards_are_recycled_individually() -> None:
    state = GameState(rng_seed=604)
    bus = CommandBus(state)
    card = CardInstance(
        "collectible",
        "machine.mining_drill.mk1",
        CardKind.MACHINE,
        Rarity.RARE,
        7.4,
        3.7,
        TradeState.COLLECTIBLE_VERIFIED,
        "token-1",
    )
    bus.dispatch(AddCard(card))

    assert state.inventory_card_stacks()[0].key is None

    bus.dispatch(RecycleCards((card.card_id,)))

    assert state.cards == {}
    assert state.scrap.amount == 10
