"""Behavioral regressions for the measured P1 causes, without timing thresholds."""
import json,os
from dataclasses import replace,fields,is_dataclass
from importlib.resources import files
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QEvent,QTimer,Qt
from PySide6.QtWidgets import QApplication,QLabel,QTabWidget,QPushButton
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.ui.main_window import MainWindow,_create_initial_state
from production_zero.ui.factory_view_v2 import FactoryViewV2,FactoryV2MachineCard,ProductionBoardViewV2
from production_zero.ui.unlock_tree_view import UnlockTreeView
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.contracts_view import ContractProductPicker
from production_zero.ui.supply_view import SupplyView
from production_zero.core.commands import (CommandBus,BuyCommonSupplyCard,SellMachines,UpgradeMachines,
    UnlockProductionSlot,ConfigureMachines,MoveMachines)
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity,CardKind
from production_zero.core.state import FactoryHall,MachineProductionState
from production_zero.core.production_templates import MachineTemplate,PurchaseTemplates,quote_templates
from production_zero.core.production_pause import effective_card_paused
from production_zero.services.local import LocalLeaderboardService
from production_zero.persistence.session_writer import snapshot_game_state,encode_snapshot,HistoryPrefix,SessionWriter
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore

@pytest.fixture(scope='module')
def definitions():
    return load_card_definitions(files('production_zero.data')/'game_definitions.json')

@pytest.fixture
def app():
    app=QApplication.instance() or QApplication([])
    yield app
    for w in app.topLevelWidgets():w.close();w.deleteLater()
    for _ in range(4):app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()

def make_state(definitions):
    r=load_resource_definitions(files('production_zero.data')/'resource_definitions.json')
    s=_create_initial_state(r,definitions);s.cash.amount=1e12;return s

def test_unlock_reuses_scene_nodes_edges_and_lazy_icons(app,definitions,monkeypatch):
    from production_zero.ui import unlock_tree_view as module
    calls=[];original=module._render_icon
    monkeypatch.setattr(module,'_render_icon',lambda *args:(calls.append(args[0]),original(*args))[1])
    v=UnlockTreeView(make_state(definitions),definitions,lambda:None)
    assert not calls
    nodes=dict(v._node_items);edges=dict(v._edge_pool)
    assert len(nodes)==353 and len(edges)==708
    v._stage_changed('PROCESSING');v._stage_changed(None)
    assert all(v._node_items[rid] is node for rid,node in nodes.items())
    assert all(v._edge_pool[key] is edge for key,edge in edges.items())
    assert len(v.canvas.scene().items())==1069
    v.resize(1366,768);v.show();app.processEvents()
    assert 0<len(set(calls))<353
    v.state.production_progress.unlocked_production_ids.add(v.graph.nodes['iron'].production_id)
    v.refresh_state()
    assert v._node_items['iron'].state_name=='unlocked'
    before=v._state_signature;v.refresh_state();assert v._state_signature is before
    edge=next(e for (source,_),e in v._edge_pool.items() if source=='iron_ore')
    edge.set_trace_state(highlighted=True,trace_active=True)
    updates=[];update=edge.update
    monkeypatch.setattr(edge,'update',lambda:(updates.append(True),update())[1])
    quantity=edge.edge.required_quantity/2
    v.state.production_progress.lifetime_produced['iron_ore']=quantity;v.refresh_state()
    assert edge._label_signature==f'{quantity:g} / {edge.edge.required_quantity:g}' and updates
    updates.clear();v.refresh_state();assert not updates


