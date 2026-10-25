"""Real starter assets, purchases, earned lifetime unlocks, actual deliveries."""
from pathlib import Path
import sys,math,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'artifacts/phase11e'))
import common as c
from phase11fg_mk import write
from phase8_offline_work_cache import install
from production_zero.ui.main_window import _create_initial_state
from production_zero.core.commands import BuyCommonSupplyCard,InstallCardInHall,InstallFreightCard,SelectMachineProduction,AssignFreightCard,UnlockProductionSlot,ExpandFreightFacility
from production_zero.core.infrastructure_prices import unit_slot_price
from production_zero.core.freight import freight_facility_expansion_cost
from production_zero.core.simulation import SimulationEngine
from production_zero.core.market import BASE_MARKET_PRICES
install(c.d.D);c.install_offline_catalog_cache();definitions=c.DEFS['N1'];rows=[];events=[]
for chain in (('iron_ore',),('wheat',),('crude_oil',),('iron_ore','iron'),('wheat','flour'),('crude_oil','bitumen'),('iron_ore','iron','iron_components'),('copper_ore','copper','copper_wire')):
    target=chain[-1];s=_create_initial_state(c.d.R,definitions);assert s.cash.amount==1250 and len(s.cards)==8
    spent=0.;clock=[0];active=[];trucks=[];solar=[];newunlocks=set(s.production_progress.unlocked_production_ids);fid=next(iter(s.freight.facilities));plant=s.energy_plants['plant-1'];hall=s.halls['hall-1']
    def buy(did):
        before=set(s.cards);BuyCommonSupplyCard(did,definitions).apply(s);return (set(s.cards)-before).pop()
    raw=chain[0];did=c.N1.recipes[raw]['machine'];site=next(h for h in s.resource_sites.values() if h.specialization==did)
    cid=next((x.card_id for x in s.cards.values() if x.definition_id==did),None)
    if cid is None:cid=buy(did);spent+=c.common_card_price(definitions[did])
    InstallCardInHall(site.hall_id,0,cid,'resources').apply(s);SelectMachineProduction(cid,c.d.P[raw][1].production_id,raw).apply(s);active.append(raw)
    cid=next(x.card_id for x in s.cards.values() if x.definition_id=='energy.solar_array');solar.append(cid);InstallCardInHall(plant.hall_id,0,cid,'energy').apply(s)
    for cid in (x.card_id for x in s.cards.values() if x.definition_id=='freight.truck'):
        InstallFreightCard(fid,len(trucks),cid,definitions).apply(s);AssignFreightCard(cid,raw,'market').apply(s);trucks.append(cid)
    engine=SimulationEngine(definitions,utc_now=lambda:1792756800+clock[0]);last=0;earn=0;first=None;installed={raw:0}
    for second in range(1,14401):
        clock[0]=second;engine.advance_time(s,1)
        if first is None and s.statistics.total_earnings>0:first=second
        if second%6==0:
            if len(active)<len(chain):
                r=chain[len(active)];v=c.N1.recipes[r];did=v['machine'];option=c.d.P[r][1]
                if option.production_id in s.production_progress.unlocked_production_ids:
                    uninstalled=next((x.card_id for x in s.cards.values() if x.definition_id==did and x.card_id not in s.installed_card_ids()),None)
                    needed=math.ceil(sum(c.N1.recipes[x]['power'] for x in (*active,r))/20)
                    extra=sum(c.common_card_price(definitions['energy.solar_array'])+ (unit_slot_price(plant,1,i+1) if i>=len(plant.unlocked_slot_indexes()) else 0) for i in range(len(solar),needed))
                    quote=extra+(0 if uninstalled else c.common_card_price(definitions[did]))
                    if s.cash.amount>=quote:
                        before=s.cash.amount
                        for i in range(len(solar),needed):
                            if i>=len(plant.unlocked_slot_indexes()):UnlockProductionSlot(plant.hall_id,plant.production_lines[0].line_id,'energy').apply(s)
                            cid=buy('energy.solar_array');InstallCardInHall(plant.hall_id,i,cid,'energy').apply(s);solar.append(cid)
                        cid=uninstalled or buy(did);InstallCardInHall(hall.hall_id,len(active)-1,cid,'factory').apply(s);SelectMachineProduction(cid,option.production_id,r).apply(s);active.append(r);installed[r]=second;spent+=before-s.cash.amount
                        for cid in trucks:AssignFreightCard(cid,r,'market').apply(s)
                        events.append(dict(product_id=target,seconds=second,action='earned unlock and funded '+r,spent=before-s.cash.amount,cash=s.cash.amount,company_level=s.company.level))
            current=active[-1];required=math.ceil(c.N1.rate(current)/40)
            if len(trucks)<required:
                i=len(trucks);facility=s.freight.facilities[fid];extra=freight_facility_expansion_cost(facility,slot_index=i) if i>=len(facility.slots) else 0
                quote=extra+c.common_card_price(definitions['freight.truck'])
                if s.cash.amount>=quote:
                    if extra:ExpandFreightFacility(fid,i).apply(s)
                    cid=buy('freight.truck');InstallFreightCard(fid,i,cid,definitions).apply(s);AssignFreightCard(cid,current,'market').apply(s);trucks.append(cid);spent+=quote
        if second in (600,1800,3600,7200,14400):
            assert math.isclose(s.cash.amount,1250+s.statistics.total_earnings-spent,rel_tol=1e-9)
            rows.append(dict(product_id=target,seconds=second,cash=s.cash.amount,earnings=s.statistics.total_earnings,investment=spent,recent_cash_min=(s.statistics.total_earnings-earn)/((second-last)/60),company_level=s.company.level,xp=sum(s.company_xp_progress.xp_by_source.values()),xp_by_source=json.dumps(s.company_xp_progress.xp_by_source),productive_seconds=s.company_xp_progress.productive_event_seconds,installed_stages=json.dumps(active),installed_at=json.dumps(installed),first_sale=first or '',trucks=len(trucks),solar=len(solar),new_unlocks=json.dumps(sorted(s.production_progress.unlocked_production_ids-newunlocks)),research_spent=s.research.spent))
            last=second;earn=s.statistics.total_earnings
    assert active==list(chain),(target,active)
    write('genesis.csv',rows);write('genesis-events.csv',events)
    print('Genesis',target,'cash',s.cash.amount,'first funded final stage',installed[target],flush=True)
