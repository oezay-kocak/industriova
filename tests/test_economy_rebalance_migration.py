from copy import deepcopy
from dataclasses import replace
import pytest
from test_economy_rebalance_xp import firm, DEFS
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore
from production_zero.core.simulation import SimulationEngine
from production_zero.core.contracts import ContractOffer,ActiveContract
from production_zero.core.consortium import Consortium,ConsortiumContract,ConsortiumPersonalReward
from production_zero.core.freight import OutboundFreightShipment
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.core.state import FactoryHall

def legacy():
    s=firm();s.cash.amount=123456.78;s.machine_production['p'].progress_seconds=5
    s.cards['p']=replace(s.cards['p'],mk_level=75,upgrade_investment=9888)
    s.cards['e']=replace(s.cards['e'],mk_level=75)
    s.resource_sites['site-1']=FactoryHall('site-1','Resources',1,board_kind='resources',specialization='machine.extractor',max_lines=3,start_unlocked_lines=1,start_slots_per_line=1)
    quote=ContractOffer('frozen','regular','Old',{'flour':100},888,77,1,unit_prices={'flour':1.625},unit_cash={'flour':2.2},balance_version=1)
    s.contracts.active['regular']=ActiveContract(quote,{'flour':12})
    consortium=Consortium('c','Test')
    consortium.contracts['daily']=ConsortiumContract('goal','daily','active',1,9999999999,{'flour':100},ConsortiumPersonalReward(cash=777),55,unit_prices={'flour':1.625},member_unit_prices={'company.local':{'flour':1.9}})
    s.consortium.consortiums['c']=consortium
    s.freight.outbound_shipments['old']=OutboundFreightShipment('old','market',resource_id='flour',quantity=10,market_price=1.625,remaining_seconds=2)
    p=serialize_game_state(s);p.pop('economy_version');p['market']['resources']['flour']['current_price']=1.625
    return p

def test_migration_preserves_assets_batches_and_all_frozen_commitments():
    old=legacy();new=serialize_game_state(deserialize_game_state(old))
    for key in ('cash','resources','cards','halls','resource_sites','energy_plants','research','company','statistics','machine_production','inventory_storage_level','warehouse_capacity'):
        assert new[key]==old[key],key
    assert new['freight']['outbound_shipments']==old['freight']['outbound_shipments']
    assert new['contracts']['active']==old['contracts']['active']
    assert new['consortium']['consortiums']['c']['contracts']==old['consortium']['consortiums']['c']['contracts']
    assert new['economy_version']==2
    assert new['market']['resources']['flour']['current_price']==BASE_MARKET_PRICES['flour']
    assert serialize_game_state(deserialize_game_state(new))==new

def test_converted_partial_batch_debits_n1_inputs_once_and_old_freight_settles_once():
    p=legacy();s=deserialize_game_state(p)
    before=s.ensure_resource('wheat').amount;factor=s.cards['p'].mk_multiplier
    engine=SimulationEngine(DEFS,utc_now=lambda:1792756800)
    t=engine.advance_time(s,1)
    assert t.outputs['flour']==12*factor
    assert s.ensure_resource('wheat').amount==before-12*factor
    assert s.cash.amount==p['cash']['amount']
    engine.advance_time(s,1)
    assert s.cash.amount==pytest.approx(p['cash']['amount']+16.25)
    engine.advance_time(s,1)
    assert s.cash.amount==pytest.approx(p['cash']['amount']+16.25)

def test_sqlite_copied_save_gets_pre_economy_backup(tmp_path):
    import sqlite3,json
    path=tmp_path/'copy.sqlite';store=SQLiteSaveStore(path);store.initialize()
    with sqlite3.connect(path) as db:db.execute('INSERT INTO saves VALUES (?,?)',('company',json.dumps(legacy())))
    before=path.read_bytes();s=store.load('company')
    assert s.economy_version==2
    assert path.read_bytes()==before
    assert (tmp_path/'copy.pre-economy-n1-c2.sqlite').exists()
    store.save('company',s)
    assert serialize_game_state(store.load('company'))==serialize_game_state(s)

def test_future_economic_version_is_rejected():
    p=legacy();p['economy_version']=999
    with pytest.raises(ValueError,match='newer economic'):deserialize_game_state(p)

def test_old_small_batch_waits_without_losing_or_inventing_inputs():
    p=legacy();p['cards']['p']['mk_level']=1;p['resources']['wheat']['amount']=2
    s=deserialize_game_state(p);engine=SimulationEngine(DEFS,utc_now=lambda:1792756800)
    before=s.company_xp_progress.productive_event_seconds
    t=engine.advance_time(s,100)
    assert not t.outputs and s.ensure_resource('wheat').amount==2
    assert s.machine_production['p'].progress_seconds==5
    assert s.machine_production['p'].status=='missing_input'
    assert s.company_xp_progress.productive_event_seconds==before
    s.ensure_resource('wheat').amount+=10
    t=engine.advance_time(s,1)
    assert t.outputs=={'flour':12}
    assert s.ensure_resource('wheat').amount==0
    assert s.machine_production['p'].progress_seconds==0
