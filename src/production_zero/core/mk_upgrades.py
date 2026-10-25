"""Instance upgrades: linear throughput, increasing opportunity-cost payback."""
from dataclasses import replace
from math import ceil, isfinite
import random

from production_zero.core.cards import create_card_instance
from production_zero.core.definitions import MachineDefinition, EnergyDefinition, FreightDefinition
from production_zero.core.enums import Rarity
from production_zero.core.market import BASE_MARKET_PRICES

MAX_MK_LEVEL = 99
# Geometric interpolation is continuous at each anchor. These are design
# horizons; a whole company's actual payback also includes its support cards.
PAYBACK_ANCHORS = ((2, 180.), (10, 600.), (30, 3600.),
                   (60, 14400.), (90, 43200.), (99, 86400.))
UPGRADE_VALUE_WEIGHT = .5
# Competing hazards: a quality result permanently ends future rolls.
UPGRADE_RARITY_PROBABILITIES = (
    (Rarity.LEGENDARY, .000005),
    (Rarity.EPIC, .00015),
    (Rarity.RARE, .0015),
    (Rarity.UNCOMMON, .012),
)


def mk_factor(level):
    if type(level) is not int or not 1 <= level <= MAX_MK_LEVEL:
        raise ValueError("MK level must be an integer from 1 to 99.")
    return 1 + .25 * (level - 1)


def base_net_profit_per_second(definition):
    """Opportunity cost of input goods, plus coal-equivalent energy cost.

    Uses every real recipe, including late products, to prevent cheap upgrades
    on an early recipe followed by switching to a very profitable late recipe.
    Logistics remains a separate bottleneck in the full-chain simulation.
    """
    if isinstance(definition, MachineDefinition):
        energy = BASE_MARKET_PRICES.get("coal", 0) * .01
        return max(.01, *(max(0., option.output_amount_for(definition) * BASE_MARKET_PRICES.get(option.output_resource, 0.) - sum(amount * BASE_MARKET_PRICES.get(rid, 0.) for rid, amount in option.input_resources.items())) / option.cycle_seconds_for(definition) - option.power_draw_for(definition) * energy for option in definition.available_production_options))
    if isinstance(definition, EnergyDefinition):
        return max(.01, definition.base_power_output * BASE_MARKET_PRICES.get("coal", 0.) * .01)
    if isinstance(definition, FreightDefinition):
        return max(.01, definition.base_capacity / definition.base_transport_time_seconds)
    raise ValueError("Unsupported machine definition")


def upgrade_payback_seconds(next_level):
    mk_factor(next_level)
    if next_level < 2:
        raise ValueError("An upgrade must target MK2 or higher.")
    for (lo, a), (hi, b) in zip(PAYBACK_ANCHORS, PAYBACK_ANCHORS[1:]):
        if next_level <= hi:
            return a * (b / a) ** ((next_level - lo) / (hi - lo))
    return PAYBACK_ANCHORS[-1][1]


def mk_upgrade_cost(card, definition):
    from production_zero.core.supply import common_card_price
    mk_factor(card.mk_level)
    if card.mk_level >= MAX_MK_LEVEL:
        raise ValueError("Machine has reached MK99.")
    # The old MK**1.7 floor independently made late support upgrades unaffordable.
    # A quarter of replacement capital, increasing by 2.5% per step, prices the
    # same +25% base capacity on every family without historical-price anchors.
    capital = .25 * common_card_price(definition) * (1 + .025 * (card.mk_level - 1))
    value = .25 * UPGRADE_VALUE_WEIGHT * base_net_profit_per_second(definition) * upgrade_payback_seconds(card.mk_level + 1)
    quote = max(capital, value)
    if not isfinite(quote) or quote <= 0:
        raise ValueError("Invalid MK upgrade quote.")
    return ceil(quote * 100) / 100


def upgraded_card(card, cost, seed):
    if card.mk_level >= MAX_MK_LEVEL:
        raise ValueError("Machine has reached MK99.")
    result = replace(card, mk_level=card.mk_level + 1, upgrade_investment=round(card.upgrade_investment + cost, 2))
    if card.rarity is not Rarity.COMMON:
        return result
    rng = random.Random(f"{seed}:mk:{card.card_id}:{result.mk_level}")
    roll = rng.random()
    cumulative = 0.
    for rarity, probability in UPGRADE_RARITY_PROBABILITIES:
        cumulative += probability
        if roll < cumulative:
            quality = create_card_instance(card.card_id, card.definition_id, card.card_kind, rarity, seed=seed, salt=f"mk:{result.mk_level}")
            return replace(result, rarity=rarity, output_bonus_percent=quality.output_bonus_percent, power_bonus_percent=quality.power_bonus_percent)
    return result


def upgrade_cards(state, definitions, card_ids):
    if not card_ids or len(set(card_ids)) != len(card_ids):
        raise ValueError("Select distinct machines.")
    # Prepare every replacement before the single debit and commit.
    replacements = {}
    total = 0.
    for card_id in card_ids:
        card = state.cards[card_id]
        cost = mk_upgrade_cost(card, definitions[card.definition_id])
        replacements[card_id] = upgraded_card(card, cost, state.rng_seed)
        total += cost
    state.cash.spend(round(total, 2))
    state.cards.update(replacements)
    state.history.append("cash", state.cash.amount)


def rarity_distribution(upgrades=98):
    chance = sum(p for _, p in UPGRADE_RARITY_PROBABILITIES)
    special = 1 - (1 - chance) ** upgrades
    return {"common": 1 - special, **{rarity.value: special * p / chance for rarity, p in UPGRADE_RARITY_PROBABILITIES}}
