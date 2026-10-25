"""Presentation order is independent of building identity, prices and simulation order."""


def ordered_building_ids(state, kind, default_ids):
    default_ids = tuple(default_ids)
    remaining = set(default_ids)
    result = []
    for uid in state.building_order.get(kind, ()):
        if uid in remaining:
            result.append(uid)
            remaining.remove(uid)
    return tuple(result) + tuple(uid for uid in default_ids if uid in remaining)


def reorder_buildings(state, kind, ids):
    if kind not in {'resources', 'factory', 'freight'}:
        raise ValueError('Unknown building list')
    units = state.freight.facilities if kind == 'freight' else state.production_units(kind)
    ids = tuple(ids)
    if len(ids) != len(units) or set(ids) != set(units):
        raise ValueError('Building list changed; try moving the building again')
    state.building_order[kind] = list(ids)
