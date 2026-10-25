"""Finite, deterministic P8 engine scenarios. Never reads a personal save."""
import argparse, json, os, sys, math
from pathlib import Path
from dataclasses import replace, asdict
from datetime import datetime,timezone

ROOT = Path.cwd()
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=ROOT)
parser.add_argument('--stage', default='after')
parser.add_argument('--quick', action='store_true')
parser.add_argument('--candidate', action='store_true')
args = parser.parse_args()
OUT = ROOT / 'artifacts/phase8' / args.stage
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(LOCALAPPDATA=str(OUT/'appdata'), APPDATA=str(OUT/'appdata'))
sys.path.insert(0, str(args.source.resolve()/'src'))
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.definitions import MachineDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState, FactoryHall, ProductionLine, MachineProductionState
from production_zero.core.freight import FreightFacility, FreightAssignment, freight_stats
from production_zero.core.contracts import generate_contract_offers, accept_contract, initialize_contracts
from production_zero.core.company import xp_required_for_next_level
from production_zero.core.production_values import ProductionValueCalculator
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.core.simulation import SimulationEngine
from production_zero.core.company_xp import utc_timestamp
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state

D = load_card_definitions(args.source/'src/production_zero/data/game_definitions.json')
PRODUCERS = {o.output_resource: (d,o) for d in D.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
NOW = float(os.environ.get("PHASE8_NOW",datetime(2026,10,22,14,14,20,tzinfo=timezone.utc).timestamp()))
SIM_CLOCK=[NOW]
if __name__=="__main__" or os.environ.get("PHASE8_FORCE_CLOCK")=="1":
    import production_zero.core.contracts as contract_module
    original_sync=contract_module.sync_company_xp_periods
    original_timestamp=contract_module.utc_timestamp
    contract_module.sync_company_xp_periods=lambda state,now_utc=None:original_sync(state,SIM_CLOCK[0] if now_utc is None else now_utc)
    contract_module.utc_timestamp=lambda now_utc=None:original_timestamp(SIM_CLOCK[0] if now_utc is None else now_utc)
PRODUCTS = {
    'early': ('iron_ore','coal','copper_ore','bauxite'),
    'mid': ('iron','copper','steel','steel_components'),
    'late': ('industrial_equipment','cargo_aircraft','high_speed_network_system','steel_components'),
}

def company(stage, mk=1, no_freight=False, power_factor=1.):
    selected = PRODUCTS[stage]
    needs = {}
    def need(rid, amount):
        needs[rid] = needs.get(rid,0) + amount
        d,o = PRODUCERS[rid]
        for inp, qty in o.input_resources.items():
            need(inp, amount*qty/o.output_amount_for(d))
    for rid in selected:
        need(rid, {'early':60.,'mid':60.,'late':4.}[stage])
    counts = {rid:max(1, math.ceil(rate/(PRODUCERS[rid][1].output_amount_for(PRODUCERS[rid][0])*60/PRODUCERS[rid][1].cycle_seconds_for(PRODUCERS[rid][0])))) for rid,rate in needs.items()}
    from production_zero.core.storage_upgrades import global_storage_base_capacity,global_storage_capacity,inventory_storage_upgrade_cost
    resources_catalog=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
    base=global_storage_base_capacity(resources_catalog)
    required=max(base,sum(needs.values())*10*(1+.25*(mk-1)))
    storage_level=max(0,math.ceil((required/base-1)/.25))
    warehouse=global_storage_capacity(resources_catalog,storage_level)
    storage_cost=sum(inventory_storage_upgrade_cost(level) for level in range(storage_level))
    s = GameState(8801, warehouse_capacity=warehouse)
    s.inventory_storage_level=storage_level
    s.freight.facilities.clear()
    s.company.level = {'early':1,'mid':25,'late':100}[stage]
    from production_zero.core.progression import initialize_production_progress
    initialize_production_progress(s,D)
    if stage!='early':s.production_progress.unlocked_production_ids.update(PRODUCERS[rid][1].production_id for rid in needs)
    groups = {}
    power = 0
    for rid,n in counts.items():
        d,o = PRODUCERS[rid]
        power += n*o.power_draw_for(d)*(1+.25*(mk-1))
        groups.setdefault(('resources' if not o.input_resources else 'factory',d.definition_id),[]).extend([(d,o)]*n)
    energy = D['energy.solar_array']
    generators = max(1,math.ceil(power/(energy.base_power_output*(1+.25*(mk-1)))*power_factor))
    groups['energy','energy'] = [(energy,None)]*generators
    serial = 0
    for (board,kind), machines in groups.items():
        for offset in range(0,len(machines),50 if board=='factory' else 15):
            batch = machines[offset:offset+(50 if board=='factory' else 15)]
            uid = f'{board}-{kind}-{offset}'
            per_line={'factory':10,'resources':10,'energy':5}[board]
            maximum={'factory':5,'resources':3,'energy':3}[board]
            lines=[ProductionLine(uid+f'.line-{line+1}',f'Line {line+1}',list(range(line*per_line,min(len(batch),(line+1)*per_line)))) for line in range(math.ceil(len(batch)/per_line))]
            hall = FactoryHall(uid,uid,len(batch),specialization=kind if board=='resources' else None,board_kind=board,max_lines=maximum,max_slots_per_line=per_line,production_lines=lines,start_unlocked_lines=1,start_slots_per_line=3 if board=='factory' else 1)
            s.production_units(board)[uid] = hall
            for i,(d,o) in enumerate(batch):
                serial += 1
                cid = f'card-{serial}'
                s.cards[cid] = replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),mk_level=mk)
                hall.slots[i].card_id = cid
                if o:s.machine_production[cid] = MachineProductionState(cid,o.output_resource,o.production_id)
    fleet = {'early': [('freight.truck',3)], 'mid':[('freight.truck',4),('freight.train',2)], 'late':[('freight.aircraft',4),('freight.ship',2)]}[stage]
    if not no_freight:
        for did,n in fleet:
            d = D[did]
            fid = f'{did}.facility'
            f = FreightFacility(fid,fid,d.facility_id,slot_count=n)
            s.freight.facilities[fid] = f
            for i in range(n):
                cid = f'{did}-{i}'
                s.cards[cid] = replace(create_card_instance(cid,did,d.card_kind,Rarity.COMMON),mk_level=mk)
                f.slots[i].card_id = cid
                s.freight.assignments[cid] = FreightAssignment(selected[0],'contract')
    # Start with EMPTY finite physical stock. Recipe availability is an explicit
    # mature-fixture assumption, not a claim of organic early progression.
    for rid in needs:s.ensure_resource(rid).amount = 0
    for rid in selected:s.ensure_resource(rid).amount = .001  # eligibility only, reported
    return s, dict(counts=counts, power_demand=power, solar=generators, storage=s.storage_capacity, warehouse_level=storage_level,warehouse_investment=storage_cost,fleet=fleet, initial_eligibility_stock=.001*len(selected))

