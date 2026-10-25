"""Validation for an explicit Freight route confirmation; no dispatch/reservation."""
from math import isfinite
from time import time

from production_zero.core.definitions import FreightDefinition
from production_zero.core.freight import OUTBOUND_FREIGHT_DESTINATIONS
from production_zero.core.machine_operations import installed_slot_snapshot


def target_problem(state, resource_id, destination, *, now=None):
    if destination not in OUTBOUND_FREIGHT_DESTINATIONS:
        return 'Choose Sell, Contract or Consortium Contract. Event is not available yet.'
    if destination == 'market':
        return ''
    now = time() if now is None else now
    if destination == 'contract':
        from production_zero.core.contract_allocation import pending_contract_deliveries
        reservations = pending_contract_deliveries(state)
        for active in state.contracts.active.values():
            offer = active.offer
            if active.status != 'active' or (offer.expires_at is not None and offer.expires_at <= now):
                continue
            pending = reservations.get((offer.contract_id, resource_id), 0.)
            if active.remaining_amount(resource_id) > pending:
                return ''
        return 'No active contract needs this cargo. Accept a contract and select this product there first; reserved deliveries already count.'
    membership = state.consortium.membership()
    if membership is None:
        return 'Join a consortium before choosing Consortium Contract.'
    consortium, _member = membership
    for kind, contract in consortium.contracts.items():
        if contract.status != 'active' or contract.expires_at <= now:
            continue
        target = f'{consortium.consortium_id}|{kind}|{contract.contract_id}'
        pending = sum(s.quantity for s in state.freight.outbound_shipments.values()
                      if s.active and s.destination_kind == destination
                      and s.target_id == target and s.resource_id == resource_id)
        if contract.remaining(resource_id) > pending:
            return ''
    return 'No active consortium contract needs this cargo. Ask a contract manager to select it; reserved deliveries already count.'


def validate_route(state, ids, resource_id, destination, *, definitions=None,
                   expected_origins=None, require_target=False):
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Select distinct installed vehicles.')
    positions = installed_slot_snapshot(state, ids)
    if expected_origins is not None and tuple(expected_origins) != positions:
        raise ValueError('The selected vehicles moved. Reopen route assignment.')
    if len(positions) != len(ids) or {p[3] for p in positions} != set(ids):
        raise ValueError('Select installed vehicles; a selected card was removed or has duplicate placement.')
    if len({p[:3] for p in positions}) != len(positions):
        raise ValueError('The selected Freight slots have duplicate indexes.')
    for board, uid, index, cid in positions:
        card = state.cards.get(cid)
        unit = state.freight.facilities.get(uid)
        if board != 'freight' or card is None or card.card_id != cid or unit is None:
            raise ValueError('Select owned, installed Freight vehicles.')
        if index < 0 or index >= unit.slot_count or index not in unit.unlocked_slot_indexes():
            raise ValueError('The selected Freight slot is no longer unlocked.')
        if definitions is not None:
            definition = definitions.get(card.definition_id)
            if not isinstance(definition, FreightDefinition) or definition.facility_id != unit.facility_type:
                raise ValueError('A selected vehicle is incompatible with its facility.')
    stock = state.resources.get(resource_id)
    if stock is None:
        raise ValueError('Select an available cargo resource.')
    if destination not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError('Choose an available delivery target.')
    if require_target:
        if not isfinite(stock.amount) or stock.amount <= 0:
            raise ValueError('No stored cargo remains. Choose another resource or wait for production.')
        problem = target_problem(state, resource_id, destination)
        if problem:
            raise ValueError(problem)
