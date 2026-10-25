"""P7 quotes, selected by the offline candidate audit; no simulations at runtime."""
from math import ceil, isfinite

PRICING_VERSION = 2
BOARD_LIMITS = {'factory': (5, 10, 3), 'resources': (3, 10, 1), 'energy': (3, 5, 1)}
SLOT_BASES = {'factory': 40.0, 'resources': 90.0, 'energy': 100.0}
RESOURCE_TYPES = frozenset({'machine.extractor', 'machine.drilling', 'machine.agriculture'})
FREIGHT_BUILD_BASES = {'garage_depot': 2000.0, 'rail_station': 8000.0, 'airport': 30000.0, 'harbor': 100000.0}
FREIGHT_SLOT_BASE = 60.0
FREIGHT_LINE_BASE = 900.0


def check_quote(cost, expected=None):
    if not isfinite(cost) or cost < 0:
        raise ValueError('Invalid infrastructure price.')
    if expected is not None and (not isfinite(expected) or expected < 0 or expected != cost):
        raise ValueError('Purchase price changed. Review the quote again.')
    return cost


def slot_price(board, line_number, slot_number, *, start_slots=None, max_slots=None):
    maximum, cap, start = BOARD_LIMITS[board]
    start = start if start_slots is None else start_slots
    cap = cap if max_slots is None else max_slots
    if type(line_number) is not int or line_number < 1 or type(slot_number) is not int or not start < slot_number <= cap:
        raise ValueError('Choose a valid additional slot.')
    return SLOT_BASES[board] * (slot_number - start)


def line_price(board, line_number, *, start_slots=None, max_slots=None):
    maximum, cap, start = BOARD_LIMITS[board]
    if type(line_number) is not int or line_number < 2:
        raise ValueError('Choose a valid additional line.')
    start = start if start_slots is None else start_slots
    cap = cap if max_slots is None else max_slots
    base = ceil((SLOT_BASES[board] * (cap-start) * start + 1) / 100) * 100
    return float(base * (line_number-1)**2)


def facility_price(board, count):
    if type(count) is not int or count < 0:
        raise ValueError('Invalid facility count.')
    maximum, cap, start = BOARD_LIMITS[board]
    if count == 0:
        return 500.0 if board == 'resources' else 1000.0
    extras = sum(SLOT_BASES[board] * i for i in range(1, cap-start+1))
    second = ceil((1.05 * (line_price(board,maximum) + extras) - extras) / 100) * 100
    try:
        quote = float(ceil(second * count**2.5 / 100) * 100)
    except (OverflowError, ValueError):
        raise ValueError('Infrastructure price exceeds the supported numeric range.') from None
    return check_quote(quote)


def production_facility_price(state, board, specialization=None, *, exclude_unit_id=None):
    units = state.production_units(board)
    if board == 'resources':
        specialization = specialization or 'machine.extractor'
        if specialization not in RESOURCE_TYPES:
            raise ValueError('Choose Mining, Agriculture or Drilling before purchasing.')
        count = sum(uid != exclude_unit_id and (unit.specialization or 'machine.extractor') == specialization for uid,unit in units.items())
    else:
        count = sum(uid != exclude_unit_id for uid in units)
    return facility_price(board,count)


def unit_line_price(unit, line_number, board=None):
    base = line_price(board if board not in (None,'legacy') else unit.board_kind,line_number,start_slots=unit.start_slots_per_line,max_slots=unit.max_slots_per_line)
    return scaled_expansion_price(base, unit.expansion_tier)


def unit_slot_price(unit, line_number, slot_number, board=None):
    base = slot_price(board if board not in (None,'legacy') else unit.board_kind,line_number,slot_number,start_slots=unit.start_slots_per_line,max_slots=unit.max_slots_per_line)
    return scaled_expansion_price(base, unit.expansion_tier)


def scaled_expansion_price(base, tier):
    if type(tier) is not int or tier < 1:
        raise ValueError('Invalid building expansion tier.')
    try:
        return check_quote(float(base * tier ** 2))
    except OverflowError:
        raise ValueError('Infrastructure price exceeds the supported numeric range.') from None


def expansion_key(board, specialization=None):
    if board in {'factory', 'energy'}:
        return board
    if board == 'resources' and (specialization or 'machine.extractor') in RESOURCE_TYPES:
        return 'resources:' + (specialization or 'machine.extractor')
    if board == 'freight' and specialization in FREIGHT_BUILD_BASES:
        return 'freight:' + specialization
    raise ValueError('Unknown building type for expansion pricing.')


def expansion_groups(state):
    groups = {}
    for board in BOARD_LIMITS:
        for unit in state.production_units(board).values():
            groups.setdefault(expansion_key(board, unit.specialization), []).append(unit)
    for unit in state.freight.facilities.values():
        groups.setdefault(expansion_key('freight', unit.facility_type), []).append(unit)
    return groups


def next_expansion_tier(state, board, specialization=None):
    key = expansion_key(board, specialization)
    units = expansion_groups(state).get(key, ())
    return max(state.infrastructure_tiers.get(key, 0), len(units), *(u.expansion_tier for u in units), 0) + 1


def record_expansion_tier(state, board, specialization, tier):
    state.infrastructure_tiers[expansion_key(board, specialization)] = tier


def infrastructure_tier_snapshot(state):
    tiers = dict(state.infrastructure_tiers)
    for key, units in expansion_groups(state).items():
        tiers[key] = max(tiers.get(key, 0), len(units), *(u.expansion_tier for u in units))
    return tiers


def migrate_infrastructure_pricing(state, source_version, resource_definitions):
    import re
    valid_keys = {'factory', 'energy', *('resources:' + k for k in RESOURCE_TYPES),
                  *('freight:' + k for k in FREIGHT_BUILD_BASES)}
    if any(k not in valid_keys or type(v) is not int or v < 0 for k, v in state.infrastructure_tiers.items()):
        raise ValueError('Invalid saved infrastructure expansion tiers.')
    for key, units in expansion_groups(state).items():
        if source_version < 2:
            # Numeric IDs give old saves a stable assignment independent of the
            # sidebar/dictionary order and user-editable building names.
            def natural_id(unit):
                uid = unit.facility_id if key.startswith('freight:') else unit.hall_id
                return tuple((1, int(part)) if part.isdigit() else (0, part) for part in re.split(r'(\d+)', uid))
            for tier, unit in enumerate(sorted(units, key=natural_id), 1):
                unit.expansion_tier = tier
        state.infrastructure_tiers[key] = max(state.infrastructure_tiers.get(key, 0), *(u.expansion_tier for u in units))
    if source_version < 2:
        from production_zero.core.storage_upgrades import migrate_storage_growth
        migrate_storage_growth(state, resource_definitions)


def resource_retype_price(state, unit, target):
    if target not in RESOURCE_TYPES:
        raise ValueError('Unknown resource site specialization.')
    if unit.specialization == target:
        return 0.0
    if any(slot.card_id for slot in unit.slots):
        raise ValueError('Move or sell machines before changing the site type.')
    # A type change buys access at the target's current quote. Slot/line spending
    # is never a credit toward cheaper acquisition of another specialization.
    return production_facility_price(state,'resources',target,exclude_unit_id=unit.hall_id)
