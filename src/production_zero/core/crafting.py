from __future__ import annotations

from production_zero.core.cards import (
    RARITY_BONUS_RANGES_TENTHS,
    CardInstance,
    create_card_instance,
)
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import Rarity


CRAFT_INPUT_COUNT = 4
RARITY_CRAFT_UPGRADES: dict[Rarity, Rarity] = {
    Rarity.UNCOMMON: Rarity.RARE,
    Rarity.RARE: Rarity.EPIC,
    Rarity.EPIC: Rarity.LEGENDARY,
}


def crafted_rarity(input_rarity: Rarity) -> Rarity:
    if input_rarity not in RARITY_CRAFT_UPGRADES:
        raise ValueError(f"{input_rarity.value.title()} cards cannot be rarity-crafted.")
    return RARITY_CRAFT_UPGRADES[input_rarity]


def crafted_bonus_tenths(input_cards: tuple[CardInstance, ...]) -> int:
    if len(input_cards) != CRAFT_INPUT_COUNT:
        raise ValueError(f"Rarity crafting requires exactly {CRAFT_INPUT_COUNT} cards.")
    input_rarity = input_cards[0].rarity
    output_rarity = crafted_rarity(input_rarity)
    if any(card.rarity is not input_rarity for card in input_cards):
        raise ValueError("All crafting input cards must have the same rarity.")

    input_lower, input_upper = RARITY_BONUS_RANGES_TENTHS[input_rarity]
    output_lower, output_upper = RARITY_BONUS_RANGES_TENTHS[output_rarity]
    input_span = input_upper - input_lower
    output_span = output_upper - output_lower
    if input_span <= 0:
        raise ValueError(f"{input_rarity.value.title()} cards cannot be rarity-crafted.")

    average_position = sum(
        (card.output_bonus_tenths - input_lower) / input_span
        for card in input_cards
    ) / len(input_cards)
    projected = output_lower + average_position * output_span
    return int(projected + 0.5)


def preview_crafted_card(
    input_cards: tuple[CardInstance, ...],
    target_definition: CardDefinition,
    card_id: str = "craft-preview",
) -> CardInstance:
    if len(input_cards) != CRAFT_INPUT_COUNT:
        raise ValueError(f"Rarity crafting requires exactly {CRAFT_INPUT_COUNT} cards.")
    if not isinstance(target_definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
        raise ValueError("Rarity crafting target must be a machine, energy, or freight card.")
    output_rarity = crafted_rarity(input_cards[0].rarity)
    return create_card_instance(
        card_id=card_id,
        definition_id=target_definition.definition_id,
        card_kind=target_definition.card_kind,
        rarity=output_rarity,
        bonus_tenths=crafted_bonus_tenths(input_cards),
    )


def craft_rarity_card(
    state,
    definitions: dict[str, CardDefinition],
    material_card_ids: tuple[str, ...],
    target_definition_id: str,
) -> CardInstance:
    if len(set(material_card_ids)) != len(material_card_ids):
        raise ValueError("Crafting input cards must be unique.")
    if target_definition_id not in definitions:
        raise ValueError(f"Unknown crafting target: {target_definition_id}")
    target_definition = definitions[target_definition_id]
    if not isinstance(target_definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
        raise ValueError("Rarity crafting target must be a machine, energy, or freight card.")

    installed = state.installed_card_ids() | state.installed_freight_card_ids()
    input_cards = []
    for card_id in material_card_ids:
        if card_id not in state.cards:
            raise ValueError(f"Unknown card: {card_id}")
        if card_id in installed:
            raise ValueError(f"Installed cards cannot be used for crafting: {card_id}")
        input_cards.append(state.cards[card_id])

    output_card = preview_crafted_card(tuple(input_cards), target_definition, _next_crafted_card_id(state))
    for card_id in material_card_ids:
        state.machine_production.pop(card_id, None)
        del state.cards[card_id]
    state.cards[output_card.card_id] = output_card
    return output_card


def _next_crafted_card_id(state) -> str:
    index = len(state.cards) + 1
    card_id = f"crafted-card-{index:04d}"
    while card_id in state.cards:
        index += 1
        card_id = f"crafted-card-{index:04d}"
    return card_id
