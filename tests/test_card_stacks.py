from __future__ import annotations

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.commands import AddCard, BuildHall, CommandBus, InstallCardInHall, RemoveCardFromHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity, TradeState
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import MachineType
from production_zero.core.state import FactoryHall, GameState


def _drill(card_id: str, rarity: Rarity = Rarity.COMMON, bonus: float = 0.0) -> CardInstance:
    return CardInstance(
        card_id=card_id,
        definition_id="machine.mining_drill.mk1",
        card_kind=CardKind.MACHINE,
        rarity=rarity,
        output_bonus_percent=bonus,
        power_bonus_percent=bonus,
    )


def test_identical_standard_cards_stack_by_definition_rarity_and_bonus_tenths() -> None:
    state = GameState(rng_seed=100)
    bus = CommandBus(state)

    for card in (
        _drill("drill-1"),
        _drill("drill-2"),
        _drill("rare-74-a", Rarity.RARE, 7.4),
        _drill("rare-74-b", Rarity.RARE, 7.4),
        _drill("rare-75", Rarity.RARE, 7.5),
    ):
        bus.dispatch(AddCard(card))

    stacks = state.inventory_card_stacks()
    quantities_by_bonus = {
        stack.first_card.output_bonus_tenths: stack.quantity
        for stack in stacks
    }

    assert quantities_by_bonus[0] == 2
    assert quantities_by_bonus[74] == 2
    assert quantities_by_bonus[75] == 1


def test_generated_rarity_cards_stack_only_when_bonus_values_match() -> None:
    state = GameState(rng_seed=105)
    bus = CommandBus(state)

    for card in (
        create_card_instance("rare-a", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74),
        create_card_instance("rare-b", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74),
        create_card_instance("rare-c", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=75),
    ):
        bus.dispatch(AddCard(card))

    stacks = sorted(state.inventory_card_stacks(), key=lambda stack: stack.first_card.output_bonus_tenths)

    assert [stack.quantity for stack in stacks] == [2, 1]
    assert stacks[0].first_card.power_bonus_tenths == 37
    assert stacks[1].first_card.power_bonus_tenths == 38
    assert all(stack.first_card.is_tradeable_by_rarity for stack in stacks)


def test_collectible_cards_remain_unstacked_even_when_card_stats_match() -> None:
    state = GameState(rng_seed=101)
    bus = CommandBus(state)

    for card in (
        CardInstance(
            "collectible-1",
            "machine.mining_drill.mk1",
            CardKind.MACHINE,
            Rarity.RARE,
            7.4,
            7.4,
            TradeState.COLLECTIBLE_VERIFIED,
            "token-1",
        ),
        CardInstance(
            "collectible-2",
            "machine.mining_drill.mk1",
            CardKind.MACHINE,
            Rarity.RARE,
            7.4,
            7.4,
            TradeState.COLLECTIBLE_VERIFIED,
            "token-2",
        ),
    ):
        bus.dispatch(AddCard(card))

    stacks = state.inventory_card_stacks()

    assert [stack.quantity for stack in stacks] == [1, 1]
    assert all(stack.key is None for stack in stacks)


def test_installing_and_removing_cards_updates_derived_stack_quantity() -> None:
    state = GameState(rng_seed=102)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (_drill("drill-1"), _drill("drill-2"), _drill("drill-3")):
        bus.dispatch(AddCard(card))

    assert state.inventory_card_stacks()[0].quantity == 3

    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-2"))

    assert state.inventory_card_stacks()[0].quantity == 1

    bus.dispatch(RemoveCardFromHall("hall-1", 0))

    assert state.inventory_card_stacks()[0].quantity == 2


def test_identical_installed_cards_keep_independent_machine_configuration() -> None:
    state = GameState(rng_seed=103)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (_drill("drill-1"), _drill("drill-2")):
        bus.dispatch(AddCard(card))

    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-2"))
    bus.dispatch(SelectMachineProduction("drill-1", "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("drill-2", "resource.coal", "coal"))

    assert state.machine_production["drill-1"].selected_production_id == "resource.iron_ore"
    assert state.machine_production["drill-2"].selected_production_id == "resource.coal"
    assert state.halls["hall-1"].slots[0].card_id == "drill-1"
    assert state.halls["hall-1"].slots[1].card_id == "drill-2"


def test_card_inventory_rows_include_available_stacks_and_in_use_cards() -> None:
    state = GameState(rng_seed=104)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (_drill("drill-1"), _drill("drill-2"), _drill("drill-3")):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    definitions = {
        "machine.mining_drill.mk1": MachineDefinition(
            definition_id="machine.mining_drill.mk1",
            name="Mining Drill MK I",
            machine_type=MachineType.MINING,
            mk_level=1,
            base_output_per_tick=12,
            base_power_draw=6,
            cycle_seconds=3,
            input_resources={},
            output_resource="iron_ore",
        )
    }

    rows = build_card_inventory_rows(state, definitions)

    assert [(row.status, row.quantity, row.definition.name) for row in rows] == [
        ("Available", 2, "Mining Drill MK I"),
        ("In Use", 1, "Mining Drill MK I"),
    ]
