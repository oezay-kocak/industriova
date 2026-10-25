from __future__ import annotations

import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton

from production_zero.core.progression import initialize_production_progress, production_options, unlock_requirements_for
from production_zero.core.resources import create_resource_inventory
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.unlock_tree_view import (
    PLAYER_STAGE_LABELS,
    UnlockTreeView,
    build_unlock_tree_graph,
    node_requirement_lines,
    unlock_tree_node_state,
)
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def _state() -> GameState:
    resources = create_resource_inventory(
        load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    )
    state = GameState(rng_seed=303, resources=resources)
    initialize_production_progress(state, _definitions())
    return state


@pytest.fixture(autouse=True)
def _dispose_windows():
    yield
    app = QApplication.instance()
    if app is not None:
        for widget in app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        app.processEvents()


def test_unlock_tree_graph_uses_runtime_unlock_requirements() -> None:
    definitions = _definitions()
    graph = build_unlock_tree_graph(definitions)
    expected_edges = {
        (requirement.resource_id, option.output_resource, requirement.quantity)
        for option in production_options(definitions)
        for requirement in unlock_requirements_for(option)
    }

    assert len(graph.nodes) == 353
    assert len(graph.edges) == 708
    assert len(graph.roots) == 49
    assert graph.maximum_depth == 3
    assert sum(node.begins_unlocked for node in graph.nodes.values()) == 49
    assert {(edge.source_resource_id, edge.target_resource_id, edge.required_quantity) for edge in graph.edges} == expected_edges


def test_unlock_tree_node_states_and_player_requirement_language() -> None:
    state = _state()
    graph = build_unlock_tree_graph(_definitions())

    assert unlock_tree_node_state(state, graph, graph.nodes["iron_ore"]) == "unlocked"
    assert unlock_tree_node_state(state, graph, graph.nodes["iron"]) == "current"
    assert unlock_tree_node_state(state, graph, graph.nodes["iron_components"]) == "locked"
    assert unlock_tree_node_state(state, graph, graph.nodes["natural_gas"]) == "unlocked"

    state.production_progress.lifetime_produced["iron_ore"] = 72
    assert node_requirement_lines(state, graph, graph.nodes["iron"]) == ("IRON ORE 72 / 100",)
    assert node_requirement_lines(state, graph, graph.nodes["natural_gas"])[0] == "UNLOCKED"
    all_copy = " ".join(
        line
        for node in graph.nodes.values()
        for line in node_requirement_lines(state, graph, node)
    ).upper()
    assert all(word not in all_copy for word in ("MASTERY", "NEXT", "LATER", "FIRST COMPLETE"))


def test_unlock_tree_opens_from_guide_and_back_returns_to_guide() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    app.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._open_production_guide()
    button = factory.findChild(QPushButton, "productionGuideUnlockTreeButton")
    assert button is not None

    button.click()
    app.processEvents()
    tree = factory.findChild(UnlockTreeView, "unlockTreeView")
    assert tree is not None
    guide = factory.findChild(QFrame, "productionGuideView")
    assert guide is not None and guide.isHidden()

    back = tree.findChild(QPushButton, "unlockTreeBackButton")
    assert back is not None
    back.click()
    app.processEvents()
    assert not guide.isHidden()


