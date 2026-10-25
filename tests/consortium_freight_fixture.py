"""Explicit reserved Freight arrivals for preserved Consortium reward fixtures.

Uses actual vehicle capacity, dispatch, storage debit, time advancement and the
central economic completion; never writes Contract progress or reward receipts.
"""
from math import isfinite
from production_zero.core.freight import start_outbound_shipment_for_card,advance_outbound_shipments
from production_zero.core.simulation import SimulationEngine
from contract_capacity_fixture import provide_capacity

def freight_contribute(api, consortium_id, company_id, kind, resource_id, amount, *, request_id=None, company_state=None, expected_contract_id=None):
    if not isfinite(amount) or amount<=0:
        raise ValueError('Amount must be finite and positive.')
    contract=api.network.consortiums[consortium_id].contracts[kind]
    if expected_contract_id is not None and contract.contract_id!=expected_contract_id:
        raise ValueError('Contract changed.')
    source=api.state if company_id==api.current_company_id else company_state
    if source is None or source.consortium.current_company_id!=company_id:
        raise PermissionError('Authoritative source company required.')
    if request_id:
        from production_zero.core.consortium import _scoped_receipt
        if _scoped_receipt('freight',company_id,request_id) in contract.processed_request_ids:return 0.
    if source.ensure_resource(resource_id).amount<amount:
        raise ValueError('Insufficient Global Storage.')
    if amount>contract.remaining(resource_id)+1e-9:
        raise ValueError('Amount exceeds remaining requirement.')
    source.consortium=api.network if source is api.state else source.consortium
    if source is not api.state:
        # Separate firm and wallet, shared authoritative Consortium network.
        from copy import copy
        source.consortium=copy(api.network)
        source.consortium.current_company_id=company_id
    provide_capacity(source,api.definitions)
    cid=next(slot.card_id for f in source.freight.facilities.values() for slot in f.slots if slot.card_id and source.cards[slot.card_id].definition_id=='freight.truck')
    from production_zero.core.commands import AssignFreightVehicles
    from production_zero.core.commands import CommandBus
    CommandBus(source).dispatch(AssignFreightVehicles((cid,),resource_id,'consortium',api.definitions))
    before=contract.delivered.get(resource_id,0.)
    remaining=amount;index=0
    while remaining>1e-9:
        shipment=start_outbound_shipment_for_card(source.freight,source.cards,api.definitions,card_id=cid,destination_kind='consortium',resource_id=resource_id,quantity=remaining,target_id=f'{consortium_id}|{kind}|{contract.contract_id}',research=source.research)
        if shipment is None:raise ValueError('Vehicle unavailable.')
        source.resources[resource_id].consume(shipment.quantity)
        # Some preserved reward fixtures recreate a remote company per product.
        # Give their independent finite shipments explicit distinct fixture IDs.
        source.freight.outbound_shipments.pop(shipment.shipment_id)
        shipment.shipment_id=(request_id if index==0 else f'{request_id}-{index}') if request_id else f'fixture-{resource_id}-{len(contract.processed_request_ids)}'
        source.freight.outbound_shipments[shipment.shipment_id]=shipment
        completed=advance_outbound_shipments(source.freight,shipment.remaining_seconds)
        engine=SimulationEngine(api.definitions,utc_now=api.clock)
        engine._complete_outbound_shipments(source,completed)
        # Replay the same accepted economic object: neither sale nor contribution.
        engine._complete_outbound_shipments(source,completed)
        remaining-=shipment.quantity;index+=1
    return contract.delivered.get(resource_id,0.)-before

def freight_receive(api,consortium_id,kind,contract_id,resource_id,amount,delivery_id):
    return freight_contribute(api,consortium_id,api.current_company_id,kind,resource_id,amount,request_id=delivery_id,expected_contract_id=contract_id)
