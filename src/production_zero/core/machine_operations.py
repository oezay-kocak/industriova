"""Validated atomic operations shared by production boards and Supply."""
from dataclasses import replace
from math import floor
from uuid import uuid4

from production_zero.core.commands import _card_allowed_on_board, SelectMachineProduction
from production_zero.core.definitions import EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import is_freight_card_busy
from production_zero.core.progression import production_options_for_machine

SITE_TYPES = {
    "machine.extractor": "Mining Complex",
    "machine.drilling": "Drilling Field",
    "machine.agriculture": "Agricultural Estate",
}


def compatible_free_slots(state, definition):
    if isinstance(definition, FreightDefinition):
        return tuple((facility, slot) for facility in state.freight.facilities.values() if facility.facility_type == definition.facility_id for slot in facility.slots if slot.index in facility.unlocked_slot_indexes() and slot.card_id is None)
    from production_zero.core.cards import create_card_instance
    probe = create_card_instance("probe", definition.definition_id, definition.card_kind, Rarity.COMMON)
    result = []
    for board in ("resources", "factory", "energy"):
        if not _card_allowed_on_board(probe, board):
            continue
        for unit in state.production_units(board).values():
            if board == "resources" and not site_accepts(state, unit, definition.definition_id):
                continue
            result.extend((unit, slot) for slot in unit.slots if slot.index in unit.unlocked_slot_indexes() and slot.card_id is None)
    return tuple(result)


def site_accepts(state, site, definition_id):
    if site.specialization is not None:
        return site.specialization == definition_id
    occupants = [state.cards[s.card_id].definition_id for s in site.slots if s.card_id in state.cards]
    return not occupants or all(did == definition_id for did in occupants)


def buy_and_install(state, definition, quantity, unit_price, *, rarity=Rarity.COMMON, bonus_tenths=0):
    from production_zero.core.cards import create_card_instance
    if type(quantity) is not int or not 1 <= quantity <= 10000:
        raise ValueError("Enter a whole purchase quantity from 1 to 10000.")
    slots = compatible_free_slots(state, definition)
    if len(slots) < quantity:
        raise ValueError(f"Only {len(slots)} compatible free slots available.")
    total = round(unit_price * quantity, 2)
    cards = [replace(create_card_instance(f"machine-{uuid4().hex}", definition.definition_id, definition.card_kind, rarity, bonus_tenths=bonus_tenths), acquisition_cost=unit_price) for _ in range(quantity)]
    state.cash.spend(total)
    for card, (unit, slot) in zip(cards, slots):
        state.cards[card.card_id] = card
        slot.card_id = card.card_id
        if getattr(unit, "board_kind", "") == "resources" and unit.specialization is None:
            unit.specialization = definition.definition_id
    state.history.append("cash", state.cash.amount)
    return tuple(card.card_id for card in cards)


def resale_value(card, definition):
    # Unknown historical acquisition is not evidence of a cash investment.
    basis = card.acquisition_cost if card.acquisition_cost is not None else 0.0
    # Random quality gains do not mint resale money. Paid Daily quality does.
    return floor((basis + card.upgrade_investment) * .8 * 100 + 1e-7) / 100


def sell_machines(state, definitions, card_ids):
    if not card_ids or len(card_ids) != len(set(card_ids)):
        raise ValueError("Select distinct machines.")
    cards = [state.cards[cid] for cid in card_ids]
    selected = set(card_ids)
    if any(not isinstance(definitions.get(card.definition_id), (MachineDefinition, EnergyDefinition, FreightDefinition)) for card in cards):
        raise ValueError("Select owned production, energy or freight cards.")
    for card in cards:
        if is_freight_card_busy(state.freight, card.card_id):
            raise ValueError("A vehicle in transit cannot be sold.")
    amount = round(sum(resale_value(card, definitions[card.definition_id]) for card in cards), 2)
    from math import isfinite
    if not isfinite(amount) or amount < 0 or not isfinite(state.cash.amount + amount):
        raise ValueError("Sale exceeds the supported cash range.")
    for unit in (*state.all_production_units(), *state.freight.facilities.values()):
        for slot in unit.slots:
            if slot.card_id in selected:
                slot.card_id = None
    for cid in card_ids:
        state.cards.pop(cid)
        state.machine_production.pop(cid, None)
        state.freight.assignments.pop(cid, None)
    state.cash.add(amount)
    state.history.append("cash", state.cash.amount)
    return amount