def test_unlock_tree_stage_filter_keeps_direct_context_and_search_focuses() -> None:
    app = _app()
    view = UnlockTreeView(_state(), _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    app.processEvents()

    view.stage_filter.select_value("PROCESSING")
    for _ in range(3):
        app.processEvents()
    processing = {
        resource_id
        for resource_id, node in view.graph.nodes.items()
        if PLAYER_STAGE_LABELS[node.stage] == "PROCESSING"
    }
    visible = set(view._node_items)
    assert processing <= visible
    assert "iron_ore" in visible
    assert "iron_components" in visible
    assert len(visible) < len(view.graph.nodes)
    assert view.canvas.minimum_zoom <= view.canvas.zoom_factor <= 0.86

    view.search.setText("Microchip")
    for _ in range(3):
        app.processEvents()
    assert view._selected_resource_id == "microchip"
    assert view._search_match_id == "microchip"
    assert "microchip" in view._node_items
    assert 0.9 <= view.canvas.zoom_factor <= 1.0
    assert view.canvas.minimum_zoom <= view.canvas.zoom_factor


def test_unlock_tree_control_bar_is_compact_and_player_facing() -> None:
    app = _app()
    view = UnlockTreeView(_state(), _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()

    buttons = view.findChildren(QPushButton, "unlockTreeStageButton")
    assert [button.text() for button in buttons] == [
        "PRIMARY PRODUCTION",
        "PROCESSING",
        "MANUFACTURING",
        "ASSEMBLY",
    ]
    assert all(button.width() == 101 for button in buttons)
    assert view.findChild(QFrame, "unlockTreeControlDeck") is not None
    assert view.findChild(QLabel, "unlockTreeControlLabel") is None
    assert view.findChild(QLabel, "unlockTreeCountLabel") is None
    assert view.findChild(QLabel, "unlockTreeSelectionSummary") is None


def test_unlock_tree_opens_at_readable_current_focus_without_full_graph_fit() -> None:
    app = _app()
    state = _state()
    before = set(state.production_progress.unlocked_production_ids)
    view = UnlockTreeView(state, _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()
    canvas = view.findChild(ZoomPanGraphicsView, "unlockTreeCanvas")

    assert canvas is view.canvas
    assert canvas.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert canvas.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert canvas.minimum_zoom == pytest.approx(0.72)
    assert canvas.fit_call_count == 0
    assert canvas.minimum_zoom <= canvas.zoom_factor <= 0.86
    focus = view._default_focus_resources()
    assert focus
    assert all(view._node_items[resource_id].state_name == "current" for resource_id in focus)
    zoom_before = canvas.zoom_factor
    canvas.zoom_by_steps(1)
    assert canvas.zoom_factor > zoom_before
    canvas.pan_by(QPointF(20, 10))
    view.select_resource("iron")
    assert state.production_progress.unlocked_production_ids == before
    assert not view.findChildren(QPushButton, "unlockTreeManualUnlockButton")
    assert not view.findChildren(QFrame, "unlockTreeCanvasControls")


def test_unlock_tree_selection_traces_neighbors_without_rebuilding_scene() -> None:
    app = _app()
    view = UnlockTreeView(_state(), _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()
    node_item_ids = {resource_id: id(item) for resource_id, item in view._node_items.items()}
    edge_item_ids = [id(item) for item in view._edge_items]

    view.select_resource("iron")
    node = view.graph.nodes["iron"]
    related = {requirement.resource_id for requirement in node.requirements} | set(node.children)
    assert view._node_items["iron"].opacity() == pytest.approx(1.0)
    assert all(view._node_items[resource_id].opacity() == pytest.approx(1.0) for resource_id in related)
    unrelated = next(resource_id for resource_id in view._node_items if resource_id not in related | {"iron"})
    assert view._node_items[unrelated].opacity() == pytest.approx(0.22)
    relevant_edges = [
        edge for edge in view._edge_items
        if "iron" in (edge.edge.source_resource_id, edge.edge.target_resource_id)
    ]
    unrelated_edges = [edge for edge in view._edge_items if edge not in relevant_edges]
    assert relevant_edges and all(edge.opacity() == pytest.approx(1.0) for edge in relevant_edges)
    assert unrelated_edges and all(edge.opacity() == pytest.approx(0.14) for edge in unrelated_edges)

    view.select_resource("copper")
    assert {resource_id: id(item) for resource_id, item in view._node_items.items()} == node_item_ids
    assert [id(item) for item in view._edge_items] == edge_item_ids


def test_unlock_tree_clear_selection_restores_graph_without_moving_camera() -> None:
    app = _app()
    view = UnlockTreeView(_state(), _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()
    view.select_resource("iron")
    view.canvas.pan_by(QPointF(37, 19))
    center_before = view.canvas.mapToScene(view.canvas.viewport().rect().center())

    view.clear_selection()

    center_after = view.canvas.mapToScene(view.canvas.viewport().rect().center())
    assert view._selected_resource_id is None
    assert not view.search.text()
    assert all(item.opacity() == pytest.approx(1.0) for item in view._node_items.values())
    assert all(not edge._trace_active for edge in view._edge_items)
    assert center_after.x() == pytest.approx(center_before.x(), abs=1.0)
    assert center_after.y() == pytest.approx(center_before.y(), abs=1.0)


def test_unlock_tree_node_and_empty_canvas_clicks_follow_player_interaction_path() -> None:
    app = _app()
    view = UnlockTreeView(_state(), _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()
    item = view._node_items["iron"]
    view.canvas.centerOn(item.sceneBoundingRect().center())
    node_position = view.canvas.mapFromScene(item.sceneBoundingRect().center())

    QTest.mouseClick(view.canvas.viewport(), Qt.MouseButton.LeftButton, pos=node_position)
    app.processEvents()
    assert view._selected_resource_id == "iron"

    other_item = view._node_items["copper"]
    view.canvas.centerOn(other_item.sceneBoundingRect().center())
    other_position = view.canvas.mapFromScene(other_item.sceneBoundingRect().center())
    QTest.mouseClick(view.canvas.viewport(), Qt.MouseButton.LeftButton, pos=other_position)
    app.processEvents()
    assert view._selected_resource_id == "copper"

    empty_position = next(
        QPoint(x, y)
        for y in range(8, view.canvas.viewport().height() - 8, 16)
        for x in range(8, view.canvas.viewport().width() - 8, 16)
        if view.canvas.itemAt(QPoint(x, y)) is None
    )
    center_before = view.canvas.mapToScene(view.canvas.viewport().rect().center())
    QTest.mouseClick(view.canvas.viewport(), Qt.MouseButton.LeftButton, pos=empty_position)
    app.processEvents()
    center_after = view.canvas.mapToScene(view.canvas.viewport().rect().center())
    assert view._selected_resource_id is None
    assert center_after.x() == pytest.approx(center_before.x(), abs=1.0)
    assert center_after.y() == pytest.approx(center_before.y(), abs=1.0)


def test_unlock_tree_default_focus_has_deterministic_starting_root_fallback() -> None:
    app = _app()
    state = _state()
    definitions = _definitions()
    graph = build_unlock_tree_graph(definitions)
    state.production_progress.unlocked_production_ids = {node.production_id for node in graph.nodes.values()}
    view = UnlockTreeView(state, definitions, lambda: None)
    view.resize(1200, 680)
    view.show()
    for _ in range(3):
        app.processEvents()

    expected = tuple(sorted(
        (resource_id for resource_id, node in graph.nodes.items() if node.begins_unlocked),
        key=lambda resource_id: (graph.nodes[resource_id].name, resource_id),
    ))
    assert view._default_focus_resources() == expected


def test_shared_zoom_pan_defaults_keep_chain_inspector_zoom_floor_unchanged() -> None:
    canvas = ZoomPanGraphicsView(object_prefix="chainInspector")
    assert canvas.minimum_zoom == pytest.approx(0.35)
    assert canvas.maximum_zoom == pytest.approx(1.75)


def test_production_guide_copy_is_concise_after_unlock_tree_addition() -> None:
    app = _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    factory._open_production_guide()
    app.processEvents()
    labels = factory.findChildren(QLabel, "productionGuideUnlock")
    copy = " ".join(label.text() for label in labels).upper()

    assert "UNLOCKED" in copy
    assert all(word not in copy for word in ("MASTERY", "NEXT", "LATER", "FIRST COMPLETE"))
