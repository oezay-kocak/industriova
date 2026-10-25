"""Qt window gestures for the requested compact industrial interaction pass."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QTabWidget,QLineEdit,QWidget
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2,FactoryV2BuildSlot,FactoryV2MachineCard,FactoryV2HallStage
from production_zero.ui.factory_view import FactoryCardSelectionTile
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.interaction_polish import BuildingChoiceDialog
from production_zero.ui.game_ui import GameButton,Accent
from production_zero.ui.freight_view import FreightView,FreightFacilityStage
from production_zero.ui.contracts_view import ContractsView,ContractProductTile
from production_zero.core.machine_operations import SITE_TYPES,resale_value
from production_zero.core.commands import BuildFreightFacility,InstallFreightCard
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state

@pytest.fixture(scope='module')
def app():
    a=QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return a

@pytest.fixture
def window(app):
    w=MainWindow(development_mode=False);w.resize(1366,768);w.show();QTest.qWait(60)
    for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
    yield w
    w.close();w.deleteLater();QTest.qWait(20)

def click(w,widget,button=Qt.MouseButton.LeftButton,pos=None,modifiers=Qt.KeyboardModifier.NoModifier):
    QTest.mouseClick(w.windowHandle(),button,modifiers,widget.mapTo(w,pos or widget.rect().center()));QTest.qWait(25)

def board(w,name):
    tabs=w.findChild(QTabWidget,'mainTabs');i=next(i for i in range(tabs.count()) if tabs.tabText(i)==name)
    nav=tabs._navigation_bar;click(w,nav,pos=nav.tabRect(i).center());return tabs.currentWidget()

def install(w,b,index=0):
    click(w,next(x for x in b.findChildren(FactoryV2BuildSlot) if x.isVisible() and x._release_slot_index==index))
    tile=next(x for x in b.findChildren(FactoryCardSelectionTile) if x.isVisible());cid=tile.property('cardId');click(w,tile);return cid

def modal(callback):
    def run():
        d=QApplication.activeModalWidget()
        assert isinstance(d,IndustrialDialog)
        QTimer.singleShot(2500, d, lambda: d.reject() if d.isVisible() else None)
        callback(d)
    QTimer.singleShot(60,run)

def press_dialog(d,widget):
    QTest.mouseClick(d.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,widget.mapTo(d,widget.rect().center()))

def test_dialog_transparent_corners_and_equal_guide_buttons(window):
    d=IndustrialDialog('Maschinen verkaufen','Extractor MK1 · common\nErlös: $72',window);d.show();QTest.qWait(40)
    assert d.accept_button.size()==d.reject_button.size()
    assert d.accept_button.height()==48
    assert d.accept_button.accent==Accent.BUILD and d.reject_button.accent==Accent.DANGER
    assert d.grab().toImage().pixelColor(0,0).alpha()==0
    assert d.message.font().pointSize()>=14
    d.close()

@pytest.mark.parametrize('name',['Resources','Factory','Energy'])
def test_building_pause_resume_updates_cards_and_label(window,name):
    b=board(window,name);cid=install(window,b)
    button=b.findChild(GameButton,'buildingPauseButton')
    assert button.text()=='PAUSE' and button.accent==Accent.DANGER
    click(window,button);assert b._units[b._selected_hall_id].paused and not b._state.cards[cid].paused and button.text()=='RESUME' and button.accent==Accent.BUILD
    click(window,button);assert not b._units[b._selected_hall_id].paused and button.text()=='PAUSE'

def test_selected_card_upgrade_upgrades_group_and_preserves_rarity(window):
    b=board(window,'Factory');one=install(window,b,0);two=install(window,b,1)
    b._state.cash.amount=10000 # isolated reachable-action fixture, not a normal-capital gameplay claim
    cards=[b._slot_widgets[i] for i in (0,1)]
    click(window,cards[0],pos=QPoint(10,10));click(window,cards[1],pos=QPoint(10,10),modifiers=Qt.KeyboardModifier.ControlModifier)
    before={cid:b._state.cards[cid].rarity for cid in (one,two)}
    modal(lambda d:press_dialog(d,d.accept_button));click(window,cards[0]._upgrade_button)
    assert all(b._state.cards[cid].mk_level==2 for cid in (one,two))
    assert all(b._state.cards[cid].rarity==before[cid] for cid in (one,two))
    assert b._state.cash.amount<10000

@pytest.mark.parametrize('name',['Resources','Factory','Energy','Freight'])
def test_pencil_renames_header_and_state(window,name):
    b=board(window,name)
    stage=b.findChild(FreightFacilityStage) if name=='Freight' else b.findChild(FactoryV2HallStage)
    def rename(d):
        field=d.findChild(QLineEdit,'buildingNameInput');field.setText('My Industrial Building');press_dialog(d,d.accept_button)
    modal(rename);click(window,stage._rename_filter.pencil)
    units=b._state.freight.facilities if name=='Freight' else b._units
    assert next(iter(units.values())).name=='My Industrial Building'

@pytest.mark.parametrize('kind',list(SITE_TYPES))
def test_build_site_choice_has_no_preselection_and_installs_requested_type(window,kind):
    b=board(window,'Resources');b._state.cash.amount=10000;before=len(b._units)
    def choose(d):
        assert isinstance(d,BuildingChoiceDialog) and d.selected_type is None and not d.accept_button.isEnabled()
        press_dialog(d,d.options[kind]);assert d.accept_button.isEnabled();press_dialog(d,d.accept_button)
    modal(choose);click(window,b._build_hall_button)
    assert len(b._units)==before+1 and b._units[b._selected_hall_id].specialization==kind

@pytest.mark.parametrize('kind',['garage_depot','rail_station','airport','harbor'])
def test_build_freight_modal_preserves_selected_facility_type(window,kind):
    b=board(window,'Freight');b._state.cash.amount=1000000
    def choose(d):
        assert d.selected_type is None
        press_dialog(d,d.options[kind]);press_dialog(d,d.accept_button)
    modal(choose);click(window,b.findChild(QWidget,'buildFreightFacilityButton'))
    assert b._state.freight.facilities[b._selected_facility_id].facility_type==kind
    assert b._state.cash.amount<1000000

def test_build_dialog_cancel_has_no_state_mutation(window):
    b=board(window,'Resources');before=serialize_game_state(b._state)
    modal(lambda d:press_dialog(d,d.reject_button));click(window,b._build_hall_button)
    assert serialize_game_state(b._state)==before

def test_machine_sale_from_card_context_is_confirmed_and_pays_once(window):
    b=board(window,'Factory');cid=install(window,b);cash=b._state.cash.amount
    value=resale_value(b._state.cards[cid],b._definitions[b._state.cards[cid].definition_id])
    def menu(d):
        sale=next(x for x in d.findChildren(GameButton,'machineContextAction') if x.text()=='Sell')
        modal(lambda confirmation:press_dialog(confirmation,confirmation.accept_button));press_dialog(d,sale)
    modal(menu);click(window,b._slot_widgets[0],button=Qt.MouseButton.RightButton)
    assert cid not in b._state.cards and b._state.cash.amount==cash+value

def test_building_sale_by_right_click_includes_its_machines(window):
    b=board(window,'Factory');b._state.cash.amount=20000;b.refresh_runtime();click(window,b._build_hall_button)
    uid=b._selected_hall_id;cid=install(window,b);cash=b._state.cash.amount
    value=b._units[uid].building_investment*.6+resale_value(b._state.cards[cid],b._definitions[b._state.cards[cid].definition_id])
    item=next(b._hall_tree.topLevelItem(i) for i in range(b._hall_tree.topLevelItemCount()) if b._hall_tree.topLevelItem(i).data(0,Qt.ItemDataRole.UserRole)==uid)
    def approve(d):
        assert '1 included machines' in d.message.text();press_dialog(d,d.accept_button)
    modal(approve);click(window,b._hall_tree.viewport(),button=Qt.MouseButton.RightButton,pos=b._hall_tree.visualItemRect(item).center())
    assert uid not in b._units and cid not in b._state.cards
    assert b._state.cash.amount==pytest.approx(cash+value)
    loaded=deserialize_game_state(serialize_game_state(b._state));assert uid not in loaded.halls and cid not in loaded.cards

def test_contract_starts_empty_accept_requires_explicit_distinct_products(window):
    b=board(window,'Contracts');assert not b._state.contracts.active
    offer=b._state.contracts.offers['regular'][0]
    from production_zero.ui.contract_product import ContractProductButton
    controls=b._selection_controls[('regular',offer.contract_id)]
    assert not controls['accept'].isEnabled()
    for i in range(2):
        click(window,controls['buttons'][i]);tile=next(x for x in b.findChildren(ContractProductTile) if x.isVisible() and x.isEnabled());click(window,tile)
    assert controls['accept'].isEnabled()
    click(window,controls['accept'])
    active=b._state.contracts.active['regular'];assert len(active.offer.requirements)==2
    req=dict(active.offer.requirements);b.refresh();assert active.offer.requirements==req

def test_resources_main_action_opens_closes_same_overlay(window):
    action=window.findChild(GameButton,'globalResourcesButton')
    assert action.accent==Accent.STORAGE and action.variant=='primary'
    click(window,action);overlay=window._global_resources
    assert overlay.isVisible()
    click(window,action);assert not overlay.isVisible()
    click(window,action);assert window._global_resources is overlay and overlay.isVisible()
    overlay.hide()

def test_freight_header_pause_preserves_route_and_identity(window):
    b=board(window,'Freight');cid='starter-truck-common-001'
    b._command_bus.dispatch(InstallFreightCard('garage-1',0,cid,b._definitions));b.refresh();QTest.qWait(30)
    button=next(x for x in b.findChildren(GameButton,'buildingPauseButton') if x.isVisible());click(window,button)
    assert b._state.freight.facilities[b._selected_facility_id].paused and not b._state.cards[cid].paused and button.text()=='RESUME'
    click(window,button);assert not b._state.cards[cid].paused

def test_occupied_freight_building_sale_rejects_active_delivery_atomically(window):
    from production_zero.core.commands import SellFreightBuilding
    from production_zero.core.freight import OutboundFreightShipment
    b=board(window,'Freight');b._state.cash.amount=10000
    b._command_bus.dispatch(BuildFreightFacility('garage_depot'))
    uid=next(reversed(b._state.freight.facilities));cid='starter-truck-common-001'
    b._command_bus.dispatch(InstallFreightCard(uid,0,cid,b._definitions))
    b._state.freight.outbound_shipments['busy']=OutboundFreightShipment('busy','market',None,'iron',20,freight_card_id=cid,remaining_seconds=30)
    before=serialize_game_state(b._state)
    with pytest.raises(ValueError,match='transit'):
        b._command_bus.dispatch(SellFreightBuilding(uid,b._definitions,True))
    assert serialize_game_state(b._state)==before

def test_last_building_sale_rejected_before_its_machines_removed(window):
    from production_zero.core.commands import SellProductionBuilding
    b=board(window,'Factory');install(window,b)
    before=serialize_game_state(b._state)
    with pytest.raises(ValueError,match='Keep one'):
        b._command_bus.dispatch(SellProductionBuilding('factory','hall-1',b._definitions,True))
    assert serialize_game_state(b._state)==before

@pytest.mark.parametrize('name',['Resources','Factory','Energy','Freight'])
def test_left_building_list_name_click_only_navigates(window,name):
    b=board(window,name);tree=b._facility_tree if name=='Freight' else b._hall_tree
    item=tree.topLevelItem(0);rect=tree.visualItemRect(item)
    units=b._state.freight.facilities if name=='Freight' else b._units
    before=next(iter(units.values())).name
    click(window,tree.viewport(),pos=QPoint(rect.left()+30,rect.top()+14))
    assert next(iter(units.values())).name==before
    assert QApplication.activeModalWidget() is None

def test_empty_resource_site_type_remains_editable_from_name_dialog(window):
    from PySide6.QtWidgets import QComboBox
    b=board(window,'Resources');unit=b._units['site-1'];specialization=unit.specialization
    def change(d):
        assert d.findChild(QComboBox,'resourceSiteType') is None
        d.findChild(QLineEdit,'buildingNameInput').setText('My mine')
        press_dialog(d,d.accept_button)
    modal(change);click(window,b.findChild(FactoryV2HallStage)._rename_filter.pencil)
    assert unit.specialization==specialization and unit.name=='My mine'
