"""Offline, bounded single-output company search. Never imported by the game.

Run with the project venv, -B. Outputs only docs/phase11c* and artifacts/phase11c.
No personal save or existing build is opened. No global optimality claim.
"""
from pathlib import Path
import csv, json, math, sys, hashlib
from functools import lru_cache
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
OUT=ROOT/'artifacts/phase11c';OUT.mkdir(exist_ok=True)
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.definitions import MachineDefinition,FreightDefinition
from production_zero.core.market import BASE_MARKET_PRICES,LEGACY_BASE_MARKET_PRICES
from production_zero.core.fixed_prices import build_fixed_prices
from production_zero.core.supply import common_card_price
from production_zero.core.infrastructure_prices import facility_price,line_price,slot_price,BOARD_LIMITS,FREIGHT_BUILD_BASES
from production_zero.core.mk_upgrades import mk_upgrade_cost,mk_factor
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.research import ResearchState,research_catalog,research_domains
from production_zero.core.modifiers import research_multiplier
from production_zero.core.storage_upgrades import inventory_storage_upgrade_cost,global_storage_base_capacity
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json')
R=load_resource_definitions(ROOT/'src/production_zero/data/resource_definitions.json')
P={o.output_resource:(d,o) for d in D.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
A={r:float(p) for r,p in BASE_MARKET_PRICES.items()}
CAT=list(csv.DictReader((ROOT/'docs/industriova-03-complete-recipe-catalog.csv').open(encoding='utf-8-sig')))
META={r['product_id']:r for r in CAT}
# Both P11-B sources are required inputs; checksum and schema coverage recorded.
capacity_path=ROOT/'docs/industriova-03-phase11b-capacity-data.csv'
CAP=list(csv.DictReader(capacity_path.open(encoding='utf-8-sig')))
assert len(P)==len(CAT)==353 and len(CAP)==20819
assert all(float(META[r]['base_sell_price'])==A[r] for r in P)
SOURCE_PROOF={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'docs/industriova-03-complete-recipe-economy-audit.md',ROOT/'docs/industriova-03-complete-recipe-catalog.csv',ROOT/'docs/industriova-03-phase11b-capacity-audit.md',capacity_path]}
roots={r for r,(d,o) in P.items() if not o.input_resources}
anchors=dict(LEGACY_BASE_MARKET_PRICES);anchors.update({r:1. for r in roots})
B=build_fixed_prices(anchors)
ORDER=sorted(P,key=lambda r:int(META[r]['maximum_processing_depth']))
C={r:1. for r in roots}
for r in ORDER:
 d,o=P[r];q=o.output_amount_for(d);minutes=o.cycle_seconds_for(d)/60
 if o.input_resources:
  C[r]=sum(C[x]*a for x,a in o.input_resources.items())/q+120*minutes/q+.01*o.power_draw_for(d)*minutes/q
MODELS={'A':A,'B':B,'C':C}

@lru_cache(None)
def needs(r):
 """Units of every production output per unit sold; merged shared branches."""
 d,o=P[r];result={r:1.}
 for x,a in o.input_resources.items():
  for y,n in needs(x).items():result[y]=result.get(y,0.)+n*a/o.output_amount_for(d)
 return result

