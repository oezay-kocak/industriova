from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.cards import CardInstance, CardStack, CardStackKey
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState


@dataclass(frozen=True, slots=True)
class CardInventoryRow:
    card: CardInstance
    definition: CardDefinition
    quantity: int
    status: str
    card_ids: tuple[str, ...] = ()

    @property
    def card_type(self) -> str:
        if isinstance(self.definition, MachineDefinition):
            return self.definition.machine_type.value
        if isinstance(self.definition, EnergyDefinition):
            return "energy"
        if isinstance(self.definition, FreightDefinition):
            return "freight"
        return "card"

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
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            continue
        rows.append(
            CardInventoryRow(
                card=stack.first_card,
                definition=definition,
                quantity=stack.quantity,
                status="Available",
                card_ids=tuple(card.card_id for card in stack.cards),
            )
        )

    deployed: dict[CardStackKey | str, list[CardInstance]] = {}
    for card_id in sorted(state.installed_card_ids() | state.installed_freight_card_ids()):
        card = state.cards.get(card_id)
        if card is None:
            continue
        deployed.setdefault(CardStackKey.from_card(card) if card.is_stackable else card_id, []).append(card)
    for cards in deployed.values():
        card_id = cards[0].card_id
        card = state.cards[card_id]
        definition = definitions.get(card.definition_id)
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            continue
        rows.append(
            CardInventoryRow(
                card=card,
                definition=definition,
                quantity=len(cards),
                status="In Use",
                card_ids=tuple(card.card_id for card in cards),
            )
        )

    return tuple(rows)


def is_placeable_card_definition(definition: CardDefinition | None) -> bool:
    return isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition))


def build_placeable_inventory_stacks(
    state: GameState,
    definitions: dict[str, CardDefinition],
) -> tuple[CardStack, ...]:
    return tuple(
        stack
        for stack in state.inventory_card_stacks()
        if is_placeable_card_definition(definitions.get(stack.first_card.definition_id))
    )
