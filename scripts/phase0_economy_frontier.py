"""Economic proposals only; evaluates formulas without writing production data."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase0_benchmark import D,R,OUT
from production_zero.core.supply import common_card_price
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.market import BASE_MARKET_PRICES

# Reuse the existing recipe/MK audit but redirect its sole output into Phase 0.
existing=(ROOT/'scripts/release_economy_audit.py').read_text(encoding='utf8')
existing=existing.replace('artifacts/industriova-release/economy-audit.json','artifacts/phase0/recipe-mk-audit.json')
exec(compile(existing,str(ROOT/'scripts/release_economy_audit.py'),'exec'),{'__name__':'__main__'})

result={'proposal_only':True,'production_data_modified':False,'production':[],'freight_frontier':[]}
for board,lines,slots,start_slots,line_base in [('factory',5,10,3,12000),('resources',3,10,1,15000),('energy',3,5,1,3000)]:
    def slot_cost(k):return math.ceil(120*(k-start_slots)**1.35/5)*5
    line_costs=[line_base*(l-1)**2 for l in range(2,lines+1)]
    per_line_slots=[slot_cost(k) for k in range(start_slots+1,slots+1)]
    # Facility must be dearer per starting slot than the most expensive
    # additional line including all its expanded slots, with 25% headroom.
    full_line=line_costs[-1]+sum(per_line_slots)
    second=math.ceil(max((full_line/slots)*start_slots*1.25,
                         full_line*1.25-sum(per_line_slots))/100)*100
    total=sum(line_costs)+lines*sum(per_line_slots)
    result['production'].append({'board':board,'start_lines':1,'start_slots':start_slots,'lines':lines,'slots_per_line':slots,
        'slot_prices_per_line':per_line_slots,'line_prices':line_costs,'full_first_expansion':total,
        'proposed_second_facility':second,'full_last_line_cost_per_added_slot':full_line/slots,
        'second_facility_cost_per_start_slot':second/start_slots})

# Baseline and an illustrative soft-progression candidate. No vehicle besides
# Ship changes. Per-type facility counts remain quadratic. Garage 1 is owned.
candidate_bases={'freight.truck':500,'freight.train':30000,'freight.aircraft':180000,'freight.ship':250000}
baseline_bases={'freight.truck':500,'freight.train':1500,'freight.aircraft':3500,'freight.ship':2500}
entries=[]
for proposal,bases in [(False,baseline_bases),(True,candidate_bases)]:
 for did in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
    d=D[did];q=d.base_capacity*60/d.base_transport_time_seconds;p=common_card_price(d)
    if proposal and did=='freight.ship':q=4000;p=3*common_card_price(D['freight.aircraft'])
    initial=3 if did=='freight.truck' else 2
    for n in range(1,25):
        expansions=max(0,n-initial);infra=300*expansions*(expansions+1)*(2*expansions+1)/6
        build=0 if did=='freight.truck' else bases[did]
        total=build+infra+n*p
        entries.append({'proposal':proposal,'type':did,'vehicles':n,'cash':total,'units_per_minute':q*n,
                        'cash_per_unit_minute':total/(q*n)})
for proposal in (False,True):
 for budget in (1000,3000,5000,10000,20000,30000,50000,100000,200000,300000,500000,1000000):
    choices=[r for r in entries if r['proposal']==proposal and r['cash']<=budget]
    best=max(choices,key=lambda x:x['units_per_minute']) if choices else None
    result['freight_frontier'].append({'proposal':proposal,'budget':budget,'best_single_facility':best})
result['freight_candidate_bases']=candidate_bases
result['freight_options']=entries
result['full_facility_examples']=[]
for did,count,board in [('machine.processor',50,'factory'),('energy.solar_array',15,'energy')]:
 d=D[did];upgrade=0;card=create_card_instance('model',did,d.card_kind,Rarity.COMMON)
 for level in range(1,100):
    if level>1:
        from dataclasses import replace
        card=replace(card,mk_level=level-1);upgrade+=mk_upgrade_cost(card,d)
    if level not in (1,2,10,50,99):continue
    f=1+.25*(level-1);per=common_card_price(d)+upgrade
    row={'definition':did,'count':count,'mk':level,'factor':f,'base_plus_paid_mk_per_card':per,
         'fleet_capital':count*per}
    if did=='machine.processor':
        row.update(output_iron_per_minute=count*60*f,power_mw=count*8*f,
                   margin_before_power_per_minute=count*105*f,
                   solar_at_same_mk=math.ceil(count*8/20))
    else:row['power_mw']=count*20*f
    result['full_facility_examples'].append(row)
(OUT/'economy-frontier.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'production':result['production'],'frontier_rows':len(result['freight_frontier'])}),flush=True)
