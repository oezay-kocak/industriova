"""Exact approved catalog, all MK quality/research states, fuel and new quotes."""
from pathlib import Path
import sys,json,math,csv
from fractions import Fraction
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'artifacts/phase11e'))
import common as c
import validate as v
from phase11fg_mk import tables,write,fund_buffer
from production_zero.core import market
from production_zero.core.definitions import MachineDefinition,EnergyDefinition,FreightDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.freight import freight_stats
from production_zero.core.research import research_catalog,ResearchState
from production_zero.core.modifiers import research_multiplier,market_sale_price,contract_cash_quote
from production_zero.core.contracts import refresh_contracts,contract_requirements_for_products,contract_reward_quote,CONTRACT_REQUIREMENT_COUNTS
from production_zero.core.consortium import ConsortiumService,CONSORTIUM_DAILY,CONSORTIUM_WEEKLY
OUT=ROOT/'artifacts/phase11fg';c.extend_curves();c.install_offline_catalog_cache();price,up,_=tables();definitions=c.DEFS['N1']
reference=list(csv.DictReader((ROOT/'docs/industriova-03-phase11e-price-comparison.csv').open(encoding='utf-8-sig')))
rows=[]
for row in reference:
    r=row['product_id'];actual=market.BASE_MARKET_PRICES[r];expected=float(row['recommended_N1_C2'])
    assert math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12)
    rows.append(dict(product_id=r,reference=expected,productive_price=actual,absolute_error=abs(actual-expected)))
write('price-verification.csv',rows)
full=ResearchState(total_earned=len(research_catalog()[1]),unlocked_node_ids=set(research_catalog()[1]));sensitivity=[];fuel=[]
for did,d in definitions.items():
    for rarity,bonus in ((Rarity.COMMON,0),(Rarity.UNCOMMON,50),(Rarity.RARE,100),(Rarity.EPIC,150),(Rarity.LEGENDARY,200)):
        for research in (None,full):
            for mk in range(1,100):
                card=replace(create_card_instance('sensitivity',did,d.card_kind,rarity,bonus_tenths=bonus),mk_level=mk)
                quote=c.upgrades.mk_upgrade_cost(card,d) if mk<99 else ''
                if quote!='':assert quote==c.upgrades.mk_upgrade_cost(replace(card,rarity=Rarity.COMMON,output_bonus_percent=0),d)
                amount=power=inputs=fuelrate=travel=0.
                if isinstance(d,MachineDefinition):
                    o=d.production_option(d.default_production_id_for_card_definition(did));speed=research_multiplier(research,'production_speed')
                    amount=o.output_amount_for(d)*card.output_multiplier*60/o.cycle_seconds_for(d)*speed
                    inputs=sum(o.input_resources.values())*card.mk_multiplier*60/o.cycle_seconds_for(d)*speed
                    power=o.power_draw_for(d)*card.power_multiplier
                elif isinstance(d,EnergyDefinition):
                    power=d.base_power_output*card.output_multiplier*research_multiplier(research,'energy_output')
                    fuelrate=d.fuel_consumption_per_minute*card.mk_multiplier
                elif isinstance(d,FreightDefinition):
                    stats=freight_stats(card,d,research);amount=stats.capacity*60/stats.transport_time_seconds;travel=stats.transport_time_seconds
                sensitivity.append(dict(family=did,mk=mk,rarity=rarity.value,bonus_percent=bonus/10,research='all 645 nodes; earned mechanical state' if research else 'none',new_next_quote=quote,cumulative_upgrade=up['new'][did,mk],output_or_transport_min=amount,input_min=inputs,power_mw=power,fuel_min=fuelrate,travel_seconds=travel,scope='mechanical sensitivity; no free research or rarity acquisition assumed'))
    if isinstance(d,EnergyDefinition) and d.requires_fuel:
        old=c.DEFS['N0'][did]
        assert math.isclose(d.fuel_consumption_per_minute,old.fuel_consumption_per_minute)
        fuel.append(dict(family=did,resource=d.fuel_resource_id,old_units_min=old.fuel_consumption_per_minute,new_units_min=d.fuel_consumption_per_minute,c2_unit_price=price[d.fuel_resource_id],opportunity_value_min=d.fuel_consumption_per_minute*price[d.fuel_resource_id],power_mw=d.base_power_output))