def return_machines_to_inventory(state, card_ids):
    """Detach an entire installed group; its ID-bound configuration is frozen.

    Simulation only visits installed slots. Inputs are consumed at completion,
    so retaining progress requires no refund, reservation or new cycle state.
    """
    if not card_ids or len(card_ids) != len(set(card_ids)):
        raise ValueError("Select distinct installed machines.")
    selected = set(card_ids)
    if not selected <= state.cards.keys():
        raise ValueError("Select owned existing machines.")
    if any(state.cards[cid].card_kind not in {CardKind.MACHINE, CardKind.ENERGY, CardKind.FREIGHT} for cid in selected):
        raise ValueError("Select production, energy or freight cards.")
    if any(is_freight_card_busy(state.freight, cid) for cid in selected):
        raise ValueError("A vehicle with a reserved shipment cannot be returned.")
    origins = [slot for unit in (*state.all_production_units(), *state.freight.facilities.values())
               for slot in unit.slots if slot.card_id in selected]
    if len(origins) != len(selected) or {slot.card_id for slot in origins} != selected:
        raise ValueError("Every returned machine must be installed exactly once.")
    for slot in origins:
        slot.card_id = None


def pause_machines(state, card_ids, paused):
    if not card_ids or len(card_ids) != len(set(card_ids)):
        raise ValueError("Select distinct machines.")
    replacements = {cid: replace(state.cards[cid], paused=bool(paused)) for cid in card_ids}
    state.cards.update(replacements)


def configure_machines(state, definitions, card_ids, production_id):
    if not card_ids or len(card_ids) != len(set(card_ids)):
        raise ValueError("Select distinct machines.")
    plans = []
    for cid in card_ids:
        definition = definitions[state.cards[cid].definition_id]
        if not isinstance(definition, MachineDefinition):
            raise ValueError("This selection contains a non-production machine.")
        option = next((p for p in production_options_for_machine(state, definition) if p.production_id == production_id), None)
        if option is None:
            raise ValueError("Recipe must be unlocked and compatible with every selected machine.")
        plans.append(SelectMachineProduction(cid, option.production_id, option.output_resource))
    for command in plans:
        command.apply(state)


def installed_slot_snapshot(state, card_ids):
    """Stable positions for a drag intent; never store mutable slot references."""
    selected = set(card_ids)
    return tuple((board, uid, slot.index, slot.card_id)
                 for board, uid, unit in _placement_units(state)
                 for slot in unit.slots if slot.card_id in selected)


def _placement_units(state):
    for board in ('resources', 'factory', 'energy'):
        for uid, unit in state.production_units(board).items():
            yield board, uid, unit
    for uid, unit in state.freight.facilities.items():
        yield 'freight', uid, unit