from functools import lru_cache
@lru_cache(None)
def ancestors(rid):
    result=set()
    for inp in PRODUCERS[rid][1].input_resources:
        result.add(inp);result.update(ancestors(inp))
    return frozenset(result)

def route(s, contract, destination='contract'):
    pending = {}
    for shipment in s.freight.outbound_shipments.values():
        if shipment.active:pending[shipment.resource_id] = pending.get(shipment.resource_id,0)+shipment.quantity
    # Choose the fullest currently available useful load; keep final-product
    # reservations separate from production inputs and other goods.
    busy = {ship.freight_card_id for ship in s.freight.outbound_shipments.values() if ship.active}
    requirements = contract.offer.requirements if hasattr(contract,'offer') else contract.requirements
    ongoing = {rid for rid,qty in requirements.items() if qty-contract.delivered.get(rid,0)-pending.get(rid,0)>1e-9}
    eligible = {rid for rid in requirements if not any(rid in ancestors(other) for other in ongoing if other!=rid)}
    planned_stock={rid:s.ensure_resource(rid).amount for rid in requirements}
    for cid in sorted(s.installed_freight_card_ids()-busy):
        options = [(min(planned_stock[rid],max(0,required-contract.delivered.get(rid,0)-pending.get(rid,0))) if rid in eligible else 0.,rid) for rid,required in (contract.offer.requirements if hasattr(contract,'offer') else contract.requirements).items()]
        qty,rid = max(options)
        s.freight.assignments[cid] = FreightAssignment(rid,destination)
        stats = freight_stats(s.cards[cid],D[s.cards[cid].definition_id],s.research)
        reserved=min(qty,stats.capacity)
        pending[rid] = pending.get(rid,0)+reserved
        planned_stock[rid] -= reserved

