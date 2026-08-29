from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.cards import CardInstance, CardStack
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState


@dataclass(frozen=True, slots=True)
class CardInventoryRow:
    card: CardInstance
    definition: CardDefinition
    quantity: int
    status: str

    @property
    def card_type(self) -> str:
        if isinstance(self.definition, MachineDefinition):
            return self.definition.machine_type.value
        if isinstance(self.definition, EnergyDefinition):
            return self.definition.energy_type.value
        if isinstance(self.definition, RecipeDefinition):
            return "recipe"
        if isinstance(self.definition, FreightDefinition):
            return "freight"
        return "card"

    @property
    def mk_level(self) -> int:
        if isinstance(self.definition, RecipeDefinition):
            return 0
        if isinstance(self.definition, FreightDefinition):
            return self.definition.class_level
        return self.definition.mk_level

    @property
    def rarity(self) -> Rarity:
        return self.card.rarity


def build_card_inventory_rows(
    state: GameState,
    definitions: dict[str, CardDefinition],
) -> tuple[CardInventoryRow, ...]:
    rows: list[CardInventoryRow] = []

    for stack in state.inventory_card_stacks():
        definition = definitions.get(stack.first_card.definition_id)
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, RecipeDefinition, FreightDefinition)):
            continue
        rows.append(
            CardInventoryRow(
                card=stack.first_card,
                definition=definition,
                quantity=stack.quantity,
                status="Available",
            )
        )

    for card_id in sorted(state.installed_card_ids() | state.installed_freight_card_ids()):
        card = state.cards[card_id]
        definition = definitions.get(card.definition_id)
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, RecipeDefinition, FreightDefinition)):
            continue
        rows.append(
            CardInventoryRow(
                card=card,
                definition=definition,
                quantity=1,
                status="In Use",
            )
        )

    return tuple(rows)


def is_placeable_card_definition(definition: CardDefinition | None) -> bool:
    return isinstance(definition, (MachineDefinition, EnergyDefinition))


def build_placeable_inventory_stacks(
    state: GameState,
    definitions: dict[str, CardDefinition],
) -> tuple[CardStack, ...]:
    return tuple(
        stack
        for stack in state.inventory_card_stacks()
        if is_placeable_card_definition(definitions.get(stack.first_card.definition_id))
    )
