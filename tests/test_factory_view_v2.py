from __future__ import annotations

import inspect
import os
from pathlib import Path
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from production_zero.core.commands import AddCash, InstallCardInHall, SelectMachineProduction
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.factory_view import FactoryView
from production_zero.ui import factory_view_v2 as factory_v2_module
from production_zero.ui.factory_view_v2 import (
    FACTORY_V2_CARD_HEIGHT,
    FACTORY_V2_CARD_WIDTH,
    FACTORY_V2_LOCKED_SLOT_HEIGHT,
    FACTORY_V2_LOCKED_SLOT_WIDTH,
    FactoryCommandDeckWidget,
    FactoryV2CommandButton,
    FactoryV2CommandModule,
    FactoryV2ActiveIndicator,
    FactoryV2HallResourceSummaryWidget,
    FactoryV2HallStage,
    FactoryV2KpiStripWidget,
    FactoryV2LinePlate,
    FactoryV2LockedSlot,
    FactoryV2MachineCard,
    FactoryV2TrackPanel,
    FactoryViewV2,
    accent_for_definition,
    machine_icon_for_definition,
    prototype_family_for_definition,
)
from production_zero.ui.game_ui import BuildSlotWidget, GameButton, MachineIcon, draw_machine_icon
from production_zero.ui.game_ui import icons as game_icons_module
from production_zero.ui.game_ui import materials as game_materials_module
from production_zero.ui.game_ui import rendering as game_rendering_module
from production_zero.ui.game_ui.rendering import factory as game_rendering_factory_module
from production_zero.ui.game_ui.rendering import (
    draw_build_slot,
    draw_build_corner_brackets,
    draw_atmospheric_color_wash,
    draw_command_chassis,
    draw_distinct_material_zones,
    draw_game_surface,
    draw_hazard_stripes,
    draw_industrial_base_surface,
    draw_industrial_edge,
    draw_panel_bolt,
    draw_panel_bolts,
    draw_panel_seam,
    draw_selection_chassis,
    draw_surface_wear,
    draw_utility_chassis,
    draw_locked_slot,
    draw_lock_warning_frame,
    draw_machine_card,
    draw_machine_card_prototype,
    draw_machine_icon_stage,
    draw_production_track,
    draw_status_badge,
    draw_status_led,
    draw_slot_hazard_footer,
    draw_warning_plate,
)
from production_zero.ui.main_window import _create_initial_state
from production_zero.ui.theme import APP_STYLESHEET


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _state_defs_bus():
    from production_zero.core.commands import CommandBus

    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    state = _create_initial_state(resource_definitions, definitions)
    return state, definitions, CommandBus(state)


def _render_widget(widget, width: int = 1920, height: int = 1080) -> QImage:
    widget.resize(width, height)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        widget.render(painter, QPoint(0, 0))
    finally:
        painter.end()
    return image


