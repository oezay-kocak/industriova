"""Actual incremental Iron chains: final slot, second line or second Factory."""
import sys,os,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7'
sys.path.insert(0,str(ROOT/'src'));os.environ.update(LOCALAPPDATA=str(OUT/'marginal-appdata'),APPDATA=str(OUT/'marginal-appdata'))
from production_zero.core.state import GameState,FactoryHall,ProductionLine,MachineProductionState
from production_zero.core.commands import PurchaseHall,UnlockProductionSlot,UnlockProductionLine,BuyCommonSupplyCard,InstallCardInHall,InstallFreightCard,ExpandFreightFacility
from production_zero.core.infrastructure_prices import unit_slot_price,unit_line_price,production_facility_price
from production_zero.core.freight import FreightAssignment
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.storage_upgrades import global_storage_base_capacity
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json');R=load_resource_definitions(ROOT/'src/production_zero/data/resource_definitions.json')
producer={o.output_resource:(d,o) for d in D.values() if hasattr(d,'available_production_options') for o in d.available_production_options}
rows=[]
for option in ('last-slot','second-line','second-factory'):
    count=1 if option=='last-slot' else 3
    s=GameState(197);s.cash.amount=1e12;s.company.level=100;s.warehouse_capacity=global_storage_base_capacity(R)
    for rid in R:s.ensure_resource(rid)
    lines=[ProductionLine('h.line-'+str(i),'Line '+str(i),list(range(9)) if i==1 else [],unlocked=i==1) for i in range(1,6)]
    hall=FactoryHall('h','Existing Factory',9,max_lines=5,start_unlocked_lines=1,production_lines=lines);s.halls['h']=hall
    # Nine paid, paused machines retain the existing slots; they supply no goods.
    for i in range(9):
        card=create_card_instance('baseline-'+str(i),'machine.processor',D['machine.processor'].card_kind,Rarity.COMMON)
        from dataclasses import replace
        s.cards[card.card_id]=replace(card,paused=True,acquisition_cost=275);hall.slots[i].card_id=card.card_id
    for board,uid,cap in [('resources','r',10),('energy','e',5)]:
        s.production_units(board)[uid]=FactoryHall(uid,uid,1,board_kind=board,max_lines=3,max_slots_per_line=cap,start_unlocked_lines=1,start_slots_per_line=1,specialization='machine.extractor' if board=='resources' else None)
    if option=='last-slot':
        infrastructure=unit_slot_price(hall,1,10);UnlockProductionSlot('h','h.line-1','factory',infrastructure).apply(s);targets=[9];target=hall
    elif option=='second-line':
        infrastructure=unit_line_price(hall,2);UnlockProductionLine('h','h.line-2','factory',infrastructure).apply(s);targets=hall.production_lines[1].slot_indexes;target=hall
    else:
        infrastructure=production_facility_price(s,'factory');PurchaseHall(expected_cost=infrastructure).apply(s);target=next(reversed(s.halls.values()));targets=target.production_lines[0].slot_indexes
    def buy(did):
        previous=set(s.cards);BuyCommonSupplyCard(did,D).apply(s);return next(iter(set(s.cards)-previous))
    def install(cid,unit,index,board,rid=None):
        InstallCardInHall(unit.hall_id,index,cid,board).apply(s)
        if rid:
            recipe=next(o for o in D[s.cards[cid].definition_id].available_production_options if o.output_resource==rid)
            s.production_progress.unlocked_production_ids.add(recipe.production_id);s.machine_production[cid]=MachineProductionState(cid,rid,recipe.production_id)
    definition,recipe=producer['iron'];requirements={rid:amount*60/recipe.cycle_seconds_for(definition)*count for rid,amount in recipe.input_resources.items()}
    power=recipe.power_draw_for(definition)*count;raw_count=0;resource=s.resource_sites['r'];energy=s.energy_plants['e']
    for rid,rate in requirements.items():
        upstream,raw_recipe=producer[rid];number=math.ceil(rate/(raw_recipe.output_amount_for(upstream)*60/raw_recipe.cycle_seconds_for(upstream)))
        for _ in range(number):
            if raw_count:UnlockProductionSlot('r','r.line-1','resources').apply(s)
            install(buy(upstream.definition_id),resource,raw_count,'resources',rid);raw_count+=1;power+=raw_recipe.power_draw_for(upstream)
    generators=math.ceil(power/D['energy.solar_array'].base_power_output)
    for i in range(generators):
        if i:UnlockProductionSlot('e','e.line-1','energy').apply(s)
        install(buy('energy.solar_array'),energy,i,'energy')
    for index in targets:install(buy(definition.definition_id),target,index,'factory','iron')
    trucks=math.ceil(60*count/40);garage=s.freight.facilities['garage-1']
    for i in range(trucks):
        if i>=3:ExpandFreightFacility('garage-1').apply(s)
        cid=buy('freight.truck');InstallFreightCard('garage-1',i,cid,D).apply(s);s.freight.assignments[cid]=FreightAssignment('iron','market')
    investment=1e12-s.cash.amount;s.cash.amount=0;engine=SimulationEngine(D);warm_cash=0;peak=0
    for elapsed in range(1,1801):
        engine.advance_time(s,1);peak=max(peak,s.used_storage)
        if elapsed==600:warm_cash=s.cash.amount
    cash_min=(s.cash.amount-warm_cash)/20
    rows.append(dict(option=option,additional_factory_slots=count,infrastructure_quote=infrastructure,investment=investment,raw_machines=raw_count,processors=count,solar=generators,trucks=trucks,power_mw=power,
      actual_cash_min=cash_min,actual_last_minute_units=s.freight.delivery_statistics.rate(facility_id='garage-1').total,nominal_transport_units_min=trucks*40,storage_capacity=s.storage_capacity,peak_goods=peak,payback_minutes=investment/cash_min,
      assumptions='Same inherited nine-slot Factory with nine paid paused machines, bare initial Mining/Energy/Garage buildings. All new machines, vehicles and extra upstream/energy/freight slots are bought through real commands; zero initial inputs, no grants during flow. Full available recipes for the capital comparison, no claim of organic leveling. 1-second Engine steps, 10-minute warm-up, 20-minute cash window.'))
(OUT/'marginal-comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(rows,indent=2))
