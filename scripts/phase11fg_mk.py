"""All 1,470 transitions and full-supply C2 chain capital, old versus new."""
from pathlib import Path
import sys, math, csv, json
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'artifacts/phase11e'))
import common as c
from production_zero.core import mk_upgrades as u
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
OUT=ROOT/'artifacts/phase11fg'

def write(name, rows):
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def fund_buffer(p):
    """Pay for seven minutes of startup sales plus real batch/cargo buffers."""
    p=dict(p);base=c.global_storage_base_capacity(c.d.R)
    production=sum(n*(c.N1.recipes[r]['output']+sum(c.N1.recipes[r]['inputs'].values()))*c.upgrades.mk_factor(p['mk']) for r,n in p['counts'].items())
    required=production+p['freight_buffer']+sum(p['sales_min'].values())*7
    level=max(p['storage_level'],math.ceil((required/base-1)*4),0)
    cost=sum(c.inventory_storage_upgrade_cost(i) for i in range(level))
    p['base_cost']+=cost-p['storage_cost'];p['storage_cost']=cost
    p['storage_level']=level;p['storage_capacity']=base*(1+.25*level)
    return p

def tables():
    price=c.prices('N1',(120,40,120,0));rows=[];tables={'old':{},'new':{}}
    oldprices=u.BASE_MARKET_PRICES;u.BASE_MARKET_PRICES=price
    try:
        for did,definition in c.DEFS['N1'].items():
            card=create_card_instance('quote',did,definition.card_kind,Rarity.COMMON)
            net=u.base_net_profit_per_second(definition);totals={'old':0.,'new':0.};previous=0;smooth_total=0.
            for mk in range(1,100):
                for key in totals: tables[key][did,mk]=totals[key]
                if mk==99: continue
                old=math.ceil(max(c.common_card_price(definition)*mk**1.7,.25*net*900*((mk+1)/2)**2.3)*100)/100
                new=u.mk_upgrade_cost(replace(card,mk_level=mk),definition)
                assert math.isfinite(new) and new>previous>0 if mk>1 else new>0
                previous=new
                totals['old']+=old;totals['new']+=new
                smooth_horizon=180*((mk+1)/2)**(math.log(480)/math.log(49.5))
                capital=.25*c.common_card_price(definition)*(1+.025*(mk-1))
                smooth_quote=math.ceil(max(capital,.125*net*smooth_horizon)*100)/100;smooth_total+=smooth_quote
                rows.append(dict(family=did,from_mk=mk,to_mk=mk+1,old_quote=old,new_quote=new,old_cumulative=totals['old'],new_cumulative=totals['new'],old_capital_floor=c.common_card_price(definition)*mk**1.7,new_capital_floor=capital,horizon_seconds=u.upgrade_payback_seconds(mk+1),smooth_candidate_seconds=smooth_horizon,smooth_candidate_quote=smooth_quote,smooth_cumulative=smooth_total,base_net_second=net,marginal_capacity=.25,single_card_value_delta_second=.25*net,isolated_payback_seconds=new/(.25*net),isolated_daily_roi=.25*net*86400/new,valuation_scope='maximum direct C2 added value minus coal equivalent; energy is an indirect capacity proxy; freight assumes one-dollar cargo; whole-company realized returns are separate'))
    finally:u.BASE_MARKET_PRICES=oldprices
    return price,tables,rows

def run():
    price,t,rows=tables();write('mk-quotes.csv',rows);c.extend_curves();chain=[]
    samples=('iron_ore','iron','copper','flour','lumber','steel','bitumen','silicon','biodiesel','industrial_equipment','microchip','ai_server')
    for r in samples:
        counts=c.counts_for(c.N1,r)
        previous={}
        for mk in range(1,100):
            opts=[fund_buffer(p) for p in c.structure('N1',r,counts,mk)]
            for key in ('old','new'):
                p=c.choose(opts,t[key]);cash=c.income(p,price)
                if mk>1:
                    before,bcash=previous[key];delta=p['cost']-before['cost'];gain=cash-bcash
                    chain.append(dict(product_id=r,curve=key,from_mk=mk-1,to_mk=mk,capital_before=before['cost'],capital_after=p['cost'],incremental_capital=delta,cash_before_min=bcash,cash_after_min=cash,additional_cash_min=gain,payback_minutes=delta/gain,daily_roi=gain*1440/delta,factory_cards=p['factory_cards'],primary_cards=p['primary_cards'],power_mw=p['power'],storage_cost=p['storage_cost'],freight=json.dumps(p['freight_groups']),scope='whole fully supplied firm; all cards including energy/freight paid at uniform MK; discrete infrastructure and storage included'))
                previous[key]=p,cash
        print(r,chain[-1]['payback_minutes']/60,flush=True)
    write('mk-chain-payback.csv',chain)
    print('quotes',len(rows),'chains',len(chain),flush=True)

if __name__=='__main__':run()
