"""Infrastructure resale uses recorded cash investment, never replacement quotes."""
from math import floor


def production_building_resale(state, board_kind, unit_id, *, include_machines=False):
    units = state.production_units(board_kind)
    unit = units[unit_id]
    if len(units) <= 1:
        raise ValueError("Keep one building of each production area available.")
    if not include_machines and any(slot.card_id is not None for slot in unit.slots):
        raise ValueError("Building is occupied. Move or sell its machines first.")
    return floor(unit.building_investment * .6 * 100) / 100


def sell_production_building(state, board_kind, unit_id, definitions=None, include_machines=False):
    amount = production_building_resale(state, board_kind, unit_id, include_machines=include_machines)
    unit = state.production_units(board_kind)[unit_id]
    ids = tuple(s.card_id for s in unit.slots if s.card_id)
    if ids:
        if definitions is None:raise ValueError("Machine definitions required for an occupied building sale.")
        from production_zero.core.machine_operations import sell_machines
        sell_machines(state, definitions, ids)
    del state.production_units(board_kind)[unit_id]
    state.cash.add(amount)
    state.history.append("cash", state.cash.amount)
    return amount


def sell_freight_building(state, facility_id, definitions=None, include_machines=False):
    facility = state.freight.facilities[facility_id]
    if len(state.freight.facilities) <= 1:
        raise ValueError("Keep one freight building available.")
    if not include_machines and any(slot.card_id is not None for slot in facility.slots):
        raise ValueError("Move or sell vehicles before selling the freight building.")
    amount = floor(facility.building_investment * .6 * 100) / 100
    ids = tuple(s.card_id for s in facility.slots if s.card_id)
    if ids:
        if definitions is None:raise ValueError("Vehicle definitions required for an occupied building sale.")
        from production_zero.core.machine_operations import sell_machines
        # Existing sell validation rejects every in-transit vehicle before mutation.
        sell_machines(state, definitions, ids)
    del state.freight.facilities[facility_id]
    state.cash.add(amount)
    state.history.append("cash", state.cash.amount)
    return amount
