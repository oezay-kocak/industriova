"""P3 visible purchase, selection, install, route and resale boundaries."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from dataclasses import replace
from importlib.resources import files
import pytest
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLineEdit, QTabWidget
from production_zero.core.commands import CommandBus, BuyCommonSupplyCard, ResetInventoryFreightRoutes, ReturnMachinesToInventory
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.freight import build_freight_facility, FreightAssignment, OutboundFreightShipment
from production_zero.core.supply import common_supply_offers, common_card_price
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.inventory_view import InventoryView, InventoryCardFrame
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.release_dialogs import IndustrialDialog
from test_phase2_inventory_backend import company, install, frozen


@pytest.fixture
def app():
    app = QApplication.instance() or QApplication([])
    yield app
    for w in app.topLevelWidgets():
        w.close(); w.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete); app.processEvents()


@pytest.fixture
def setup(app):
    defs = load_card_definitions(files('production_zero.data')/'game_definitions.json')
    state = company(defs); bus = CommandBus(state)
    inventory = InventoryView(state, defs, command_bus=bus, release_mode=True)
    inventory.resize(1100, 650); inventory.show(); app.processEvents()
    supply = SupplyView(state, bus, defs, inventory.refresh)
    return state, defs, bus, inventory, supply


def answer(app, callback):
    visited = []
    def run():
        dialog = app.activeModalWidget()
        assert isinstance(dialog, IndustrialDialog)
        visited.append(dialog.message.text())
        callback(dialog)
    QTimer.singleShot(0, run)
    return visited


def choose(app, inventory, cid):
    row = next(r for r in inventory._workspace_rows if cid in r.card_ids)
    index = inventory._workspace_rows.index(row)
    inventory._workspace_scroll.verticalScrollBar().setValue(index // inventory._workspace_columns * 234)
    inventory._materialize_workspace(); app.processEvents()
    card = next(w for w in inventory._workspace_pool if w.isVisible() and cid in w._inventory_row.card_ids)
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    return row


@pytest.mark.parametrize('quantity', [1, 7])
@pytest.mark.parametrize('condition', ['normal', 'full', 'no-facility'])
def test_visible_common_purchase_goes_to_inventory(app, setup, quantity, condition):
    s, defs, bus, inv, supply = setup
    if condition == 'full':
        bus.dispatch(BuyCommonSupplyCard('machine.processor', defs, 6))
        for index, cid in enumerate(s.cards): install(s, defs, cid, index)
    elif condition == 'no-facility': s.halls.clear()
    supply._type_filter.setCurrentText('Processing'); supply._show_section(1)
    supply.resize(1000, 620); supply.show(); app.processEvents()
    offer = next(o for o in common_supply_offers(defs) if o.definition_id == 'machine.processor')
    card = next(c for c in supply._common_card_pool if c.isVisible() and c._supply_data.offer == offer)
    before = set(s.cards); slots = s.installed_card_ids(); cash = s.cash.amount
    visited = answer(app, lambda d: (d.quantity.setValue(quantity), d.accept_button.click()))
    card._buy_button.click()
    ids = set(s.cards) - before
    assert len(ids) == quantity and s.installed_card_ids() == slots
    assert s.cash.amount == cash - quantity * offer.price_cash and visited
    assert ids <= set(inv._workspace_by_id)
    assert all(s.cards[cid].mk_level == 1 and s.cards[cid].acquisition_cost == offer.price_cash for cid in ids)


@pytest.mark.parametrize('affordable', [0, 1, 12, 10001])
def test_dialog_max_cash_and_single_unit_card_price(setup, affordable):
    s, defs, bus, inv, supply = setup
    offer = common_supply_offers(defs)[0]; s.cash.amount = offer.price_cash * affordable
    dialog = supply._purchase_dialog(offer, 'common'); dialog.max_button.click()
    assert dialog.quantity.value() == min(10000, affordable)
    assert dialog.accept_button.isEnabled() == bool(affordable)
    assert dialog.max_button.isEnabled() == bool(affordable)
    assert f'${offer.price_cash:,.2f}' in dialog.message.text()
    assert f'${min(10000, affordable)*offer.price_cash:,.2f}' in dialog.total.text()
    assert supply._quantity_priced_data(supply._display_data_for_offer(offer), 'common').price_text == supply._display_data_for_offer(offer).price_text


@pytest.mark.parametrize('source', ['machine_daily', 'freight_daily'])
def test_daily_quality_limits_and_repeat_commit_are_atomic(setup, source):
    s, defs, bus, inv, supply = setup
    offer = getattr(s.supply, source + '_offers')[0]
    data=supply._display_data_for_offer(offer);cache_size=len(supply._common_display_cache)
    next_offer=replace(offer,offer_id=offer.offer_id+'-next-period',period_index=offer.period_index+1)
    rebound=supply._display_data_for_offer(next_offer)
    assert rebound.offer==next_offer and rebound.offer_id==next_offer.offer_id and rebound.name==data.name
    assert len(supply._common_display_cache)==cache_size
    supply._display_data_for_offer(offer)
    dialog = supply._purchase_dialog(offer, source)
    assert dialog.quantity is None and offer.rarity.value in dialog.message.text()
    supply._commit_purchase(dialog); before = frozen(s)
    with pytest.raises(ValueError): supply._commit_purchase(dialog)
    assert frozen(s) == before
    card = next(iter(s.cards.values()))
    assert card.rarity == offer.rarity and card.acquisition_cost == offer.price_cash
    assert supply._purchase_problem(offer, source, 1)[0] == 'Purchase Limit Reached'


@pytest.mark.parametrize('case', ['cancel', 'cash', 'price', 'repeat', 'expired'])
def test_purchase_confirmation_boundaries(app, setup, case):
    s, defs, bus, inv, supply = setup
    offer = next(o for o in common_supply_offers(defs) if o.definition_id == 'machine.processor')
    source = 'common'
    if case == 'expired': source = 'machine_daily'; offer = s.supply.machine_daily_offers[0]
    dialog = supply._purchase_dialog(offer, source)
    if case == 'cancel':
        before = frozen(s); answer(app, lambda d: d.reject_button.click()); supply._buy_offer(offer, source)
        assert frozen(s) == before; return
    if case == 'cash': s.cash.amount = 0
    if case == 'price': defs[offer.definition_id] = replace(defs[offer.definition_id], base_power_draw=999)
    if case == 'expired': s.market.elapsed_seconds += 86400
    if case == 'repeat': supply._commit_purchase(dialog)
    before = frozen(s)
    with pytest.raises((ValueError, KeyError)): supply._commit_purchase(dialog)
    assert frozen(s) == before


@pytest.mark.parametrize('did', ['machine.extractor', 'machine.processor', 'energy.solar_array', 'freight.truck'])
def test_visible_install_preserves_instance(app, setup, did):
    s, defs, bus, inv, supply = setup
    if did == 'freight.truck': build_freight_facility(s.freight, defs[did].facility_id)
    bus.dispatch(BuyCommonSupplyCard(did, defs)); cid = next(iter(s.cards))
    s.cards[cid] = replace(s.cards[cid], mk_level=99, rarity=Rarity.LEGENDARY, acquisition_cost=123.45, upgrade_investment=45)
    card = s.cards[cid]; inv.refresh(); choose(app, inv, cid)
    visited = answer(app, lambda d: (d.findChild(QComboBox, 'inventoryInstallTarget').setCurrentIndex(0), d.accept_button.click()))
    inv._workspace_action(inv._install_workspace_card)
    assert visited and s.cards[cid] is card
    assert cid in s.installed_card_ids() | s.installed_freight_card_ids()
    assert cid not in inv._workspace_by_id
    bus.dispatch(ReturnMachinesToInventory((cid,))); inv.refresh()
    assert cid in inv._workspace_by_id and s.cards[cid] is card


def test_route_can_be_inspected_reset_and_installed(app, setup):
    s, defs, bus, inv, supply = setup
    bus.dispatch(BuyCommonSupplyCard('freight.truck', defs)); cid = next(iter(s.cards))
    s.freight.facilities.clear()
    facility = build_freight_facility(s.freight, defs['freight.truck'].facility_id)
    s.freight.assignments[cid] = FreightAssignment('missing-resource', 'market')
    inv.refresh(); choose(app, inv, cid)
    assert any('INVALID' in c.toolTip() and 'missing-resource' in c.toolTip() for c in inv._workspace_pool if c.isVisible())
    answer(app, lambda d: d.accept_button.click()); inv._workspace_action(inv._reset_workspace_route)
    assert cid not in s.freight.assignments
    answer(app, lambda d: d.accept_button.click()); inv._workspace_action(inv._install_workspace_card)
    assert facility.slots[0].card_id == cid


@pytest.mark.parametrize('invalid', ['busy', 'installed', 'missing', 'mixed', 'duplicate'])
def test_route_reset_rejects_entire_group(setup, invalid):
    s, defs, bus, inv, supply = setup
    bus.dispatch(BuyCommonSupplyCard('freight.truck', defs, 2)); a, b = tuple(s.cards)
    s.freight.assignments[a] = FreightAssignment('iron_ore', 'market')
    ids = (a, b)
    if invalid == 'busy': s.freight.outbound_shipments['busy'] = OutboundFreightShipment('busy', 'market', freight_card_id=b)
    if invalid == 'installed': install(s, defs, b)
    if invalid == 'missing': ids = (a, 'absent')
    if invalid == 'duplicate': ids = (a, a)
    if invalid == 'mixed':
        bus.dispatch(BuyCommonSupplyCard('machine.processor', defs)); ids = (a, next(cid for cid in s.cards if cid not in (a,b)))
    before = frozen(s)
    with pytest.raises(ValueError): bus.dispatch(ResetInventoryFreightRoutes(ids))
    assert frozen(s) == before


@pytest.mark.parametrize('accept', [False, True])
def test_inventory_stack_quantity_sale_and_cancel(app, setup, accept):
    s, defs, bus, inv, supply = setup
    bus.dispatch(BuyCommonSupplyCard('machine.processor', defs, 5)); cid = next(iter(s.cards))
    inv.refresh(); row = choose(app, inv, cid)
    assert len(inv._workspace_ids()) == 1
    inv._workspace_quantity_changed(3); ids = inv._workspace_ids()
    assert len(ids) == 3 and set(ids) <= set(row.card_ids)
    cash = s.cash.amount; before = frozen(s)
    visited = answer(app, lambda d: d.accept_button.click() if accept else d.reject_button.click())
    inv._workspace_action(inv._sell_workspace_cards)
    expected = 3 * int(common_card_price(defs['machine.processor']) * .8 * 100) / 100
    assert visited and '3 selected' in visited[0] and f'${expected:,.2f}' in visited[0]
    if accept:
        assert len(s.cards) == 2 and s.cash.amount == cash + expected
        assert not inv._workspace_ids()
    else: assert frozen(s) == before


@pytest.mark.parametrize('count', [500, 5000, 10000])
def test_distinct_inventory_rows_are_bounded_and_reachable(app, setup, count):
    s, defs, bus, inv, supply = setup
    d = defs['machine.processor']
    for i in range(count):
        s.cards[str(i)] = replace(create_card_instance(str(i), d.definition_id, d.card_kind, Rarity.COMMON), acquisition_cost=float(i))
    inv.refresh(); app.processEvents()
    assert len(inv._workspace_rows) == count
    assert len(inv.findChildren(InventoryCardFrame)) < 100
    assert set(inv._workspace_by_id) == set(s.cards)
    scroll = inv._workspace_scroll.verticalScrollBar(); scroll.setValue(scroll.maximum()); app.processEvents()
    assert any(c.isVisible() and c._inventory_row == inv._workspace_rows[-1] for c in inv._workspace_pool)
    pool = tuple(inv._workspace_pool); position = scroll.value()
    choose(app, inv, inv._workspace_rows[-1].card.card_id); inv.refresh(); app.processEvents()
    assert scroll.value() == position and tuple(inv._workspace_pool) == pool and len(inv._workspace_ids()) == 1
    inv.reset_for_state_change()
    assert not inv._workspace_ids() and inv._workspace_active is None


def test_supply_removed_controls_and_four_basic_categories(setup):
    s, defs, bus, inv, supply = setup
    assert supply.findChild(QLineEdit, 'supplySearch') is None
    assert supply.findChild(QComboBox, 'supplyBuyQuantity') is None
    assert supply.findChild(QComboBox, 'supplySortSelect') is None
    assert tuple(supply._type_filter.itemText(i) for i in range(supply._type_filter.count())) == ('All','Resources','Energy','Factory','Freight')
    for category in ('Resources', 'Factory', 'Energy', 'Freight'):
        supply._type_filter.setCurrentText(category)
        assert supply._filtered_common_data
        assert all(supply._supply_category(d.definition) == category for d in supply._filtered_common_data)
    assert inv.findChild(QTabWidget, 'inventorySubTabs') is None


@pytest.mark.parametrize('kind,did,quantity', [('resources','machine.extractor',1),('factory','machine.processor',2),('energy','energy.solar_array',1),('freight','freight.truck',2)])
def test_board_context_return_reaches_inventory_and_preserves_configuration(app, kind, did, quantity):
    from production_zero.ui.main_window import MainWindow
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.production_board_views import ResourcesViewV2, EnergyViewV2
    from production_zero.ui.freight_view import FreightView
    from production_zero.ui.release_freight import vehicle_actions
    from production_zero.ui.game_ui import GameButton
    from production_zero.core.commands import InstallCardInHall, InstallFreightCard
    from production_zero.core.machine_operations import compatible_free_slots
    from production_zero.core.state import MachineProductionState
    window=MainWindow(development_mode=False);window.resize(1366,768);window.show()
    factory=window.findChild(FactoryViewV2);factory.pause_simulation();s=factory._state;defs=factory._definitions;s.cash.amount=1e12
    before=set(s.cards);factory._command_bus.dispatch(BuyCommonSupplyCard(did,defs,quantity));ids=tuple(set(s.cards)-before)
    for cid,(unit,slot) in zip(ids,compatible_free_slots(s,defs[did])):
        if kind=='freight':InstallFreightCard(unit.facility_id,slot.index,cid,defs).apply(s)
        else:InstallCardInHall(unit.hall_id,slot.index,cid,kind).apply(s)
        s.cards[cid]=replace(s.cards[cid],mk_level=50,rarity=Rarity.LEGENDARY,upgrade_investment=199,paused=True)
        if kind in {'factory','resources'}:
            p=defs[did].available_production_options[0]
            s.machine_production[cid]=MachineProductionState(cid,p.output_resource,p.production_id,2.5,'paused')
    originals={cid:s.cards[cid] for cid in ids};progress=dict(s.machine_production)
    cls={'resources':ResourcesViewV2,'factory':FactoryViewV2,'energy':EnergyViewV2,'freight':FreightView}[kind]
    board=window.findChild(cls);tabs=window.findChild(QTabWidget,'mainTabs');tabs.setCurrentWidget(board);app.processEvents()
    if kind=='freight':board._selected_vehicles=set(ids)
    else:board._selected_machines=set(ids)
    seen=answer(app,lambda d:next(b for b in d.findChildren(GameButton,'machineContextAction') if b.text()=='RETURN TO INVENTORY').click())
    if kind=='freight':vehicle_actions(board,ids[0])
    else:board._card_actions(ids[0])
    assert seen and not set(ids)&(s.installed_card_ids()|s.installed_freight_card_ids())
    assert all(s.cards[cid] is originals[cid] for cid in ids) and s.machine_production==progress
    inv=window.findChild(InventoryView);tabs.setCurrentWidget(inv);app.processEvents()
    assert set(ids)<=set(inv._workspace_by_id)
    assert inv.findChild(QTabWidget,'inventorySubTabs') is None
    window.close()


def test_busy_freight_context_return_rejects_complete_group(app, monkeypatch):
    from production_zero.ui.main_window import MainWindow
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.freight_view import FreightView
    from production_zero.ui import release_freight
    from production_zero.ui.game_ui import GameButton
    from production_zero.core.commands import InstallFreightCard
    window=MainWindow();window.show();window.findChild(FactoryViewV2).pause_simulation()
    view=window.findChild(FreightView);s=view._state;facility=s.freight.facilities['garage-1']
    ids=('starter-truck-common-001','starter-truck-common-002')
    for i,cid in enumerate(ids):InstallFreightCard(facility.facility_id,i,cid,view._definitions).apply(s)
    s.freight.outbound_shipments['busy']=OutboundFreightShipment('busy','market',freight_card_id=ids[1],quantity=3,remaining_seconds=12)
    view._selected_vehicles=set(ids);before=frozen(s);errors=[]
    monkeypatch.setattr(release_freight,'inform',lambda *args:errors.append(args[-1]))
    answer(app,lambda d:next(b for b in d.findChildren(GameButton,'machineContextAction') if b.text()=='RETURN TO INVENTORY').click())
    release_freight.vehicle_actions(view,ids[0])
    assert errors and 'reserved' in errors[0] and frozen(s)==before
    window.close()


def test_mainwindow_load_and_new_game_clear_inventory_references(app):
    from production_zero.ui.main_window import MainWindow
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.dev_tools_view import DevToolsView
    window=MainWindow(development_mode=True);window.show();window.findChild(FactoryViewV2).pause_simulation()
    inv=window.findChild(InventoryView);supply=window.findChild(SupplyView);dev=window.findChild(DevToolsView)
    tabs=window.findChild(QTabWidget,'mainTabs');tabs.setCurrentWidget(inv);app.processEvents()
    inv._choose_workspace_card(inv._workspace_rows[0]);old=set(inv._workspace_ids())
    loaded=company(inv._definitions);loaded.cards['new-only']=replace(create_card_instance('new-only','machine.processor',inv._definitions['machine.processor'].card_kind,Rarity.EPIC),mk_level=50)
    dev._load_state_callback(loaded);app.processEvents()
    assert not inv._workspace_ids() and set(inv._workspace_by_id)=={'new-only'}
    assert all(c._inventory_row is None or not old.intersection(c._inventory_row.card_ids) for c in inv._workspace_pool)
    assert all(c.property('cardId') is None or c.property('cardId') in loaded.cards for c in inv._workspace_pool)
    assert all(c._inventory_row is None or c.property('rarity')==c._inventory_row.rarity.value for c in inv._workspace_pool)
    inv._choose_workspace_card(inv._workspace_rows[0]);dev._reset_callback();app.processEvents()
    assert not inv._workspace_ids() and 'new-only' not in inv._workspace_by_id
    assert all(c._inventory_row is None or 'new-only' not in c._inventory_row.card_ids for c in inv._workspace_pool)
    assert all(c.property('cardId') is None or c.property('cardId') in inv._state.cards for c in inv._workspace_pool)
    assert supply._hover_popup is None or not supply._hover_popup.isVisible()
    window.close()


@pytest.mark.parametrize('kind', ['machine','energy','freight'])
def test_visible_daily_machine_energy_freight_purchase(app, setup, kind):
    from production_zero.core.supply import refresh_supply
    s,defs,bus,inv,supply=setup
    source='freight_daily' if kind=='freight' else 'machine_daily'
    for _ in range(30):
        refresh_supply(s,defs)
        offer=next((o for o in getattr(s.supply,source+'_offers') if o.card_kind.value==kind),None)
        if offer:break
        s.market.elapsed_seconds+=86400
    assert offer is not None
    supply.resize(1200,720);supply.show();supply.refresh();app.processEvents()
    card=next(c for c in supply.findChildren(__import__('production_zero.ui.supply_view',fromlist=['SupplyOfferCardFrame']).SupplyOfferCardFrame)
        if c._supply_data is not None and c._supply_data.offer==offer and c._source==source)
    before=set(s.cards);cash=s.cash.amount
    seen=answer(app,lambda d:d.accept_button.click())
    card._buy_button.click();ids=set(s.cards)-before
    assert seen and len(ids)==1 and not ids&(s.installed_card_ids()|s.installed_freight_card_ids())
    cid=ids.pop();assert cid in inv._workspace_by_id
    assert s.cards[cid].rarity==offer.rarity and s.cash.amount==cash-offer.price_cash
    assert s.cards[cid].output_bonus_tenths==offer.bonus_tenths
    supply.refresh();assert card._buy_button.isEnabled() is False


def test_quantity_keeps_focus_pool_and_does_not_refresh_other_views(app,setup):
    s,defs,bus,inv,supply=setup
    bus.dispatch(BuyCommonSupplyCard('machine.processor',defs,50));inv.refresh()
    choose(app,inv,next(iter(s.cards)));pool=tuple(inv._workspace_pool)
    calls=[];inv._on_state_changed=lambda:calls.append(True)
    inv._workspace_pool[0].setFocus();inv._workspace_quantity_changed(40)
    app.processEvents()
    assert inv._workspace_pool[0].hasFocus() and tuple(inv._workspace_pool)==pool
    assert len(inv._workspace_ids())==40 and not calls
    assert inv.findChild(QTabWidget,'inventorySubTabs') is None


def test_complete_ui_purchase_install_return_resume_and_sale_once(app):
    from production_zero.ui.main_window import MainWindow
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.game_ui import GameButton
    from production_zero.core.simulation import SimulationEngine
    from production_zero.core.machine_operations import resale_value
    window=MainWindow(development_mode=False);window.resize(1366,768);window.show()
    board=window.findChild(FactoryViewV2);board.pause_simulation();s=board._state;defs=board._definitions;s.cash.amount=1e12
    tabs=window.findChild(QTabWidget,'mainTabs');supply=window.findChild(SupplyView);inv=window.findChild(InventoryView)
    tabs.setCurrentWidget(supply);supply._show_section(1);supply._type_filter.setCurrentText('Processing');app.processEvents()
    offer=next(o for o in common_supply_offers(defs) if o.definition_id=='machine.processor')
    card=next(c for c in supply._common_card_pool if c.isVisible() and c._supply_data.offer==offer)
    before=set(s.cards);answer(app,lambda d:(d.quantity.setValue(2),d.accept_button.click()));card._buy_button.click()
    acquired=set(s.cards)-before;assert len(acquired)==2 and not acquired&s.installed_card_ids()
    tabs.setCurrentWidget(inv);app.processEvents();choose(app,inv,sorted(acquired)[0]);cid=inv._workspace_ids()[0];original=s.cards[cid]
    answer(app,lambda d:d.accept_button.click());inv._workspace_action(inv._install_workspace_card)
    assert cid in s.installed_card_ids() and s.cards[cid] is original
    solar=next(c.card_id for c in s.cards.values() if c.definition_id=='energy.solar_array')
    choose(app,inv,solar);answer(app,lambda d:d.accept_button.click());inv._workspace_action(inv._install_workspace_card)
    definition=defs['machine.processor'];recipe=next(p for p in definition.available_production_options if p.input_resources)
    s.production_progress.unlocked_production_ids.add(recipe.production_id)
    s.ensure_machine_production(cid,recipe.output_resource,recipe.production_id)
    for rid in recipe.input_resources:s.ensure_resource(rid).amount=1000
    cycle=recipe.cycle_seconds_for(definition);engine=SimulationEngine(defs,utc_now=lambda:1792324800.)
    engine.advance_time(s,cycle*.4);assert s.machine_production[cid].progress_seconds==pytest.approx(cycle*.4)
    def return_via_context():
        tabs.setCurrentWidget(board);app.processEvents();board._selected_machines={cid}
        answer(app,lambda d:next(b for b in d.findChildren(GameButton,'machineContextAction') if b.text()=='RETURN TO INVENTORY').click())
        board._card_actions(cid)
    return_via_context();resources=s.resource_snapshot();engine.advance_time(s,cycle*5)
    assert s.resource_snapshot()==resources and s.machine_production[cid].progress_seconds==pytest.approx(cycle*.4)
    tabs.setCurrentWidget(inv);app.processEvents();choose(app,inv,cid)
    answer(app,lambda d:d.accept_button.click());inv._workspace_action(inv._install_workspace_card)
    totals=engine.advance_time(s,cycle*.6)
    assert totals.outputs[recipe.output_resource]==pytest.approx(recipe.output_amount_for(definition))
    for rid,amount in recipe.input_resources.items():assert totals.inputs[rid]==pytest.approx(amount)
    assert not engine.advance_time(s,0).outputs and s.cards[cid] is original
    return_via_context();tabs.setCurrentWidget(inv);app.processEvents();choose(app,inv,cid)
    cash=s.cash.amount;value=resale_value(original,definition)
    answer(app,lambda d:d.accept_button.click());inv._workspace_action(inv._sell_workspace_cards)
    assert cid not in s.cards and s.cash.amount==cash+value and len(acquired&set(s.cards))==1
    inv._workspace_action(inv._sell_workspace_cards);assert s.cash.amount==cash+value
    window.close()


def test_completed_and_cancelled_ui_dialogs_release_their_children(app,setup):
    s,defs,bus,inv,supply=setup
    dialog=IndustrialDialog('Install card','Advanced International Industrial Processing Machine With A Very Long Name · Select a compatible facility and free slot.\nNo purchase: this card keeps its ID, quality and investments.',inv,accept_text='INSTALL')
    target=QComboBox();target.addItem('Hall 1 · Slot 1')
    dialog.layout().itemAt(0).widget().layout().insertWidget(2,target)
    dialog.show();app.processEvents()
    assert dialog.message.height()>=dialog.message.heightForWidth(dialog.message.width())
    assert dialog.accept_button.geometry().bottom()<=dialog.height()
    dialog.reject();dialog.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    offer=next(o for o in common_supply_offers(defs) if o.definition_id=='machine.processor')
    for accept in (True,False,True,False):
        answer(app,lambda d:d.accept_button.click() if accept else d.reject_button.click())
        supply._buy_offer(offer,'common')
        app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        assert supply.findChildren(QDialog)==[]
    choose(app,inv,next(iter(s.cards)))
    for _ in range(3):
        answer(app,lambda d:d.reject_button.click());inv._workspace_action(inv._install_workspace_card)
        answer(app,lambda d:d.reject_button.click());inv._workspace_action(inv._sell_workspace_cards)
        app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        assert inv.findChildren(QDialog)==[]
