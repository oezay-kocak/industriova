"""Conservative, finite production plans for contract generation, never per paint.

Rates describe recoverable capacity: resume/reconfigure owned equipment in paid
slots, clear warehouse space and reassign freight. Stock, routes and pause are
deliberately not quote inputs. Thus a transient stop cannot buy an easier offer.
Each full chain reserves upstream throughput, power and a finite batch buffer.
Selected products share a serial time budget, so intermediate goods cannot be
promised twice. Actual engine duration includes ramp-up and freight batches.
"""
from dataclasses import dataclass
from collections import defaultdict
from hashlib import sha256
import json
from math import floor, isfinite

from production_zero.core.definitions import MachineDefinition, EnergyDefinition, FreightDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.modifiers import research_multiplier
from production_zero.core.progression import is_production_unlocked
from production_zero.core.market import market_price_for

BALANCE_VERSION = 1
TARGET_MINUTES = {"regular": 8., "daily": 60., "weekly": 240.}
CASH_BONUS = {"regular": 0., "daily": .20, "weekly": .40}


@dataclass(frozen=True)
class CapacityPlan:
    rates: dict[str, float]
    production_rates: dict[str, float]
    freight_per_minute: float
    power: float
    signature: str


def capacity_inputs(state):
    """Immutable lasting inputs, checked directly even after external mutations."""
    return (
        state.economy_version,
        tuple(sorted((c.card_id, c.definition_id, c.mk_level, c.output_bonus_percent, c.power_bonus_percent) for c in state.cards.values())),
        tuple(sorted((h.hall_id, h.board_kind, h.specialization, tuple(sorted(h.unlocked_slot_indexes()))) for h in state.all_production_units())),
        tuple(sorted((f.facility_id, f.facility_type, tuple(sorted(f.unlocked_slot_indexes()))) for f in state.freight.facilities.values())),
        tuple(sorted((cid,p.selected_production_id) for cid,p in state.machine_production.items())),
        tuple(sorted(state.production_progress.unlocked_production_ids)),
        tuple(sorted(rid for rid,amount in state.production_progress.lifetime_produced.items() if amount>0)),
        tuple(sorted(state.research.unlocked_node_ids)), tuple(sorted(state.research.specializations.items())),
        state.storage_capacity, state.company.level,
    )


def capacity_signature(state, inputs=None):
    """Keep the existing quote signature/IDs byte-for-byte unchanged."""
    payload = capacity_inputs(state) if inputs is None else inputs
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _usable_cards(state, definitions):
    # Count a card only once, in an already paid compatible slot. Installed
    # legacy mixed boards remain valid. Uninstalled cards can fill FREE slots.
    placed = state.installed_card_ids() | state.installed_freight_card_ids()
    installed = {h.slots[i].card_id for h in state.all_production_units() for i in h.unlocked_slot_indexes() if h.slots[i].card_id}
    installed |= {f.slots[i].card_id for f in state.freight.facilities.values() for i in f.unlocked_slot_indexes() if f.slots[i].card_id}
    result = [state.cards[cid] for cid in sorted(installed) if cid in state.cards]
    free = []
    for hall in state.all_production_units():
        for i in hall.unlocked_slot_indexes():
            if hall.slots[i].card_id is None:
                free.append((hall.board_kind, hall.specialization))
    freight_free = []
    for facility in state.freight.facilities.values():
        for i in facility.unlocked_slot_indexes():
            if facility.slots[i].card_id is None:
                freight_free.append(facility.facility_type)
    for card in sorted(state.cards.values(), key=lambda c: (-c.output_multiplier, c.card_id)):
        if card.card_id in placed:
            continue
        definition = definitions.get(card.definition_id)
        if isinstance(definition, FreightDefinition):
            if definition.facility_id in freight_free:
                freight_free.remove(definition.facility_id)
                result.append(card)
            continue
        for index, (board, specialization) in enumerate(free):
            compatible = (isinstance(definition, EnergyDefinition) and board == "energy") or (
                isinstance(definition, MachineDefinition) and (
                    (board == "resources" and (specialization == definition.definition_id or (specialization is None and definition.machine_type.value == "extractor"))) or
                    (board == "factory" and definition.machine_type.value in {"processor", "fabricator", "assembler"})))
            if compatible:
                free.pop(index)
                result.append(card)
                break
    return result


