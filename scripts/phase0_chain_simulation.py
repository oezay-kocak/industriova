"""Actual SimulationEngine runs for the six Phase 0 analytic contract fixtures."""
import sys,os,json,math,time
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase0_benchmark import D,R,OUT,state
from production_zero.core.definitions import MachineDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import FactoryHall,MachineProductionState
from production_zero.core.freight import FreightFacility,FreightAssignment
from production_zero.core.contracts import ContractOffer,ActiveContract,refresh_contracts
from production_zero.core.simulation import SimulationEngine
from production_zero.core.market import BASE_MARKET_PRICES
producer={o.output_resource:(d,o) for d in {d.definition_id:d for d in D.values()}.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
rows=json.loads((OUT/'economy-model.json').read_text())['contracts'];results=[]
for row in rows:
    s=state();s.cash.amount=0;s.cards.clear();s.halls.clear();s.resource_sites.clear();s.energy_plants.clear();s.machine_production.clear()
    s.freight.facilities.clear();s.freight.assignments.clear();s.freight.outbound_shipments.clear()
    s.contracts.active.clear();s.company.level=row['level'];s.company.current_xp=0;s.warehouse_capacity=1e15
    for stock in s.resources.values():stock.amount=0
    s.production_progress.unlocked_production_ids.update(o.production_id for d,o in producer.values())
    mk=row['mk'];card_number=0
    def add(d,option=None):
        global card_number
        card_number+=1;cid=f'sim-{card_number}'
        s.cards[cid]=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),mk_level=mk)
        if option:
            board='resources' if not option.input_resources else 'factory'
            group=d.definition_id if board=='resources' else 'factory'
            cap=30 if board=='resources' else 50
        else:board='energy';group='energy';cap=15
        units=s.production_units(board)
        hosts=[u for u in units.values() if u.specialization==group and any(x.card_id is None for x in u.slots)]
        if not hosts:
            hid=f'{board}-{len(units)}';hosts=[FactoryHall(hid,hid,cap,board_kind=board,specialization=group,
                max_lines=3 if board!='factory' else 5,max_slots_per_line=5 if board=='energy' else 10,
                start_unlocked_lines=3 if board!='factory' else 5,start_slots_per_line=5 if board=='energy' else 10)]
            units[hid]=hosts[0]
        slot=next(x for x in hosts[0].slots if x.card_id is None);slot.card_id=cid
        if option:s.machine_production[cid]=MachineProductionState(cid,option.output_resource,option.production_id)
        return cid
    for rid,n in row['upstream_machine_counts'].items():
        for _ in range(n):add(*producer[rid])
    for _ in range(row['solar_count_at_same_mk']):add(D['energy.solar_array'])
    d=D[row['freight_type']];cid='contract-vehicle'
    s.cards[cid]=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),mk_level=mk)
    s.freight.facilities['vehicle-home']=FreightFacility('vehicle-home','Vehicle home',d.facility_id,slot_count=2)
    s.freight.facilities['vehicle-home'].slots[0].card_id=cid
    refresh_contracts(s,D)
    kind=row['kind'];offer=ContractOffer('phase0-contract',kind,'Phase 0',row['requirements'],row['accepted_cash'],row['accepted_xp'],
         s.contracts.daily_period_index if kind=='daily' else s.contracts.weekly_period_index)
    s.contracts.active[kind]=ActiveContract(offer)
    engine=SimulationEngine(D);start=time.perf_counter();limit=min(14400,math.ceil(row['conservative_sequential_minutes']*60*3+1200))
    elapsed=0;selection=None
    while elapsed<limit and s.contracts.active[kind].status=='active':
        active=s.contracts.active[kind]
        needs=[]
        for rid in row['requirements']:
            pending=sum(x.quantity for x in s.freight.outbound_shipments.values() if x.active and x.resource_id==rid and x.destination_kind=='contract')
            remaining=active.remaining_amount(rid)-pending
            if remaining>1e-6:needs.append((rid,s.resources[rid].amount))
        # Prefer a stocked requested product; do not cancel an in-flight reservation.
        if needs:
            choice=max(needs,key=lambda x:x[1])[0]
            s.freight.assignments[cid]=FreightAssignment(choice,'contract')
        engine.advance_time(s,1);elapsed+=1
    result={'scenario':row['scenario'],'kind':kind,'elapsed_seconds':elapsed,'completed':s.contracts.active[kind].status=='completed',
       'limit_seconds':limit,'wall_seconds':time.perf_counter()-start,'production_cards':len(s.machine_production),
       'factory_halls':len(s.halls),'resource_sites':len(s.resource_sites),'energy_plants':len(s.energy_plants),
       'solar_cards':row['solar_count_at_same_mk'],'power_mw':s.energy.generated,
       'delivered':s.contracts.active[kind].delivered,'required':row['requirements'],'cash':s.cash.amount,
       'ending_level':s.company.level,'ending_xp':s.company.current_xp,
       'min_stock':min(x.amount for x in s.resources.values())}
    results.append(result);print(json.dumps(result),flush=True)
    (OUT/'chain-simulation.json').write_text(json.dumps(results,indent=2),encoding='utf8')
