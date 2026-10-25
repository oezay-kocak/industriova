import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from pathlib import Path
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.commands import PurchaseHall, PurchaseProductionUnit, UnlockProductionLine, UnlockProductionSlot, CommandBus
from production_zero.core.infrastructure_prices import facility_price
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore

@pytest.mark.parametrize('generic', [False, True])
def test_unlimited_purchase_roundtrip_and_local_limits(generic,tmp_path):
    s=deserialize_game_state(serialize_game_state(GameState(11)));s.cash.amount=1e15
    legacy=FactoryHall('old','Old',3,max_lines=6)
    s.halls['old']=legacy
    for n in range(1,25):
        before=s.cash.amount
        cmd=PurchaseProductionUnit('factory','Hall','hall',5,10,1,3) if generic else PurchaseHall()
        cmd.apply(s)
        assert before-s.cash.amount==facility_price('factory',n)
        h=next(reversed(s.halls.values()))
        assert (h.max_lines,h.max_slots_per_line)==(5,10)
        for line in h.production_lines:
            if not line.unlocked:UnlockProductionLine(h.hall_id,line.line_id,'factory').apply(s)
            while len(line.slot_indexes)<10:UnlockProductionSlot(h.hall_id,line.line_id,'factory').apply(s)
        assert len(h.unlocked_slot_indexes())==50
        with pytest.raises(ValueError):UnlockProductionSlot(h.hall_id,line.line_id,'factory').apply(s)
    assert sum(len(h.unlocked_slot_indexes()) for h in s.halls.values())>500
    payload=serialize_game_state(s)
    restored=deserialize_game_state(payload)
    assert serialize_game_state(restored)==payload
    assert restored.halls['old'].max_lines==6
    store=SQLiteSaveStore(tmp_path/'company.sqlite')
    store.initialize()
    store.save('company',s)
    assert serialize_game_state(store.load('company'))==payload
    from production_zero.core.commands import InstallCardInHall
    from production_zero.core.cards import create_card_instance
    from production_zero.core.enums import CardKind, Rarity
    targets=[(h.hall_id,i) for h in s.halls.values() if h.hall_id!='old' for i in h.unlocked_slot_indexes()]
    for number,(hid,index) in enumerate(targets[:501]):
        cid=f'installed-{number}'
        s.cards[cid]=create_card_instance(cid,'machine.processor',CardKind.MACHINE,Rarity.COMMON)
        InstallCardInHall(hid,index,cid,'factory').apply(s)
    assert len(s.installed_card_ids())==501

def test_curve_and_insufficient_cash_are_atomic():
    assert [facility_price('factory',n) for n in range(3)]==[1000,15200,86000]
    assert all(facility_price('factory',n+1)>facility_price('factory',n) for n in range(1,1000))
    s=GameState(1);before=serialize_game_state(s)
    with pytest.raises(ValueError):PurchaseHall().apply(s)
    assert serialize_game_state(s)==before
    for n in (10**124,10**1000):
        with pytest.raises(ValueError):facility_price('factory',n)

def test_many_halls_ui_retains_navigation_items():
    from PySide6.QtWidgets import QApplication
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.data.definitions import load_card_definitions
    app=QApplication.instance() or QApplication([])
    s=GameState(2)
    s.halls={f'h-{n}':FactoryHall(f'h-{n}',f'Hall {n}',3,max_lines=5,start_unlocked_lines=1) for n in range(1000)}
    view=FactoryViewV2(s,CommandBus(s),load_card_definitions(Path('src/production_zero/data/game_definitions.json')))
    view._timer.stop()
    first=view._hall_tree.topLevelItem(0)
    view._refresh_hall_tree()
    assert view._hall_tree.topLevelItemCount()==1000
    assert view._hall_tree.topLevelItem(0) is first
    view.close();view.deleteLater();app.processEvents()
