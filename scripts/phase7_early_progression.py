"""Finite-capital bootstrap respecting actual recipe unlocks; no recipe grants."""
import sys,os,json,argparse
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
ROOT=Path.cwd();OUT=ROOT/'artifacts/phase7'
p=argparse.ArgumentParser();p.add_argument('--stage',default='before');p.add_argument('--source',type=Path,default=ROOT);args=p.parse_args()
sys.path[:0]=[str(args.source.resolve()/'src'),str(OUT)]
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/args.stage/'early-appdata'),APPDATA=str(OUT/args.stage/'early-appdata'))
from phase7_pricing_candidates import CURVES
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.ui.main_window import _create_initial_state
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import FactoryHall,MachineProductionState
from production_zero.core.freight import FreightAssignment
from production_zero.core.simulation import SimulationEngine
from production_zero.core.supply import common_card_price
from production_zero.core.commands import SelectMachineProduction
from production_zero.core.progression import is_production_unlocked
D=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json');R=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
rows=[]
for curve in CURVES:
    s=_create_initial_state(R,D)
    # Counterfactual infrastructure purchases are explicitly quoted by curve;
    # assets, recipes, initial stock, fuel and every subsequent sale use the game.
    startup=curve.slot('resources',1,2)+curve.slot('resources',1,3)+curve.slot('energy',1,2)+common_card_price(D['energy.solar_array'])+common_card_price(D['freight.truck'])
    assert startup<=1250;s.cash.spend(startup);spent=startup
    factory=s.halls['hall-1']
    if curve.name=='old':
        factory=FactoryHall('hall-1','Hall 1',6,max_lines=5,start_unlocked_lines=2);s.halls['hall-1']=factory
    else:
        factory=FactoryHall('hall-1','Hall 1',3,max_lines=5,start_unlocked_lines=1);s.halls['hall-1']=factory
    resource=s.resource_sites['site-1'];resource.production_lines[0].slot_indexes=[0,1,2];resource.slot_count=3
    energy=s.energy_plants['plant-1'];energy.production_lines[0].slot_indexes=[0,1];energy.slot_count=2
    solar='early-solar';truck='early-truck'
    s.cards[solar]=create_card_instance(solar,'energy.solar_array',D['energy.solar_array'].card_kind,Rarity.COMMON)
    s.cards[truck]=create_card_instance(truck,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON)
    pending_recipes={};recipe_milestones=[]
    def configure(cid,unit,index,rid):
        unit.slots[index].card_id=cid;definition=D[s.cards[cid].definition_id]
        option=next(o for o in definition.available_production_options if o.output_resource==rid)
        if is_production_unlocked(s,option):
            SelectMachineProduction(cid,option.production_id,rid).apply(s)
        else:
            s.machine_production[cid]=MachineProductionState(cid,'',None)
            pending_recipes[cid]=(rid,option)
    for i,rid in enumerate(('iron_ore','coal','iron_ore')):configure(f'test-drill-common-00{i+1}',resource,i,rid)
    for i,cid in enumerate(('test-furnace-common-001','test-blast-furnace-common-001')):configure(cid,factory,i,'iron')
    energy.slots[0].card_id='test-solar-common-001';energy.slots[1].card_id=solar
    garage=s.freight.facilities['garage-1']
    for i,cid in enumerate(('starter-truck-common-001','starter-truck-common-002',truck)):
        garage.slots[i].card_id=cid;s.freight.assignments[cid]=FreightAssignment('iron','market')
    milestones=[];pending=['machine.agriculture','machine.drilling'];engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,22,12,tzinfo=timezone.utc))
    for elapsed in range(1,1801):
        engine.advance_time(s,1)
        for cid,(rid,recipe) in list(pending_recipes.items()):
            if is_production_unlocked(s,recipe):
                SelectMachineProduction(cid,recipe.production_id,rid).apply(s)
                recipe_milestones.append(dict(card=cid,recipe=recipe.production_id,seconds=elapsed));del pending_recipes[cid]
        if not pending:continue
        did=pending[0];facility_cost=curve.build('resources',len(s.resource_sites) if curve.name=='old' else sum(u.specialization==did for u in s.resource_sites.values()))
        # Buy the site, actual machine and sufficient solar/slots as one planned
        # affordable milestone; no unlimited grants or negative cash permitted.
        needs_solar=did=='machine.drilling'
        energy_cost=curve.slot('energy',1,3)+common_card_price(D['energy.solar_array']) if needs_solar else 0
        total=facility_cost+common_card_price(D[did])+energy_cost
        if s.cash.amount<total:continue
        s.cash.spend(total);spent+=total;uid='early-'+did
        unit=FactoryHall(uid,uid,1,board_kind='resources',specialization=did,max_lines=3,max_slots_per_line=10,start_unlocked_lines=1,start_slots_per_line=1);s.resource_sites[uid]=unit
        cid=uid+'-card';s.cards[cid]=create_card_instance(cid,did,D[did].card_kind,Rarity.COMMON)
        primary=next(o for o in D[did].available_production_options if not o.input_resources)
        configure(cid,unit,0,primary.output_resource)
        if needs_solar:
            cid='early-extra-solar';s.cards[cid]=create_card_instance(cid,'energy.solar_array',D['energy.solar_array'].card_kind,Rarity.COMMON)
            energy.production_lines[0].slot_indexes.append(2);energy.slot_count=3;energy.slots[2].card_id=cid
        milestones.append(dict(type=did,seconds=elapsed,cash=s.cash.amount,cost=total,building_cost=facility_cost));pending.pop(0)
    assert len(milestones)==2 and s.cash.amount>=0
    rows.append(dict(curve=curve.name,initial_cash=1250,startup_purchases=startup,recipe_unlocks=recipe_milestones,milestones=milestones,final_cash=s.cash.amount,total_spent=spent,
        actual_sales=s.statistics.total_earnings,actual_sales_per_min=s.statistics.total_earnings/30,actual_last_minute_units=s.freight.delivery_statistics.rate(facility_id='garage-1').total,
        finite_storage_capacity=s.storage_capacity,ending_goods=s.used_storage,minimum_stock=min(x.amount for x in s.resources.values()),
        assumptions='Existing starter cards and exact initial resources, upfront affordable first-chain expansion, then 1-second real Engine steps. Recipe choices go through SelectMachineProduction only after existing lifetime-output unlocks; no recipe grant or preconfigured locked Iron. No grants after start. Candidate site/slot purchases modeled and debited at quoted costs; branch machines and extra solar also paid. Branch goods are retained, main Iron chain earns actual sales. Initial cards free as in game. No level/Contract reward changes.'))
    print(curve.name,[(r['type'],r['seconds'],r['cost']) for r in milestones],flush=True)
(OUT/args.stage/'early-progression.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