def reachable_capacity(state, definitions, signature=None):
    # Optional unusable fuel equipment must never erase an independently
    # powered chain. Compare conservative operating modes, not current pause.
    cards = _usable_cards(state, definitions)
    signature = capacity_signature(state) if signature is None else signature
    storage_capacity = state.storage_capacity
    independent = _capacity_for_power(state, definitions, include_fuel=False, cards=cards, signature=signature, storage_capacity=storage_capacity)
    fuel_cards = [(c,definitions[c.definition_id]) for c in cards
                  if isinstance(definitions.get(c.definition_id),EnergyDefinition) and definitions[c.definition_id].requires_fuel]
    supported = [(c,d) for c,d in fuel_cards if state.production_progress.lifetime_produced.get(d.fuel_resource_id,0.)>0 or independent.production_rates.get(d.fuel_resource_id,0.)>0]
    if not supported:
        return independent
    # A small self-sustaining plant remains an option when running every owned
    # plant would exhaust fuel. Bound the search to all supported plants plus
    # one least-burning plant per fuel, never exponential subset enumeration.
    choices = {frozenset(c.card_id for c,_ in supported)}
    for fuel in {d.fuel_resource_id for _,d in supported}:
        card,_ = min(((c,d) for c,d in supported if d.fuel_resource_id==fuel),key=lambda pair:(pair[1].fuel_consumption_per_minute*pair[0].mk_multiplier,-pair[1].base_power_output*pair[0].output_multiplier,pair[0].card_id))
        choices.add(frozenset((card.card_id,)))
    modes = [independent]
    for chosen in sorted(choices,key=lambda ids:tuple(sorted(ids))):
        candidate = _capacity_for_power(state,definitions,include_fuel=True,fuel_card_ids=chosen, cards=cards, signature=signature, storage_capacity=storage_capacity)
        if candidate.production_rates:modes.append(candidate)
    production = {rid:max(p.production_rates.get(rid,0.) for p in modes) for rid in sorted({rid for p in modes for rid in p.production_rates})}
    rates = {rid:min(rate,independent.freight_per_minute) for rid,rate in production.items() if independent.freight_per_minute>0}
    return CapacityPlan(rates,production,independent.freight_per_minute,max(p.power for p in modes),independent.signature)


