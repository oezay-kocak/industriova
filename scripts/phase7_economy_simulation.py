"""P7 counterfactual candidate audit. Engine flows are real; quotes are models.

Mature scenes are feasibility/replacement-capital comparisons, not start-to-end
playthroughs. Inputs start at zero except an explicitly costed minute of fuel.
"""
import sys,os,json,math,argparse
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
from functools import lru_cache
ROOT=Path.cwd();OUT=ROOT/'artifacts/phase7'
parser=argparse.ArgumentParser();parser.add_argument('--stage',default='before');parser.add_argument('--source',type=Path,default=ROOT);args=parser.parse_args()
os.environ.update(LOCALAPPDATA=str(OUT/args.stage/'appdata'),APPDATA=str(OUT/args.stage/'appdata'))
sys.path[:0]=[str(args.source.resolve()/'src'),str(OUT)]
from phase7_pricing_candidates import CURVES,BOARDS,START,production_layout,checks
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.storage_upgrades import global_storage_base_capacity,global_storage_capacity,inventory_storage_upgrade_cost
from production_zero.core.definitions import MachineDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState,FactoryHall,ProductionLine,MachineProductionState
from production_zero.core.freight import FreightFacility,FreightAssignment,freight_stats
from production_zero.core.simulation import SimulationEngine
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core import supply
D0=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json')
original_price=supply.common_card_price
producer={o.output_resource:(d,o) for d in D0.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
@lru_cache(None)
def depth(rid):return 0 if not producer[rid][1].input_resources else 1+max(depth(r) for r in producer[rid][1].input_resources)
ORDER=sorted(producer,key=depth,reverse=True)

def definitions(curve):
    d=dict(D0);d['freight.ship']=replace(d['freight.ship'],base_capacity=40000 if curve.name=='old' else 16000)
    def price(definition):
        if definition.definition_id=='freight.ship':return 48200 if curve.name=='old' else 14955
        return original_price(definition)
    supply.common_card_price=price
    return d

def card_cost(definition,mk):
    card=create_card_instance('capital-probe',definition.definition_id,definition.card_kind,Rarity.COMMON)
    total=supply.common_card_price(definition)
    for level in range(1,mk):total+=mk_upgrade_cost(replace(card,mk_level=level),definition)
    return total

def freight_cost(curve,kind,n):
    return sum(curve.freight_expansion(kind,index) for index in range(START[kind],max(START[kind],n)))

def fleet_options(curve,d,required):
    rows=[]
    for did in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
        definition=d[did];kind=definition.facility_id
        for mk in (1,2,10,50,99):
            factor=1+.25*(mk-1);rate=definition.base_capacity*factor/definition.base_transport_time_seconds*60
            n=max(1,math.ceil(required/rate-1e-10));price=card_cost(definition,mk)
            # Compare up to three facilities, with a bounded partition search.
            if n>192:continue
            best=None
            for facilities in range(1,min(3,n)+1):
                dp={0:(0,[])}
                for number in range(facilities):
                    fee=0 if kind=='garage_depot' and number==0 else curve.freight_facility(kind,number)
                    nd={}
                    for owned,(cost,parts) in dp.items():
                        for count in range(1,min(64,n-owned)+1):
                            candidate=(cost+fee+freight_cost(curve,kind,count)+count*price,parts+[count]);key=owned+count
                            if key not in nd or candidate[0]<nd[key][0]:nd[key]=candidate
                    dp=nd
                if n in dp and (best is None or dp[n][0]<best[0]):best=dp[n]
            if best:
                rows.append(dict(definition=did,mk=mk,vehicles=n,facilities=best[1],investment=best[0],nominal_units_min=n*rate))
    return sorted(rows,key=lambda r:r['investment'])

def plan(target,mk,energy,d):
    factor=1+.25*(mk-1);fuel_need=0.;previous=None
    for iteration in range(30):
        needs=dict(target)
        if energy.fuel_resource_id:needs[energy.fuel_resource_id]=needs.get(energy.fuel_resource_id,0)+fuel_need
        counts={};power=0.
        for rid in ORDER:
            required=needs.get(rid,0)
            if required<=0:continue
            definition,option=producer[rid];capacity=option.output_amount_for(definition)*60/option.cycle_seconds_for(definition)*factor
            number=math.ceil(required/capacity-1e-10);counts[rid]=number
            power+=number*option.power_draw_for(definition)*factor
            # Plan enough upstream goods for each installed producer at full output.
            cycles=number*60/option.cycle_seconds_for(definition)*factor
            for resource,amount in option.input_resources.items():needs[resource]=needs.get(resource,0)+amount*cycles
        generators=math.ceil(power/(energy.base_power_output*factor)-1e-10)
        key=(counts,generators)
        if key==previous:return counts,needs,power,generators,fuel_need
        previous=key;fuel_need=generators*energy.fuel_consumption_per_minute*factor
    raise ValueError('Energy/fuel fixed point did not converge')

def simulate(curve,name,target,mk=1,energy_id='energy.solar_array',duration=1800,forced_fleet=None):
    d=definitions(curve);energy=d[energy_id]
    counts,needs,power,generators,fuel_rate=plan(target,mk,energy,d)
    s=GameState(197);s.freight.facilities.clear();s.company.level=100;s.cash.amount=0
    s.production_progress.unlocked_production_ids.update(o.production_id for _,o in producer.values())
    for rid in needs:s.ensure_resource(rid)
    for rid in target:s.ensure_resource(rid)
    # Finite 10-minute goods buffer, plus the chosen transport's cycle buffer.
    resources=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
    base_storage=global_storage_base_capacity(resources)
    required_storage=max(base_storage,math.ceil(sum(needs.values())*10/5000)*5000)
    s.inventory_storage_level=max(0,math.ceil((required_storage/base_storage-1)/.25))
    s.warehouse_capacity=global_storage_capacity(resources,s.inventory_storage_level)
    storage_investment=sum(inventory_storage_upgrade_cost(level) for level in range(s.inventory_storage_level))
    if energy.fuel_resource_id:s.ensure_resource(energy.fuel_resource_id).amount=fuel_rate
    seed_value=fuel_rate*BASE_MARKET_PRICES.get(energy.fuel_resource_id,0)
    groups={}
    for rid,n in counts.items():
        definition,option=producer[rid];board='resources' if not option.input_resources else 'factory'
        group=definition.definition_id if board=='resources' else 'factory'
        groups.setdefault((board,group),[]).extend([(definition,option)]*n)
    groups['energy','energy']=[(energy,None)]*generators
    investment=seed_value+storage_investment;serial=0;units_bought={'factory':1,'energy':1};resource_seen={'machine.extractor':1,'machine.drilling':0,'machine.agriculture':0}
    unit_summary=[]
    for (board,group),machines in groups.items():
        maximum,per_line,start=BOARDS[board];cap=maximum*per_line
        if board=='factory' and len(machines)>500:raise ValueError('Scenario exceeds ten real Factory Halls')
        for part in range(0,len(machines),cap):
            batch=machines[part:part+cap];cost,layout=production_layout(curve,board,len(batch));investment+=cost
            if board=='resources':
                seen=resource_seen[group];fee=0 if group=='machine.extractor' and part==0 else curve.build(board,sum(resource_seen.values()) if curve.name=='old' else seen)
                resource_seen[group]+=0 if group=='machine.extractor' and part==0 else 1
            else:
                seen=units_bought[board];fee=0 if part==0 else curve.build(board,seen);units_bought[board]+=int(part>0)
            investment+=fee;uid=f'{board}-{group}-{part}';lines=[];position=0
            for line,n in enumerate(layout,1):
                lines.append(ProductionLine(f'{uid}.line-{line}',f'Line {line}',list(range(position,position+n)),unlocked=bool(n),unlock_cost=0 if n else curve.line(board,line)))
                position+=n
            unit=FactoryHall(uid,uid,position,board_kind=board,specialization=group if board=='resources' else None,max_lines=maximum,max_slots_per_line=per_line,production_lines=lines,start_unlocked_lines=2 if curve.name=='old' and board=='factory' else 1,start_slots_per_line=start)
            s.production_units(board)[uid]=unit
            for index,(definition,option) in zip(sorted(unit.unlocked_slot_indexes()),batch):
                serial+=1;cid=f'chain-{serial}';card=replace(create_card_instance(cid,definition.definition_id,definition.card_kind,Rarity.COMMON),mk_level=mk)
                s.cards[cid]=card;unit.slots[index].card_id=cid;investment+=card_cost(definition,mk)
                if option:s.machine_production[cid]=MachineProductionState(cid,option.output_resource,option.production_id)
            unit_summary.append(dict(board=board,type=group,machines=len(batch),owned_slots=position,layout=layout,infrastructure=cost+fee))
    alternatives=[];fleet=[]
    for rid,rate in target.items():
        options=fleet_options(curve,d,rate);alternatives.append(dict(resource=rid,options=options))
        selected=forced_fleet or [options[0]]
        for chosen in selected:
            definition=d[chosen['definition']];investment+=chosen['investment'];fleet.append(chosen)
            for facility_number,n in enumerate(chosen['facilities']):
                fid=f"freight-{rid}-{chosen['definition']}-{facility_number}";unit=FreightFacility(fid,fid,definition.facility_id,slot_count=max(START[definition.facility_id],n));s.freight.facilities[fid]=unit
                for i in range(n):
                    cid=f'{fid}-{i}';s.cards[cid]=replace(create_card_instance(cid,definition.definition_id,definition.card_kind,Rarity.COMMON),mk_level=chosen['mk'])
                    unit.slots[i].card_id=cid;s.freight.assignments[cid]=FreightAssignment(rid,'market')
    total_sold=0;units_at_warmup=0;last_delivery=-1
    engine=SimulationEngine(d,utc_now=lambda:datetime(2026,10,22,12,tzinfo=timezone.utc));peak=0;cash_at_warmup=0;gross_fuel=0;last_600_units=0
    for elapsed in range(6,duration+1,6):
        totals=engine.advance_time(s,6);peak=max(peak,s.used_storage)
        if energy.fuel_resource_id:gross_fuel+=totals.gross_power/(energy.base_power_output*(1+.25*(mk-1)))*energy.fuel_consumption_per_minute*(1+.25*(mk-1))*.1
        events=[e for e in s.freight.completed_market_deliveries if e.delivery_id>last_delivery]
        total_sold+=sum(e.market_amount for e in events)
        if events:last_delivery=events[-1].delivery_id
        if elapsed==600:cash_at_warmup=s.cash.amount;units_at_warmup=total_sold
    # Existing P6 ten-minute aggregates: actual economic completion quantities.
    delivered=sum(sum(amounts) for entries in s.freight.delivery_statistics.buckets.values() for amounts in entries.values())
    cash_min=(s.cash.amount-cash_at_warmup)/((duration-600)/60)
    return dict(curve=curve.name,scenario=name,mk=mk,energy=energy_id,target_units_min=target,machine_counts=counts,production_cards=sum(counts.values()),energy_cards=generators,
        units=unit_summary,investment=investment,nominal_power_demand_mw=power,nominal_power_supply_mw=generators*energy.base_power_output*(1+.25*(mk-1)),
        storage_investment=storage_investment,storage_level=s.inventory_storage_level,finite_storage_capacity=s.storage_capacity,peak_goods=peak,initial_fuel=fuel_rate,initial_fuel_value=seed_value,actual_fuel_consumed=gross_fuel,
        actual_units_min_after_warmup=(total_sold-units_at_warmup)/((duration-600)/60),actual_last_600_seconds_units=delivered,actual_units_min_last_600=delivered/10,actual_cash_min_after_warmup=cash_min,
        payback_minutes=investment/cash_min if cash_min>0 else None,minimum_stock=min(x.amount for x in s.resources.values()),fleet=fleet,fleet_alternatives=alternatives,
        assumptions='Mature company with full recipe access; Common cards at stated MK. All upstream goods start at zero; only a costed minute of initial fuel. No external replenishment. Six-second engine steps, 10-minute warm-up. Finite explicitly sized buffer. Capital quotes include all cards and MK cash at no random rarity gain; starting board buildings credited, no free card credit. Engine owns only the modeled slot layouts; extra empty unlocked slots are costed. This is a feasibility/capital comparison, not a progression playthrough.')

def frontier(curve,d):
    # Four-type combinations, up to 64 vehicles/type in at most 3 facilities.
    # Each type uses MK1; higher MK and mixed configurations are compared above.
    states=[(0.,0.,{})]
    for did in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
        definition=d[did];kind=definition.facility_id;options=[(0,0,0)]
        # Enumerate 1/2/3 similarly sized facilities, then Pareto prune totals.
        for n in range(1,65):
            best=None
            for facilities in range(1,min(3,n)+1):
                parts=[n//facilities+(i<n%facilities) for i in range(facilities)]
                cost=sum((0 if kind=='garage_depot' and i==0 else curve.freight_facility(kind,i))+freight_cost(curve,kind,count)+count*supply.common_card_price(definition) for i,count in enumerate(parts))
                if best is None or cost<best:best=cost
            options.append((best,n*definition.base_capacity/definition.base_transport_time_seconds*60,n))
        combined=sorted(((cost+extra,capacity+rate,{**mix,**({did:n} if n else {})}) for cost,capacity,mix in states for extra,rate,n in options),key=lambda r:(r[0],r[1]))
        states=[];best_rate=-1
        for cost,capacity,mix in combined:
            if capacity>best_rate+1e-8:states.append((cost,capacity,mix));best_rate=capacity
    return [dict(budget=budget,investment=chosen[0],capacity_units_min=chosen[1],vehicles=chosen[2]) for budget in (1000,5000,15000,50000,100000,250000,500000,1000000,2000000) for chosen in [max((r for r in states if r[0]<=budget),key=lambda r:r[1])]]

destination=OUT/args.stage;destination.mkdir(parents=True,exist_ok=True)
result=dict(checks={},scenarios=[],frontiers={},method='Counterfactual quote candidates are audit-only; actual material flow uses the existing SimulationEngine. No personal save. Runtime wall times are not performance measurements. Frontier is a bounded search, not a proof of global optimality for unlimited facilities, arbitrary MK or rarity.')
for curve in CURVES:
    result['checks'][curve.name]=checks(curve);d=definitions(curve)
    result['frontiers'][curve.name]=frontier(curve,d)
    for name,rid,base,mk,energy in [('early-chain','iron',120,1,'energy.solar_array'),('mid-chain','steel_components',60,10,'energy.solar_array'),
        ('late-mk10','industrial_equipment',10,10,'energy.solar_array'),('late-mk50','cargo_aircraft',1,50,'energy.solar_array'),('late-mk99','high_speed_network_system',1,99,'energy.solar_array')]:
        row=simulate(curve,name,{rid:base*(1+.25*(mk-1))},mk,energy);result['scenarios'].append(row)
        print(curve.name,name,round(row['investment'],2),round(row['actual_cash_min_after_warmup'],2),flush=True)
        (destination/'economy-simulation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    # Existing coal, gas and uranium fuel rules, with self-produced fuel chains.
    for energy_id in [key for key,d in D0.items() if getattr(d,'fuel_resource_id',None)]:
        row=simulate(curve,'fuel-'+energy_id,{'steel_components':60},1,energy_id);result['scenarios'].append(row)
        (destination/'economy-simulation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    for alt_mk in (1,10,50):
        try:
            row=simulate(curve,'late-same-output-mk'+str(alt_mk),{'high_speed_network_system':25.5},alt_mk)
            result['scenarios'].append(row)
        except ValueError as error:
            result.setdefault('infeasible_alternatives',[]).append(dict(curve=curve.name,mk=alt_mk,reason=str(error)))
    mixed=[]
    for did,n in [('freight.truck',5),('freight.train',2),('freight.aircraft',3),('freight.ship',2)]:
        definition=d[did];kind=definition.facility_id
        fee=0 if kind=='garage_depot' else curve.freight_facility(kind,0)
        mixed.append(dict(definition=did,mk=1,vehicles=n,facilities=[n],investment=fee+freight_cost(curve,kind,n)+n*card_cost(definition,1),nominal_units_min=n*definition.base_capacity/definition.base_transport_time_seconds*60))
    result['scenarios'].append(simulate(curve,'mixed-fleet-fed-chain',{'iron':12000},10,forced_fleet=mixed))
    result['scenarios'].append(simulate(curve,'mixed-fleet-fed-chain-mk1',{'iron':12000},1,forced_fleet=mixed))
    result['scenarios'].append(simulate(curve,'mid-same-output-mk1',{'steel_components':195},1))
result['selected']='A'
assert all(r['minimum_stock']>=0 and r['actual_cash_min_after_warmup']>0 for r in result['scenarios'])
assert all(all(row[key] for key in ('later_line_not_cheaper_per_start_slot','new_full_first_line_not_cheaper_than_last_line')) for board,row in result['checks']['A'].items() if board in BOARDS)
assert result['checks']['A']['garage']['prefer_second_fleet']
result['selection']='A is the lowest-priced complete candidate tested. All three production-board escape checks and second-Fleet comparison pass. Higher candidates add capital without improving material-flow feasibility. Early cash-access playthrough is a separate audit; late scenes do not establish an organic leveling trajectory.'
(destination/'economy-simulation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('selected A',flush=True)
