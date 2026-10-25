"""Explicit powered/transported equipment for contract-focused synthetic tests."""
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import FactoryHall
from production_zero.core.freight import FreightFacility


def provide_capacity(state, definitions):
    if 'p8-fixture-mining' in state.resource_sites:
        return
    state.warehouse_capacity = max(75280., state.storage_capacity)
    groups = [
        ('resources','mining',['machine.extractor']),
        ('resources','drilling',['machine.drilling']),
        ('resources','agriculture',['machine.agriculture']),
        ('factory','machines',['machine.processor','machine.fabricator','machine.assembler']),
        ('energy','power',['energy.solar_array']*4),
    ]
    for board,name,ids in groups:
        uid='p8-fixture-'+name
        hall=FactoryHall(uid,name,len(ids),board_kind=board,specialization=ids[0] if board=='resources' else None,max_lines=1,max_slots_per_line=len(ids),start_unlocked_lines=1,start_slots_per_line=len(ids))
        state.production_units(board)[uid]=hall
        for i,did in enumerate(ids):
            cid=uid+str(i)
            state.cards[cid]=create_card_instance(cid,did,definitions[did].card_kind,Rarity.COMMON)
            hall.slots[i].card_id=cid
    freight=FreightFacility('p8-fixture-freight','Fixture Garage')
    state.freight.facilities[freight.facility_id]=freight
    for i in range(3):
        cid='p8-fixture-truck'+str(i)
        state.cards[cid]=create_card_instance(cid,'freight.truck',definitions['freight.truck'].card_kind,Rarity.COMMON)
        freight.slots[i].card_id=cid


def provide_logistics(state, definitions):
    """Power, warehouse and trucks only; keep legacy mixed-board test layout."""
    provide_capacity(state,definitions)
    for uid in ('p8-fixture-mining','p8-fixture-drilling','p8-fixture-agriculture'):
        hall=state.resource_sites.pop(uid,None)
        if hall:
            for slot in hall.slots:
                if slot.card_id:state.cards.pop(slot.card_id,None)
    hall=state.halls.pop('p8-fixture-machines',None)
    if hall:
        for slot in hall.slots:
            if slot.card_id:state.cards.pop(slot.card_id,None)

    # Keep this deliberately legacy mixed-board fixture in the old command
    # resolution mode; the generator still sees its actual installed solar.
    plant=state.energy_plants.pop('p8-fixture-power',None)
    if plant:state.halls[plant.hall_id]=plant


def remote_stock(company_id, resource_id, amount):
    """Finite synthetic sender storage for server-boundary contribution tests."""
    from production_zero.core.state import GameState
    state=GameState(8800,warehouse_capacity=max(75280.,amount))
    state.consortium.current_company_id=company_id
    state.ensure_resource(resource_id).amount=amount
    return state
