"""Offline static sensitivity and Pareto analysis; source/catalog only."""
from pathlib import Path
import csv,json,sys
from collections import defaultdict
root=Path.cwd();sys.path.insert(0,str(root/'src'))
from production_zero.data.definitions import load_card_definitions
from production_zero.core.definitions import MachineDefinition
from production_zero.core.research import ResearchState,research_catalog
from production_zero.core.modifiers import research_multiplier,contract_cash_quote
from production_zero.core.state import GameState
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.freight import freight_stats
import production_zero.core.market as market
out=root/'artifacts/phase11c'
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def write(p,data):
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
D=load_card_definitions(root/'src/production_zero/data/game_definitions.json');P={o.output_resource:(d,o) for d in D.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
comparison=read(root/'docs/industriova-03-phase11c-price-model-comparison.csv');meta={r['product_id']:r for r in comparison}
sensitivity=[]
for model in ('A','B','C'):
 old=market.BASE_MARKET_PRICES;market.BASE_MARKET_PRICES={r['product_id']:float(r['price_'+model]) for r in comparison}
 try:
  for mk,bonus,research in [(1,0,False),(10,0,False),(50,0,False),(99,0,False),(1,5,False),(1,10,False),(1,20,False),(1,0,True),(10,20,True)]:
   s=GameState(1)
   if research:s.research=ResearchState(total_earned=645,unlocked_node_ids=set(research_catalog()[1]))
   for rid,(d,o) in P.items():
    rarity=Rarity.COMMON if bonus==0 else {5:Rarity.UNCOMMON,10:Rarity.RARE,20:Rarity.LEGENDARY}[bonus]
    c=create_card_instance('sensitivity',d.definition_id,d.card_kind,rarity,bonus_tenths=bonus*10);c=__import__('dataclasses').replace(c,mk_level=mk)
    speed=research_multiplier(s.research,'production_speed');price=market.BASE_MARKET_PRICES[rid]*research_multiplier(s.research,'value',rid)
    row=dict(product_id=rid,model=model,mk=mk,rarity=rarity.value,bonus_percent=bonus,research='645 nodes, no product specialization' if research else 'none',output_min=o.output_amount_for(d)*60/o.cycle_seconds_for(d)*c.output_multiplier*speed,power_mw=o.power_draw_for(d)*c.power_multiplier,input_multiplier=c.mk_multiplier*speed,market_quote=price,regular_unit_cash=contract_cash_quote(s,{rid:1.}),daily_unit_cash=contract_cash_quote(s,{rid:1.})*1.2,weekly_unit_cash=contract_cash_quote(s,{rid:1.})*1.4,consortium_daily_pool_per_unit=price*1.15,consortium_weekly_pool_per_unit=price*1.25,conditions='Contract values conditional quotes, not guaranteed offers/completions; Consortium highest-member quote, not whole pool per member; quality premium not priced')
    sensitivity.append(row)
 finally:market.BASE_MARKET_PRICES=old
write(out/'sensitivity-contract-quotes.csv',sensitivity)
companies=read(out/'company-search.csv');groups=defaultdict(list)
for r in companies:groups[r['budget'],r['level']].append(r)
pareto=[];branches=[]
for (budget,level),group in groups.items():
 for model in ('A','B','C'):
  def vector(r):
   return (float(r['cost']),-float(r['continuous_cash_min_'+model]),float(r['power_mw']),int(r['factory_cards']),float(meta[r['product_id']]['company_level']),float(D[r['freight_id']].base_transport_time_seconds))
  vectors={r['product_id']:vector(r) for r in group}
  frontier=[]
  for rid,v in vectors.items():
   if not any(all(a<=b for a,b in zip(w,v)) and any(a<b for a,b in zip(w,v)) for other,w in vectors.items() if other!=rid):frontier.append(rid)
  best=max(float(r['continuous_cash_min_'+model]) for r in group)
  pareto.append(dict(budget=budget,level=level,model=model,count=len(frontier),products=';'.join(frontier),dimensions='cost, cash/min, MW, factory cards, required level, base trip delay; static scoped companies, not all firms'))
  domain_groups=defaultdict(list)
  for r in group:domain_groups[r['domain']].append(r)
  for domain,candidates in domain_groups.items():
   b=max(candidates,key=lambda r:float(r['continuous_cash_min_'+model]));value=float(b['continuous_cash_min_'+model])
   branches.append(dict(budget=budget,level=level,model=model,domain=domain,best_product=b['product_id'],continuous_cash_min=value,lag_to_best_percent=(1-value/best)*100,cost=b['cost'],scope='Best sampled single-output/uniform-MK company in domain, no global optimum'))
write(out/'pareto-multidimensional.csv',pareto);write(out/'industry-comparison.csv',branches)
print('sensitivity',len(sensitivity),'Pareto',len(pareto),'branches',len(branches))