def plan_slot_permutation(state, card_ids, board_kind, target_unit_id,
                          target_indexes, *, definitions=None, expected_origins=None):
    """Close injective source->destination paths into cycles, then validate.

    At each path end, its original occupant (including None) returns to the
    path's root. Already closed cycles need no displaced counterpart. All
    assignments and resource specializations are prepared before any mutation.
    """
    if (not card_ids or any(not isinstance(cid, str) for cid in card_ids)
            or len(set(card_ids)) != len(card_ids)
            or len(card_ids) != len(target_indexes)
            or any(type(i) is not int or i < 0 for i in target_indexes)
            or len(set(target_indexes)) != len(target_indexes)):
        raise ValueError('Select distinct cards and distinct unlocked target slots.')
    if board_kind not in {'resources', 'factory', 'energy', 'freight'}:
        raise ValueError('Choose a compatible board.')
    selected = set(card_ids)
    slots, units, locations = {}, {}, {}
    for board, uid, unit in _placement_units(state):
        units[board, uid] = unit
        for slot in unit.slots:
            key = (board, uid, slot.index)
            if key in slots:
                raise ValueError('Duplicate slot identity. Reload a valid company.')
            slots[key] = slot
            if slot.card_id is not None:
                locations.setdefault(slot.card_id, []).append(key)
    if len({id(slot) for slot in slots.values()}) != len(slots):
        raise ValueError('Duplicate physical slot identity.')
    if any(cid not in state.cards or state.cards[cid].card_id != cid or len(locations.get(cid, ())) != 1 for cid in selected):
        raise ValueError('Every moving card must be owned and installed exactly once.')
    if expected_origins is not None:
        current = installed_slot_snapshot(state, card_ids)
        if tuple(map(tuple, expected_origins)) != current:
            raise ValueError('The source positions changed. Start a new drag.')
    origins = tuple(locations[cid][0] for cid in card_ids)
    targets = tuple((board_kind, target_unit_id, i) for i in target_indexes)
    if any(key not in slots for key in targets):
        raise ValueError('The target slot no longer exists or is locked.')
    forward = dict(zip(origins, targets))
    reverse = {target: origin for origin, target in forward.items()}
    final = {target: cid for target, cid in zip(targets, card_ids)}
    for end in targets:
        if end in forward:
            continue
        root = end
        while root in reverse:
            root = reverse[root]
        final[root] = slots[end].card_id
    # An injective finite graph is a disjoint union of paths and cycles.
    if set(final) != set(origins) | set(targets):
        raise ValueError('Ambiguous slot permutation.')
    specializations = []
    affected = {key[:2] for key in final}
    for key, cid in final.items():
        board, uid, index = key
        unit = units[board, uid]
        if index not in unit.unlocked_slot_indexes():
            raise ValueError('A source or target slot is locked.')
        if cid is None:
            continue
        if cid not in state.cards or state.cards[cid].card_id != cid or len(locations.get(cid, ())) != 1:
            raise ValueError('A counterpart must be owned and installed exactly once.')
        card = state.cards[cid]
        if board == 'freight':
            definition = (definitions or {}).get(card.definition_id)
            if card.card_kind is not CardKind.FREIGHT or not isinstance(definition, FreightDefinition) or definition.facility_id != unit.facility_type:
                raise ValueError('A vehicle is incompatible with its resulting facility.')
            if is_freight_card_busy(state.freight, cid):
                raise ValueError('A source or counterpart has a reserved delivery. Wait for arrival before moving it.')
        elif not _card_allowed_on_board(card, board):
            raise ValueError('A source or counterpart is incompatible with its resulting board.')
    for board, uid in affected:
        if board != 'resources':
            continue
        unit = units[board, uid]
        occupants = [final.get((board, uid, slot.index), slot.card_id) for slot in unit.slots]
        if any(cid is not None and cid not in state.cards for cid in occupants):
            raise ValueError('The resource site contains an unknown card.')
        families = {state.cards[cid].definition_id for cid in occupants if cid is not None}
        if len(families) > 1 or (families and unit.specialization is not None and families != {unit.specialization}):
            raise ValueError('The resulting resource site has incompatible machine families.')
        if families and unit.specialization is None:
            specializations.append((unit, next(iter(families))))
    return tuple((slots[key], cid) for key, cid in final.items()), tuple(specializations)


def commit_slot_permutation(plan):
    assignments, specializations = plan
    for slot, cid in assignments:
        slot.card_id = cid
    for unit, family in specializations:
        unit.specialization = family


def move_machines(state, card_ids, board_kind, target_unit_id, target_indexes, *, expected_origins=None):
    commit_slot_permutation(plan_slot_permutation(
        state, card_ids, board_kind, target_unit_id, target_indexes,
        expected_origins=expected_origins))

def copy_configuration(state, card_ids):
    return tuple((state.cards[cid].definition_id, state.machine_production[cid].selected_production_id if cid in state.machine_production else None, state.cards[cid].paused) for cid in card_ids)


def paste_configuration(state, definitions, card_ids, configurations):
    if not configurations or len(card_ids) != len(configurations) or len(set(card_ids)) != len(card_ids):
        raise ValueError("Select the same number of existing machines as copied configurations.")
    plans = []
    for cid, (definition_id, production_id, paused) in zip(card_ids, configurations):
        if state.cards[cid].definition_id != definition_id:
            raise ValueError("Copied configuration requires matching machine families.")
        definition = definitions[definition_id]
        if production_id is not None and production_id not in {p.production_id for p in production_options_for_machine(state, definition)}:
            raise ValueError("Copied production is unavailable.")
        plans.append((cid, production_id, paused))
    for cid, production_id, paused in plans:
        if production_id is not None:
            configure_machines(state, definitions, (cid,), production_id)
        elif cid in state.machine_production:
            configuration = state.machine_production[cid]
            configuration.selected_production_id = None
            configuration.target_resource_id = ""
            configuration.progress_seconds = 0.
        pause_machines(state, (cid,), paused)
