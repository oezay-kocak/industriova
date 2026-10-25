"""Reviewed test expectation changes: C2 quotes and isolated test-save profile."""
from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1];changes=[]
path=root/'tests/test_freight.py';source=path.read_text(encoding='utf-8')
parts=re.split(r'(?=^def test_)',source,flags=re.M)
for i,part in enumerate(parts):
    old=part
    # These assertions settle 40 Iron at the approved $4 (formerly $3.75).
    if any(name in part.split('\n',1)[0] for name in ('test_truck_market_delivery_autoroutes','test_market_delivery_without_contract','test_partial_contract_market_delivery','test_full_contract_market_delivery','test_market_delivery_routes_across','test_market_delivery_completes_contracts','test_train_market_delivery')):
        part=part.replace('== 3.75','== 4.0').replace('== 150','== 160').replace('before + 150','before + 160')
    # Coal is now the same $1 Primary basis as all other raw resources.
    if any(name in part.split('\n',1)[0] for name in ('test_auto_sell_uses_freight_and_waits','test_auto_sell_dispatches_same','test_auto_sell_shipment_progresses')):
        part=part.replace('state.cash.amount == 48','state.cash.amount == 40').replace('state.statistics.total_earnings == 48','state.statistics.total_earnings == 40').replace('state.cash.amount == 96','state.cash.amount == 80')
    # Four Steel in a frozen new shipment settle at $6.75, exactly $27.
    if any(name in part.split('\n',1)[0] for name in ('test_market_sell_creates_shipment','test_clearing_freight_route_preserves')):
        part=part.replace('shipment.market_price == 10','shipment.market_price == 6.75').replace('state.cash.amount == 40','state.cash.amount == 27').replace('state.statistics.total_earnings == 40','state.statistics.total_earnings == 27')
    if part!=old:changes.append(dict(path=str(path.relative_to(root)),test=part.split('\n',1)[0],reason='Approved C2 prices; shipment timing, quantities and exactly-once assertions retained'))
    parts[i]=part
path.write_text(''.join(parts),encoding='utf-8')
for name in ('test_dev_save_store.py','test_final_micro_polish.py','test_industriova_save_reset.py'):
    path=root/'tests'/name;old=path.read_text(encoding='utf-8');new=old.replace('playtests/dev6/saves','playtests/economy-rebalance-test/saves').replace('"playtests" / "dev6"','"playtests" / "economy-rebalance-test"')
    if old!=new:changes.append(dict(path=str(path.relative_to(root)),reason='Separate economy test save directory; original dev6 saves remain excluded'));path.write_text(new,encoding='utf-8')
(root/'artifacts/phase11fg/reviewed-test-expectations.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
print(len(changes),'reviewed expectation groups')
