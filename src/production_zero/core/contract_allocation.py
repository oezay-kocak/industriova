"""One Contract cargo planner shared by runtime and explicit delivery commands."""
from math import fsum, isfinite

from production_zero.core.definitions import FreightDefinition
from production_zero.core.freight import (
    contract_shipment_allocations, start_outbound_shipment_for_card, _FreightDispatchIndex)


def pending_contract_deliveries(state):
    pending = {}
    for shipment in state.freight.outbound_shipments.values():
        if not shipment.active or not shipment.resource_id:
            continue
        for target, quantity in contract_shipment_allocations(shipment).items():
            if target in shipment.cancelled_contract_prices:
                continue
            key = target, shipment.resource_id
            pending[key] = pending.get(key, 0.) + quantity
    return pending


def allocate_contract_cargo(state, resource_id, quantity, *, pending=None):
    """Priority 2 -> 1 -> Even; capped equal shares within each priority.

    Reservations reduce each target's need. This pure plan never redirects an
    existing shipment and never assigns more cargo than the physical quantity.
    """
    from production_zero.core.contracts import CONTRACT_KINDS
    if not isfinite(quantity) or quantity < 0:
        raise ValueError('Contract cargo must be finite and nonnegative.')
    pending = pending_contract_deliveries(state) if pending is None else pending
    groups = {2: [], 1: [], 0: []}
    for kind in CONTRACT_KINDS:
        active = state.contracts.active.get(kind)
        if active is None or active.status != 'active':
            continue
        need = max(0., active.remaining_amount(resource_id) - pending.get((active.offer.contract_id, resource_id), 0.))
        if need > 0:
            groups[state.contracts.priorities.get(kind, 0)].append((active.offer.contract_id, need))
    result = {}
    left = quantity
    for priority in (2, 1, 0):
        targets = groups[priority]
        budget = min(left, fsum(need for _, need in targets))
        assigned = {}
        while targets and budget > 0:
            share = budget / len(targets)
            capped = [(target, need) for target, need in targets if need <= share]
            if capped:
                for target, need in capped:
                    assigned[target] = need
                budget = max(0., budget - fsum(need for _, need in capped))
                targets = [(target, need) for target, need in targets if need > share]
            else:
                for index, (target, need) in enumerate(targets):
                    amount = min(need, share if index < len(targets) - 1 else budget)
                    if amount > 0:
                        assigned[target] = amount
                    budget = max(0., budget - amount)
                break
        result.update(assigned)
        left = max(0., left - fsum(assigned.values()))
        if left <= 0:
            break
    return result


def dispatch_contract_freight(state, definitions, *, resource_ids=None, _dispatch_index=None):
    """Reserve each physical vehicle once, including mixed-target cargo."""
    pending = pending_contract_deliveries(state)
    index = _dispatch_index if _dispatch_index is not None else _FreightDispatchIndex(state.freight)
    busy = index.busy
    sent = {}
    for cid in index.ordered_card_ids:
        assignment = state.freight.assignments.get(cid)
        if cid in busy or assignment is None or assignment.destination_kind != 'contract':
            continue
        rid = assignment.resource_id
        if resource_ids is not None and rid not in resource_ids:
            continue
        card = state.cards.get(cid)
        definition = definitions.get(card.definition_id) if card else None
        if not isinstance(definition, FreightDefinition):
            continue
        stock = state.ensure_resource(rid)
        maximum = min(stock.amount, index.stats(card, definition, state.research).capacity)
        if maximum <= 0:
            continue
        allocation = allocate_contract_cargo(state, rid, maximum, pending=pending)
        if not allocation:
            continue
        quantity = fsum(allocation.values())
        shipment = start_outbound_shipment_for_card(state.freight, state.cards, definitions,
            card_id=cid, destination_kind='contract', resource_id=rid, quantity=quantity,
            target_id=next(iter(allocation)) if len(allocation) == 1 else None,
            contract_allocations=allocation, research=state.research, _dispatch_index=index)
        if shipment is None:
            continue
        stock.consume(shipment.quantity)
        busy.add(cid)
        sent[rid] = sent.get(rid, 0.) + shipment.quantity
        for target, amount in allocation.items():
            key = target, rid
            pending[key] = pending.get(key, 0.) + amount
        state.history.append(f'resource.{rid}', stock.amount)
    return sent
