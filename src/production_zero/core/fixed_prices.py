"""Authoritative N1/C2 prices, without historical minimum-price anchors."""
from importlib.resources import files
from math import fsum, isfinite
from production_zero.core.definitions import MachineDefinition
from production_zero.data.definitions import load_card_definitions


STAGE_LABOUR_PER_MINUTE = {'processor': 120., 'fabricator': 40., 'assembler': 120.}
PRIMARY_PRICE = 1.


def build_fixed_prices(resource_catalog):
    """Use catalog IDs only; recursively add each recipe's own machine work.

    Input prices contain upstream work already. Energy infrastructure is paid
    by the player; C2 has no separate energy surcharge or recursive rounding.
    """
    prices = {}
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    recipes = [(definition, option) for definition in definitions.values() if isinstance(definition, MachineDefinition) for option in definition.available_production_options]
    if len({o.output_resource for _, o in recipes}) != len(recipes) or {o.output_resource for _, o in recipes} != set(resource_catalog):
        raise ValueError('Fixed price catalog requires exactly one producer per product.')
    pending = list(recipes)
    ready = set()
    while pending:
        advanced = False
        for definition, option in tuple(pending):
            if not set(option.input_resources) <= ready:
                continue
            output = option.output_amount_for(definition)
            cycle = option.cycle_seconds_for(definition)
            if not all(isfinite(x) and x > 0 for x in (output, cycle, *option.input_resources.values())):
                raise ValueError('Fixed prices require positive finite quantities and times.')
            inputs = fsum(prices[rid] * amount for rid, amount in option.input_resources.items()) / output
            price = inputs + STAGE_LABOUR_PER_MINUTE[definition.machine_type.value] * cycle / (60 * output) if option.input_resources else PRIMARY_PRICE
            if not isfinite(price) or price <= 0:
                raise ValueError('Invalid fixed product price.')
            prices[option.output_resource] = price
            ready.add(option.output_resource)
            pending.remove((definition, option))
            advanced = True
        if not advanced:
            raise ValueError("Fixed price calculation found cyclic or missing recipe inputs.")
    return prices