def _capacity_for_power(state, definitions, *, include_fuel, fuel_card_ids=None, cards=None, signature=None, storage_capacity=None):
    cards = _usable_cards(state, definitions) if cards is None else cards
    signature = capacity_signature(state) if signature is None else signature
    storage_capacity = state.storage_capacity if storage_capacity is None else storage_capacity
    machines = defaultdict(list)
    configured_machines = defaultdict(list)
    power = 0.
    independent_power = 0.
    fuel = defaultdict(float)
    freight = 0.
    for card in cards:
        definition = definitions.get(card.definition_id)
        if isinstance(definition, MachineDefinition):
            machines[definition.machine_type].append((card, definition))
            production = state.machine_production.get(card.card_id)
            if production and production.selected_production_id:
                rid = definition.production_option(production.selected_production_id).output_resource
                configured_machines[rid].append((card,definition))
        elif isinstance(definition, EnergyDefinition):
            if definition.requires_fuel and (not include_fuel or fuel_card_ids is not None and card.card_id not in fuel_card_ids):
                continue
            power += definition.base_power_output * card.output_multiplier * research_multiplier(state.research, "energy_output")
            if definition.requires_fuel:
                fuel[definition.fuel_resource_id] += definition.fuel_consumption_per_minute * card.mk_multiplier
            else:
                independent_power += definition.base_power_output * card.output_multiplier * research_multiplier(state.research, "energy_output")
        elif isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition, state.research)
            freight += stats.capacity * 60 / stats.transport_time_seconds
    producers = {}
    # A fuel-only cold start cannot manufacture its first fuel without power.
    # Historical real fuel production is stable proof of an established chain;
    # an empty/pause snapshot cannot remove that proof or cheapen the offer.
    if fuel and independent_power <= 0 and any(state.production_progress.lifetime_produced.get(rid,0.) <= 0 for rid in fuel):
        return CapacityPlan({}, {}, freight, power, signature)
    for definition in definitions.values():
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                if definition.is_compatible_with(option) and is_production_unlocked(state, option):
                    producers.setdefault(option.output_resource, (definition, option))
    speed = research_multiplier(state.research, "production_speed")
    # Reconfigurable products all choose the same lowest-output family member.
    # min preserves the original stable-sort tie order without sorting the full
    # owned family again for every possible product.
    reconfigurable = {kind: min(pool, key=lambda pair: pair[0].output_multiplier)
                      for kind, pool in machines.items()}
    cache = {}

    def work(resource_id, stack=()):
        if resource_id in cache:
            return cache[resource_id]
        if resource_id not in producers or resource_id in stack:
            return None
        definition, option = producers[resource_id]
        pool = configured_machines.get(resource_id,[])
        configured = bool(pool)
        if not pool:
            # A newly chosen product can be configured on one existing machine;
            # do not silently assume every other machine is reconfigured too.
            fallback = reconfigurable.get(definition.machine_type)
            pool = [fallback] if fallback is not None else []
        # A whole machine must fit available power. Average energy is insufficient.
        usable = []
        remaining_power = power
        for card, machine in sorted(pool, key=lambda pair: option.power_draw_for(pair[1]) * pair[0].power_multiplier):
            draw = option.power_draw_for(machine) * card.power_multiplier
            if draw <= remaining_power + 1e-9:
                remaining_power -= draw
                usable.append((card, machine))
        if not usable:
            return None
        output = sum(option.output_amount_for(d) * c.output_multiplier * speed * 60 / option.cycle_seconds_for(d) for c, d in usable)
        # Lowest bonus is conservative for input efficiency; MK scales inputs.
        bonus = min(c.output_multiplier / c.mk_multiplier for c, _ in usable)
        batch = max(option.output_amount_for(d) * c.output_multiplier + sum(option.input_resources.values()) * c.mk_multiplier for c, d in usable)
        if batch > storage_capacity + 1e-9:
            return None
        work_key = resource_id
        if not configured:
            card, machine = usable[0]
            selected = state.machine_production.get(card.card_id)
            work_key = machine.production_option(selected.selected_production_id).output_resource if selected and selected.selected_production_id else "unconfigured:"+card.card_id
        workload = {work_key: 1 / output}
        energy_per_unit = sum(option.power_draw_for(d) * c.power_multiplier for c,d in usable) / output
        footprint = {resource_id: batch}
        for rid, amount in option.input_resources.items():
            upstream = work(rid, (*stack, resource_id))
            if upstream is None:
                return None
            ratio = amount / (option.output_amount_for(definition) * bonus)
            for family, effort in upstream[0].items():
                workload[family] = workload.get(family,0.) + ratio * effort
            energy_per_unit += ratio * upstream[1]
            footprint.update(upstream[2])
        if sum(footprint.values()) > storage_capacity + 1e-9:
            return None
        cache[resource_id] = workload, energy_per_unit, footprint
        return cache[resource_id]

    # Burn is a full-time background load. Reserve producer work and energy
    # for all powered fuel plants before offering any exported product.
    fuel_work = defaultdict(float)
    fuel_power = 0.
    for rid, amount in fuel.items():
        effort = work(rid)
        if effort is None:
            return CapacityPlan({}, {}, freight, power, signature)
        for family, minutes in effort[0].items():
            fuel_work[family] += amount * minutes
        fuel_power += amount * effort[1]

    production_rates = {}
    if power > fuel_power and max(fuel_work.values(),default=0.) <= 1:
        for rid in producers:
            effort = work(rid)
            if effort is not None:
                bounds = [(1-fuel_work.get(family,0.))/minutes for family,minutes in effort[0].items()]
                if effort[1]>0:bounds.append((power-fuel_power)/effort[1])
                if min(bounds)>0:
                    production_rates[rid] = min(bounds)
    rates = {rid: min(rate, freight) for rid, rate in production_rates.items() if freight > 0}
    return CapacityPlan(rates, production_rates, freight, power, signature)


def requirements_for_rates(rates, prices, selected, minutes):
    if not selected or any(rates.get(rid, 0) <= 0 for rid in selected):
        raise ValueError("Selected products need a complete powered chain, paid slots and Freight.")
    # Equal fixed goods value per slot. Serial shares prevent reuse of the same
    # machine, raw material, energy or freight capacity across selected goods.
    goods_value = minutes / sum(1 / (rates[rid] * prices[rid]) for rid in selected)
    return {rid: float(max(1, floor(goods_value / prices[rid]))) for rid in selected}


def combined_rates(member_rates):
    """Time-share each member among only its supported products, never n*local."""
    result = defaultdict(float)
    for rates in member_rates:
        for rid, rate in rates.items():
            if isfinite(rate) and rate > 0:
                result[rid] += rate
    return dict(result)
