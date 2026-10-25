"""One additive resolver for Research and future event/Consortium contributions.

Research nodes sum against a mechanic's pre-Research base. Existing rarity,
upgrade and market behavior define that base and are not rebalanced here.
Product lookup uses exactly one domain and never consults recipes.
"""
from dataclasses import dataclass
from functools import lru_cache
from production_zero.core.research import research_catalog, research_domains, specialization_catalog


@dataclass(frozen=True, slots=True)
class Modifier:
    effect_type: str
    scope: str
    target: str
    value: float


@lru_cache(maxsize=256)
def _research_modifiers(allocation: frozenset[str], specializations: tuple[tuple[str, str], ...] = ()) -> tuple[Modifier, ...]:
    nodes = research_catalog()[1]
    totals = {}
    for nid in sorted(allocation):
        node = nodes.get(nid)
        if node:
            key = (node.effect_type, node.effect_scope, node.effect_target)
            totals[key] = totals.get(key, 0.0) + node.effect_value
    slots = specialization_catalog()
    for slot_id, product_id in specializations:
        slot = slots.get(slot_id)
        if slot and slot.major_node_id in allocation and research_domains().get(product_id) == slot.tree_id.removeprefix("industry."):
            key = ("value", "product", product_id)
            totals[key] = totals.get(key, 0.0) + slot.value_bonus
    return tuple(Modifier(*key, value) for key, value in totals.items())


def modifier_bonus(research, effect_type: str, resource_id: str | None = None, *, additional=()) -> float:
    domain = research_domains().get(resource_id) if resource_id else None
    modifiers = _research_modifiers(frozenset(research.unlocked_node_ids), tuple(sorted(research.specializations.items()))) if research is not None else ()
    return sum(m.value for m in (*modifiers, *additional) if m.effect_type == effect_type and (
        (m.scope == "global" and m.target == "*")
        or (resource_id is not None and m.scope == "product" and m.target == resource_id)
        or (domain is not None and m.scope == "domain" and m.target == domain)))


def research_multiplier(research, effect_type: str, resource_id: str | None = None) -> float:
    return 1.0 + modifier_bonus(research, effect_type, resource_id)


def market_sale_price(state, resource_id: str) -> float:
    from production_zero.core.market import market_price_for
    return market_price_for(state.market, resource_id) * research_multiplier(state.research, "value", resource_id)


def contract_cash_quote(state, requirements) -> float:
    from production_zero.core.market import market_price_for
    company_contract_bonus = modifier_bonus(state.research, "contract_value")
    return sum(market_price_for(state.market, rid) * amount *
               (1.0 + modifier_bonus(state.research, "value", rid) + company_contract_bonus)
               for rid, amount in requirements.items())
