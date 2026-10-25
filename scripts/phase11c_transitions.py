"""Whole-chain versus sale of direct inputs at the same net flow, offline."""
from pathlib import Path
import sys,json,math
root=Path.cwd();sys.path.insert(0,str(root/'src'))
source=(root/'scripts/phase11c_economy.py').read_text(encoding='utf8')
exec(compile(source.split('BUDGETS=')[0],'phase11c catalog prefix','exec'),globals())

def cut_plan(r):
 full=layout(r,1.,1);counts={x:n for x,n in full['counts'].items() if x!=r};groups=Counter();power=0;cost=0
 for x,n in counts.items():
  d,o=P[x];groups[d.definition_id]+=n;power+=n*o.power_draw_for(d)
 for did,n in groups.items():cost+=max(0,n-gifts.get(did,0))*common_card_price(D[did])
 for did in ('machine.extractor','machine.drilling','machine.agriculture'):cost+=boardcost('resources',groups[did])
 cost+=boardcost('factory',sum(groups[x] for x in ('machine.processor','machine.fabricator','machine.assembler')))
 energy=[]
 for did in ('energy.solar_array','energy.wind_turbine'):
  n=math.ceil(power/D[did].base_power_output);energy.append(boardcost('energy',n)+max(0,n-gifts.get(did,0))*common_card_price(D[did]))
 cost+=min(energy)
 d,o=P[r];flows={x:a/o.output_amount_for(d) for x,a in o.input_resources.items()}
 fleets=[]
 for did in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
  fd=D[did];rate=fd.base_capacity*60/fd.base_transport_time_seconds
  n=sum(math.ceil(value/rate) for value in flows.values());fleets.append((fleet_cost(did,n,1),did,n))
 fc,did,n=min(fleets);cost+=fc
 # Full-chain buffer is conservative also for the cut with no final conversion.
 cost+=sum(inventory_storage_upgrade_cost(k) for k in range(full['storage_level']))
 return dict(cost=cost,power=power,freight_id=did,freight_count=n,flows=flows,counts=counts)

rows=[]
for r in ORDER:
 d,o=P[r]
 if not o.input_resources:continue
 final=layout(r,1.,1);cut=cut_plan(r)
 for model,prices in MODELS.items():
  cash_final=prices[r];cash_cut=sum(prices[x]*v for x,v in cut['flows'].items());delta=cash_final-cash_cut;investment=final['cost']-cut['cost']
  row=dict(product_id=r,model=model,target_units_min=1,company_level=META[r]['company_level'],final_capital=final['cost'],cut_capital=cut['cost'],additional_capital=investment,additional_factory_cards=final['counts'][r],additional_requested_mw=final['power_mw']-cut['power'],final_freight_units_min=1,cut_freight_units_min=sum(cut['flows'].values()),final_freight_id=final['freight_id'],cut_freight_id=cut['freight_id'],cut_export_quantities=json.dumps(cut['flows'],sort_keys=True),nominal_additional_cash_min=delta,conditional_payback_minutes=max(0,investment)/delta if delta>0 else '',conditions='Continuous scheduled 1 final unit/min; same upstream flows; homogeneous freight fleet alternatives; zero research, common MK1, mature earned unlocks; conditional calculation, not realized Engine cashflow')
  for t in (10,30,60,120,480):row['conditional_incremental_net_'+str(t)+'min']=delta*t-investment
  rows.append(row)
write_csv(OUT/'processing-transitions.csv',rows)
print('all',len(rows),'model/processing transitions')
