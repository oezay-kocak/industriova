from dataclasses import asdict
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QFrame,QLabel,QPushButton,QComboBox,QLineEdit,QScrollArea,QWidget,QTabWidget
from production_zero.ui.secondary_views import ResourceBrowser,ResourceCategoryRail,StageFilterBar,browser_resource_metadata
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView
from production_zero.core.freight import FreightAssignment
from production_zero.core.simulation import SimulationEngine
from production_zero.core.commands import AssignFreightCard,AddResource,SetResourceCapacity
from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
from test_factory_ui import _app,_add_freight_inventory_card,_install_freight_from_drawer,_install_factory_card_from_selection,_open_production_selection_for_slot
from test_freight import _install_freight_card,_definitions
from production_zero.core.commands import CommandBus

@pytest.fixture
def window():
    app=_app()
    w=MainWindow(); w.findChild(FactoryViewV2).pause_simulation()
    yield w
    w.close();w.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    app.processEvents()

@pytest.mark.parametrize('legacy_value',[0,25,100,'obsolete-invalid-value',None])
def test_old_reserve_is_ignored_and_never_serialized(legacy_value):
    definitions=_definitions(); state=GameState(rng_seed=301);bus=CommandBus(state)
    _install_freight_card(state,bus,definitions)
    bus.dispatch(AssignFreightCard('truck-1','iron_ore','market'))
    bus.dispatch(SetResourceCapacity('iron_ore',100));bus.dispatch(AddResource('iron_ore',30))
    payload=serialize_game_state(state)
    payload['freight']['assignments']['truck-1']['reserve_percent']=legacy_value
    loaded=deserialize_game_state(payload)
    assert asdict(loaded.freight.assignments['truck-1'])=={'resource_id':'iron_ore','destination_kind':'market'}
    assert 'reserve_percent' not in serialize_game_state(loaded)['freight']['assignments']['truck-1']
    totals=SimulationEngine(definitions).advance_time(loaded,1)
    assert totals.auto_sold=={'iron_ore':30}
    assert loaded.resources['iron_ore'].amount==0

@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_all_secondary_states_fit_actual_window(window,size):
    app=_app();window.resize(*size);window.show();f=window.findChild(FactoryViewV2);r=window.findChild(ResourcesViewV2);g=window.findChild(FreightView)
    def check():
        for _ in range(8):app.processEvents()
        assert (window.width(),window.height())==size
    r._on_slot_clicked(0);_install_factory_card_from_selection(r,'Extractor');_open_production_selection_for_slot(r);check()
    assert r.findChild(ResourceBrowser)
    f._open_production_guide();check()
    for rid in ('iron','high_speed_network_system'):
        f._open_chain_from_guide(rid);check()
        canvas=f.findChild(ZoomPanGraphicsView,'chainInspectorCanvas');assert canvas
        content=canvas.content_widget;assert content
        assert content.findChildren(QWidget,'chainStageGroup')
        assert not content.findChildren(QFrame,'chainStagePanel')
        assert not content.findChildren(QScrollArea)
        assert all(box.height() >= 92 for box in content.findChildren(QFrame,'chainResourceBox'))
        assert all(box.findChild(QLabel, 'chainResourceAmount') is not None for box in content.findChildren(QFrame,'chainResourceBox'))
        assert canvas.minimum_zoom <= canvas.zoom_factor <= 1.0
    for rid,count in [('high_speed_network_system',0),('bauxite',1),('limestone',2),('iron',3),('copper',None)]:
        f._open_used_in_detail(rid);check()
        rows=f.findChildren(QFrame,'guideRecipeRow')
        assert len(rows)==(len(f._guide_recipe_index.used_in(rid)) if count is None else count)
        if rows:
            assert all(row.height()==208 for row in rows)
            assert all('OUTPUT' in row.findChild(QLabel,'guideRecipeDetail').text() for row in rows)
    tabs=window.findChild(QTabWidget,'mainTabs')
    tabs.setCurrentWidget(g);g._open_drawer(0);check()
    assert g._filtered_drawer_cards()  # starter trucks are present
    _add_freight_inventory_card(g,'modern-truck','freight.truck');g.refresh();check()
    g._install_card_from_selection('modern-truck');g._open_assignment_view('modern-truck');check()
    assert g.findChild(ResourceBrowser)
    g._state.ensure_resource('steel').amount=17
    g._select_assignment_resource('steel');check()
    assert 'modern-truck' not in g._state.freight.assignments
    g._choose_assignment_destination('market')
    g._confirm_assignment();check()
    assert g.findChild(QWidget,'freightAssignmentReserveSlider') is None
    assert g.findChild(QPushButton,'freightApplyMarketAssignmentButton') is None
    assert g._state.freight.assignments['modern-truck'].resource_id=='steel'

