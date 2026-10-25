"""P7 displayed quotes commit exactly once through the existing real views."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QLabel, QComboBox, QWidget
from PySide6.QtTest import QTest
from test_ui_interaction_recovery import app, window, board
from production_zero.core.commands import PurchaseProductionUnit, BuildFreightFacility
from production_zero.core.infrastructure_prices import production_facility_price, unit_line_price
from production_zero.core.freight import FreightFacility
from production_zero.persistence.sqlite_store import serialize_game_state
from production_zero.ui.factory_view_v2 import FactoryV2LockedSlot, FactoryV2LockedLine
from production_zero.ui.freight_view import FreightView
from production_zero.ui.game_ui import GameButton


@pytest.mark.parametrize('name',['Factory','Resources','Energy'])
@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_displayed_slot_and_line_quote_matches_actual_debit(window,name,size):
    window.resize(*size);b=board(window,name);s=b._state;s.cash.amount=1e9;b.refresh_view()
    u=b._units[b._selected_hall_id]
    assert sum(l.unlocked for l in u.production_lines)==1
    slot=next(w for w in b.findChildren(FactoryV2LockedSlot) if w.isVisible() and w.property('slotNumber')==u.start_slots_per_line+1)
    price=slot.property('unlockCost');cash=s.cash.amount
    QTest.mouseClick(slot,Qt.MouseButton.LeftButton);QTest.qWait(10)
    assert cash-s.cash.amount==price
    # The next line remains available while the preceding line is incomplete.
    line=next(w for w in b.findChildren(FactoryV2LockedLine) if w.isVisible())
    price=line.property('unlockCost');cash=s.cash.amount
    assert price==unit_line_price(u,2)
    QTest.mouseClick(line._unlock_button,Qt.MouseButton.LeftButton);QTest.qWait(10)
    assert cash-s.cash.amount==price and u.production_lines[1].unlocked


@pytest.mark.parametrize('name',['Factory','Energy'])
def test_build_button_quote_and_stale_rejection(window,name):
    b=board(window,name);s=b._state;s.cash.amount=1e9;b.refresh_view()
    price=b._build_hall_button.property('quotedCost');cash=s.cash.amount
    b._purchase_hall()
    assert cash-s.cash.amount==price==next(reversed(b._units.values())).building_investment
    # A concurrent purchase invalidates the quote still shown on this view.
    maximum,cap,start=(5,10,3) if name=='Factory' else (3,5,1)
    PurchaseProductionUnit(b._board_config.board_kind,name,'concurrent',maximum,cap,1,start).apply(s)
    before=serialize_game_state(s)
    with pytest.raises(ValueError,match='price changed'):b._purchase_hall()
    assert serialize_game_state(s)==before


@pytest.mark.parametrize('target',['machine.extractor','machine.agriculture','machine.drilling'])
@pytest.mark.parametrize('decision',['buy','cancel','stale'])
def test_resource_type_is_selected_before_final_quote(window,monkeypatch,target,decision):
    from production_zero.ui.interaction_polish import BuildingChoiceDialog
    b=board(window,'Resources');s=b._state;s.cash.amount=1e9
    expected=production_facility_price(s,'resources',target);cash=s.cash.amount;count=len(b._units);notices=[]
    monkeypatch.setattr('production_zero.ui.release_board.inform',lambda *a:notices.append(a))
    def choose(dialog):
        assert target in dialog.options
        dialog.options[target].click()
        assert dialog.accept_button.text()==f'BUY · ${expected:,.2f}'
        if decision=='stale':
            PurchaseProductionUnit('resources','Site','concurrent',3,10,1,1,target).apply(s)
        return decision!='cancel'
    monkeypatch.setattr(BuildingChoiceDialog,'exec',choose)
    b._purchase_hall()
    if decision=='buy':
        assert len(b._units)==count+1 and cash-s.cash.amount==expected
        assert b._units[b._selected_hall_id].specialization==target
    elif decision=='cancel':assert len(b._units)==count and s.cash.amount==cash
    else:
        assert len(b._units)==count+1 and cash-s.cash.amount==expected and notices


@pytest.mark.parametrize('stale',[False,True])
def test_rename_shows_paid_type_change_quote(window,monkeypatch,stale):
    b=board(window,'Resources');s=b._state;s.cash.amount=1e9;unit=b._units[b._selected_hall_id]
    cash=s.cash.amount;notices=[]
    monkeypatch.setattr('production_zero.ui.release_board.inform',lambda *a:notices.append(a))
    def rename(parent,current,apply):
        if stale:
            from copy import deepcopy
            b._units[unit.hall_id]=deepcopy(unit)
        apply('Named estate')
    monkeypatch.setattr('production_zero.ui.interaction_polish.rename_building',rename)
    b._rename_building()
    assert unit.specialization=='machine.extractor' and s.cash.amount==cash
    if stale:assert unit.name!='Named estate' and notices
    else:assert unit.name=='Named estate' and not notices


@pytest.mark.parametrize('kind',['garage_depot','rail_station','airport','harbor'])
def test_freight_next_line_is_disabled_until_previous_slots_are_complete(window,kind):
    f=window.findChild(FreightView);s=f._state;s.cash.amount=1e9
    u=FreightFacility('p7',kind,kind);s.freight.facilities[u.facility_id]=u;f._selected_facility_id=u.facility_id
    window.findChild(QTabWidget,'mainTabs').setCurrentWidget(f);f.refresh();QTest.qWait(10)
    button=next(w for w in f.findChildren(GameButton,'unlockFreightLineButton') if w.isVisible())
    assert not button.isEnabled() and button.property('slotIndex')==8 and button.property('unlockCost')==900
    before=serialize_game_state(s);QTest.mouseClick(button,Qt.MouseButton.LeftButton)
    assert serialize_game_state(s)==before
    from production_zero.core.commands import ExpandFreightFacility
    for index in range(len(u.slots),8):ExpandFreightFacility(u.facility_id,index).apply(s)
    f.refresh();QTest.qWait(10)
    button=next(w for w in f.findChildren(GameButton,'unlockFreightLineButton') if w.isVisible())
    assert button.isEnabled()
    cash=s.cash.amount;QTest.mouseClick(button,Qt.MouseButton.LeftButton);QTest.qWait(10)
    assert cash-s.cash.amount==900 and set(u.unlocked_slot_indexes())==set(range(9))


@pytest.mark.parametrize('kind,price',[('garage_depot',8000),('rail_station',8000),('airport',30000),('harbor',100000)])
def test_freight_choice_uses_the_confirmed_quote(window,monkeypatch,kind,price):
    from production_zero.ui.interaction_polish import BuildingChoiceDialog
    f=window.findChild(FreightView);s=f._state;s.cash.amount=1e9;cash=s.cash.amount
    def choose(dialog):
        dialog.options[kind].click()
        assert dialog.accept_button.text()==f'BUY · ${price:,.2f}'
        return True
    monkeypatch.setattr(BuildingChoiceDialog,'exec',choose)
    f._build_facility()
    assert cash-s.cash.amount==price


def test_legacy_future_line_cost_uses_current_displayed_price(window):
    b=board(window,'Factory');s=b._state;s.cash.amount=1e9;u=b._units[b._selected_hall_id]
    u.production_lines[1].unlock_cost=750;b.refresh_view()
    line=next(w for w in b.findChildren(FactoryV2LockedLine) if w.isVisible())
    assert line.property('unlockCost')==900 and '$900' in line._unlock_button.text()
    cash=s.cash.amount;line._unlock_button.click()
    assert cash-s.cash.amount==900
