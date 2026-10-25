from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from production_zero.ui.game_ui import (
    GAME_UI_TOKENS,
    Accent,
    BuildSlotWidget,
    GameButton,
    GameCardFrame,
    GameIcon,
    GameIconWidget,
    GamePanel,
    GameUiShowcase,
    InteractionState,
    LockedUpgradeWidget,
    MaterialLevel,
    ProductionTrack,
    ResourceChip,
    StatusBadge,
    draw_game_icon,
    draw_game_panel,
    draw_glow_edge,
    draw_inset_surface,
    draw_track_surface,
    draw_upgrade_surface,
)
from production_zero.ui.theme import APP_STYLESHEET, Theme


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _painted_pixels(image: QImage) -> int:
    hits = 0
    step_x = max(1, image.width() // 24)
    step_y = max(1, image.height() // 18)
    for x in range(0, image.width(), step_x):
        for y in range(0, image.height(), step_y):
            if image.pixelColor(x, y).alpha() > 0:
                hits += 1
    return hits


def test_game_ui_tokens_cover_core_design_language() -> None:
    tokens = GAME_UI_TOKENS

    assert tokens.colors.background
    assert tokens.colors.surface_0 != tokens.colors.surface_3
    assert tokens.colors.chassis_light
    assert tokens.colors.chassis_mid
    assert tokens.colors.chassis_shadow
    assert tokens.colors.recessed_dark
    assert tokens.colors.recessed_mid
    assert tokens.colors.recessed_edge
    assert tokens.colors.panel != tokens.colors.interactive
    assert tokens.colors.edge_highlight
    assert tokens.colors.neutral_edge
    assert tokens.colors.neutral_edge_secondary
    assert tokens.colors.neutral_edge_highlight
    assert tokens.colors.separator
    assert tokens.colors.text_primary
    assert tokens.colors.text_secondary
    assert tokens.colors.text_muted
    assert tokens.colors.safety_yellow
    assert tokens.colors.area_anchor_red
    assert tokens.colors.warning_orange
    assert tokens.colors.accent(Accent.CASH).isValid()
    assert tokens.colors.accent(Accent.ENERGY).isValid()
    assert tokens.colors.accent(Accent.EXTRACTOR).isValid()
    assert tokens.colors.accent(Accent.PROCESSOR).isValid()
    assert tokens.colors.accent(Accent.STORAGE).isValid()
    assert tokens.colors.accent(Accent.SUCCESS).isValid()
    assert tokens.colors.accent(Accent.WARNING).isValid()
    assert tokens.colors.accent(Accent.DANGER).isValid()
    assert tokens.colors.accent(Accent.BUILD).isValid()
    assert tokens.colors.accent(Accent.LOCKED).isValid()
    assert tokens.geometry.radius_small < tokens.geometry.radius_large
    assert tokens.geometry.padding_sm < tokens.geometry.padding_lg
    assert tokens.geometry.card_width > 0
    assert tokens.material.glow_soft_alpha < tokens.material.glow_strong_alpha
    assert tokens.typography.card_title().pointSize() > 0
    assert tokens.typography.brand_display().pointSize() > tokens.typography.section_title().pointSize()
    assert tokens.typography.industrial_title().bold()
    assert "Bahnschrift Condensed" in tokens.typography.family
    assert "Agency FB" in tokens.typography.family
    assert tokens.typography.brand_display().stretch() == 68
    assert tokens.typography.industrial_title().stretch() == 72
    assert tokens.typography.industrial_label().stretch() == 84
    assert tokens.typography.micro_label().stretch() == 90
    assert tokens.typography.brand_display().stretch() < tokens.typography.card_title().stretch()
    assert tokens.typography.industrial_title().stretch() < tokens.typography.micro_label().stretch()
    assert tokens.typography.status_label().bold()
    assert tokens.colors.accent(Accent.EXTRACTOR) != tokens.colors.accent(Accent.SUCCESS)
    assert tokens.colors.accent(Accent.PROCESSOR) != tokens.colors.accent(Accent.ENERGY)
    assert tokens.colors.accent(Accent.BUILD) == tokens.colors.qcolor(tokens.colors.safety_yellow)
    assert tokens.colors.accent(Accent.WARNING) == tokens.colors.qcolor(tokens.colors.warning)
    assert tokens.colors.accent(Accent.LOCKED) == tokens.colors.qcolor(tokens.colors.warning_orange)
    assert tokens.colors.qcolor(tokens.colors.area_anchor_red) != tokens.colors.accent(Accent.WARNING)
    assert tokens.colors.accent(Accent.WARNING) == tokens.colors.accent(Accent.LOCKED)
    assert tokens.colors.accent(Accent.DANGER) != tokens.colors.qcolor(tokens.colors.area_anchor_red)
    assert tokens.colors.qcolor(tokens.colors.neutral_edge) != tokens.colors.accent(Accent.ENERGY)
    assert tokens.colors.qcolor(tokens.colors.neutral_edge) != tokens.colors.accent(Accent.BUILD)
    assert tokens.colors.qcolor(tokens.colors.neutral_edge).blue() >= tokens.colors.qcolor(tokens.colors.neutral_edge).red()


def test_legacy_tabs_use_light_chassis_and_dark_recessed_materials() -> None:
    stylesheet = APP_STYLESHEET
    for selector in (
        "QWidget#chartsOverviewPage",
        "QWidget#marketOverviewPage",
        "QScrollArea#contractsBoardScroll",
        "QWidget#supplyDailyPage",
        "QWidget#packsPage",
        "QWidget#leaderboardRankingPage",
    ):
        assert selector in stylesheet

    assert "#d9ddd5" in stylesheet
    assert "#ece9dc" in stylesheet
    assert "rgba(6, 9, 9, 246)" in stylesheet
    assert "QTableView#marketTableView" in stylesheet
    assert "QFrame#contractCard" in stylesheet
    assert all(selector in stylesheet for selector in ("QLabel#chartsHeroTitle", "QLabel#marketHeroTitle", "QLabel#leaderboardHeroTitle"))


def test_charts_light_surfaces_use_dark_text_and_readable_filter_states() -> None:
    stylesheet = APP_STYLESHEET
    assert "QLabel#chartResourceName" in stylesheet
    assert "color: #18201d;" in stylesheet
    assert "QWidget#chartFilterDeck QLabel#sectionLabel" in stylesheet
    assert "color: #222a26;" in stylesheet

    chip_start = stylesheet.index("QPushButton#chartFilterChip {")
    chip_end = stylesheet.index("QPushButton#chartFilterChip:hover", chip_start)
    inactive_chip = stylesheet[chip_start:chip_end]
    assert f"color: {Theme.FILTER_INACTIVE_TEXT};" in inactive_chip
    assert "border: 1px solid rgba(45, 54, 50, 132);" in inactive_chip

    active_start = stylesheet.index('QPushButton#chartFilterChip[active="true"]')
    active_end = stylesheet.index("QPushButton#marketFilterChip", active_start)
    active_chip = stylesheet[active_start:active_end]
    assert "background: qlineargradient" in active_chip
    assert f"color: {Theme.FILTER_ACTIVE_TEXT};" in active_chip
    assert "rgba(37, 185, 232, 190)" in active_chip


def test_material_primitives_render_offscreen_without_pixel_perfect_assertions() -> None:
    _app()
    image = QImage(420, 260, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        draw_game_panel(painter, QRectF(10, 10, 180, 90), accent=Accent.ENERGY, state=InteractionState.SELECTED, level=MaterialLevel.ELEVATED)
        draw_inset_surface(painter, QRectF(210, 10, 180, 58), accent=Accent.STORAGE)
        draw_track_surface(painter, QRectF(10, 118, 380, 52), accent=Accent.ENERGY)
        draw_upgrade_surface(painter, QRectF(10, 188, 120, 58), state=InteractionState.HOVER)
        draw_glow_edge(painter, QRectF(150, 188, 120, 58), accent=Accent.CASH, state=InteractionState.HOVER)
    finally:
        painter.end()

    assert _painted_pixels(image) > 12


def test_procedural_icons_render_all_foundation_icons() -> None:
    _app()
    image = QImage(640, 160, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    try:
        for index, icon in enumerate(GameIcon):
            x = 8 + (index % 10) * 62
            y = 8 + (index // 10) * 68
            draw_game_icon(painter, icon, QRectF(x, y, 44, 44))
    finally:
        painter.end()

    assert _painted_pixels(image) > 20


def test_foundation_widgets_are_parented_embedded_and_renderable() -> None:
    _app()
    host = QWidget()
    widgets = [
        GamePanel("Panel", "Subtitle", parent=host),
        GameButton("Primary", variant="primary", parent=host),
        ResourceChip(GameIcon.IRON, "Iron", "420", "+12/min", parent=host),
        StatusBadge("Running", parent=host),
        BuildSlotWidget(parent=host),
        LockedUpgradeWidget(parent=host),
        GameCardFrame(parent=host),
        ProductionTrack(parent=host),
        GameIconWidget(GameIcon.STEEL, parent=host),
    ]

    for widget in widgets:
        assert widget.parent() is host
        assert not widget.isWindow()
        widget.resize(max(widget.minimumWidth(), 160), max(widget.minimumHeight(), 80))
        image = QImage(widget.width(), widget.height(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        try:
            widget.render(painter, QPoint(0, 0))
        finally:
            painter.end()
        assert _painted_pixels(image) > 0


def test_game_button_interaction_states() -> None:
    _app()
    button = GameButton("Upgrade", variant="upgrade")

    assert button.variant == "upgrade"
    assert button.interaction_state() == InteractionState.NORMAL
    button.setSelected(True)
    assert button.interaction_state() == InteractionState.SELECTED
    button.setSelected(False)
    button.setEnabled(False)
    assert button.interaction_state() == InteractionState.DISABLED
    button.setEnabled(True)
    button._pressed = True
    assert button.interaction_state() == InteractionState.PRESSED
    button._pressed = False
    assert button.interaction_state() == InteractionState.NORMAL


def test_showcase_builds_all_foundation_components_without_visible_top_levels() -> None:
    _app()
    host = QWidget()
    baseline = {
        widget
        for widget in QApplication.topLevelWidgets()
        if widget.isVisible()
    }
    showcase = GameUiShowcase(parent=host)
    QApplication.processEvents()

    assert showcase.objectName() == "gameUiShowcase"
    assert showcase.findChild(GameButton, "gameButton") is not None
    assert showcase.findChild(ResourceChip, "resourceChip") is not None
    assert showcase.findChild(BuildSlotWidget, "buildSlotWidget") is not None
    assert showcase.findChild(LockedUpgradeWidget, "lockedUpgradeWidget") is not None
    assert showcase.findChild(StatusBadge, "statusBadge") is not None
    assert showcase.findChild(GameCardFrame, "gameCardFrame") is not None
    assert showcase.findChild(ProductionTrack, "productionTrack") is not None
    assert len(showcase.findChildren(GameIconWidget, "gameIcon")) >= 12
    assert {
        widget
        for widget in QApplication.topLevelWidgets()
        if widget.isVisible()
    } == baseline


def test_showcase_renders_to_qimage_at_standard_and_high_dpi_sizes() -> None:
    _app()
    showcase = GameUiShowcase()

    image = showcase.render_to_image(900, 560)
    high_dpi = showcase.render_to_image(700, 420, device_pixel_ratio=1.5)

    assert image.width() == 900
    assert image.height() == 560
    assert image.devicePixelRatio() == 1.0
    assert _painted_pixels(image) > 30
    assert high_dpi.width() == 1050
    assert high_dpi.height() == 630
    assert high_dpi.devicePixelRatio() == 1.5
    assert _painted_pixels(high_dpi) > 30
