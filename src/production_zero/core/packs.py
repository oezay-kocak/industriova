from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import CardKind, MachineType, Rarity

if TYPE_CHECKING:
    from production_zero.core.state import GameState


DAILY_MINI_PACK = "daily_mini"
FULL_PACK = "full"
PACK_TYPE_LABELS = {
    DAILY_MINI_PACK: "Daily Mini Pack",
    FULL_PACK: "Full Pack",
}


@dataclass(frozen=True, slots=True)
class PackCategoryDefinition:
    category_id: str
    name: str
    description: str


PACK_CATEGORIES: tuple[PackCategoryDefinition, ...] = (
    PackCategoryDefinition("general", "General", "All available card types"),
    PackCategoryDefinition("extraction", "Primary Production", "Extractor, Drilling Rig, and Harvester cards"),
    PackCategoryDefinition("energy", "Energy", "Energy generation cards"),
    PackCategoryDefinition("processing", "Processing", "Processing machines"),
    PackCategoryDefinition("freight", "Freight", "Freight transport cards"),
)

GENERAL_PACK_CATEGORY_WEIGHTS: tuple[tuple[CardKind, float], ...] = (
    (CardKind.MACHINE, 35.0),
    (CardKind.ENERGY, 20.0),
    (CardKind.FREIGHT, 20.0),
)


@dataclass(frozen=True, slots=True)
class PackInstance:
    pack_id: str
    pack_type: str
    source: str = "system"


@dataclass(slots=True)
class PackInventory:
    unopened: list[PackInstance] = field(default_factory=list)
    opened_count: int = 0
    last_opened_cards: list[CardInstance] = field(default_factory=list)


def grant_pack(state: GameState, pack_type: str, source: str) -> str:
    if pack_type not in PACK_TYPE_LABELS:
        raise ValueError(f"Unknown pack type: {pack_type}")
    pack_id = _next_pack_id(state)
    state.packs.unopened.append(PackInstance(pack_id=pack_id, pack_type=pack_type, source=source))
    return pack_id


def grant_packs(state: GameState, pack_type: str, quantity: int, source: str) -> tuple[str, ...]:
    if quantity < 0:
        raise ValueError("Pack quantity cannot be negative.")
    return tuple(grant_pack(state, pack_type, source) for _ in range(quantity))


def open_pack(
    state: GameState,
    definitions: dict[str, CardDefinition],
    pack_id: str,
    category_id: str = "general",
) -> tuple[CardInstance, ...]:
    pack = next((pack for pack in state.packs.unopened if pack.pack_id == pack_id), None)
    if pack is None:
        raise ValueError(f"Unknown unopened pack: {pack_id}")
    if pack.pack_type == DAILY_MINI_PACK:
        category_id = "general"
    candidates = _candidate_definitions(definitions, category_id)
    if not candidates:
        raise ValueError(f"No card definitions available for pack category: {category_id}")

    seed = f"{state.rng_seed}:pack:{pack.pack_id}:{state.packs.opened_count}:{category_id}"
    rng = random.Random(seed)
    cards: list[CardInstance] = []
    rarities = _rarities_for_pack(pack.pack_type, rng)
    for slot_index, rarity in enumerate(rarities, start=1):
        definition = _choose_definition_for_category(candidates, category_id, rng)
        card_id = _next_pack_card_id(state, len(cards))
        cards.append(
            create_card_instance(
                card_id=card_id,
                definition_id=definition.definition_id,
                card_kind=definition.card_kind,
                rarity=rarity,
                seed=state.rng_seed,
                salt=f"{pack.pack_id}:{category_id}:{slot_index}:{definition.definition_id}",
            )
        )

    state.packs.unopened.remove(pack)
    state.packs.opened_count += 1
    state.packs.last_opened_cards = cards
    for card in cards:
        state.cards[card.card_id] = card
    return tuple(cards)


def pack_category_by_id(category_id: str) -> PackCategoryDefinition:
    for category in PACK_CATEGORIES:
        if category.category_id == category_id:
            return category
    raise ValueError(f"Unknown pack category: {category_id}")


def pack_category_pool_counts(definitions: dict[str, CardDefinition], category_id: str = "general") -> dict[CardKind, int]:
    return dict(Counter(definition.card_kind for definition in _candidate_definitions(definitions, category_id)))


