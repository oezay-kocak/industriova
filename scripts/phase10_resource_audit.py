"""Fixed-price/raw-resource audit using catalog math and isolated real engines."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
from collections import defaultdict
import json, math, os, sys
root=Path.cwd();out=root/'artifacts/phase10';sys.path.insert(0,str(root/'src'))
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'audit-appdata'),APPDATA=str(out/'audit-appdata'))
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.definitions import MachineDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.supply import common_card_price
from production_zero.core.market import market_price_for
from production_zero.core.state import GameState,FactoryHall,MachineProductionState
from production_zero.core.freight import FreightFacility,FreightAssignment,freight_stats
from production_zero.core.simulation import SimulationEngine
from production_zero.core.progression import progression_resources,unlock_requirements_for
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.production_values import ProductionValueCalculator
from production_zero.ui.main_window import _create_initial_state
D=load_card_definitions(root/'src/production_zero/data/game_definitions.json')
R=load_resource_definitions(root/'src/production_zero/data/resource_definitions.json')
producer={o.output_resource:(d,o) for d in D.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
consumers=defaultdict(list)
for rid,(d,o) in producer.items():
 for ingredient,amount in o.input_resources.items():
  inputs=sum(market_price_for(None,key)*qty for key,qty in o.input_resources.items())
  consumers[ingredient].append(dict(resource=rid,name=R[rid].name,machine=d.definition_id,
   amount=amount,output=o.output_amount_for(d),inputs=dict(o.input_resources),output_price=market_price_for(None,rid),
   input_value_per_cycle=inputs,added_value_per_cycle=market_price_for(None,rid)*o.output_amount_for(d)-inputs))
raws=[(rid,d,o) for rid,(d,o) in producer.items() if not o.input_resources]
calculator=ProductionValueCalculator(D);chain=[]
def base_needs(rid):
 d,o=producer[rid];q=o.output_amount_for(d)
 if not o.input_resources:return {rid:1.}
 result=defaultdict(float)
 for ingredient,qty in o.input_resources.items():
  for raw,n in base_needs(ingredient).items():result[raw]+=n*qty/q
 return dict(result)
for rid,(d,o) in producer.items():
 pv=calculator.value_for_resource(rid);needs=base_needs(rid)
 work=float(pv.value_per_unit)
 chain.append(dict(resource=rid,name=R[rid].name,depth=pv.depth,raw_inputs_per_unit=needs,
  base_price=market_price_for(None,rid),machine_minutes_per_unit=work,
  gross_cash_per_total_machine_minute=market_price_for(None,rid)/work,
  raw_sell_opportunity=sum(market_price_for(None,k)*n for k,n in needs.items()),
  company_level=progression_resources().get(rid,{}).get('company_level'),
  unlock_inputs=[dict(resource=q.resource_id,amount=q.quantity) for q in unlock_requirements_for(o)]))
rows=[]
for rid,d,o in raws:
 rate=o.output_amount_for(d)*60/o.cycle_seconds_for(d);power=o.power_draw_for(d)
 rows.append(dict(resource=rid,name=R[rid].name,machine=d.definition_id,rate=rate,price=market_price_for(None,rid),
  machine_cost=common_card_price(d),power=power,solar_generators=math.ceil(power/D['energy.solar_array'].base_power_output),
  gross_cash_min=rate*market_price_for(None,rid),freight_units_min=rate,
  company_level=progression_resources().get(rid,{}).get('company_level'),
  initially_unlocked=o.production_id in _create_initial_state(R,D).production_progress.unlocked_production_ids,
  consumers=consumers[rid],descendants=sum(rid in e['raw_inputs_per_unit'] for e in chain if e['resource']!=rid)))
# Reuse only pure catalog work in this offline engine audit, after an exact
# comparison of all 353 values. Performance measurements never install it.
from phase8_offline_work_cache import install
cache_proof=install(D)
engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,23,12,tzinfo=timezone.utc))
simulations=[]
representatives={'iron_ore','coal','copper_ore','bauxite','limestone','quartz','crude_oil','timber','wheat'}
for rid,d,o in raws:
 for mk,rarity,bonus in ([(1,Rarity.COMMON,0.)] + ([(10,Rarity.COMMON,0.),(99,Rarity.COMMON,0.),(1,Rarity.LEGENDARY,20.)] if rid in representatives else [])):
  s=GameState(10);s.halls.clear();s.resource_sites.clear();s.energy_plants.clear();s.freight.facilities.clear()
  s.warehouse_capacity=1e9;s.company.level=100
  s.production_progress.unlocked_production_ids.update(p.production_id for _,p in producer.values())
  machine=replace(create_card_instance('raw',d.definition_id,d.card_kind,rarity),mk_level=mk,output_bonus_percent=bonus)
  s.cards['raw']=machine
  s.resource_sites['raw']=FactoryHall('raw','Raw',1,board_kind='resources',specialization=d.definition_id)
  s.resource_sites['raw'].slots[0].card_id='raw'
  s.machine_production['raw']=MachineProductionState('raw',rid,o.production_id)
  count=math.ceil(o.power_draw_for(d)*machine.power_multiplier/D['energy.solar_array'].base_power_output)
  s.energy_plants['power']=FactoryHall('power','Power',count,board_kind='energy')
  for index in range(count):
   cid='solar'+str(index);s.cards[cid]=create_card_instance(cid,'energy.solar_array',D['energy.solar_array'].card_kind,Rarity.COMMON)
   s.energy_plants['power'].slots[index].card_id=cid
  truck=replace(create_card_instance('truck','freight.truck',D['freight.truck'].card_kind,rarity),mk_level=mk,output_bonus_percent=bonus)
  s.cards['truck']=truck;garage=FreightFacility(facility_id='garage',name='Garage',facility_type='garage_depot');s.freight.facilities['garage']=garage;garage.slots[0].card_id='truck'
  s.freight.assignments['truck']=FreightAssignment(rid,'market');s.ensure_resource(rid)
  capital=common_card_price(d)+count*common_card_price(D['energy.solar_array'])+common_card_price(D['freight.truck'])
  for card,definition in ((machine,d),(truck,D['freight.truck'])):
   capital+=sum(mk_upgrade_cost(replace(card,mk_level=level),definition) for level in range(1,mk))
  for second in range(600):engine.advance_time(s,1)
  simulations.append(dict(resource=rid,mk=mk,rarity=rarity.value,bonus=bonus,seconds=600,
   actual_cash=s.cash.amount,cash_min=s.cash.amount/10,earnings=s.statistics.total_earnings,
   remaining_stock=s.ensure_resource(rid).amount,active_shipments=sum(q.active for q in s.freight.outbound_shipments.values()),
   p6_units_min=s.freight.delivery_statistics.rate(facility_id='garage').total,
   solar_generators=count,power=s.energy.consumed,capital=capital,capital_basis="Common acquisition reference plus actual MK upgrades; Legendary acquisition premium not priced",
   theoretical_production_min=o.output_amount_for(d)*60/o.cycle_seconds_for(d)*machine.output_multiplier,
   theoretical_freight_min=freight_stats(truck,D['freight.truck'],s.research).capacity * 60 / freight_stats(truck,D['freight.truck'],s.research).transport_time_seconds))
  assert s.cash.amount>=0 and all(stock.amount>=0 for stock in s.resources.values())
  print(rid,mk,rarity.value,round(s.cash.amount/10,3),flush=True)
result=dict(raws=rows,chains=chain,simulations=simulations,cache_proof=cache_proof,
 assumptions='600 one-second real engine ticks; zero initial stock, full recipe/level unlock for capability comparison; Common replacement-capital reference (machines/solar/truck/MK); non-Common acquisition premium excluded, no recurring solar money cost; no Research. One matching-MK vehicle. Finite start/end shipment latency included. Not an organic early-game playthrough; initial unlock status is listed separately. No prices or recipes changed.')
(out/'resource-price-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('AUDITED',len(rows),'raws',len(chain),'chains',len(simulations),'engine strategies',flush=True)
