"""Independent persisted scopes; never rewrite an individual machine's pause flag."""
def production_slot_paused(unit, index):
    return unit.paused or any(line.paused and index in line.slot_indexes for line in unit.production_lines)


def freight_line_number(facility, index):
    return index // facility.line_capacity


def freight_slot_paused(facility, index):
    return facility.paused or freight_line_number(facility, index) in facility.paused_lines


def effective_card_paused(state, card_id):
    if state.cards[card_id].paused:
        return True
    for unit in state.all_production_units():
        for slot in unit.slots:
            if slot.card_id == card_id:
                return production_slot_paused(unit, slot.index)
    return any(freight_slot_paused(unit, slot.index) for unit in state.freight.facilities.values()
               for slot in unit.slots if slot.card_id == card_id)