def write_csv(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

comparison=[]
for r in ORDER:
 d,o=P[r];q=o.output_amount_for(d);rate=q*60/o.cycle_seconds_for(d)
 work=sum(n/float(META[x]['mk1_common_output_per_minute']) for x,n in needs(r).items())
 mwmin=sum(n*float(META[x]['power_mw'])/float(META[x]['mk1_common_output_per_minute']) for x,n in needs(r).items())
 row=dict(product_id=r,name=R[r].name,stage=META[r]['stage'],domain=research_domains()[r],company_level=META[r]['company_level'],machine_id=d.definition_id,output_per_cycle=q,cycle_seconds=o.cycle_seconds_for(d),direct_power_mw=o.power_draw_for(d),recursive_machine_minutes_per_unit=work,chain_mw_minutes_per_unit=mwmin,raw_units_per_unit=json.dumps({x:n for x,n in needs(r).items() if x in roots},sort_keys=True),freight_units_per_unit_sold=1,all_production_units_per_unit=json.dumps(needs(r),sort_keys=True))
 assert abs(work-float(META[r]['production_value_machine_minutes_per_unit']))<1e-10
 for model,prices in MODELS.items():
  iv=sum(prices[x]*a for x,a in o.input_resources.items());added=q*prices[r]-iv
  row.update({f'price_{model}':prices[r],f'direct_input_cycle_{model}':iv,f'added_value_cycle_{model}':added,f'added_value_machine_minute_{model}':added*60/o.cycle_seconds_for(d)})
 for model,prices in [('B',B),('C',C)]:
  row[f'delta_{model}']=prices[r]-A[r];row[f'delta_percent_{model}']=(prices[r]/A[r]-1)*100
 row['difference_reason']='Primary normalization' if r in roots else 'B: normalized raw inputs, retained anchors; C: no anchors, incremental machine work and energy opportunity allowance'
 comparison.append(row)
write_csv(ROOT/'docs/industriova-03-phase11c-price-model-comparison.csv',comparison)

unique={d.definition_id:d for d in D.values()}
MK=(1,10,50,99)
UP={}
for did,d in unique.items():
 card=create_card_instance('offline',did,d.card_kind,Rarity.COMMON);cost=0.
 for k in range(1,100):
  if k in MK:UP[did,k]=cost
  if k<99:cost+=mk_upgrade_cost(replace(card,mk_level=k),d)
gifts={'machine.extractor':3,'machine.processor':2,'energy.solar_array':1,'freight.truck':2}

@lru_cache(None)
def boardcost(board,n):
 ml,cap,start=BOARD_LIMITS[board];total=0.
 for j in range(math.ceil(n/(ml*cap))):
  if j:total+=facility_price(board,j)
  left=min(ml*cap,n-j*ml*cap)
  for line in range(1,math.ceil(left/cap)+1):
   if line>1:total+=line_price(board,line)
   total+=sum(slot_price(board,line,k) for k in range(start+1,min(cap,left-(line-1)*cap)+1))
 return total

@lru_cache(None)
def fleet_cost(did,n,mk):
 from production_zero.core.freight import FreightFacility,freight_facility_expansion_cost,FREIGHT_FACILITY_START_SLOTS
 d=D[did];start=FREIGHT_FACILITY_START_SLOTS[d.facility_id]
 f=FreightFacility('offline','offline',d.facility_id,slot_count=start)
 # One growing freight building. Other-type first building is not a starter gift.
 infrastructure=0 if did=='freight.truck' else FREIGHT_BUILD_BASES[d.facility_id]
 infrastructure+=sum(freight_facility_expansion_cost(f,slot_index=i) for i in range(start,n))
 return infrastructure+max(0,n-gifts.get(did,0))*common_card_price(d)+n*UP[did,mk]

@lru_cache(None)
def layout(r,rate,mk=1,speed=1.,freight_bonus=1.,bonus=0.):
 """Monotone fixed layout family, not all feasible companies; exact quotes."""
 m=mk_factor(mk);counts={};power=0.;groups=Counter();cost=0.;buffer=0.
 # Rarity improves every upstream output too: propagate actual per-unit needs.
 demand={r:rate}
 for x in reversed(ORDER):
  if x not in demand:continue
  d,o=P[x];q=o.output_amount_for(d);out=q*m*(1+bonus/100)*speed*60/o.cycle_seconds_for(d)
  n=math.ceil(demand[x]/out-1e-10);counts[x]=n
  power+=n*o.power_draw_for(d)*m*(1+bonus/200)
  groups[d.definition_id]+=n
  buffer+=n*(q*m*(1+bonus/100)+sum(o.input_resources.values())*m)
  for y,a in o.input_resources.items():demand[y]=demand.get(y,0.)+demand[x]*a/(q*(1+bonus/100))
 for did,n in groups.items():cost+=max(0,n-gifts.get(did,0))*common_card_price(D[did])+n*UP[did,mk]
 for did in ('machine.extractor','machine.drilling','machine.agriculture'):cost+=boardcost('resources',groups[did])
 cost+=boardcost('factory',sum(groups[x] for x in ('machine.processor','machine.fabricator','machine.assembler')))
 energy_options=[]
 for edid in ('energy.solar_array','energy.wind_turbine'):
  ed=D[edid];n=math.ceil(power/(ed.base_power_output*m*(1+bonus/100))-1e-10)
  ec=boardcost('energy',n)+max(0,n-gifts.get(edid,0))*common_card_price(ed)+n*UP[edid,mk]
  energy_options.append((ec,edid,n))
 ec,edid,en=min(energy_options);cost+=ec
 fleet=[]
 for fdid in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
  fd=D[fdid];through=fd.base_capacity*m*(1+bonus/100)*freight_bonus*60/(fd.base_transport_time_seconds*(1+bonus/200))
  n=max(1,math.ceil(rate/through-1e-10));fleet.append((fleet_cost(fdid,n,mk),fdid,n,through*n))
 fc,fdid,fn,fr=min(fleet);cost+=fc
 base=global_storage_base_capacity(R);sl=max(0,math.ceil((buffer/base-1)*4))
 cost+=sum(inventory_storage_upgrade_cost(k) for k in range(sl))
 return dict(product_id=r,rate=rate,mk=mk,cost=cost,counts=counts,power_mw=power,energy_id=edid,energy_count=en,freight_id=fdid,freight_count=fn,freight_capacity=fr,storage_level=sl,buffer_capacity=base*(1+.25*sl),bonus=bonus,speed=speed,freight_bonus=freight_bonus)

for row in comparison:
 plan=layout(row['product_id'],1.,1)
 row.update(defined_target_units_min=1.,capital_for_nominal_target=plan['cost'],installed_chain_power_mw=plan['power_mw'],required_machine_counts=json.dumps(plan['counts'],sort_keys=True),required_energy_id=plan['energy_id'],required_energy_count=plan['energy_count'],required_freight_id=plan['freight_id'],required_freight_count=plan['freight_count'],capital_conditions='MK1/Common; mature unlocks; starter assets credited; nominal sustained-flow layout, engine/controller qualification required')
write_csv(ROOT/'docs/industriova-03-phase11c-price-model-comparison.csv',comparison)

BUDGETS=(1250,5000,10000,50000,100000,500000,1000000,10000000,1e9,1e12)
search=[];saved={};coverage=[]
for budget in BUDGETS:
 for level in (1,5,25):
  eligible=[r for r in P if all(int(META[x]['company_level'])<=level for x in needs(r))]
  # Maturity cohort: lifetime unlocks already earned, no RP; genesis separate engine run.
  for r in eligible:
   best=None
   for mk in MK:
    lo,hi=0.,1.
    while hi<1e6 and layout(r,hi,mk)['cost']<=budget:lo,hi=hi,hi*2
    for _ in range(12):
     mid=(lo+hi)/2
     if layout(r,mid,mk)['cost']<=budget:lo=mid
     else:hi=mid
    if lo<=0:continue
    plan=layout(r,lo,mk)
    if best is None or plan['rate']>best['rate']:best=plan
   if best is None:continue
   saved[(budget,level,r)]=best
   rec=dict(budget=budget,level=level,cohort='earned lifetime unlocks; no research; common; genesis endowment retained',product_id=r,domain=research_domains()[r],**{k:v for k,v in best.items() if k not in ('product_id','counts')},machines=json.dumps(best['counts'],sort_keys=True),factory_cards=sum(n for x,n in best['counts'].items() if x not in roots))
   for model,prices in MODELS.items():rec[f'continuous_cash_min_{model}']=best['rate']*prices[r]
   search.append(rec)
  print('search',budget,level,len(eligible),flush=True)
write_csv(OUT/'company-search.csv',search)

summary=[]
for budget in BUDGETS:
 for level in (1,5,25):
  cohort=[r for r in search if r['budget']==budget and r['level']==level]
  for model,prices in MODELS.items():
   metric=f'continuous_cash_min_{model}';best=max(cohort,key=lambda r:r[metric]);front=[]
   for r in cohort:
    if not any(t['cost']<=r['cost'] and t[metric]>=r[metric] and (t['cost']<r['cost'] or t[metric]>r[metric]) for t in cohort):front.append(r['product_id'])
   # Relaxed resource-card-only investment: no energy/freight/slots, fractional cards.
   # Lower bound on capital per unit/min, thus upper bound on all such common flows.
   upper=0.
   for r in cohort:
    unit=sum(n*min((common_card_price(P[x][0])+UP[P[x][0].definition_id,k])/(float(META[x]['mk1_common_output_per_minute'])*mk_factor(k)) for k in MK) for x,n in needs(r['product_id']).items())
    upper=max(upper,(budget+2160)*prices[r['product_id']]/unit)
   for r in cohort:r[f'lag_percent_{model}']=(1-r[metric]/best[metric])*100
   summary.append(dict(budget=budget,level=level,model=model,best_product=best['product_id'],best_continuous_cash_min=best[metric],frontier_count=len(front),frontier_products=';'.join(front),within_20_percent=sum(r[metric]>=.8*best[metric] for r in cohort),searched=len(cohort),relaxed_upper_cash_min=upper,upper_gap_percent=(1-best[metric]/upper)*100))
write_csv(OUT/'company-search.csv',search);write_csv(OUT/'frontiers.csv',summary)

def build_state(plan,genesis=False):
 from production_zero.core.state import GameState,FactoryHall,ProductionLine,MachineProductionState
 from production_zero.core.freight import FreightFacility,FreightAssignment
 from production_zero.core.resources import create_resource_inventory
 s=GameState(1001,resources=create_resource_inventory(R));s.halls.clear();s.resource_sites.clear();s.energy_plants.clear();s.freight.facilities.clear();s.cash.amount=0
 s.company.level=max(int(META[x]['company_level']) for x in plan['counts'])
 s.production_progress.unlocked_production_ids={o.production_id for d,o in P.values()}
 s.warehouse_capacity=plan['buffer_capacity'];s.inventory_storage_level=plan['storage_level']
 groups=defaultdict(list)
 for r,n in plan['counts'].items():
  d,o=P[r];board='resources' if r in roots else 'factory';groups[(board,d.definition_id if board=='resources' else 'mixed')]+=[(d,o)]*n
 groups['energy','mixed']=[(D[plan['energy_id']],None)]*plan['energy_count']
 serial=0
 for (board,kind),cards in groups.items():
  ml,cap,start=BOARD_LIMITS[board]
  for offset in range(0,len(cards),ml*cap):
   batch=cards[offset:offset+ml*cap];uid=f'{board}-{kind}-{offset}'
   lines=[ProductionLine(uid+str(j),str(j),list(range(j*cap,min((j+1)*cap,len(batch))))) for j in range(math.ceil(len(batch)/cap))]
   hall=FactoryHall(uid,uid,len(batch),board_kind=board,specialization=kind if board=='resources' else None,max_lines=ml,max_slots_per_line=cap,production_lines=lines)
   s.production_units(board)[uid]=hall
   for i,(d,o) in enumerate(batch):
    serial+=1;cid=str(serial);card=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),mk_level=plan['mk'])
    s.cards[cid]=card;hall.slots[i].card_id=cid
    if o:s.machine_production[cid]=MachineProductionState(cid,o.output_resource,o.production_id)
 fd=D[plan['freight_id']];n=plan['freight_count'];f=FreightFacility('freight','freight',fd.facility_id,slot_count=n);s.freight.facilities['freight']=f
 for i in range(n):
  cid='freight'+str(i);s.cards[cid]=replace(create_card_instance(cid,fd.definition_id,fd.card_kind,Rarity.COMMON),mk_level=plan['mk']);f.slots[i].card_id=cid;s.freight.assignments[cid]=FreightAssignment(plan['product_id'],'market')
 return s

