"""P5 visible production choices, unlock requirements and real market XP feedback."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from test_ui_interaction_recovery import app, window, board
from production_zero.core.cards import create_card_instance
from production_zero.core.commands import InstallCardInHall, InstallFreightCard, AssignFreightCard, SellResource
from production_zero.core.enums import Rarity
from production_zero.core.progression import record_lifetime_production
from production_zero.core.simulation import SimulationEngine
from production_zero.ui.factory_view import ProductionSelectionTile
from production_zero.ui.unlock_tree_view import UnlockTreeView, node_requirement_lines
from production_zero.ui.event_feed import EventFeedWidget


def install(b, did):
    unit = next(u for u in b._units.values() if b._board_config.board_kind != 'resources' or u.specialization == did)
    cid = 'p5-card'
    b._state.cards[cid] = create_card_instance(cid, did, b._definitions[did].card_kind, Rarity.COMMON)
    InstallCardInHall(unit.hall_id, 0, cid, b._board_config.board_kind).apply(b._state)
    b._selected_hall_id = unit.hall_id; b.refresh_view()
    return unit, cid


@pytest.mark.parametrize('kind', ['machine.extractor', 'machine.drilling', 'machine.agriculture'])
def test_all_matching_primary_resources_are_selectable_at_level_one(window, kind):
    b = board(window, 'Resources'); unit, cid = install(b, kind)
    b._open_production_drawer(cid); QTest.qWait(15)
    tiles = b.findChildren(ProductionSelectionTile)
    expected = {o.production_id for o in b._definitions[kind].available_production_options}
    assert {t.property('productionId') for t in tiles} == expected
    assert all(t.isEnabled() for t in tiles) and b._state.company.level == 1
    chosen = tiles[-1]; production_id = chosen.property('productionId')
    QTest.mouseClick(chosen, Qt.MouseButton.LeftButton)
    assert b._state.machine_production[cid].selected_production_id == production_id


def test_factory_starts_compact_and_unlock_appears_after_100_own_units(window):
    b = board(window, 'Factory'); _, cid = install(b, 'machine.processor')
    b._open_production_drawer(cid); QTest.qWait(15)
    tiles = b.findChildren(ProductionSelectionTile)
    assert len(tiles) <= 2 and all(not t.isEnabled() for t in tiles)
    iron = next(o for o in b._definitions['machine.processor'].available_production_options if o.output_resource == 'iron')
    record_lifetime_production(b._state, {'iron_ore': 99}, b._definitions); b.refresh_runtime()
    assert not any(t.isEnabled() for t in b.findChildren(ProductionSelectionTile))
    reason = b._locked_production_reason(iron)
    assert 'LEVEL' not in reason and '1 MORE IRON ORE' in reason
    record_lifetime_production(b._state, {'iron_ore': 1}, b._definitions); b.refresh_runtime(); QTest.qWait(15)
    target = next(t for t in b.findChildren(ProductionSelectionTile) if t.property('productionId') == iron.production_id)
    assert target.isEnabled() and b._state.company.level == 1
    QTest.mouseClick(target, Qt.MouseButton.LeftButton)
    assert b._state.machine_production[cid].selected_production_id == iron.production_id


@pytest.mark.parametrize('size', [(1366, 768), (1600, 980), (1920, 1080)])
def test_unlock_tree_uses_100_unit_edges_and_no_level_gates(window, size):
    window.resize(*size); b = board(window, 'Factory')
    tree = UnlockTreeView(b._state, b._definitions, lambda: None)
    tree.setParent(window)
    tree.resize(size[0]-100, size[1]-200); tree.show(); QTest.qWait(10)
    assert sum(node.begins_unlocked for node in tree.graph.nodes.values()) == 49
    assert {edge.required_quantity for edge in tree.graph.edges} == {100}
    assert {item.state_name for item in tree._node_items.values()} <= {'current', 'locked', 'unlocked'}
    assert all('LEVEL' not in line for node in tree.graph.nodes.values()
               for line in node_requirement_lines(b._state, tree.graph, node))
    b._state.production_progress.lifetime_produced['iron_ore'] = 99; tree.refresh_state()
    assert node_requirement_lines(b._state, tree.graph, tree.graph.nodes['iron']) == ('IRON ORE 99 / 100',)
    record_lifetime_production(b._state, {'iron_ore': 1}, b._definitions); tree.refresh_state()
    assert tree._node_items['iron'].state_name == 'unlocked'
    assert not tree.grab().isNull()
    tree.close(); tree.deleteLater()


def test_market_arrival_updates_xp_header_and_existing_activity_feedback(window):
    b = board(window, 'Factory'); s = b._state; definitions = b._definitions
    cid = next(cid for cid, card in s.cards.items() if card.definition_id == 'freight.truck')
    InstallFreightCard('garage-1', 0, cid, definitions).apply(s)
    record_lifetime_production(s, {'iron_ore': 100}, definitions)
    AssignFreightCard(cid, 'iron', 'market').apply(s)
    s.ensure_resource('iron').amount = 40
    SellResource('iron', 40, definitions).apply(s)
    feed = window.findChild(EventFeedWidget)
    SimulationEngine(definitions, utc_now=lambda: 1000000).advance_time(s, 60)
    b._simulation_advanced_callback(); feed.flush_pending()
    assert s.company_xp_progress.xp_by_source['market_sales'] == 16
    assert window._global_header._xp_bar.value() > 0
    assert s.company.current_xp == 16
    assert any(e.event_type == 'xp' and e.amount == 16 for e in feed.history)


def test_new_version_starts_fresh_beside_previous_test_database(app, tmp_path, monkeypatch):
    import hashlib
    import json
    from production_zero.persistence.sqlite_store import SQLiteSaveStore, serialize_game_state
    from production_zero.persistence.paths import default_company_save_path
    from production_zero.ui.main_window import MainWindow
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    old = tmp_path / 'Industriova/playtests/production-xp-test/saves/company.sqlite'
    old.parent.mkdir(parents=True)
    old_store = SQLiteSaveStore(old); old_store.initialize()
    old_store.save_payload('company', json.dumps({'cash': {'amount': 999999}, 'state_schema_version': 9}))
    digest = hashlib.sha256(old.read_bytes()).hexdigest()
    current = default_company_save_path()
    assert current != old and 'contract-auto-test' in current.parts
    current.parent.mkdir(parents=True)
    w = MainWindow(save_store=SQLiteSaveStore(current), development_mode=False)
    try:
        assert w._session_state.cash.amount == 1250
        assert len(w._session_state.production_progress.unlocked_production_ids) == 49
        assert serialize_game_state(w._session_state)['game_ruleset'] == 'contract-priority-auto-v1'
    finally:
        w.close(); w.deleteLater(); QTest.qWait(20)
    assert hashlib.sha256(old.read_bytes()).hexdigest() == digest