def single(stage, kind, mk):
    from phase8_offline_work_cache import install
    install(D)
    SIM_CLOCK[0]=NOW
    s, info = company(stage,mk)
    initialize_contracts(s,D,now_utc=NOW)
    offer = s.contracts.offers[kind][0]
    selected = PRODUCTS[stage][:{'regular':2,'daily':3,'weekly':4}[kind]]
    candidate_snapshot = None
    if args.candidate:
        sys.path.insert(0,str(ROOT/'artifacts/phase8'))
        from contract_capacity import reachable_capacity, requirements_for_rates, TARGET_MINUTES, CASH_BONUS
        plan = reachable_capacity(s,D)
        requirements = requirements_for_rates(plan.rates,BASE_MARKET_PRICES,selected,TARGET_MINUTES[kind])
        offer = replace(offer,requirements=requirements)
        s.contracts.offers[kind] = [offer]
        candidate_snapshot = requirements
    try:
        accept_contract(s,kind,offer.contract_id,D,selected_resource_ids=selected)
    except ValueError as exc:
        return dict(stage=stage,kind=kind,mk=mk,feasible=False,error=str(exc),**info)
    active = s.contracts.active[kind]
    if candidate_snapshot:
        from production_zero.core.contracts import contract_work_xp_quote
        active.offer=replace(active.offer,reward_cash=round(sum(BASE_MARKET_PRICES[r]*q for r,q in candidate_snapshot.items())*(1+CASH_BONUS[kind]),2),reward_xp=contract_work_xp_quote(s,D,kind,candidate_snapshot))
    snapshot = active.offer
    needed_products = set()
    def include(rid):
        if rid in needed_products:return
        needed_products.add(rid)
        for upstream in PRODUCERS[rid][1].input_resources:include(upstream)
    for rid in selected:include(rid)
    clock=[NOW]
    engine = SimulationEngine(D,utc_now=lambda:clock[0])
    end = 24*3600
    peak = 0
    for elapsed in range(6,end+1,6):
        clock[0]=SIM_CLOCK[0]=NOW+elapsed
        # Keep finite working buffers; pause excess upstream output, no gifts.
        # This is a deterministic manual-equivalent scheduling policy.
        for cid,production in s.machine_production.items():
            d = D[s.cards[cid].definition_id]
            o = d.production_option(production.selected_production_id)
            buffer = max(o.output_amount_for(d)*s.cards[cid].output_multiplier*4, info['counts'].get(o.output_resource,1)*o.output_amount_for(d)*s.cards[cid].output_multiplier*4)
            s.cards[cid] = replace(s.cards[cid], paused=o.output_resource not in needed_products or s.ensure_resource(o.output_resource).amount>=buffer)
        route(s,active)
        engine.advance_time(s,6)
        peak = max(peak,s.used_storage)
        if active.status!='active':break
    value = sum(BASE_MARKET_PRICES[rid]*qty for rid,qty in snapshot.requirements.items())
    pv = ProductionValueCalculator(D)
    work = sum(qty*pv.value_for_resource(rid).value_per_unit for rid,qty in snapshot.requirements.items())
    freight_rate = sum(freight_stats(s.cards[cid],D[s.cards[cid].definition_id]).capacity*60/freight_stats(s.cards[cid],D[s.cards[cid].definition_id]).transport_time_seconds for cid in s.installed_freight_card_ids())
    nominal={rid:0. for rid in snapshot.requirements}
    for cid,production in s.machine_production.items():
        if production.target_resource_id not in nominal:continue
        d=D[s.cards[cid].definition_id];o=d.production_option(production.selected_production_id)
        nominal[o.output_resource]+=o.output_amount_for(d)*s.cards[cid].output_multiplier*60/o.cycle_seconds_for(d)
    import importlib.util
    module_spec=importlib.util.spec_from_file_location('phase8_capacity_reference',ROOT/'src/production_zero/core/contract_capacity.py')
    module=importlib.util.module_from_spec(module_spec);sys.modules[module_spec.name]=module;module_spec.loader.exec_module(module)
    planning=module.reachable_capacity(s,D)
    reachable_production_minutes=sum(qty/planning.production_rates[rid] for rid,qty in snapshot.requirements.items()) if all(planning.production_rates.get(rid,0)>0 for rid in snapshot.requirements) else None
    row = dict(stage=stage,kind=kind,mk=mk,requirements=snapshot.requirements,goods_value=value,cash=snapshot.reward_cash,bonus=snapshot.reward_cash/value-1,xp=snapshot.reward_xp,rp={'regular':0,'daily':1,'weekly':3}[kind],work_pv=work,elapsed_minutes=elapsed/60,completed=active.status=='completed',paid_contract_cash=snapshot.reward_cash if active.status=='completed' else 0.,actual_wallet_cash=s.cash.amount,status=active.status,nominal_production_minutes=max(qty/nominal[rid] for rid,qty in snapshot.requirements.items()),reachable_production_plan_minutes=reachable_production_minutes,production_rates=planning.production_rates,company_level_after=s.company.level,total_rp_after=s.research.total_earned,levelup_rp=s.company.level-{'early':1,'mid':25,'late':100}[stage],freight_minimum_minutes=sum(snapshot.requirements.values())/freight_rate,freight_per_minute=freight_rate,peak_goods=peak,xp_share_next_level=snapshot.reward_xp/xp_required_for_next_level({'early':1,'mid':25,'late':100}[stage]),minimum_stock=min(stock.amount for stock in s.resources.values()),delivered=active.delivered,**info)
    row.update(cash_per_minute=snapshot.reward_cash/(elapsed/60) if row['completed'] else None,xp_per_minute=snapshot.reward_xp/(elapsed/60) if row['completed'] else None)
    print(json.dumps({k:row[k] for k in ('stage','kind','mk','elapsed_minutes','completed','cash','xp')}),flush=True)
    return row

