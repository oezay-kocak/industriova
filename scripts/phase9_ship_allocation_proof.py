"""Exact requested 10,000-cargo / 6,000-needed example through real Freight."""
from pathlib import Path
import sys,os,json
from dataclasses import replace
root=Path.cwd();out=root/'artifacts/phase9';os.environ.update(LOCALAPPDATA=str(out/'ship-proof-appdata'),APPDATA=str(out/'ship-proof-appdata'));sys.path[:0]=[str(root),str(root/'src'),str(root/'tests')]
from test_phase9_freight_only import scenario,D
from consortium_freight_fixture import freight_contribute
from contract_capacity_fixture import remote_stock
from production_zero.core.commands import CommandBus,BuildFreightFacility,BuyCommonSupplyCard,InstallFreightCard,AssignFreightVehicles
from production_zero.core.simulation import SimulationEngine
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
s,api,guild,c,clock=scenario(10000);s.cash.amount=1e6;s.ensure_resource('iron_ore').amount=10000
bus=CommandBus(s);bus.dispatch(BuildFreightFacility('harbor'));harbor=next(f for f in s.freight.facilities.values() if f.facility_type=='harbor')
old=set(s.cards);bus.dispatch(BuyCommonSupplyCard('freight.ship',D));cid=next(iter(set(s.cards)-old));bus.dispatch(InstallFreightCard(harbor.facility_id,0,cid,D));bus.dispatch(AssignFreightVehicles((cid,),'iron_ore','consortium',D))
engine=SimulationEngine(D,utc_now=lambda:clock[0]);engine.advance_time(s,0)
q=next(q for q in s.freight.outbound_shipments.values() if q.freight_card_id==cid)
assert q.quantity==10000 and s.resources['iron_ore'].amount==0 and not c.delivered
freight_contribute(api,guild.consortium_id,'member-1','daily','iron_ore',4000,company_state=remote_stock('member-1','iron_ore',4000))
assert c.remaining('iron_ore')==6000
before_cash=s.cash.amount;engine.advance_time(s,q.remaining_seconds)
r=s.freight.delivery_statistics.rate(card_id=cid);factor=r.observing_seconds/60
allocation=dict(consortium=r.consortium*factor,sell=r.sell*factor,total=r.total*factor)
assert allocation==dict(consortium=6000,sell=4000,total=10000)
assert s.resources['iron_ore'].amount==0 and s.cash.amount-before_cash==4123
snapshot=serialize_game_state(s);engine._complete_outbound_shipments(s,(q,replace(q,economic_processed=False)))
assert serialize_game_state(s)==snapshot
loaded=deserialize_game_state(snapshot);engine._complete_outbound_shipments(loaded,(replace(q,economic_processed=False),))
assert serialize_game_state(loaded)==snapshot
report=dict(cargo=10000,remaining_at_arrival=6000,accepted_allocation=allocation,stock_after_dispatch=0,stock_after_arrival=0,cash_delta=4123,contract_cash_snapshot=123,sell_cash=4000,duplicate_original_and_cloned_receipt_unchanged=True,save_load_retry_unchanged=True,assumptions='Synthetic funded mature fixture, one Ship bought and installed with existing Commands. Goods are finite owned stock, reserved by actual Engine dispatch. A separate member delivers 4,000 with real truck dispatch/advancement before ship arrival. No personal save. Allocation inferred from the single local completion in the P6 60-second window.')
(out/'ship-allocation-proof.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)