def test_direct_unlock_icon_preserves_legacy_widget_pixels(app):
    from PySide6.QtGui import QPixmap
    from production_zero.ui import unlock_tree_view as module
    from production_zero.ui.resource_icons import ResourceIconWidget
    from production_zero.ui.theme import APP_STYLESHEET
    original=app.styleSheet()
    try:
        for stylesheet in ('',APP_STYLESHEET):
            app.setStyleSheet(stylesheet)
            module._icon_background.cache_clear();module._render_icon.cache_clear()
            widget=ResourceIconWidget('iron_ore',size=38)
            legacy=QPixmap(38,38);legacy.fill(Qt.GlobalColor.transparent);widget.render(legacy)
            assert module._render_icon('iron_ore',widget.icon_key,widget.accent_key).toImage()==legacy.toImage()
            widget.deleteLater()
    finally:
        app.setStyleSheet(original)
        module._icon_background.cache_clear();module._render_icon.cache_clear()


def test_raster_atlas_matches_all_original_smooth_scaled_pixels():
    import hashlib
    from PySide6.QtGui import QImage
    from production_zero.ui import resource_art as art
    atlas=art._ui_raster_atlas();assert not atlas.isNull()
    digests=json.loads(atlas.text('source_sha256'))
    for rid,path in art.RESOURCE_RASTER_ASSETS.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digests[rid]
        for size in art.UI_RASTER_SIZES:
            expected=art.resource_raster_image(rid).scaled(size,size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            assert art._scaled_resource_raster(rid,size,size)==expected, (rid,size)
    assert atlas.sizeInBytes()==8337408

def test_guide_materializes_results_and_updates_progress_without_reopening(app,definitions):
    s=make_state(definitions);b=FactoryViewV2(s,CommandBus(s),definitions);b.pause_simulation()
    board=b._factory_v2_board;slots=dict(b._slot_widgets)
    b._open_production_guide();panel=b._cached_guide_panel
    assert b._guide_tile_create_count==len(b._filtered_guide_items())<353
    b._on_guide_search_changed('iron');tile=next(t for t in b._guide_grid_host.findChildren(__import__('production_zero.ui.factory_view',fromlist=['ProductionGuideTile']).ProductionGuideTile) if t.property('resourceId')=='iron')
    s.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    b.refresh_runtime()
    assert tile.property('progressionState')=='unlocked'
    cached=b._guide_requirements_cache
    b._on_guide_search_changed('copper');b._on_guide_search_changed('iron')
    assert b._guide_requirements_cache is cached and b._cached_guide_panel is panel
    # Every logical product can still be reached using the existing search path.
    for rid in b._guide_option_index():
        b._on_guide_search_changed(rid.replace('_',' '))
        if rid not in [o.output_resource for o in b._filtered_guide_items()]:
            b._on_guide_search_changed(rid)
        assert any(o.output_resource==rid for o in b._filtered_guide_items())
    assert b._guide_tile_create_count==353
    b._close_drawer()
    assert b._factory_v2_board is board and b._slot_widgets==slots
    b._open_production_guide()
    assert b._cached_guide_panel is panel
    b.reset_for_state_change()
    assert b._cached_guide_panel is None and b._factory_v2_board is not board
    assert b._suspended_board is None

def test_picker_lazy_search_scroll_and_tile_identity(app,definitions):
    from types import SimpleNamespace
    resources=load_resource_definitions(files('production_zero.data')/'resource_definitions.json')
    picker=ContractProductPicker([SimpleNamespace(resource_id=rid,name=r.name) for rid,r in resources.items()],resources,set(),'Iron Ore',purpose_label='CUMULATIVE PRODUCTION')
    picker.resize(950,650);picker.show();app.processEvents()
    assert len(picker._products)==353 and len(picker.tiles)<100
    first=picker.tiles[0];rid=first.property('resourceId')
    picker._scroll.verticalScrollBar().setValue(picker._scroll.verticalScrollBar().maximum());app.processEvents()
    assert len(picker.tiles)<353
    for target in ('iron_ore','quantum_computing_module',rid):
        picker.search.setText(target.replace('_',' '));app.processEvents()
        assert target in picker._tiles_by_id
        assert not picker._tiles_by_id[target].isHidden()
    assert picker._tiles_by_id[rid] is first
    selected=[];picker.product_selected.connect(selected.append)
    picker._tiles_by_id[rid].selected.emit(rid);assert selected==[rid]

def test_leaderboard_own_row_identity_profile_and_reopened_picker(app,definitions):
    s=make_state(definitions);v=LeaderboardView(LocalLeaderboardService(s));v.show();v._set_ranking_index(2)
    row=v._production_own_layout.itemAt(0).widget();v._search.setText('Your Company');v._search_jump()
    profiles=[];v.profile_requested.connect(profiles.append)
    for value in (1,20000,1e30):
        s.production_progress.lifetime_produced['iron_ore']=value;v.refresh()
        assert v._production_own_layout.itemAt(0).widget() is row
        assert v._located_row is row
        assert row.findChild(QLabel,'leaderboardValue').text()==f'{value:,.1f} produced'
    row.findChild(QPushButton).click();assert profiles[-1].production_amount==1e30
    def close_dialog():v._product_dialog.reject()
    QTimer.singleShot(0,close_dialog);v._open_product_picker();picker=v._product_picker;dialog=v._product_dialog
    QTimer.singleShot(0,close_dialog);v._open_product_picker()
    assert v._product_picker is picker and v._product_dialog is dialog

def test_pause_location_is_revalidated_after_move_load_and_scope_changes(app,definitions):
    s=make_state(definitions);s.cards.clear();s.halls.clear()
    for hid in ('a','b'):s.halls[hid]=FactoryHall(hid,hid,6,max_lines=5)
    card=create_card_instance('x','machine.processor',CardKind.MACHINE,Rarity.COMMON);s.cards['x']=card
    s.halls['a'].slots[0].card_id='x';h=s.halls['a']
    w=FactoryV2MachineCard(h.slots[0],card,definitions[card.definition_id],None,s)
    assert w._status_text()=='IDLE'
    for building,line,individual in ((True,False,False),(False,True,False),(False,False,True),(False,False,False)):
        h.paused=building;h.production_lines[0].paused=line;s.cards['x']=replace(card,paused=individual)
        w.set_data(h.slots[0],s.cards['x'],definitions[card.definition_id],None,s)
        assert (w._status_text()=='PAUSED')==effective_card_paused(s,'x')
    MoveMachines(('x',),'factory','b',(0,)).apply(s);s.halls['b'].paused=True
    assert w._status_text()=='PAUSED' and w._pause_location[0] is s.halls['b']
    s.cards['y']=create_card_instance('y','machine.processor',CardKind.MACHINE,Rarity.COMMON)
    s.halls['b'].slots[3].card_id='y'
    MoveMachines(('x','y'),'factory','b',(3,0)).apply(s)
    s.halls['b'].paused=False;s.halls['b'].production_lines[0].paused=True
    assert w._status_text()=='IDLE' and w._pause_location[1] is s.halls['b'].slots[3]
    assert not effective_card_paused(s,'x') and effective_card_paused(s,'y')
    loaded=deserialize_game_state(serialize_game_state(s))
    loaded.halls['b'].paused=False
    w.set_data(loaded.halls['b'].slots[3],loaded.cards['x'],definitions[card.definition_id],None,loaded)
    assert w._status_text()=='IDLE' and w._pause_location[0] is loaded.halls['b']

@pytest.mark.parametrize('count',(50,500))
def test_quick_actions_commit_once_and_visible_views_are_current(app,definitions,count):
    window=MainWindow(development_mode=False,charts_enabled=False)
    for timer in window.findChildren(QTimer):timer.stop()
    s=window._session_state;s.cash.amount=1e12
    # Ordinary legal halls, 50 places each, twenty purchases leave room at target.
    s.halls.clear();s.cards.clear();s.machine_production.clear()
    for n in range(count//50):
        hid=f'h{n}';h=FactoryHall(hid,hid,50,max_lines=5,start_unlocked_lines=5,start_slots_per_line=10);s.halls[hid]=h
        for i in range(50):
            cid=f'{hid}-{i}';s.cards[cid]=create_card_instance(cid,'machine.processor',CardKind.MACHINE,Rarity.COMMON)
            if i<30 or n<count//50-1:h.slots[i].card_id=cid
    factory=window.findChild(FactoryViewV2);factory._selected_hall_id=list(s.halls)[-1]
    tabs=window.findChild(QTabWidget,'mainTabs');supply=window.findChild(SupplyView);tabs.setCurrentWidget(supply)
    bus=supply._bus;before=set(s.cards);history=len(bus.history);cash=s.cash.amount
    for _ in range(20):supply._buy_common('machine.processor')
    acquired=tuple(set(s.cards)-before)
    assert len(acquired)==20 and len(bus.history)==history+20
    from production_zero.core.supply import common_card_price
    assert s.cash.amount==cash-20*common_card_price(definitions['machine.processor'])
    assert factory.property('uiDirty')
    # P2 buys ownership only; retain the original occupied-board UI workload
    # through explicit installation outside the purchase callbacks.
    from production_zero.core.commands import InstallCardInHall
    for index,cid in enumerate(acquired,30):
        InstallCardInHall(factory._selected_hall_id,index,cid,"factory").apply(s)
    tabs.setCurrentWidget(factory)
    assert not factory.property('uiDirty') and len(factory._slot_widgets)==50
    unchanged=next(iter(factory._slot_widgets.values()))
    rebuilds=factory._structural_refresh_count
    for cid in acquired:
        bus.dispatch(SellMachines((cid,),definitions));factory.refresh_view()
        from production_zero.ui.factory_view_v2 import _compact_value
        assert window._global_header._cash_value.text()==f'${_compact_value(s.cash.amount)}'
        assert window._global_header._cash_value.toolTip()==f'${s.cash.amount:,.2f}'
    assert len(s.cards)==count and factory._structural_refresh_count==rebuilds
    # A line without sales keeps its original widgets.
    assert next(iter(factory._slot_widgets.values())) is unchanged
    cid=s.halls[factory._selected_hall_id].slots[0].card_id
    for _ in range(4):bus.dispatch(UpgradeMachines((cid,),definitions));factory.refresh_view()
    assert factory._slot_widgets[0]._card.mk_level==5
    option=next(o for o in definitions['machine.processor'].available_production_options if o.output_resource=='iron')
    s.production_progress.unlocked_production_ids.add(option.production_id)
    for _ in range(20):bus.dispatch(ConfigureMachines((cid,),option.production_id,definitions));factory.refresh_view()
    assert factory._slot_widgets[0]._production_state.selected_production_id==option.production_id
    line=s.halls[factory._selected_hall_id].production_lines[-1]
    factory._selected_machines={s.halls[factory._selected_hall_id].slots[i].card_id for i in range(10)}
    factory._copy_selection()
    templates=factory._configuration_clipboard
    assert len(templates)==10 and all(t.definition_id=='machine.processor' for t in templates)
    price=quote_templates(s,definitions,templates,'factory',factory._selected_hall_id,line.line_id)[2]
    bus.dispatch(PurchaseTemplates(templates,'factory',factory._selected_hall_id,line.line_id,definitions,price));factory.refresh_view()
    # All five unlocked lines remain visible, including their vacant slots.
    assert len(s.cards)==count+10 and len(factory._slot_widgets)==50
    assert len(bus.history)==history+20+20+4+20+1
    assert all(s.cards[slot.card_id].mk_level==1 for slot in s.halls[factory._selected_hall_id].slots[-10:])

def test_incremental_slot_unlock_preserves_other_lines(app,definitions):
    s=make_state(definitions);b=FactoryViewV2(s,CommandBus(s),definitions);b.pause_simulation()
    hall=s.halls[b._selected_hall_id];other=b._line_panels[hall.production_lines[1].line_id]
    first=hall.production_lines[0];before=s.cash.amount
    b._unlock_slot(first.line_id)
    assert len(first.slot_indexes)==4 and b._line_panels[hall.production_lines[1].line_id] is other
    assert s.cash.amount==before-40 and len(b._command_bus.history)==1

def _mutable_ids(value,seen=None):
    seen=set() if seen is None else seen
    if id(value) in seen:return set()
    seen.add(id(value));result=set()
    if isinstance(value,HistoryPrefix):return result
    if is_dataclass(value):values=[getattr(value,f.name) for f in fields(value)];result.add(id(value))
    elif isinstance(value,dict):values=list(value.values());result.add(id(value))
    elif isinstance(value,(list,set,tuple)):values=list(value);result.update([id(value)] if not isinstance(value,tuple) else [])
    else:return result
    for item in values:result.update(_mutable_ids(item,seen))
    return result

def test_snapshot_no_live_mutable_aliases_and_encoding_matches_serializer(definitions):
    s=make_state(definitions)
    s.company.achievement_titles.append('Frozen')
    s.production_progress.lifetime_produced['iron_ore']=17
    expected=json.loads(json.dumps(serialize_game_state(s)))
    snap=snapshot_game_state(s)
    assert not (_mutable_ids(s)&_mutable_ids(snap))
    s.company.achievement_titles.append('Later');s.production_progress.lifetime_produced['iron_ore']=999
    s.halls.clear();s.cards.clear();s.contracts.offers.clear();s.consortium.consortiums.clear()
    assert json.loads(encode_snapshot(snap))==expected

def test_writer_failure_recovery_order_and_sqlite_integrity(definitions,tmp_path):
    store=SQLiteSaveStore(tmp_path/'company.sqlite');store.initialize();writes=[]
    class Flaky:
        def save_payload(self,slot,payload):
            number=json.loads(payload)['tick'];writes.append(number)
            if number==1:raise OSError('isolated write failure')
            store.save_payload(slot,payload)
    s=make_state(definitions);writer=SessionWriter(Flaky())
    try:
        s.tick=1;writer.submit(snapshot_game_state(s));assert isinstance(writer.poll(wait=True),OSError)
        for tick in (2,3):s.tick=tick;writer.submit(snapshot_game_state(s))
        assert writer.poll(wait=True) is None and writes in ([1,2,3], [1,3])
    finally:writer.shutdown()
    assert store.load('company').tick==3
    import sqlite3
    with sqlite3.connect(tmp_path/'company.sqlite') as db:assert db.execute('pragma integrity_check').fetchone()[0]=='ok'


def test_queued_autosave_then_new_game_is_ordered_and_shutdown_drains(definitions,tmp_path):
    from threading import Event
    entered,release=Event(),Event();writes=[]
    store=SQLiteSaveStore(tmp_path/'new-game.sqlite');store.initialize()
    class DelayedStore:
        def save_payload(self,slot,payload):
            data=json.loads(payload)
            if data['tick']==42:
                entered.set();assert release.wait(5)
            writes.append(data['company']['selected_title']);store.save_payload(slot,payload)
    old=make_state(definitions);old.tick=42;old.company.selected_title='Old autosave'
    new=make_state(definitions);new.company.selected_title='New game';new.tick=0
    writer=SessionWriter(DelayedStore())
    try:
        writer.submit(snapshot_game_state(old));assert entered.wait(2)
        writer.submit(snapshot_game_state(new))
        old.company.selected_title='Later old mutation';new.company.selected_title='Later new mutation'
        release.set();writer.shutdown()
        assert writer.poll(wait=True) is None
    finally:
        release.set();writer.shutdown()
    assert writes==['Old autosave','New game']
    loaded=store.load('company');assert loaded.tick==0 and loaded.company.selected_title=='New game'