def main():
    import multiprocessing
    from phase8_simulation_checkpoint import begin,finish
    fingerprint=begin(OUT,'contract-balance-simulation.json',args.source)
    if fingerprint is None:return
    os.environ['PHASE8_FORCE_CLOCK']='1'
    cases=[(stage,kind,mk) for stage in ('early','mid','late') for mk in ((1,) if args.quick else (1,2,10,50,99)) for kind in ('regular','daily','weekly')]
    # Independent company worlds; results retain case order, not finish order.
    with multiprocessing.get_context('spawn').Pool(4) as pool:
        rows=pool.starmap(single,cases,chunksize=1)
    result = dict(source=str(args.source.resolve()),stage=args.stage,fixed_utc_start=NOW,routing_policy="Sorted card IDs; each proposed load reserves available stock before assigning the next card; upstream export waits for dependent requested products.",scenarios=rows,assumptions='Explicit recipe-access fixtures; all upstream inputs produced by real engine, finite paid storage sized from a ten-minute upstream buffer, no replenishment, 0.001 initial stock per selectable product only for existing eligibility; UTC advances with engine time, six-second ticks, 24-hour right censoring or actual expiry. Configured complete multi-product chains and whole solar/freight. Not an organically played progression or capital optimization.')
    from phase8_offline_work_cache import install
    result['offline_work_cache_proof']=install(D)
    finish(OUT,'contract-balance-simulation.json',result,fingerprint)

if __name__=='__main__':main()
