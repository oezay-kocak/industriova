"""Shared-network, finite-stock multi-company freight engine scenarios."""
import sys, argparse, json, runpy
from pathlib import Path
from dataclasses import replace, asdict

root=Path.cwd()
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=root);parser.add_argument('--stage',default='after')
args=parser.parse_args()
sys.argv=[str(root/'scripts/phase8_contract_simulation.py'),'--source',str(args.source),'--stage',args.stage]
fixture=runpy.run_path(str(root/'scripts/phase8_contract_simulation.py'),run_name='fixture')
company=fixture['company'];D=fixture['D'];route=fixture['route'];NOW=fixture['NOW'];PRODUCERS=fixture['PRODUCERS']
from production_zero.core.consortium import ConsortiumService,ConsortiumMember
from production_zero.core.simulation import SimulationEngine
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
import importlib.util
reference_spec=importlib.util.spec_from_file_location('phase8_group_capacity_reference',root/'src/production_zero/core/contract_capacity.py')
reference=importlib.util.module_from_spec(reference_spec);sys.modules[reference_spec.name]=reference;reference_spec.loader.exec_module(reference)


def scenario(name,shapes,kind='daily',specialized=False,leave=False,direct=False,products_override=None):
    from phase8_offline_work_cache import install
    install(D)
    states=[];metadata=[]
    products=(products_override or fixture['PRODUCTS']['early'])[:3 if kind=='daily' else 4]
    for i,shape in enumerate(shapes):
        stage,mk,no_freight=shape[:3]
        s,info=company(stage,mk,no_freight=no_freight)
        if len(shape)>3 and shape[3]=='no-power':
            removed={slot.card_id for unit in s.energy_plants.values() for slot in unit.slots if slot.card_id}
            s.energy_plants.clear()
            for cid in removed:s.cards.pop(cid,None)
        if len(shape)>3 and shape[3]=='poor-freight':
            from production_zero.core.freight import FreightFacility,FreightAssignment
            from production_zero.core.cards import create_card_instance
            from production_zero.core.enums import Rarity
            facility=FreightFacility('poor-garage','Starter Garage')
            s.freight.facilities[facility.facility_id]=facility
            for j in range(2):
                cid=f'poor-truck-{j}';s.cards[cid]=create_card_instance(cid,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON)
                facility.slots[j].card_id=cid;s.freight.assignments[cid]=FreightAssignment('iron_ore','consortium')
        if specialized:
            wanted=fixture['PRODUCTS']['early'][i*2:i*2+2]
            s.production_progress.unlocked_production_ids={PRODUCERS[rid][1].production_id for rid in wanted}
            for rid in fixture['PRODUCTS']['early']:s.ensure_resource(rid).amount=.001 if rid in wanted else 0
            for unit in s.all_production_units():
                for slot in unit.slots:
                    production=s.machine_production.get(slot.card_id)
                    if production and production.target_resource_id not in wanted:
                        s.cards.pop(slot.card_id);s.machine_production.pop(slot.card_id);slot.card_id=None
        # Explicit manual setup, before the quote: the mid fixture owns spare
        # ore extractors, but no configured Bauxite producer. Reconfigure one
        # real duplicate rather than pretending its potential produces goods.
        from collections import Counter
        from production_zero.core.progression import is_production_unlocked
        changes=[]
        configured=Counter(p.target_resource_id for p in s.machine_production.values())
        for rid in products:
            if rid not in fixture['PRODUCTS']['early'] or configured[rid] or not is_production_unlocked(s,PRODUCERS[rid][1]):continue
            candidates=[cid for cid,p in s.machine_production.items() if s.cards[cid].definition_id==PRODUCERS[rid][0].definition_id and configured[p.target_resource_id]>1]
            if not candidates:continue
            cid=sorted(candidates)[-1];old=s.machine_production[cid]
            configured[old.target_resource_id]-=1;configured[rid]+=1
            s.machine_production[cid]=replace(old,target_resource_id=rid,selected_production_id=PRODUCERS[rid][1].production_id)
            changes.append(dict(card=cid,previous=old.target_resource_id,selected=rid))
        info['counts']=dict(configured);info['manual_configuration_before_quote']=changes
        info['power_demand']=sum(D[s.cards[cid].definition_id].production_option(p.selected_production_id).power_draw_for(D[s.cards[cid].definition_id])*s.cards[cid].power_multiplier for cid,p in s.machine_production.items())
        states.append(s);metadata.append(info)
    current_time=[NOW]
    local=states[0]
    api=ConsortiumService(local,D,clock=lambda:current_time[0])
    guild=api.create('Finite Freight Cooperative')
    network=local.consortium
    ids=[network.current_company_id]+[f'member-{i}' for i in range(1,len(states))]
    for cid,s in zip(ids[1:],states[1:]):
        guild.members[cid]=ConsortiumMember(cid,cid,s.company.level)
        s.consortium.current_company_id=cid
        if hasattr(api,'update_capacity_snapshot'):api.update_capacity_snapshot(cid,s)
        else:guild.members[cid].capable_resource_ids=tuple(r for r in s.resources if s.resources[r].amount>0)
        s.consortium=network
    try:contract=api.start_contract(guild.consortium_id,ids[0],kind,products)
    except ValueError as exc:
        return dict(scenario=name,kind=kind,members=len(states),feasible=False,error=str(exc))
    snapshot=dict(requirements=dict(contract.requirements),reward=asdict(contract.personal_reward),consortium_xp=contract.consortium_xp_reward)
    member_rates={cid:dict(getattr(member,'capacity_rates',{})) for cid,member in guild.members.items()}
    reference_rates={cid:reference.reachable_capacity(s,D).production_rates for cid,s in zip(ids,states)}
    freight_rates=[sum(fixture['freight_stats'](s.cards[cid],D[s.cards[cid].definition_id],s.research).capacity*60/fixture['freight_stats'](s.cards[cid],D[s.cards[cid].definition_id],s.research).transport_time_seconds for cid in s.installed_freight_card_ids()) for s in states]
    powers=[sum(D[s.cards[slot.card_id].definition_id].base_power_output*s.cards[slot.card_id].output_multiplier for unit in s.energy_plants.values() for slot in unit.slots if slot.card_id) for s in states]
    engines=[SimulationEngine(D,utc_now=lambda:current_time[0]) for s in states]
    peaks=[0.]*len(states);min_stocks=[0.]*len(states)
    target_products=set(products)
    for rid in products:target_products.update(fixture["ancestors"](rid))
    target=f'{guild.consortium_id}|{kind}|{contract.contract_id}'
    completion_company_id=None
    step=30
    for elapsed in range(step,24*3600+1,step):
        current_time[0]=NOW+elapsed
        api.expire_contracts(guild.consortium_id)
        for index,(cid,s,engine) in enumerate(zip(ids,states,engines)):
            departed=leave and cid==ids[-1] and elapsed>=600
            if departed and cid in guild.members:api.leave(guild.consortium_id,cid)
            network.current_company_id=cid
            for card_id,prod in s.machine_production.items():
                d=D[s.cards[card_id].definition_id];o=d.production_option(prod.selected_production_id)
                buffer=o.output_amount_for(d)*s.cards[card_id].output_multiplier*max(4,metadata[index]['counts'].get(o.output_resource,1)*4)
                s.cards[card_id]=replace(s.cards[card_id],paused=o.output_resource not in target_products or s.ensure_resource(o.output_resource).amount>=buffer)
            if not departed and not direct:route(s,contract,'consortium')
            previous_status=contract.status
            engine.advance_time(s,step)
            if direct and not departed and contract.status=='active':
                member_service=ConsortiumService(s,D,clock=lambda:current_time[0])
                for rid,required in contract.requirements.items():
                    quantity=min(s.ensure_resource(rid).amount,contract.remaining(rid))
                    if quantity>0:member_service.contribute(guild.consortium_id,cid,kind,rid,quantity,request_id=f'direct:{cid}:{elapsed}:{rid}')
            if previous_status!='completed' and contract.status=='completed':completion_company_id=cid
            peaks[index]=max(peaks[index],s.used_storage)
        if contract.status in ('completed','expired'):break
    completion_elapsed=elapsed
    if contract.status in ('completed','expired'):
        for tail in range(step,600+step,step):
            if not any(s.freight.outbound_shipments for s in states):break
            current_time[0]=NOW+completion_elapsed+tail
            for cid,s,engine in zip(ids,states,engines):
                network.current_company_id=cid;engine.advance_time(s,step)
    network.current_company_id=ids[0]
    value=sum(BASE_MARKET_PRICES[r]*q for r,q in snapshot['requirements'].items())
    receipts={cid:asdict(reward) for cid,reward in network.reward_receipts.get(contract.contract_id,{}).items()}
    total_cash=sum(reward['cash'] for reward in receipts.values())
    row=dict(scenario=name,kind=kind,members=len(states),company_shapes=shapes,delivery_mode='direct existing storage contribution' if direct else 'freight',engine_step_seconds=step,completion_company_id=completion_company_id,requirements=snapshot['requirements'],goods_value=value,pool_snapshot=snapshot['reward'],reward_receipts=receipts,total_receipt_cash=total_cash,bonus_all_receipts=total_cash/value-1 if contract.status=='completed' else None,consortium_xp=snapshot['consortium_xp'],elapsed_minutes=completion_elapsed/60,completed=contract.status=='completed',status=contract.status,contributions=contract.contributions,delivered=contract.delivered,member_peak_goods=peaks,company_metadata=metadata,member_proven_rates=member_rates,member_freight_per_minute=freight_rates,member_power=powers,minimum_stock=min(stock.amount for s in states for stock in s.resources.values()),cash_per_minute=total_cash/(elapsed/60) if contract.status=='completed' else None,forfeited=sorted(contract.forfeited_member_ids),outbound_after_drain=sum(len(s.freight.outbound_shipments) for s in states),member_wallet_cash=[s.cash.amount for s in states],member_level_after=[s.company.level for s in states],member_research_points_after=[s.research.total_earned for s in states])
    # No live-state fields are requoted by persistence; inspect receipts too.
    loaded=deserialize_game_state(serialize_game_state(local))
    restored=loaded.consortium.consortiums[guild.consortium_id].contracts[kind]
    row['roundtrip_terms_and_contributions']=asdict(restored)==asdict(contract)
    row['reference_member_production_rates']=reference_rates
    print(json.dumps({k:row[k] for k in ('scenario','kind','members','elapsed_minutes','completed','total_receipt_cash')}),flush=True)
    return row


