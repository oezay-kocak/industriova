from __future__ import annotations

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition


def mk_upgrade_scrap_cost(current_mk: int, next_mk: int) -> int:
    if current_mk <= 0 or next_mk <= current_mk:
        raise ValueError("MK upgrade requires a higher MK level.")
    return 20 * current_mk * next_mk


def next_mk_definition(
    card: CardInstance,
    definitions: dict[str, CardDefinition],
) -> CardDefinition | None:
    current = definitions.get(card.definition_id)
    if current is None:
        raise ValueError(f"Unknown card definition: {card.definition_id}")
    if isinstance(current, FreightDefinition):
        return None
    current_mk = _mk_level(current)
    if current_mk <= 0:
        return None
    family_id = _family_id(current)
    unique_definitions = {
        definition.definition_id: definition
        for definition in definitions.values()
    }
    candidates = [
        definition
        for definition in unique_definitions.values()
        if definition.card_kind is card.card_kind
        and _family_id(definition) == family_id
        and _mk_level(definition) > current_mk
    ]
    if not candidates:
        return None
    return min(candidates, key=_mk_level)


def upgrade_preview(
    card: CardInstance,
    definitions: dict[str, CardDefinition],
    card_id: str = "mk-upgrade-preview",
) -> CardInstance:
    next_definition = next_mk_definition(card, definitions)
    if next_definition is None:
        raise ValueError("Max MK")
    return create_card_instance(
        card_id=card_id,
        definition_id=next_definition.definition_id,
        card_kind=next_definition.card_kind,
        rarity=card.rarity,
        bonus_tenths=card.output_bonus_tenths,
    )


def upgrade_mk_card(
    state,
    definitions: dict[str, CardDefinition],
    card_id: str,
) -> CardInstance:
    if card_id not in state.cards:
        raise ValueError(f"Unknown card: {card_id}")
    if card_id in state.installed_card_ids():
        raise ValueError(f"Installed cards cannot be MK-upgraded: {card_id}")
    card = state.cards[card_id]
    current_definition = definitions.get(card.definition_id)
    next_definition = next_mk_definition(card, definitions)
    if current_definition is None:
        raise ValueError(f"Unknown card definition: {card.definition_id}")
    if next_definition is None:
        raise ValueError("Max MK")

    cost = mk_upgrade_scrap_cost(_mk_level(current_definition), _mk_level(next_definition))
    state.scrap.spend(cost)
    upgraded = create_card_instance(
        card_id=_next_upgraded_card_id(state),
        definition_id=next_definition.definition_id,
        card_kind=next_definition.card_kind,
        rarity=card.rarity,
        bonus_tenths=card.output_bonus_tenths,
    )
    state.machine_production.pop(card_id, None)
    del state.cards[card_id]
    state.cards[upgraded.card_id] = upgraded
    state.history.append("industrial_scrap", state.scrap.amount)
    return upgraded


def _mk_level(definition: CardDefinition) -> int:
    if isinstance(definition, RecipeDefinition):
        return int(getattr(definition, "mk_level", 0))
    if isinstance(definition, FreightDefinition):
        return 0
    return definition.mk_level


def _family_id(definition: CardDefinition) -> str:
    definition_id = definition.definition_id
    marker = ".mk"
    if marker in definition_id:
        prefix, suffix = definition_id.rsplit(marker, 1)
        if suffix.isdigit():
            return prefix
    return definition_id


def _next_upgraded_card_id(state) -> str:
    index = len(state.cards) + 1
    card_id = f"mk-upgrade-card-{index:04d}"
    while card_id in state.cards:
        index += 1
        card_id = f"mk-upgrade-card-{index:04d}"
    return card_id
