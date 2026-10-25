"""Price the early MK1 fixture and finance its gap with real starter stock."""
import json,os,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(O/'investment-appdata'),APPDATA=str(O/'investment-appdata'))
sys.path.insert(0,str(R/'src'))
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.core.infrastructure_prices import slot_price
from production_zero.core.supply import common_card_price
from production_zero.core.modifiers import market_sale_price
from production_zero.core.freight import FreightAssignment
from production_zero.core.simulation import SimulationEngine
from production_zero.ui.main_window import _create_initial_state
d=load_card_definitions(R/'src/production_zero/data/game_definitions.json')
resources=load_resource_definitions(R/'src/production_zero/data/resource_definitions.json')
s=_create_initial_state(resources,d)
initial_cash=s.cash.amount
initial_goods={rid:stock.amount for rid,stock in s.resources.items() if stock.amount>0}
costs=dict(resources_slots_2_to_4=sum(slot_price('resources',1,i) for i in (2,3,4)),extra_extractor=common_card_price(d['machine.extractor']),energy_slot_2=slot_price('energy',1,2),extra_solar=common_card_price(d['energy.solar_array']),third_truck=common_card_price(d['freight.truck']))
total=sum(costs.values());goods_value=sum(market_sale_price(s,rid)*q for rid,q in initial_goods.items())
garage=next(iter(s.freight.facilities.values()))
trucks=[cid for cid,c in s.cards.items() if c.definition_id=='freight.truck']
for i,(cid,rid) in enumerate(zip(trucks,('iron_ore','copper_ore'))):
    garage.slots[i].card_id=cid;s.freight.assignments[cid]=FreightAssignment(rid,'market')
clock=[1792678460.]
engine=SimulationEngine(d,utc_now=lambda:clock[0])
for elapsed in range(6,301,6):
    clock[0]+=6;engine.advance_time(s,6)
    if s.cash.amount>=total:break
assert s.cash.amount>=total and not s.installed_card_ids()
result=dict(starting_cash=initial_cash,costs=costs,total=total,minimum_prior_cash_earnings=max(0,total-initial_cash),initial_goods=initial_goods,initial_goods_sell_value=goods_value,financing_engine_seconds=elapsed,financing_wallet=s.cash.amount,financing_sell_earnings=s.cash.amount-initial_cash,assumptions='Actual new-game state, only its two owned starter trucks installed in existing free garage slots. Existing iron/copper stock sold through real six-second engine steps. No production, contract completion, cash gift, capital optimization or new-game progression claimed. Target fixture is four MK1 extractors, two solar arrays, three trucks; higher MK scenarios are controlled mature scaling states.')
(O/'early-investment-proof.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