write('mk-rarity-research.csv',sensitivity);write('fuel-verification.csv',fuel)
research_rows=[]
for r in c.IDS:
    for rs in (None,full):
        from production_zero.core.state import GameState
        s=GameState(1)
        if rs:s.research=rs
        value=market_sale_price(s,r);contract=contract_cash_quote(s,{r:1})
        research_rows.append(dict(product_id=r,research='all' if rs else 'none',base_price=price[r],market_sale=value,regular_unit_quote=contract,speed=research_multiplier(s.research,'production_speed'),energy=research_multiplier(s.research,'energy_output'),freight=research_multiplier(s.research,'freight_capacity'),storage=research_multiplier(s.research,'storage_capacity')))
write('price-research-consumers.csv',research_rows)
contracts=[];consortiums=[]
for r in ('flour','steel','biodiesel','industrial_equipment','microchip','ai_server'):
    p=c.choose([fund_buffer(p) for p in c.structure('N1',r,c.counts_for(c.N1,r),1)],up['new']);s,_=v.state(p,definitions,max(1000000,p['cost']*2),25)
    refresh_contracts(s,definitions,now_utc=1792756800)
    for kind,offers in s.contracts.offers.items():
        offer=offers[0]
        assert all(math.isclose(value,price[x]) for x,value in offer.unit_prices.items())
        available=sorted(set(offer.capacity_rates)&set(p['counts']));count=CONTRACT_REQUIREMENT_COUNTS[kind]
        if len(available)<count:continue
        chosen=tuple(available[:count]);requirements=contract_requirements_for_products(s,offer,definitions,chosen);cash,xp=contract_reward_quote(s,offer,definitions,requirements)
        value=sum(price[x]*n for x,n in requirements.items());expected=value*(1+{'regular':0,'daily':.2,'weekly':.4}[kind]);assert abs(cash-expected)<=.0051
        contracts.append(dict(company_product=r,kind=kind,requirements=json.dumps(requirements),market_value=value,quoted_cash=cash,quoted_xp=xp,category_ratio=cash/value,scope='actual offer and capacity resolver; new C2 quotes; not counted as earned company cash'))
    service=ConsortiumService(s,definitions,clock=lambda:1792756800);group=service.create('Economy quote test')
    for kind in (CONSORTIUM_DAILY,CONSORTIUM_WEEKLY):
        candidates=service.contract_candidates(group.consortium_id,kind);count=3 if kind==CONSORTIUM_DAILY else 4
        if len(candidates)<count:continue
        selected=tuple(candidates[:count]);requirements=service.preview_contract(group.consortium_id,kind,selected);reward,xp=service.preview_contract_rewards(group.consortium_id,kind)
        value=sum(price[x]*n for x,n in requirements.items());assert abs(reward.cash-value*(1.15 if kind==CONSORTIUM_DAILY else 1.25))<=.0051
        frozen=service.start_contract(group.consortium_id,service.current_company_id,kind,selected)
        assert frozen.personal_reward==reward
        consortiums.append(dict(company_product=r,kind=kind,requirements=json.dumps(requirements),market_value=value,pool_cash=reward.cash,company_xp=reward.company_xp,consortium_xp=xp,scope='one-member actual preview/start snapshot; pool is not full cash per contributing member'))
write('contract-quotes.csv',contracts);write('consortium-quotes.csv',consortiums)
proof=dict(prices=353,max_price_error=max(r['absolute_error'] for r in rows),quality_research_states=len(sensitivity),price_consumer_states=len(research_rows),fuel=fuel,personal_quotes=len(contracts),consortium_quotes=len(consortiums))
(OUT/'audit-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof,indent=2),flush=True)