@pytest.mark.parametrize('browser_kind',['factory','guide','cargo'])
def test_browser_rail_search_filter_and_tile_reuse(window,browser_kind):
    f=window.findChild(FactoryViewV2);r=window.findChild(ResourcesViewV2);g=window.findChild(FreightView)
    if browser_kind=='factory':
        r._on_slot_clicked(0);_install_factory_card_from_selection(r,'Extractor');_open_production_selection_for_slot(r)
        view=r;tile_name='productionSelectionTile';search_name='productionSearchInput'
    elif browser_kind=='guide':
        f._open_production_guide();view=f;tile_name='productionGuideTile';search_name='productionGuideSearchInput'
    else:
        _add_freight_inventory_card(g,'rail-truck','freight.truck');_install_freight_from_drawer(g,0,'rail-truck');g._open_assignment_view('rail-truck')
        view=g;tile_name='freightAssignmentResourceTile';search_name='freightAssignmentSearch'
    rail=view.findChild(ResourceCategoryRail);assert rail
    assert rail.buttons[0].toolTip()=='All resources'
    categories={r.category for r in browser_resource_metadata().values()}
    assert all(b.property('category') in categories for b in rail.buttons[1:])
    before={t.property('resourceId'):t for t in view.findChildren(QFrame,tile_name)}
    search=view.findChild(QLineEdit,search_name);search.setText('IrOn')
    after=view.findChildren(QFrame,tile_name);assert after
    if browser_kind=='guide':
        # Newly reached P1 results may materialize now; all previously reached
        # tiles, and every result on the second identical search, must be reused.
        reached={t.property('resourceId'):t for t in after}
        assert all(reached[rid] is tile for rid,tile in before.items())
        search.clear();search.setText('IrOn')
        assert {t.property('resourceId'):t for t in view.findChildren(QFrame,tile_name)}==reached
    else:
        assert all(t is before[t.property('resourceId')] for t in after)
    search.setText('');button=next(b for b in rail.buttons if b.property('category')=='Ores / Metals');button.click()
    assert button.isChecked();assert sum(b.isChecked() for b in rail.buttons)==1
    filtered_tiles = view.findChildren(QFrame, tile_name)
    if browser_kind == 'guide':
        filtered_tiles = [tile for tile in filtered_tiles if tile.isVisible()]
    assert all(browser_resource_metadata()[t.property('resourceId')].category=='Ores / Metals' for t in filtered_tiles)
    assert all(not combo.isVisible() for combo in rail.findChildren(QComboBox))


def test_freight_compatibility_search_and_no_redundant_filters(window):
    g=window.findChild(FreightView)
    _add_freight_inventory_card(g,'good','freight.truck');_add_freight_inventory_card(g,'wrong','freight.train')
    g._open_drawer(0)
    assert [c.card_id for c in g._filtered_drawer_cards()]==['good']
    assert g.findChild(QComboBox,'freightClassFilter') is None
    assert g.findChild(QComboBox,'freightRarityFilter') is None
    search=g.findChild(QLineEdit,'freightCardSearch');search.setText('nOtFoUnD')
    assert not g._filtered_drawer_cards()
    assert g.findChild(QFrame,'freightSelectionEmpty')
    search.setText('TRUCK');assert len(g._filtered_drawer_cards())==1


def test_production_guide_uses_direct_v2_stage_controls(window):
    f=window.findChild(FactoryViewV2);f._open_production_guide()
    control=f.findChild(StageFilterBar,'productionGuideStageFilter');assert control
    assert f.findChild(QComboBox,'productionGuideStageFilter') is None
    assert [button.text() for button in control.buttons]==['ALL','PRIMARY PRODUCTION','PROCESSOR','FABRICATOR','ASSEMBLER']
    assert all(button.objectName()=='productionGuideStageButton' for button in control.buttons)
    control.setCurrentText('Processing')
    assert control.currentText()=='Processing'
    assert next(button for button in control.buttons if button.text()=='PROCESSOR').isChecked()