# Real-engine validation, zero material endowment; budgets/quotes come from search.
# No offline price is installed in source files or persisted to a game save.
from phase8_offline_work_cache import install
cacheproof=install(D)
from production_zero.core.simulation import SimulationEngine
import production_zero.core.market as market
engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,23,12,tzinfo=timezone.utc))
sim=[]
representatives=['iron_ore','copper_ore','crude_oil','platinum_ore','wheat','iron','steel','lumber','flour','biodiesel','microchip','industrial_equipment','ai_server']
for r in representatives:
 key=(1000000,25,r)
 if key not in saved:continue
 plan=saved[key]
 # Keep real-engine sample bounded to manageable company size, not free extra money.
 if sum(plan['counts'].values())>150:plan=layout(r,1.,1)
 for model,prices in MODELS.items():
  original=market.BASE_MARKET_PRICES;market.BASE_MARKET_PRICES=prices
  try:
   s=build_state(plan);marks={600,1800,3600,7200}
   capacity=min([plan['freight_capacity'],*[n*float(META[x]['mk1_common_output_per_minute'])*mk_factor(plan['mk'])/needs(r)[x] for x,n in plan['counts'].items()]])
   for second in range(1,7201):
    engine.advance_time(s,1.)
    if second in marks:sim.append(dict(product_id=r,model=model,seconds=second,cash=s.cash.amount,earnings=s.statistics.total_earnings,investment=plan['cost'],nominal_rate=capacity,target_rate=plan['rate'],nominal_cash_min=capacity*prices[r],remaining_stock=s.used_storage,warehouse_capacity=s.storage_capacity,realized_cash_min=s.cash.amount/(second/60),net_after_investment=s.cash.amount-plan['cost'],company_level_cohort=25,kind='zero stock, pre-earned unlocks, fixed layout, no reinvestment',layout=json.dumps(plan,sort_keys=True)))
  finally:market.BASE_MARKET_PRICES=original
 print('engine',r,flush=True)
write_csv(OUT/'engine-validation.csv',sim)
(OUT/'proof.json').write_text(json.dumps(dict(sources=SOURCE_PROOF,products=len(comparison),scenarios=len(search),summary=summary,engine_rows=len(sim),cache_proof=cacheproof),indent=2),encoding='utf8')
print('offline complete',flush=True)