def _rarities_for_pack(pack_type: str, rng: random.Random) -> tuple[Rarity, ...]:
    if pack_type == DAILY_MINI_PACK:
        return tuple(_weighted_rarity(rng, _DAILY_MINI_WEIGHTS) for _ in range(3))
    if pack_type == FULL_PACK:
        return (
            Rarity.COMMON,
            Rarity.COMMON,
            Rarity.COMMON,
            Rarity.COMMON,
            Rarity.UNCOMMON,
            _weighted_rarity(rng, _FULL_SLOT_6_WEIGHTS),
        )
    raise ValueError(f"Unknown pack type: {pack_type}")


_DAILY_MINI_WEIGHTS: tuple[tuple[Rarity, float], ...] = (
    (Rarity.COMMON, 75.0),
    (Rarity.UNCOMMON, 19.0),
    (Rarity.RARE, 5.0),
    (Rarity.EPIC, 0.8),
    (Rarity.LEGENDARY, 0.2),
)
_FULL_SLOT_6_WEIGHTS: tuple[tuple[Rarity, float], ...] = (
    (Rarity.UNCOMMON, 88.0),
    (Rarity.RARE, 10.0),
    (Rarity.EPIC, 1.0),
    (Rarity.LEGENDARY, 1.0),
)


def _weighted_rarity(rng: random.Random, weights: tuple[tuple[Rarity, float], ...]) -> Rarity:
    roll = rng.uniform(0.0, sum(weight for _, weight in weights))
    cursor = 0.0
    for rarity, weight in weights:
        cursor += weight
        if roll <= cursor:
            return rarity
    return weights[-1][0]


def _candidate_definitions(
    definitions: dict[str, CardDefinition],
    category_id: str,
) -> tuple[CardDefinition, ...]:
    pack_category_by_id(category_id)
    candidates = []
    unique_definitions = {
        definition.definition_id: definition
        for definition in definitions.values()
    }
    for definition in unique_definitions.values():
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            continue
        if category_id == 'general':
            candidates.append(definition)
        elif category_id == 'extraction' and isinstance(definition, MachineDefinition) and definition.machine_type in {
            MachineType.EXTRACTOR,
            MachineType.DRILLING,
            MachineType.AGRICULTURE,
        }:
            candidates.append(definition)
        elif category_id == 'energy' and isinstance(definition, EnergyDefinition):
            candidates.append(definition)
        elif category_id == 'processing' and isinstance(definition, MachineDefinition) and (definition.machine_type is MachineType.PROCESSOR):
            candidates.append(definition)
        elif category_id == 'freight' and isinstance(definition, FreightDefinition):
            candidates.append(definition)
    return tuple(sorted(candidates, key=lambda definition: definition.definition_id))


def _choose_definition_for_category(
    candidates: tuple[CardDefinition, ...],
    category_id: str,
    rng: random.Random,
) -> CardDefinition:
    if category_id != "general":
        return rng.choice(candidates)
    candidates_by_kind = _candidates_by_kind(candidates)
    available_weights = tuple(
        (card_kind, weight)
        for card_kind, weight in GENERAL_PACK_CATEGORY_WEIGHTS
        if candidates_by_kind.get(card_kind)
    )
    if not available_weights:
        return rng.choice(candidates)
    selected_kind = _weighted_card_kind(rng, available_weights)
    return rng.choice(candidates_by_kind[selected_kind])


def _candidates_by_kind(candidates: tuple[CardDefinition, ...]) -> dict[CardKind, tuple[CardDefinition, ...]]:
    grouped: dict[CardKind, list[CardDefinition]] = {}
    for definition in candidates:
        grouped.setdefault(definition.card_kind, []).append(definition)
    return {
        card_kind: tuple(sorted(definitions, key=lambda definition: definition.definition_id))
        for card_kind, definitions in grouped.items()
    }


def _weighted_card_kind(rng: random.Random, weights: tuple[tuple[CardKind, float], ...]) -> CardKind:
    roll = rng.uniform(0.0, sum(weight for _, weight in weights))
    cursor = 0.0
    for card_kind, weight in weights:
        cursor += weight
        if roll <= cursor:
            return card_kind
    return weights[-1][0]


def _next_pack_id(state: GameState) -> str:
    existing = {pack.pack_id for pack in state.packs.unopened}
    index = len(existing) + state.packs.opened_count + 1
    pack_id = f"pack-{index:04d}"
    while pack_id in existing:
        index += 1
        pack_id = f"pack-{index:04d}"
    return pack_id


def _next_pack_card_id(state: GameState, offset: int) -> str:
    index = len(state.cards) + offset + 1
    card_id = f"pack-card-{index:04d}"
    while card_id in state.cards:
        index += 1
        card_id = f"pack-card-{index:04d}"
    return card_id