def _painted_samples(image: QImage) -> int:
    hits = 0
    for x in range(0, image.width(), max(1, image.width() // 48)):
        for y in range(0, image.height(), max(1, image.height() // 27)):
            if image.pixelColor(x, y).alpha() > 0 and image.pixelColor(x, y).value() > 0:
                hits += 1
    return hits


def _save_preview(image: QImage, filename: str) -> Path:
    path = Path("artifacts") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path))
    return path


def _bright_corner_pixels(image: QImage, margin: int = 10) -> int:
    hits = 0
    regions = (
        (0, 0),
        (image.width() - margin, 0),
        (0, image.height() - margin),
        (image.width() - margin, image.height() - margin),
    )
    for start_x, start_y in regions:
        for x in range(start_x, start_x + margin):
            for y in range(start_y, start_y + margin):
                color = image.pixelColor(x, y)
                if color.alpha() > 24 and color.value() > 120:
                    hits += 1
    return hits


def test_factory_view_v1_and_v2_are_both_constructible_offscreen() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    v1 = FactoryView(state, bus, definitions)
    v2 = FactoryViewV2(state, bus, definitions)

    assert v1.findChild(QFrame, "factoryHallCommandBoard") is not None
    assert v2.objectName() == "factoryViewV2"
    assert v2.findChild(QFrame, "factoryV2Board") is not None
    assert v2.findChild(QFrame, "factoryV2HallStage") is not None


def test_factory_view_v2_build_install_and_core_state_display() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    view = FactoryViewV2(state, bus, definitions)

    build_slot = view.findChild(QWidget, "factoryV2BuildSlot")
    assert build_slot is not None
    build_slot.clicked.emit()
    assert view._drawer_mode == "cards"
    assert view._drawer_slot_index == 0

    view._install_card_from_selection("test-solar-common-001")
    assert state.halls["hall-1"].slots[0].card_id == "test-solar-common-001"
    assert view.findChild(FactoryV2MachineCard, "factoryV2MachineCard") is not None
    assert view.findChild(QFrame, "factoryV2HallOverview") is not None


def test_factory_view_v2_locked_slot_and_locked_line_unlock_use_commands() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(AddCash(10_000))
    view = FactoryViewV2(state, bus, definitions)
    hall = state.halls["hall-1"]
    initial_line_slots = len(hall.production_lines[0].slot_indexes)

    locked_slot = view.findChild(QFrame, "lockedSlotPanel")
    assert locked_slot is not None
    locked_slot.activated.emit()
    assert len(hall.production_lines[0].slot_indexes) == initial_line_slots + 1

    view.refresh_view()
    locked_line = next(panel for panel in view.findChildren(QFrame, "lockedLinePanel") if panel.property("lineId") == "hall-1.line-3")
    locked_line.activated.emit()
    assert hall.production_lines[2].unlocked is True


def test_factory_view_v2_machine_status_refreshes_after_production_selection() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    view = FactoryViewV2(state, bus, definitions)
    card = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    assert card is not None
    assert card._status_text() in {"NO RESOURCE", "NO RECIPE", "IDLE"}

    bus.dispatch(SelectMachineProduction("test-drill-common-001", "resource.iron_ore", "iron_ore"))
    view._refresh_runtime_widgets()
    assert card._status_text() in {"RUNNING", "IDLE", "STORAGE FULL", "NO POWER"}


def test_factory_view_v2_machine_icons_render_and_map_expected_types() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()

    assert machine_icon_for_definition(definitions["energy.solar_array.mk1"]) == MachineIcon.SOLAR_ARRAY
    assert machine_icon_for_definition(definitions["machine.extractor.mk1"]) == MachineIcon.EXTRACTOR
    assert machine_icon_for_definition(definitions["machine.processor.mk1"]) == MachineIcon.PROCESSOR

    image = QImage(520, 120, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        for index, icon in enumerate(MachineIcon):
            draw_machine_icon(painter, icon, image.rect().adjusted(10 + index * 62, 14, -450 + index * 62, -14))
    finally:
        painter.end()
    assert _painted_samples(image) > 0


def test_factory_view_v2_machine_icon_family_renders_all_sizes_states_and_unknowns() -> None:
    _app()

    for icon in MachineIcon:
        for size in (48, 64, 128):
            for disabled in (False, True):
                image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(0)
                painter = QPainter(image)
                try:
                    draw_machine_icon(painter, icon, QRectF(0, 0, size, size), disabled=disabled)
                finally:
                    painter.end()
                assert _painted_samples(image) > 0

    image = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_machine_icon(painter, "unknown-machine", QRectF(0, 0, 64, 64))  # type: ignore[arg-type]
    finally:
        painter.end()
    assert _painted_samples(image) > 0


def test_factory_view_v2_machine_icons_are_procedural_qpainter_primitives() -> None:
    source = inspect.getsource(game_icons_module)

    assert "QPixmap" not in source
    assert "QImage(" not in source
    assert ".png" not in source
    assert ".svg" not in source
    assert "draw_machine_icon" in source
    assert "QPainter" in source


def test_factory_view_v2_machine_cards_use_prototype_renderer_with_runtime_data(monkeypatch) -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    calls = []

    original = factory_v2_module.draw_machine_card_prototype

    def recorder(painter, rect, **kwargs):
        calls.append((QRectF(rect), dict(kwargs)))
        original(painter, rect, **kwargs)

    monkeypatch.setattr(factory_v2_module, "draw_machine_card_prototype", recorder)
    view = FactoryViewV2(state, bus, definitions)
    card = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    assert card is not None

    image = _render_widget(card, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)

    assert _painted_samples(image) > 24
    assert calls
    rect, kwargs = calls[0]
    assert rect.width() == FACTORY_V2_CARD_WIDTH - 2
    assert rect.height() == FACTORY_V2_CARD_HEIGHT - 2
    assert kwargs["title"] == "EXTRACTOR"
    assert kwargs["family"] == "extractor"
    assert kwargs["meta"] == "MK1 · COMMON"
    assert kwargs["detail"] == ""
    assert kwargs["secondary"] == "SELECT RESOURCE >"
    assert kwargs["secondary_control"] is True
    assert kwargs["disabled"] is False
    assert kwargs["hover"] is False


def test_factory_view_v2_experimental_rendering_foundation_is_asset_free_and_paints() -> None:
    _app()
    image = QImage(680, 280, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_game_surface(painter, QRectF(8, 8, 180, 120))
        draw_production_track(painter, QRectF(204, 8, 220, 120))
        draw_machine_card(painter, QRectF(452, 8, 132, 214), accent=factory_v2_module.Accent.ENERGY)
        draw_machine_icon_stage(painter, QRectF(474, 58, 88, 88), icon=MachineIcon.PROCESSOR, accent=factory_v2_module.Accent.ENERGY)
        draw_status_badge(painter, QRectF(468, 196, 100, 18), text="RUNNING", accent=factory_v2_module.Accent.SUCCESS)
        draw_build_slot(painter, QRectF(12, 152, 132, 120))
        draw_locked_slot(painter, QRectF(176, 152, 132, 120))
    finally:
        painter.end()

    source = inspect.getsource(game_rendering_module) + inspect.getsource(game_rendering_factory_module)
    assert "QPixmap" not in source
    assert "QImage(" not in source
    assert ".png" not in source
    assert ".svg" not in source
    assert _painted_samples(image) > 30


def test_factory_view_v2_phase2_rendering_states_paint_game_objects() -> None:
    _app()
    image = QImage(760, 300, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        machine_rect = QRectF(24, 28, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)
        draw_machine_card(
            painter,
            machine_rect,
            accent=factory_v2_module.Accent.ENERGY,
            rarity_accent=factory_v2_module.Accent.UNCOMMON,
            hover=True,
            active=True,
        )
        draw_machine_icon_stage(
            painter,
            QRectF(machine_rect.left() + 8, machine_rect.top() + 49, machine_rect.width() - 16, 103),
            icon=MachineIcon.EXTRACTOR,
            accent=factory_v2_module.Accent.ENERGY,
        )
        build_stage = draw_build_slot(painter, QRectF(210, 28, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT), hover=True, pressed=True)
        locked_module = draw_locked_slot(painter, QRectF(396, 28, FACTORY_V2_LOCKED_SLOT_WIDTH, FACTORY_V2_LOCKED_SLOT_HEIGHT))
    finally:
        painter.end()

    assert build_stage.width() > 38
    assert build_stage.height() > 38
    assert FACTORY_V2_LOCKED_SLOT_WIDTH - 32 <= locked_module.width() < FACTORY_V2_LOCKED_SLOT_WIDTH
    assert FACTORY_V2_LOCKED_SLOT_HEIGHT - 56 <= locked_module.height() < FACTORY_V2_LOCKED_SLOT_HEIGHT
    assert _painted_samples(image) > 34


def test_factory_view_v2_build_and_locked_slots_use_industrial_safety_language() -> None:
    _app()
    image = QImage(420, 260, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        build_stage = draw_build_slot(painter, QRectF(18, 18, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT), hover=True, pressed=True)
        locked_module = draw_locked_slot(painter, QRectF(210, 18, FACTORY_V2_LOCKED_SLOT_WIDTH, FACTORY_V2_LOCKED_SLOT_HEIGHT), enabled=True)
        draw_build_corner_brackets(painter, QRectF(18, 18, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT), hover=True)
        draw_slot_hazard_footer(painter, QRectF(18, 18, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT), hover=True)
        draw_lock_warning_frame(painter, locked_module, enabled=True)
    finally:
        painter.end()

    rendering_source = inspect.getsource(game_rendering_factory_module)
    build_source = inspect.getsource(game_rendering_factory_module.draw_build_slot)
    locked_source = inspect.getsource(game_rendering_factory_module.draw_locked_slot)
    view_source = inspect.getsource(factory_v2_module)

    assert "def draw_build_corner_brackets" in rendering_source
    assert "def draw_slot_hazard_footer" in rendering_source
    assert "def draw_lock_warning_frame" in rendering_source
    assert "draw_hazard_stripes(" in inspect.getsource(game_rendering_factory_module.draw_slot_hazard_footer)
    assert "GameIcon.BUILD" not in build_source
    assert "draw_build_corner_brackets(painter, pad, hover=hover)" in build_source
    assert "draw_slot_hazard_footer(painter, pad, hover=hover)" in build_source
    assert "draw_lock_warning_frame(painter, module, enabled=enabled)" in locked_source
    assert "GAME_UI_TOKENS.colors.safety_yellow" in view_source
    assert "GAME_UI_TOKENS.colors.warning_orange" in view_source
    assert build_stage.width() >= 70
    assert build_stage.height() >= 70
    assert locked_module.width() > build_stage.width()
    assert _painted_samples(image) > 38


def test_factory_view_v2_rollout_chassis_primitives_paint_distinct_module_families() -> None:
    _app()
    image = QImage(620, 190, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        utility = draw_utility_chassis(painter, QRectF(12, 16, 176, 66), accent=factory_v2_module.Accent.STORAGE, active=True)
        command = draw_command_chassis(painter, QRectF(214, 16, 188, 88), accent=factory_v2_module.Accent.ENERGY, selected=True)
        rank = draw_command_chassis(painter, QRectF(428, 16, 150, 88), accent=factory_v2_module.Accent.CASH, rank=True)
        selection = draw_selection_chassis(painter, QRectF(12, 118, 190, 54), accent=factory_v2_module.Accent.ENERGY, selected=True)
    finally:
        painter.end()

    assert utility.height() < command.height()
    assert rank.width() < command.width()
    assert selection.height() < command.height()
    assert _painted_samples(image) > 28


def test_factory_view_v2_industrial_art_direction_reduces_neon_cyan_materials() -> None:
    rendering_source = inspect.getsource(game_rendering_factory_module)
    v2_source = inspect.getsource(factory_v2_module)

    for source in (rendering_source, v2_source):
        assert "98, 190, 232" not in source
        assert "#62bee8" not in source.lower()
        assert "#69d4ff" not in source.lower()

    energy = factory_v2_module.Accent.ENERGY
    industrial_energy = game_rendering_factory_module.GAME_UI_TOKENS.colors.accent(energy)
    assert industrial_energy.blue() - industrial_energy.red() < 45
    assert industrial_energy.green() - industrial_energy.red() < 35


def test_factory_view_v2_near_future_industrial_reduces_sci_fi_chamfers() -> None:
    rendering_source = inspect.getsource(game_rendering_factory_module)

    assert "min(rect.width(), rect.height()) * 0.13" not in rendering_source
    assert "cut = 9 if compact else 13" not in rendering_source
    assert "painter.drawRoundedRect(top_rect, 5, 5)" in rendering_source
    assert "path = _machine_chassis_path(pad)" in rendering_source
    assert "draw_build_corner_brackets(painter, pad, hover=hover)" in rendering_source

    colors = game_rendering_factory_module.GAME_UI_TOKENS.colors
    energy = colors.accent(factory_v2_module.Accent.ENERGY)
    build = colors.accent(factory_v2_module.Accent.BUILD)
    assert energy.red() > energy.blue()
    assert energy.green() > energy.blue()
    assert build.red() > build.blue()
    assert build.green() > build.blue()


def test_factory_view_v2_category_colors_are_distinct_from_state_colors() -> None:
    colors = game_rendering_factory_module.GAME_UI_TOKENS.colors

    extractor = colors.accent(factory_v2_module.Accent.EXTRACTOR)
    energy = colors.accent(factory_v2_module.Accent.ENERGY)
    processor = colors.accent(factory_v2_module.Accent.PROCESSOR)
    build = colors.accent(factory_v2_module.Accent.BUILD)
    locked = colors.accent(factory_v2_module.Accent.LOCKED)
    running = colors.accent(factory_v2_module.Accent.SUCCESS)

    assert extractor.red() > extractor.blue()
    assert energy.red() > energy.blue()
    assert processor.blue() >= processor.red()
    assert build != locked
    assert running != extractor
    assert running != energy
    assert running != processor


def test_factory_view_v2_atmospheric_wash_uses_multiple_category_families() -> None:
    _app()
    image = QImage(520, 160, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_atmospheric_color_wash(painter, QRectF(8, 8, 504, 144), strength=2, radius=12)
    finally:
        painter.end()

    source = inspect.getsource(game_rendering_factory_module.draw_atmospheric_color_wash)
    assert "Accent.EXTRACTOR" in source
    assert "Accent.PROCESSOR" in source
    assert "Accent.STORAGE" in source
    assert "Accent.ENERGY" in source
    assert "Accent.LOCKED" in source
    assert "zones = (" in source
    assert "for accent, start, end, zone_alpha in zones" in source
    assert _painted_samples(image) > 24


def test_factory_view_v2_distinct_material_zones_replace_global_wash_strategy() -> None:
    _app()
    image = QImage(640, 180, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_industrial_base_surface(painter, QRectF(8, 8, 624, 164), strength=2, radius=12, role="board")
    finally:
        painter.end()

    source = inspect.getsource(game_rendering_factory_module)
    view_source = inspect.getsource(factory_v2_module)
    assert "def draw_distinct_material_zones" in source
    assert "def draw_industrial_base_surface" in source
    assert '"board": (' in source
    assert '"hall": (' in source
    assert '"track": (' in source
    assert '"command": (' in source
    assert "draw_industrial_base_surface(painter, rect.adjusted(4, 4, -4, -4)" in view_source
    assert 'role="board"' in view_source
    assert "draw_hall_control_assembly(painter, rect, variant=1)" in view_source
    assert 'role="track"' in source
    assert 'role="command"' in view_source
    assert "draw_distinct_material_zones(painter, rect.adjusted(4, 4, -4, -4)" not in view_source
    assert "draw_distinct_material_zones(painter, rect.adjusted(9, 9, -9, -9)" not in source
    assert "draw_atmospheric_color_wash(painter, rect.adjusted(4, 4, -4, -4)" not in source
    assert "draw_atmospheric_color_wash(painter, rect.adjusted(9, 9, -9, -9)" not in source
    assert _painted_samples(image) > 24


def test_factory_view_v2_industrial_base_surfaces_avoid_painterly_patches() -> None:
    _app()
    board = QImage(640, 180, QImage.Format.Format_ARGB32_Premultiplied)
    track_a = QImage(640, 180, QImage.Format.Format_ARGB32_Premultiplied)
    track_b = QImage(640, 180, QImage.Format.Format_ARGB32_Premultiplied)
    for image, role, variant in ((board, "board", 0), (track_a, "track", 0), (track_b, "track", 1)):
        image.fill(0)
        painter = QPainter(image)
        try:
            draw_industrial_base_surface(painter, QRectF(8, 8, 624, 164), strength=2, radius=12, role=role, variant=variant)
        finally:
            painter.end()

    base_source = inspect.getsource(game_rendering_factory_module.draw_industrial_base_surface)
    function_source = inspect.getsource(game_rendering_factory_module.draw_distinct_material_zones)
    surface_source = inspect.getsource(game_rendering_factory_module.draw_game_surface)
    track_source = inspect.getsource(game_rendering_factory_module.draw_production_track)
    command_source = inspect.getsource(factory_v2_module.FactoryCommandDeckWidget.paintEvent)
    assert "drawRoundedRect(rect, radius, radius)" in base_source
    assert "draw_distinct_material_zones" not in surface_source
    assert "draw_distinct_material_zones" not in track_source
    assert "draw_distinct_material_zones" not in command_source
    assert "QRadialGradient(zone.center()" not in base_source
    assert "zone = QRectF(rect.left() + rect.width() * start, rect.top(), rect.width() * (end - start), rect.height())" not in function_source
    assert "for x_ratio in (0.22, 0.42, 0.64, 0.80)" not in function_source
    assert '"track-alt"' in base_source
    assert board != track_a
    assert track_a != track_b
    assert _painted_samples(board) > 24
    assert _painted_samples(track_a) > 24
    assert _painted_samples(track_b) > 24


def test_factory_view_v2_semantic_edges_keep_empty_surfaces_neutral() -> None:
    _app()
    source = inspect.getsource(game_rendering_factory_module)
    view_source = inspect.getsource(factory_v2_module)
    track_surface_source = inspect.getsource(game_materials_module.draw_track_surface)
    glow_edge_source = inspect.getsource(game_materials_module.draw_glow_edge)
    theme_source = APP_STYLESHEET

    assert "neutral_edge" in inspect.getsource(game_rendering_factory_module.GAME_UI_TOKENS.colors.__class__)
    assert "draw_game_panel(painter, rect, accent=Accent.NEUTRAL" in view_source
    assert "draw_hall_control_assembly(painter, rect, variant=1)" in view_source
    assert "header_panel = rect.adjusted(16, 14, -16, -14)" in view_source
    assert "draw_game_surface(painter, rect, accent=Accent.NEUTRAL, radius=18, depth=1, role=\"board\")" in view_source
    assert "draw_hall_control_assembly(painter, rect, variant=1)" in view_source
    assert "draw_track_surface(painter, rect, accent=Accent.NEUTRAL" in view_source
    assert "draw_game_surface(painter, rect, accent=Accent.NEUTRAL, depth=0, radius=18, role=\"track\"" in source
    assert "accent: Accent = Accent.NEUTRAL" in track_surface_source
    assert "if accent == Accent.NEUTRAL and state == InteractionState.NORMAL" in glow_edge_source
    assert "QFrame#factoryCommandDivider" in theme_source
    assert "rgba(242, 194, 91, 48)" not in theme_source
    assert "QTreeWidget#hallTreeV2::item:selected" in theme_source
    assert "border-color: rgba(242, 194, 91, 100)" not in theme_source


def test_factory_view_v2_chassis_edges_are_neutral_with_local_accents() -> None:
    _app()
    command_source = inspect.getsource(game_rendering_factory_module.draw_command_chassis)
    utility_source = inspect.getsource(game_rendering_factory_module.draw_utility_chassis)
    machine_source = inspect.getsource(game_rendering_factory_module.draw_machine_card)
    build_source = inspect.getsource(game_rendering_factory_module.draw_build_slot)
    locked_source = inspect.getsource(game_rendering_factory_module.draw_locked_slot)
    theme_source = APP_STYLESHEET

    assert "neutral_edge_secondary" in inspect.getsource(game_rendering_factory_module.GAME_UI_TOKENS.colors.__class__)
    assert "painter.setPen(QPen(_accent(accent, 142 if selected else 96)" in command_source
    assert "painter.setPen(QPen(_neutral_edge_highlight(88 if active or warning else 56)" in utility_source
    assert "painter.setPen(QPen(_neutral_edge_highlight(86 + int(lift * 18))" in machine_source
    assert "painter.setBrush(_accent(accent, 62 + int(lift * 22)))" in machine_source
    assert "draw_build_corner_brackets(painter, pad, hover=hover)" in build_source
    assert "draw_slot_hazard_footer(painter, pad, hover=hover)" in build_source
    assert "painter.setPen(QPen(_safety_yellow" in build_source
    assert "draw_lock_warning_frame(painter, module, enabled=enabled)" in locked_source
    assert "painter.setPen(QPen(_warning_orange" in locked_source
    assert "painter.setBrush(_warning_orange" in locked_source
    assert "QPushButton#buildHallButtonV2" in theme_source
    assert "border: 1px solid rgba(216, 240, 106, 106)" not in theme_source
    assert "border: 2px solid rgba(7, 8, 7, 238)" in theme_source


def test_factory_view_v2_uses_light_industrial_chassis_with_dark_recessed_modules() -> None:
    _app()
    token_source = inspect.getsource(game_rendering_factory_module.GAME_UI_TOKENS.colors.__class__)
    rendering_source = inspect.getsource(game_rendering_factory_module)
    materials_source = inspect.getsource(game_materials_module.draw_game_panel)
    inset_source = inspect.getsource(game_materials_module.draw_inset_surface)
    view_source = inspect.getsource(factory_v2_module)
    theme_source = APP_STYLESHEET

    assert "chassis_light" in token_source
    assert "chassis_mid" in token_source
    assert "chassis_shadow" in token_source
    assert "recessed_dark" in token_source
    assert "recessed_edge" in token_source
    assert "base_top = tokens.colors.qcolor(tokens.colors.chassis_light)" in materials_source
    assert "base_bottom = tokens.colors.qcolor(tokens.colors.chassis_shadow)" in materials_source
    assert "tokens.colors.qcolor(tokens.colors.recessed_dark" in inset_source
    assert "QColor(230, 228, 216, 150)" in rendering_source
    assert "QColor(226, 224, 214, 212 + depth * 10)" in rendering_source
    assert "QColor(38, 45, 45, 168 if active else 146)" in rendering_source
    assert "def draw_hall_control_assembly" in rendering_source
    assert "GAME_UI_TOKENS.typography.brand_display()" in view_source
    assert "GAME_UI_TOKENS.typography.industrial_title()" in view_source
    assert 'font-family: "Bahnschrift Condensed", "Bahnschrift SemiCondensed", "Agency FB", "Arial Narrow", "Bahnschrift", "Segoe UI"' in theme_source
    assert "QFrame#factoryV2Sidebar" in theme_source
    assert "stop:0 #d3d2c8" in theme_source


def test_factory_view_v2_safety_identity_uses_warning_plates_hazard_and_leds() -> None:
    _app()
    image = QImage(420, 150, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_hazard_stripes(painter, QRectF(8, 8, 170, 24), stripe_width=8, radius=3)
        draw_warning_plate(painter, QRectF(8, 48, 142, 34), text="LINE 01")
        draw_status_led(painter, QRectF(8, 100, 94, 24), active=True)
    finally:
        painter.end()

    token_source = inspect.getsource(game_rendering_factory_module.GAME_UI_TOKENS.colors.__class__)
    rendering_source = inspect.getsource(game_rendering_factory_module)
    view_source = inspect.getsource(factory_v2_module)
    theme_source = APP_STYLESHEET

    assert "safety_yellow" in token_source
    assert "area_anchor_red" in token_source
    assert "warning_orange" in token_source
    assert "def draw_hazard_stripes" in rendering_source
    assert "def draw_warning_plate" in rendering_source
    assert "_area_anchor_red(252 if selected else 210)" in rendering_source
    assert "def _warning_red" not in rendering_source
    assert "def draw_status_led" in rendering_source
    assert "draw_hazard_stripes(" in view_source
    assert "primary=QColor(200, 42, 32, 246)" in view_source
    assert "secondary=QColor(246, 240, 226, 218)" in view_source
    assert "class FactoryV2LinePlate" in view_source
    assert "draw_warning_plate(painter" in view_source
    assert "class FactoryV2ActiveIndicator" in view_source
    assert "draw_status_led(painter" in view_source
    assert "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe764" in theme_source
    assert "border-color: rgba(255, 210, 31, 230)" in theme_source
    assert _painted_samples(image) > 20


def test_factory_view_v2_mockup_alignment_uses_harder_chassis_and_local_module_colors() -> None:
    _app()
    token_source = inspect.getsource(game_rendering_factory_module.GAME_UI_TOKENS.colors.__class__)
    rendering_source = inspect.getsource(game_rendering_factory_module)
    view_source = inspect.getsource(factory_v2_module)
    theme_source = APP_STYLESHEET

    assert 'chassis_light: str = "#d8d6cd"' in token_source
    assert 'chassis_mid: str = "#a7aaa0"' in token_source
    assert 'cash: str = "#7fed18"' in token_source
    assert 'storage: str = "#25b9e8"' in token_source
    assert "QColor(230, 228, 216, 150)" in rendering_source
    assert "QColor(34, 40, 40, 224 if selected else 206)" in rendering_source
    assert "QColor(226, 48, 34, 252 if selected else 208)" in rendering_source
    assert "rect.bottom() - 42" in view_source
    assert "rect.width() * 0.16" in view_source
    assert "stripe_width=18" in view_source
    assert "QLabel#factoryV2CashLabel" in theme_source
    assert "QLabel#factoryV2EnergyLabel" in theme_source
    assert "QLabel#factoryV2StorageLabel" in theme_source
    assert "color: #080908" in theme_source
    assert "stop:0 #d3d2c8" in theme_source
    assert "stop:0 #fff06f" in theme_source


def test_factory_view_v2_typography_uses_condensed_industrial_hierarchy() -> None:
    tokens = game_rendering_factory_module.GAME_UI_TOKENS
    token_source = inspect.getsource(tokens.typography.__class__)
    theme_source = APP_STYLESHEET

    assert "Bahnschrift Condensed" in tokens.typography.family
    assert "Bahnschrift SemiCondensed" in tokens.typography.family
    assert "Agency FB" in tokens.typography.family
    assert tokens.typography.brand_display().stretch() == 68
    assert tokens.typography.industrial_title().stretch() == 72
    assert tokens.typography.industrial_label().stretch() == 84
    assert tokens.typography.status_label().stretch() == 84
    assert tokens.typography.micro_label().stretch() == 90
    assert "font.setStretch(68)" in token_source
    assert "font.setStretch(72)" in token_source
    assert 'QLabel#factoryV2DeckTitle' in theme_source
    assert "font-size: 40px" in theme_source
    assert "font-size: 25px" in theme_source
    assert "font-" + "stretch" not in theme_source
    assert "QPushButton#productionGuideButton" in theme_source
    assert 'font-family: "Bahnschrift Condensed"' in theme_source
    assert "QLabel#factoryV2NavTitle" in theme_source
    assert "QLabel#factoryV2NavSubtitle" in theme_source
    assert "QLabel#factoryV2NavTitle {\n    background: transparent;\n    color: #090a08;\n    font-family: \"Bahnschrift Condensed\", \"Bahnschrift SemiCondensed\", \"Agency FB\", \"Arial Narrow\", \"Bahnschrift\", \"Segoe UI\";\n    font-size: 42px;" in theme_source
    assert "QLabel#factoryV2NavSubtitle {\n    background: transparent;\n    color: #c83a2b;\n    font-family: \"Bahnschrift Condensed\", \"Bahnschrift SemiCondensed\", \"Agency FB\", \"Arial Narrow\", \"Bahnschrift\", \"Segoe UI\";\n    font-size: 16px;" in theme_source
    assert "QTreeWidget#hallTreeV2 {\n    background: rgba(8, 13, 14, 178);" in theme_source
    assert "QTreeWidget#hallTreeV2" in theme_source and "font-size: 19px;" in theme_source
    assert "QTreeWidget#hallTreeV2::item {\n    padding: 24px 14px;" in theme_source


def test_factory_view_v2_material_polish_uses_deterministic_wear_bolts_and_seams() -> None:
    _app()
    first = QImage(420, 220, QImage.Format.Format_ARGB32_Premultiplied)
    second = QImage(420, 220, QImage.Format.Format_ARGB32_Premultiplied)
    for image in (first, second):
        image.fill(0)
        painter = QPainter(image)
        try:
            draw_game_surface(painter, QRectF(8, 8, 170, 92), accent=factory_v2_module.Accent.NEUTRAL, role="command", depth=2)
            draw_surface_wear(painter, QRectF(16, 16, 150, 74), seed=123, density=5)
            draw_panel_bolts(painter, QRectF(190, 8, 96, 92), inset=10, radius=3)
            draw_panel_bolt(painter, QPoint(326, 30), radius=3)
            draw_panel_seam(painter, QPoint(304, 70), QPoint(388, 70), accent=factory_v2_module.Accent.ENERGY)
            draw_industrial_edge(painter, QRectF(300, 104, 96, 84), radius=10)
            draw_hazard_stripes(painter, QRectF(16, 130, 180, 16), stripe_width=8, radius=3)
            draw_warning_plate(painter, QRectF(214, 130, 142, 34), text="LINE 01")
            draw_build_slot(painter, QRectF(16, 150, 92, 62), hover=True)
            draw_locked_slot(painter, QRectF(126, 150, 92, 62), enabled=True)
        finally:
            painter.end()

    source = inspect.getsource(game_rendering_factory_module)
    build_source = inspect.getsource(game_rendering_factory_module.draw_build_slot)
    locked_source = inspect.getsource(game_rendering_factory_module.draw_locked_slot)
    base_source = inspect.getsource(game_rendering_factory_module.draw_industrial_base_surface)
    surface_source = inspect.getsource(game_rendering_factory_module.draw_game_surface)
    command_source = inspect.getsource(game_rendering_factory_module.draw_command_chassis)

    assert first == second
    assert "def draw_panel_bolt" in source
    assert "def draw_panel_bolts" in source
    assert "def draw_surface_wear" in source
    assert "def draw_panel_seam" in source
    assert "def draw_industrial_edge" in source
    assert "draw_surface_wear(painter, rect.adjusted(10, 8, -10, -8)" in base_source
    assert "draw_industrial_edge(painter, rect, radius=radius, inset=2)" in surface_source
    assert "draw_panel_seam(" in surface_source
    assert "draw_panel_bolts(painter, panel, inset=7" in command_source
    assert "draw_surface_wear(painter, pad.adjusted(13, 15, -13, -28)" in build_source
    assert "draw_panel_bolts(painter, pad, inset=12" in build_source
    assert "draw_surface_wear(painter, module.adjusted(13, 18, -13, -22)" in locked_source
    assert "draw_panel_bolts(painter, module, inset=9" in locked_source
    assert _painted_samples(first) > 40


def test_factory_view_v2_material_hierarchy_keeps_passive_surfaces_matte_and_gameplay_edges_crisp() -> None:
    _app()
    base_source = inspect.getsource(game_rendering_factory_module.draw_industrial_base_surface)
    surface_source = inspect.getsource(game_rendering_factory_module.draw_game_surface)
    track_source = inspect.getsource(game_rendering_factory_module.draw_production_track)
    command_source = inspect.getsource(game_rendering_factory_module.draw_command_chassis)
    build_source = inspect.getsource(game_rendering_factory_module.draw_build_slot)
    locked_source = inspect.getsource(game_rendering_factory_module.draw_locked_slot)
    materials_source = inspect.getsource(game_materials_module.draw_game_panel)
    view_source = inspect.getsource(factory_v2_module)
    theme_source = APP_STYLESHEET

    hall_assembly_source = inspect.getsource(game_rendering_factory_module.draw_hall_control_assembly)

    assert "QColor(255, 255, 248, 9 + strength * 3)" in base_source
    assert "QColor(255, 255, 246, 8 + depth * 3)" in surface_source
    assert "QColor(0, 0, 0, 30 + depth * 5)" in surface_source
    assert "def draw_hall_control_assembly" in hall_assembly_source
    assert "QColor(76, 82, 79, 242)" in hall_assembly_source
    assert "QColor(35, 42, 41, 248)" in hall_assembly_source
    assert "top_reflection = QLinearGradient" in hall_assembly_source
    assert "QColor(255, 255, 246, 30)" in hall_assembly_source
    assert "accent_bar_rect = QRectF(panel.left() + 18, panel.top() + 13, panel.width() * 0.56, 3)" in hall_assembly_source
    assert "draw_panel_seam(" not in hall_assembly_source
    assert "rail_top = QRectF" in track_source
    assert "rail_bottom = QRectF" in track_source
    assert "QColor(18, 22, 21, 184)" in track_source
    assert "QColor(8, 11, 11, 204)" in track_source
    assert "QColor(238, 232, 212, 5)" in track_source
    assert "QColor(246, 244, 229, 78)" in track_source
    assert "QPen(_accent(accent, 142 if selected else 96), 1.45)" in command_source
    assert "QPen(_safety_yellow(210 + int(lift * 38)), 2.35)" in build_source
    assert "QPen(_warning_orange(204 if enabled else 154), 1.85)" in locked_source
    assert "edge_alpha = 56 if accent == Accent.NEUTRAL else 88" in materials_source
    assert "tokens.colors.accent(accent, 54 if state != InteractionState.PRESSED else 34)" in materials_source
    assert "GameButton(\"Expand\", variant=\"primary\", accent=Accent.BUILD)" in view_source
    assert "FactoryV2CommandButton(\"Production Guide\", accent=Accent.BUILD)" in view_source
    assert "super().__init__(text, variant=\"primary\", accent=accent)" in view_source
    assert "right_stack.setContentsMargins(0, 8, 0, 0)" in view_source
    assert "rect.width() * 0.16" in view_source
    assert "QPushButton#expandResourceStorageButton[factoryV2StorageCta=\"true\"]" in theme_source
    assert "QPushButton#productionGuideButton" in theme_source
    assert "background: qlineargradient" in theme_source


def test_factory_view_v2_machine_card_prototype_renders_five_family_signage_cards() -> None:
    _app()
    cards = (
        ("Extractor", "extractor", "Machine · MK I", "Output 60/min"),
        ("Processor", "processor", "Machine · MK I", "Power 12 MW"),
        ("Assembler", "assembly", "Machine · MK I", "Input 2x"),
        ("Solar Array", "energy", "Energy · MK I", "+25 MW"),
        ("Freight Truck", "transport", "Logistics · MK I", "Capacity 20"),
    )
    image = QImage(920, 300, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        for index, (title, family, meta, detail) in enumerate(cards):
            draw_machine_card_prototype(
                painter,
                QRectF(18 + index * 178, 22, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT),
                title=title,
                family=family,
                meta=meta,
                detail=detail,
                active=index == 0,
            )
    finally:
        painter.end()

    source = inspect.getsource(game_rendering_factory_module.draw_machine_card_prototype)
    icon_source = inspect.getsource(game_rendering_factory_module._draw_prototype_pictogram)
    family_source = inspect.getsource(game_rendering_factory_module)
    runtime_source = inspect.getsource(FactoryV2MachineCard)
    preview = _save_preview(image, "factory_view_v2_machine_card_prototype_preview.png")

    assert '"extractor": QColor("#d8a642")' in family_source
    assert '"processor": QColor("#df6b2f")' in family_source
    assert '"assembly": QColor("#c83a2b")' in family_source
    assert '"energy": QColor("#ffd21f")' in family_source
    assert '"transport": QColor("#25b9e8")' in family_source
    assert "body = QLinearGradient(rect.topLeft(), rect.bottomRight())" in source
    assert "sign = QRectF(rect.left() + 14, rect.top() + 54" in source
    assert "header_title = QRectF" in source
    assert "main_info = QRectF" in source
    assert "secondary_info = QRectF" in source
    assert "max_cell=1.12" in source
    assert 'QColor("#d6e2dd")' in source
    assert "align=Qt.AlignmentFlag.AlignHCenter" in source
    assert "draw_panel_bolts(painter, rect, inset=10" in source
    assert "_accent(Accent.BUILD" not in source
    assert "drawLine(sign.left()" not in source
    assert "_point(rect, 0.18, 0.18)" not in icon_source
    assert "secondary_control" in source
    assert "draw_machine_card_prototype" in runtime_source
    for family in ("extractor", "processor", "assembly", "energy", "transport"):
        assert f'family == "{family}"' in icon_source
    assert preview.exists()
    assert _painted_samples(image) > 60


def test_factory_view_v2_machine_category_accent_mapping_is_type_based() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "test-furnace-common-001"))
    view = FactoryViewV2(state, bus, definitions)

    cards = {card._card.card_id: card for card in view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard")}

    assert accent_for_definition(cards["test-drill-common-001"]._definition) == factory_v2_module.Accent.EXTRACTOR
    assert accent_for_definition(cards["test-solar-common-001"]._definition) == factory_v2_module.Accent.ENERGY
    assert accent_for_definition(cards["test-furnace-common-001"]._definition) == factory_v2_module.Accent.PROCESSOR
    assert prototype_family_for_definition(cards["test-drill-common-001"]._definition) == "extractor"
    assert prototype_family_for_definition(cards["test-solar-common-001"]._definition) == "energy"
    assert prototype_family_for_definition(cards["test-furnace-common-001"]._definition) == "processor"


def test_factory_view_v2_machine_card_visual_hierarchy_exposes_primary_message() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    view = FactoryViewV2(state, bus, definitions)

    machine_cards = view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard")
    assert len(machine_cards) >= 2
    extractor = next(card for card in machine_cards if card._card.card_id == "test-drill-common-001")
    solar = next(card for card in machine_cards if card._card.card_id == "test-solar-common-001")

    assert extractor._primary_value_text() == "SELECT"
    assert extractor._primary_caption_text() == "NO RESOURCE SELECTED"
    assert extractor._title_text() == "EXTRACTOR"
    assert extractor._meta_text() == "MK1 · COMMON"
    assert solar._primary_value_text().endswith("MW")
    assert solar._status_text() == "ONLINE"
    assert solar._title_text() == "SOLAR ARRAY"
    assert solar._shows_cycle_progress() is False

    for card in (extractor, solar):
        image = _render_widget(card, 220, 224)
        assert _painted_samples(image) > 24


def test_factory_view_v2_machine_cards_show_selected_runtime_resource(monkeypatch) -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "test-furnace-common-001"))
    bus.dispatch(SelectMachineProduction("test-drill-common-001", "recipe.extract.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("test-furnace-common-001", "recipe.processor.iron", "iron"))
    calls = []

    original = factory_v2_module.draw_machine_card_prototype

    def recorder(painter, rect, **kwargs):
        calls.append(dict(kwargs))
        original(painter, rect, **kwargs)

    monkeypatch.setattr(factory_v2_module, "draw_machine_card_prototype", recorder)
    view = FactoryViewV2(state, bus, definitions)
    machine_cards = view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard")

    for card in machine_cards:
        _render_widget(card, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)

    by_title = {call["title"]: call for call in calls}
    assert by_title["EXTRACTOR"]["secondary"] == "IRON ORE >"
    assert by_title["PROCESSOR"]["secondary"] == "IRON >"
    assert by_title["EXTRACTOR"]["detail"].endswith("/CYCLE")
    assert by_title["PROCESSOR"]["detail"].endswith("/CYCLE")


def test_factory_view_v2_machine_resource_inset_replaces_circular_selector() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    view = FactoryViewV2(state, bus, definitions)
    card = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    emitted: list[str] = []

    class ClickEvent:
        def __init__(self, position):
            self._position = position

        def button(self):
            return Qt.MouseButton.LeftButton

        def position(self):
            return self._position

    assert card is not None
    assert card._production_change_available() is True
    assert card._resource_control_rect().width() > 80
    assert card._resource_control_rect().height() >= 18
    card.production_change_requested.connect(emitted.append)
    card.mousePressEvent(ClickEvent(card._resource_control_rect().center()))

    paint_source = inspect.getsource(FactoryV2MachineCard.paintEvent)
    assert emitted == ["test-drill-common-001"]
    assert "drawEllipse" not in paint_source
    assert "_config_rect" not in inspect.getsource(FactoryV2MachineCard)


def test_factory_view_v2_machine_card_runtime_zones_do_not_overlap() -> None:
    source = inspect.getsource(game_rendering_factory_module.draw_machine_card_prototype)
    runtime_source = inspect.getsource(FactoryV2MachineCard.paintEvent)

    assert "sign = QRectF(rect.left() + 14, rect.top() + 54" in source
    assert "main_info = QRectF(rect.left() + 14, sign.bottom() + 7" in source
    assert "secondary_info = QRectF(rect.left() + 14, sign.bottom() + 24" in source
    assert "progress = QRectF(rect.left() + 18, footer.top() - 7" in runtime_source
    assert "footer = QRectF(rect.left() + 10, rect.bottom() - 27" in runtime_source


def test_factory_view_v2_active_machine_card_polish_keeps_geometry_and_content_focus() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-furnace-common-001"))
    bus.dispatch(SelectMachineProduction("test-furnace-common-001", "recipe.processor.iron", "iron"))
    processor_state = state.machine_production["test-furnace-common-001"]
    processor_state.progress_seconds = 1.0
    processor_state.status = "running"
    view = FactoryViewV2(state, bus, definitions)

    card = next(card for card in view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard") if card._card.card_id == "test-furnace-common-001")
    image = _render_widget(card, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)

    assert card.width() == FACTORY_V2_CARD_WIDTH
    assert card.height() == FACTORY_V2_CARD_HEIGHT
    assert card._title_text() == "PROCESSOR"
    assert card._meta_text() == "MK1 · COMMON"
    assert card._prototype_secondary_text() == "IRON >"
    assert card._status_text() == "RUNNING"
    assert card._primary_value_text().startswith("+")
    assert card._primary_caption_text()
    assert card._shows_cycle_progress() is True
    assert _painted_samples(image) > 24


def test_factory_view_v2_machine_card_progress_reads_existing_runtime_state() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-furnace-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(SelectMachineProduction("test-furnace-common-001", "recipe.processor.iron", "iron"))
    processor_state = state.machine_production["test-furnace-common-001"]
    processor_state.progress_seconds = 1.5
    processor_state.status = "running"
    view = FactoryViewV2(state, bus, definitions)

    processor = next(card for card in view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard") if card._card.card_id == "test-furnace-common-001")
    solar = next(card for card in view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard") if card._card.card_id == "test-solar-common-001")
    production = processor._active_production()

    assert production is not None
    assert processor._shows_cycle_progress() is True
    assert processor._cycle_progress_ratio() == processor_state.progress_seconds / production.cycle_seconds_for(processor._definition)
    assert solar._shows_cycle_progress() is False
    assert solar._cycle_progress_ratio() == 0.0


def test_factory_view_v2_build_and_locked_slots_render_as_game_targets() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    view = FactoryViewV2(state, bus, definitions)

    build_slot = view.findChild(QWidget, "factoryV2BuildSlot")
    locked_slot = view.findChild(FactoryV2LockedSlot, "lockedSlotPanel")

    assert build_slot is not None
    assert build_slot.width() == FACTORY_V2_CARD_WIDTH
    assert build_slot.height() == FACTORY_V2_CARD_HEIGHT
    assert locked_slot is not None
    assert locked_slot.width() == FACTORY_V2_CARD_WIDTH == FACTORY_V2_LOCKED_SLOT_WIDTH
    assert locked_slot.height() == FACTORY_V2_CARD_HEIGHT == FACTORY_V2_LOCKED_SLOT_HEIGHT
    assert locked_slot.property("slotNumber") is not None
    assert locked_slot.property("unlockCost") is not None
    assert build_slot.__class__.__name__ == "FactoryV2BuildSlot"

    assert _painted_samples(_render_widget(build_slot, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)) > 24
    assert _painted_samples(_render_widget(locked_slot, FACTORY_V2_LOCKED_SLOT_WIDTH, FACTORY_V2_LOCKED_SLOT_HEIGHT)) > 16


def test_factory_view_v2_cards_use_compact_module_proportions_in_tracks() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(SelectMachineProduction("test-drill-common-001", "recipe.extract.iron_ore", "iron_ore"))
    view = FactoryViewV2(state, bus, definitions)

    machine = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    build_slot = view.findChild(QWidget, "factoryV2BuildSlot")
    locked_slot = view.findChild(FactoryV2LockedSlot, "lockedSlotPanel")
    track = view.findChild(FactoryV2TrackPanel, "factoryV2ProductionTrack")

    assert machine is not None
    assert build_slot is not None
    assert locked_slot is not None
    assert track is not None
    assert machine.width() == FACTORY_V2_CARD_WIDTH
    assert machine.height() == FACTORY_V2_CARD_HEIGHT
    assert build_slot.size() == machine.size()
    assert machine.width() < 170
    assert machine.height() > 220
    assert locked_slot.size() == machine.size()
    assert track.minimumHeight() >= FACTORY_V2_CARD_HEIGHT + 56


def test_factory_view_v2_cards_build_and_locked_slots_share_raised_baseline() -> None:
    app = _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    view = FactoryViewV2(state, bus, definitions)

    _render_widget(view, 1920, 1080)
    app.processEvents()
    track = view.findChild(FactoryV2TrackPanel, "factoryV2ProductionTrack")
    machine = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    build_slot = view.findChild(QWidget, "factoryV2BuildSlot")
    locked_slot = view.findChild(FactoryV2LockedSlot, "lockedSlotPanel")

    assert track is not None
    assert machine is not None
    assert build_slot is not None
    assert locked_slot is not None
    assert machine.y() == build_slot.y() == locked_slot.y()
    assert machine.y() <= 58
    assert "layout.setSpacing(6)" in inspect.getsource(factory_v2_module.FactoryViewV2._build_line_panel)


def test_factory_view_v2_command_deck_groups_primary_systems_operations_and_rank() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    deck = FactoryCommandDeckWidget(state, len(definitions), resource_definitions, bus, None)

    assert deck.objectName() == "factoryV2CommandDeck"
    assert deck.findChild(QFrame, "factoryV2PrimarySystems") is not None
    assert deck.findChild(QFrame, "factoryV2ResourceStrip") is not None
    assert deck.findChild(QFrame, "factoryV2ProgressionZone") is not None
    assert deck.findChild(QFrame, "factoryV2RankEmblem") is not None
    assert isinstance(deck.findChild(QFrame, "factoryV2PrimarySystems"), FactoryV2CommandModule)
    assert isinstance(deck.findChild(QFrame, "factoryV2ResourceStrip"), FactoryV2CommandModule)
    assert isinstance(deck.findChild(QFrame, "factoryV2ProgressionZone"), FactoryV2CommandModule)
    assert isinstance(deck.findChild(QFrame, "factoryV2RankEmblem"), FactoryV2CommandModule)
    assert deck.findChild(QFrame, "factoryV2StorageModule") is not None
    assert deck.findChild(QFrame, "factoryV2PrimarySystems")._accent == factory_v2_module.Accent.STORAGE
    assert deck.findChild(QFrame, "factoryV2ResourceStrip")._accent == factory_v2_module.Accent.PROCESSOR
    assert deck.findChild(QLabel, "factoryV2OperationsLabel").text() == "GLOBAL OPERATIONS"
    assert deck.findChild(QLabel, "factoryV2OperationsHint").text() == "READY FOR FACTORY-WIDE SIGNALS"
    assert deck.findChild(QLabel, "factoryV2ResourceName") is None
    assert deck.findChild(QLabel, "factoryV2ResourceAmount") is None
    storage_button = deck.findChild(GameButton, "expandResourceStorageButton")
    assert storage_button is not None
    assert storage_button.accent == factory_v2_module.Accent.BUILD
    assert storage_button.variant == "primary"
    assert storage_button.property("factoryV2StorageCta") is True
    assert "text_color = \"#10120a\"" in inspect.getsource(GameButton)
    deck_source = inspect.getsource(FactoryCommandDeckWidget)
    assert "rect.width() * 0.16" in deck_source
    assert "stripe_width=18" in deck_source
    image = _render_widget(deck, 1920, 132)
    assert image.width() == 1920
    assert image.height() == 132
    assert _painted_samples(image) > 30


def test_factory_view_v2_topbar_primary_values_are_readable_without_overlap() -> None:
    app = _app()
    state, definitions, bus = _state_defs_bus()
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    deck = FactoryCommandDeckWidget(state, len(definitions), resource_definitions, bus, None)

    _render_widget(deck, 1920, 148)
    app.processEvents()

    labels = [
        deck.findChild(QLabel, "factoryV2CashValue"),
        deck.findChild(QLabel, "factoryV2EnergyValue"),
        deck.findChild(QLabel, "factoryV2StorageValue"),
    ]
    assert all(label is not None for label in labels)
    for label in labels:
        assert label.text()
        assert label.fontMetrics().horizontalAdvance(label.text()) <= label.rect().width()
        assert label.fontMetrics().boundingRect(label.text()).height() <= label.rect().height()

    value_rects = []
    for label in labels:
        top_left = label.mapTo(deck, label.rect().topLeft())
        value_rects.append(label.rect().translated(top_left))
    for index, rect in enumerate(value_rects):
        for other in value_rects[index + 1 :]:
            assert not rect.intersects(other)

    cash_rect, energy_rect, _storage_rect = value_rects
    assert abs(cash_rect.center().y() - energy_rect.center().y()) <= 3
    assert abs(cash_rect.height() - energy_rect.height()) <= 2

    cash_metric = deck.findChild(QLabel, "factoryV2CashValue").parentWidget()
    energy_metric = deck.findChild(QLabel, "factoryV2EnergyValue").parentWidget()
    assert cash_metric is not None
    assert energy_metric is not None
    assert cash_metric.objectName() == "factoryV2Metric"
    assert energy_metric.objectName() == "factoryV2Metric"
    assert abs(cash_metric.width() - energy_metric.width()) <= 4


def test_factory_view_v2_command_deck_storage_rank_and_branding_are_clean() -> None:
    app = _app()
    state, definitions, bus = _state_defs_bus()
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    deck = FactoryCommandDeckWidget(state, len(definitions), resource_definitions, bus, None)

    image = _render_widget(deck, 1920, 148)
    app.processEvents()

    assert deck.findChild(QLabel, "factoryV2DeckSubtitle") is None
    assert all("deterministic industry" not in label.text() for label in deck.findChildren(QLabel))
    assert all("cards ·" not in label.text() for label in deck.findChildren(QLabel))
    assert deck.findChild(QLabel, "factoryV2DeckTitle").text() == "PRODUCTION ZERO"
    assert deck.findChild(QLabel, "factoryV2Level").text() == "LEVEL 1"
    assert deck.findChild(QLabel, "factoryV2RankTitle").text() == "FOUNDER"
    assert deck.findChild(QFrame, "factoryV2RankEmblem") is not None
    assert isinstance(deck.findChild(QFrame, "factoryV2StorageModule"), FactoryV2CommandModule)

    storage_icon = deck.findChild(QWidget, "factoryV2StorageIcon")
    storage_label = deck.findChild(QLabel, "factoryV2StorageLabel")
    storage_value = deck.findChild(QLabel, "factoryV2StorageValue")
    storage_button = deck.findChild(GameButton, "expandResourceStorageButton")
    rank_emblem = deck.findChild(QFrame, "factoryV2RankEmblem")
    rank_icon = deck.findChild(QWidget, "factoryV2RankIcon")
    level = deck.findChild(QLabel, "factoryV2Level")
    rank_title = deck.findChild(QLabel, "factoryV2RankTitle")
    xp = deck.findChild(QLabel, "factoryV2Xp")
    assert storage_label is not None
    assert storage_value is not None
    assert storage_button is not None
    assert storage_icon is not None
    assert rank_emblem is not None
    assert rank_icon is not None
    assert level is not None
    assert rank_title is not None
    assert xp is not None
    assert storage_button.height() >= 34
    storage_module = deck.findChild(QFrame, "factoryV2StorageModule")
    progression_zone = deck.findChild(QFrame, "factoryV2ProgressionZone")
    assert storage_module is not None
    assert progression_zone is not None
    assert storage_icon.mapTo(storage_module, storage_icon.rect().topLeft()).y() == 12
    assert storage_label.mapTo(storage_module, storage_label.rect().topLeft()).y() == 12
    assert storage_value.mapTo(storage_module, storage_value.rect().topLeft()).y() > storage_label.mapTo(storage_module, storage_label.rect().topLeft()).y()
    assert storage_button.mapTo(storage_module, storage_button.rect().topLeft()).y() == 54
    assert rank_emblem.width() == 82
    assert rank_icon.width() == 64
    assert rank_emblem.width() >= 2 * 42 - 2
    assert level.mapTo(deck, level.rect().topLeft()).x() > rank_emblem.mapTo(deck, rank_emblem.rect().topLeft()).x() + rank_emblem.width()
    assert level.mapTo(progression_zone, level.rect().topLeft()).y() == 15
    assert rank_title.mapTo(progression_zone, rank_title.rect().topLeft()).y() > level.mapTo(progression_zone, level.rect().topLeft()).y()
    assert xp.mapTo(progression_zone, xp.rect().topLeft()).y() > rank_title.mapTo(progression_zone, rank_title.rect().topLeft()).y()

    for label in (storage_label, storage_value):
        bounding = label.fontMetrics().boundingRect(label.text())
        assert bounding.height() <= label.rect().height()
        assert label.fontMetrics().horizontalAdvance(label.text()) <= label.rect().width()

    button_text = storage_button._text.upper()
    assert storage_button.fontMetrics().horizontalAdvance(button_text) <= storage_button.rect().width() - 16
    assert _bright_corner_pixels(image, margin=8) <= 24


def test_factory_view_v2_utility_panels_and_guide_use_rollout_runtime_widgets() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(SelectMachineProduction("test-drill-common-001", "recipe.extract.iron_ore", "iron_ore"))
    view = FactoryViewV2(state, bus, definitions)

    image = _render_widget(view, 1920, 1080)

    summary = view.findChild(FactoryV2HallResourceSummaryWidget, "hallResourceSummary")
    guide = view.findChild(FactoryV2CommandButton, "productionGuideButton")
    kpi = view.findChild(FactoryV2KpiStripWidget, "hallKpiStrip")
    utility_items = view.findChildren(QFrame, "hallResourceSummaryItem")

    assert summary is not None
    assert guide is not None
    assert kpi is not None
    assert utility_items
    assert "productionGuideButton" in inspect.getsource(FactoryV2CommandButton)
    assert "super().__init__(text, variant=\"primary\", accent=accent)" in inspect.getsource(FactoryV2CommandButton)
    assert "super().paintEvent(event)" in inspect.getsource(FactoryV2CommandButton)
    button_source = inspect.getsource(GameButton.paintEvent)
    assert "GAME_UI_TOKENS.typography.industrial_title()" in button_source
    assert "font.setPointSize(12 if self.height() <= 38 else 14)" in button_source
    assert "font.setWeight(font.Weight.Black)" in button_source
    hall_source = inspect.getsource(FactoryV2HallStage)
    assert "header_panel = rect.adjusted(16, 14, -16, -14)" in hall_source
    assert "header_panel.width() * 0.62" not in hall_source
    assert "header_panel.bottom() - 18" not in hall_source
    assert "header_body.setColorAt" not in inspect.getsource(FactoryV2HallStage)
    assert all(item.property("factoryV2Utility") is True for item in utility_items)
    assert _painted_samples(image) > 100


def test_factory_view_v2_track_lines_stay_inside_rounded_panel_corners() -> None:
    _app()
    track = FactoryV2TrackPanel(1, "Production Line 01")

    image = _render_widget(track, 960, track.minimumHeight())

    assert _painted_samples(image) > 30
    assert _bright_corner_pixels(image, margin=10) <= 64


def test_factory_view_v2_hall_overview_is_compact_and_stage_text_fits() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    view = FactoryViewV2(state, bus, definitions)
    image = _render_widget(view, 1600, 900)

    overview = view.findChild(QFrame, "factoryV2HallOverview")
    stage = view.findChild(QFrame, "factoryV2HallStage")

    assert overview is not None
    assert stage is not None
    assert overview.minimumHeight() <= 168
    assert stage.minimumHeight() <= 140
    assert stage.geometry().height() >= stage.minimumHeight()
    assert _painted_samples(image) > 100


def test_factory_view_v2_build_slot_stage_uses_square_geometry() -> None:
    _app()
    slot = BuildSlotWidget("Build Slot", "Install machine")
    slot.setFixedSize(FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)
    outer = QRectF(1, 1, slot.width() - 2, slot.height() - 2)

    stage = slot._stage_rect(outer)
    icon_rect = stage.adjusted(stage.width() * 0.25, stage.height() * 0.25, -stage.width() * 0.25, -stage.height() * 0.25)

    assert stage.width() == stage.height()
    assert abs(stage.center().x() - outer.center().x()) < 0.01
    assert icon_rect.width() == icon_rect.height()
    assert _painted_samples(_render_widget(slot, FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)) > 24


def test_factory_view_v2_rounded_panel_children_do_not_fill_rectangular_corners() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    view = FactoryViewV2(state, bus, definitions)
    view.resize(1600, 900)
    view.show()
    QApplication.processEvents()

    for object_name in ("factoryV2Board", "factoryV2HallOverview", "factoryV2HallStage", "factoryV2ProductionTrack"):
        widget = view.findChild(QWidget, object_name)
        assert widget is not None
        assert widget.autoFillBackground() is False
        assert widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert widget.palette().color(widget.backgroundRole()).alpha() == 0

    locked_line = view.findChild(QFrame, "lockedLinePanel")
    assert locked_line is not None
    assert locked_line.property("factoryV2") is True
    assert locked_line.autoFillBackground() is False
    assert locked_line.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert locked_line.palette().color(locked_line.backgroundRole()).alpha() == 0

    scroll = view.findChild(QScrollArea, "factoryV2Scroll")
    assert scroll is not None
    assert scroll.frameShape() == QFrame.Shape.NoFrame
    assert scroll.autoFillBackground() is False
    assert scroll.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert scroll.viewport().objectName() == "factoryV2ScrollViewport"
    assert scroll.viewport().autoFillBackground() is False
    assert scroll.viewport().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert scroll.viewport().palette().color(scroll.viewport().backgroundRole()).alpha() == 0
    lines_content = view.findChild(QWidget, "factoryV2LinesContent")
    assert lines_content is not None
    assert lines_content.palette().color(lines_content.backgroundRole()).alpha() == 0


def test_factory_view_v2_sidebar_hall_overview_and_rarity_hooks_are_runtime_widgets() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    view = FactoryViewV2(state, bus, definitions)

    assert view.findChild(QFrame, "factoryV2Sidebar") is not None
    assert view.findChild(QLabel, "factoryV2NavTitle") is not None
    assert view.findChild(QLabel, "factoryV2NavSubtitle") is not None
    assert view._hall_tree.objectName() == "hallTreeV2"
    assert view._hall_tree.topLevelItem(0).text(0).startswith("Hall 1")
    assert "slots" in view._hall_tree.topLevelItem(0).text(0)
    assert view._build_hall_button.objectName() == "buildHallButtonV2"
    assert "Build Hall" in view._build_hall_button.text()
    assert view.findChild(QFrame, "factoryV2HallOverview") is not None
    assert any(label.text() == "LINE 01" for label in view.findChildren(FactoryV2LinePlate, "factoryV2LineTitle"))
    assert view.findChild(FactoryV2ActiveIndicator, "factoryV2ActiveIndicator") is not None
    assert not any(label.text() == "PRODUCTION TRACK" for label in view.findChildren(QLabel, "factoryV2LineEyebrow"))

    bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    view.refresh_view()
    machine = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    assert machine is not None
    image = _render_widget(machine, 220, 220)
    assert _painted_samples(image) > 20


def test_factory_view_v2_install_flash_hook_marks_recent_machine_temporarily() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    view = FactoryViewV2(state, bus, definitions)
    view._on_slot_clicked(0)
    view._install_card_from_selection("test-solar-common-001")

    machine = view.findChild(FactoryV2MachineCard, "factoryV2MachineCard")
    assert machine is not None
    assert machine.property("installFlash") is True


def test_factory_view_v2_1920_layout_renders_without_visible_top_level_windows() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "test-furnace-common-001"))
    view = FactoryViewV2(state, bus, definitions)

    before = [widget for widget in QApplication.topLevelWidgets() if widget.isVisible()]
    image = _render_widget(view, 1920, 1080)
    after = [widget for widget in QApplication.topLevelWidgets() if widget.isVisible()]

    assert image.width() == 1920
    assert image.height() == 1080
    assert _painted_samples(image) > 100
    assert after == before
    assert len(view.findChildren(FactoryV2MachineCard, "factoryV2MachineCard")) >= 3
    assert view.findChild(QWidget, "factoryV2BuildSlot") is not None
    assert view.findChild(QFrame, "lockedLinePanel") is not None


def test_factory_view_v2_polish_preview_composition_renders_1920x1080() -> None:
    _app()
    state, definitions, bus = _state_defs_bus()
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    bus.dispatch(AddCash(5_000))
    bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "test-solar-common-001"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "test-furnace-common-001"))
    bus.dispatch(SelectMachineProduction("test-drill-common-001", "recipe.extract.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("test-furnace-common-001", "recipe.processor.iron", "iron"))
    drill_state = state.machine_production["test-drill-common-001"]
    drill_state.status = "running"
    drill_state.progress_seconds = 3.0
    processor_state = state.machine_production["test-furnace-common-001"]
    processor_state.status = "running"
    processor_state.progress_seconds = 1.0

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(10)
    layout.addWidget(FactoryCommandDeckWidget(state, len(definitions), resource_definitions, bus, None))
    view = FactoryViewV2(state, bus, definitions)
    layout.addWidget(view, 1)

    image = _render_widget(root, 1920, 1080)
    active_preview = _save_preview(image, "factory_view_v2_experimental_phase2_active.png")
    rollout_preview = _save_preview(image, "factory_view_v2_ui_language_rollout_pass1_preview.png")
    art_direction_preview = _save_preview(image, "factory_view_v2_industrial_art_direction_preview.png")
    near_future_preview = _save_preview(image, "factory_view_v2_near_future_industrial_preview.png")
    color_language_preview = _save_preview(image, "factory_view_v2_industrial_color_language_preview.png")
    atmosphere_preview = _save_preview(image, "factory_view_v2_atmospheric_color_integration_preview.png")
    distinct_atmosphere_preview = _save_preview(image, "factory_view_v2_distinct_multi_color_atmosphere_preview.png")
    distinct_materials_preview = _save_preview(image, "factory_view_v2_distinct_colored_materials_preview.png")
    local_materials_preview = _save_preview(image, "factory_view_v2_local_material_color_integration_preview.png")
    calm_base_preview = _save_preview(image, "factory_view_v2_calm_industrial_base_surfaces_preview.png")
    semantic_active_preview = _save_preview(image, "factory_view_v2_semantic_edge_color_active.png")
    neutral_chassis_active_preview = _save_preview(image, "factory_view_v2_neutral_chassis_local_accent_active.png")
    industrial_foundation_active_preview = _save_preview(image, "factory_view_v2_industrial_foundation_pass1_active.png")
    safety_identity_active_preview = _save_preview(image, "factory_view_v2_safety_identity_pass2_active.png")
    slot_redesign_active_preview = _save_preview(image, "factory_view_v2_build_locked_slot_redesign_active.png")
    runtime_machine_card_preview = _save_preview(image, "factory_view_v2_runtime_machine_card_prototype_preview.png")
    hierarchy_preview = _save_preview(image, "factory_view_v2_runtime_machine_card_hierarchy_preview.png")
    resource_status_preview = _save_preview(image, "factory_view_v2_runtime_machine_card_resource_status_preview.png")
    readable_stack_preview = _save_preview(image, "factory_view_v2_runtime_machine_card_readability_preview.png")
    interactive_resource_preview = _save_preview(image, "factory_view_v2_runtime_machine_card_resource_control_preview.png")
    final_micro_polish_preview = _save_preview(image, "factory_view_v2_final_micro_polish_preview.png")

    empty_state, empty_definitions, empty_bus = _state_defs_bus()
    empty_root = QWidget()
    empty_layout = QVBoxLayout(empty_root)
    empty_layout.setContentsMargins(18, 18, 18, 18)
    empty_layout.setSpacing(10)
    empty_layout.addWidget(FactoryCommandDeckWidget(empty_state, len(empty_definitions), resource_definitions, empty_bus, None))
    empty_layout.addWidget(FactoryViewV2(empty_state, empty_bus, empty_definitions), 1)
    empty_image = _render_widget(empty_root, 1920, 1080)
    empty_preview = _save_preview(empty_image, "factory_view_v2_experimental_phase2_empty.png")
    semantic_empty_preview = _save_preview(empty_image, "factory_view_v2_semantic_edge_color_empty.png")
    neutral_chassis_empty_preview = _save_preview(empty_image, "factory_view_v2_neutral_chassis_local_accent_empty.png")
    industrial_foundation_empty_preview = _save_preview(empty_image, "factory_view_v2_industrial_foundation_pass1_empty.png")
    safety_identity_empty_preview = _save_preview(empty_image, "factory_view_v2_safety_identity_pass2_empty.png")
    slot_redesign_empty_preview = _save_preview(empty_image, "factory_view_v2_build_locked_slot_redesign_empty.png")

    assert image.width() == 1920
    assert image.height() == 1080
    assert empty_image.width() == 1920
    assert empty_image.height() == 1080
    assert _painted_samples(image) > 100
    assert _painted_samples(empty_image) > 100
    assert active_preview.exists()
    assert rollout_preview.exists()
    assert art_direction_preview.exists()
    assert near_future_preview.exists()
    assert color_language_preview.exists()
    assert atmosphere_preview.exists()
    assert distinct_atmosphere_preview.exists()
    assert distinct_materials_preview.exists()
    assert local_materials_preview.exists()
    assert calm_base_preview.exists()
    assert semantic_active_preview.exists()
    assert neutral_chassis_active_preview.exists()
    assert industrial_foundation_active_preview.exists()
    assert safety_identity_active_preview.exists()
    assert slot_redesign_active_preview.exists()
    assert runtime_machine_card_preview.exists()
    assert hierarchy_preview.exists()
    assert resource_status_preview.exists()
    assert readable_stack_preview.exists()
    assert interactive_resource_preview.exists()
    assert final_micro_polish_preview.exists()
    assert empty_preview.exists()
    assert semantic_empty_preview.exists()
    assert neutral_chassis_empty_preview.exists()
    assert industrial_foundation_empty_preview.exists()
    assert safety_identity_empty_preview.exists()
    assert slot_redesign_empty_preview.exists()
    assert root.findChild(QFrame, "factoryV2HallOverview") is not None
    assert root.findChild(QFrame, "factoryV2CommandDeck") is not None