def test_secondary_views_share_v2_chassis_and_actions(window):
    f=window.findChild(FactoryViewV2);g=window.findChild(FreightView)
    f._open_production_guide()
    assert f.findChild(QFrame,'secondaryControlDeck')
    assert f.findChild(QFrame,'secondaryContentChassis')
    assert f.findChild(QPushButton,'productionGuideBackButton').property('secondaryAction') is True
    f._open_chain_from_guide('iron')
    assert f.findChild(QFrame,'secondaryTechnicalChassis')
    assert f.findChild(QPushButton,'chainInspectorBackButton').property('secondaryAction') is True
    assert f.findChild(QPushButton,'chainInspectorScrollLeftButton') is None
    assert f.findChild(QFrame,'chainInspectorCanvasControls') is None
    assert f.findChild(QPushButton,'chainInspectorFitButton') is None
    action=f.findChild(QPushButton,'guideUsedInOpenButton')
    assert action.findChild(QLabel,'usedInActionEyebrow').text()=='USED IN'
    assert action.findChild(QLabel,'usedInActionChevron').text()=='›'
    action.click()
    assert f.findChild(QFrame,'secondaryContentChassis')
    assert f.findChild(QPushButton,'usedInBackButton').property('secondaryAction') is True
    _add_freight_inventory_card(g,'v2-test-truck','freight.truck');g._open_drawer(0)
    assert g.findChild(QFrame,'secondaryContentChassis')
    assert g.findChild(QPushButton,'freightCloseDrawerButton').property('secondaryAction') is True
    g._install_card_from_selection('v2-test-truck');g._open_assignment_view('v2-test-truck')
    assert g.findChild(QFrame,'secondaryControlDeck')
    assert g.findChild(QFrame,'secondaryContentChassis')
    assert g.findChild(QWidget,'freightAssignmentBackButton').text()=='CANCEL'


def test_reused_cargo_tile_updates_stock_and_guide_tile_updates_progress(window):
    f=window.findChild(FactoryViewV2);g=window.findChild(FreightView)
    _add_freight_inventory_card(g,'live-tile','freight.truck');_install_freight_from_drawer(g,0,'live-tile');g._open_assignment_view('live-tile')
    g._state.ensure_resource('steel').amount=1
    g._populate_assignment_resource_grid()
    tile=next(t for t in g.findChildren(QFrame,'freightAssignmentResourceTile') if t.property('resourceId')=='steel')
    g._state.ensure_resource('steel').amount=17
    g._populate_assignment_resource_grid()
    assert next(t for t in g.findChildren(QFrame,'freightAssignmentResourceTile') if t.property('resourceId')=='steel') is tile
    assert tile.findChild(QLabel,'freightAssignmentTileStock').text() == '17 STORED'
    f._open_production_guide()
    tile=next(t for t in f.findChildren(QFrame,'productionGuideTile') if t.property('resourceId')=='aluminum')
    option=f._guide_option_index()['aluminum']
    f._state.production_progress.unlocked_production_ids.add(option.production_id)
    f._populate_guide_grid()
    assert next(t for t in f.findChildren(QFrame,'productionGuideTile') if t.property('resourceId')=='aluminum') is tile
    assert tile.findChild(QLabel,'productionGuideUnlock').text()=='UNLOCKED'


def test_dense_chain_summary_does_not_expand_window(window):
    app=_app();window.resize(1366,768);window.show();f=window.findChild(FactoryViewV2)
    for rid in ('fusion_reactor_module','nuclear_reactor','supercomputer'):
        f._open_chain_from_guide(rid)
        for _ in range(8):app.processEvents()
        assert (window.width(),window.height())==(1366,768)
        canvas=f.findChild(ZoomPanGraphicsView,'chainInspectorCanvas')
        assert canvas is not None and canvas.content_widget is not None
        target=next(
            box for box in canvas.content_widget.findChildren(QFrame,'chainResourceBox')
            if box.property('target')
        )
        links=target.findChildren(QPushButton,'guideRecipeInputLink')
        assert len(links)==4
        assert all(button.height()==16 for button in links)
