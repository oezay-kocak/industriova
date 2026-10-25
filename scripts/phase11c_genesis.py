"""Real P10 genesis, command-driven installation and bounded reinvestment policy."""
from pathlib import Path
import sys,csv,json
from datetime import datetime,timezone
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'src'))
from production_zero.ui.main_window import _create_initial_state
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.commands import BuyCommonSupplyCard,InstallCardInHall,InstallFreightCard,SelectMachineProduction,AssignFreightCard,ExpandFreightFacility
from production_zero.core.freight import freight_facility_expansion_cost
from production_zero.core.simulation import SimulationEngine
from production_zero.core.definitions import MachineDefinition
from production_zero.core.fixed_prices import build_fixed_prices
import production_zero.core.market as market
from phase8_offline_work_cache import install
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json');R=load_resource_definitions(ROOT/'src/production_zero/data/resource_definitions.json');install(D)
P={o.output_resource:(d,o) for d in D.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
prices=list(csv.DictReader((ROOT/'docs/industriova-03-phase11c-price-model-comparison.csv').open(encoding='utf-8-sig')))
rows=[];events=[]
for model in ('A','B','C'):
 for rid in ('iron_ore','copper_ore','crude_oil','wheat'):
  for process in (False,True):
   if process and rid=='crude_oil':continue
   original=market.BASE_MARKET_PRICES;market.BASE_MARKET_PRICES={r['product_id']:float(r['price_'+model]) for r in prices}
   try:
    s=_create_initial_state(R,D);d,o=P[rid];site=next(h for h in s.resource_sites.values() if h.specialization==d.definition_id)
    cid=next((c.card_id for c in s.cards.values() if c.definition_id==d.definition_id),None)
    if cid is None:
     before=set(s.cards);BuyCommonSupplyCard(d.definition_id,D).apply(s);cid=(set(s.cards)-before).pop()
    InstallCardInHall(site.hall_id,0,cid,'resources').apply(s);SelectMachineProduction(cid,o.production_id,rid).apply(s)
    solar=next(c.card_id for c in s.cards.values() if c.definition_id=='energy.solar_array');InstallCardInHall('plant-1',0,solar,'energy').apply(s)
    fid=next(iter(s.freight.facilities));trucks=[c.card_id for c in s.cards.values() if c.definition_id=='freight.truck']
    for i,tid in enumerate(trucks):InstallFreightCard(fid,i,tid,D).apply(s);AssignFreightCard(tid,rid,'market').apply(s)
    target={'iron_ore':'iron','copper_ore':'copper','wheat':'flour'}.get(rid);configured=False;invested=1250-s.cash.amount
    events.append(dict(model=model,product=rid,processing=process,second=0,action='initial equipment purchase/installation; genesis gifts credited',cash=s.cash.amount))
    engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,23,12,tzinfo=timezone.utc))
    for second in range(1,28801):
     engine.advance_time(s,1)
     if process and not configured and P[target][1].production_id in s.production_progress.unlocked_production_ids:
      proc=next(c.card_id for c in s.cards.values() if c.definition_id=='machine.processor');InstallCardInHall('hall-1',0,proc,'factory').apply(s);SelectMachineProduction(proc,P[target][1].production_id,target).apply(s)
      for tid in trucks:AssignFreightCard(tid,target,'market').apply(s)
      configured=True;events.append(dict(model=model,product=rid,processing=process,second=second,action='earned unlock; install owned processor and reroute',cash=s.cash.amount))
     if second%60==0 and len(trucks)<4:
      f=s.freight.facilities[fid];slot=len(trucks);cost=205+(freight_facility_expansion_cost(f,slot_index=slot) if slot>=len(f.slots) else 0)
      if s.cash.amount>=cost:
       if slot>=len(f.slots):ExpandFreightFacility(fid,slot).apply(s)
       before=set(s.cards);BuyCommonSupplyCard('freight.truck',D).apply(s);tid=(set(s.cards)-before).pop();InstallFreightCard(fid,slot,tid,D).apply(s);AssignFreightCard(tid,target if configured else rid,'market').apply(s);trucks.append(tid);invested+=cost
       events.append(dict(model=model,product=rid,processing=process,second=second,action='reinvest cash in truck/slot',cash=s.cash.amount))
     if second in (600,1800,3600,7200,28800):rows.append(dict(model=model,raw_product=rid,processing=process,target=target if configured else rid,seconds=second,cash=s.cash.amount,earnings=s.statistics.total_earnings,additional_investment=invested,company_level=s.company.level,truck_count=len(trucks),research_spent=s.research.spent,kind='actual P10 genesis; initial stock included, never extrapolated as steady output; reinvestment policy max four trucks'))
   finally:market.BASE_MARKET_PRICES=original
   print('genesis',model,rid,process,flush=True)
out=ROOT/'artifacts/phase11c'
for name,data in [('genesis.csv',rows),('investment-events.csv',events)]:
 with (out/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