def run_case(task):
    positional,keywords=task
    return scenario(*positional,**keywords)

def main():
    from phase8_simulation_checkpoint import begin,finish
    out=root/'artifacts/phase8'/args.stage
    fingerprint=begin(out,'consortium-balance-simulation.json',args.source)
    if fingerprint is None:return
    jobs=[]
    cases=[
        ('one-small',[('early',1,False)]),
        ('two-small',[('early',1,False)]*2),
        ('five-mid',[('mid',2,False)]*5),
        ('ten-advanced',[('late',10,False)]*10),
        ('mixed',[('early',1,False),('late',10,False)]+[('early',1,True)]*8),
        ('no-freight',[('early',1,True)]*2),
        ('some-no-freight',[('early',1,False),('early',1,True)]),
        ('one-no-power',[('early',1,False),('early',1,False,'no-power')]),
        ('strong-poor-freight',[('late',99,True,'poor-freight')]),
    ]
    for kind in ('daily','weekly'):
        for name,shapes in cases:jobs.append(((name,shapes,kind),{}))
        jobs.append((('specialized',[('early',1,False)]*2,kind),dict(specialized=True)))
        jobs.append((('member-leaves',[('early',1,False)]*2,kind),dict(leave=True)))
        jobs.append((('one-small-direct',[('early',1,False)],kind),dict(direct=True)))
        jobs.append((('ten-advanced-direct',[('late',10,False)]*10,kind),dict(direct=True)))
        jobs.append((('no-freight-direct',[('early',1,True)]*2,kind),dict(direct=True)))
        jobs.append((('strong-poor-freight-direct',[('late',99,True,'poor-freight')],kind),dict(direct=True)))
        jobs.append((('advanced-products',[('late',10,False)]*5,kind),dict(products_override=fixture['PRODUCTS']['late'])))
        jobs.append((('mixed-products',[('late',10,False),('early',1,False)],kind),dict(products_override=('iron_ore','cargo_aircraft','high_speed_network_system','steel_components'))))
    import multiprocessing
    with multiprocessing.get_context("spawn").Pool(4) as pool:
        rows=pool.map(run_case,jobs,chunksize=1)
    out=root/'artifacts/phase8'/args.stage
    finish(out,'consortium-balance-simulation.json',dict(scenarios=rows,source=str(args.source.resolve()),fixed_utc_start=NOW,assumptions='Real engine for each isolated company, shared local network; 30-second round-robin steps, finite paid storage from each recorded company fixture, no goods replenishment. Whole powered equipment as declared by the single-company fixture. Remote economic entitlements are reported as the existing network receipts: no new online wallet/claim system is simulated. 24-hour right censoring or actual expiry. Existing direct-storage contributions are separately labeled, with real produced stock; no human delay. Remaining flights are drained after completion; a departed company keeps running so its reserved cargo reaches Sell fallback. Member capability derives from actual states; old version receives only its existing declared capability list. Routing reserves actual stock per proposed load in sorted card order; specialized firms physically lack the other production machines.'),fingerprint)

if __name__=="__main__":main()
