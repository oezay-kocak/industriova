from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS, InteractionState, MaterialLevel


def _path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def _adjust(color: QColor, state: InteractionState) -> QColor:
    adjusted = QColor(color)
    if state == InteractionState.HOVER:
        adjusted = adjusted.lighter(116)
    elif state == InteractionState.PRESSED:
        adjusted = adjusted.darker(118)
    elif state == InteractionState.SELECTED:
        adjusted = adjusted.lighter(126)
    elif state == InteractionState.DISABLED:
        adjusted.setAlpha(GAME_UI_TOKENS.material.disabled_alpha)
    return adjusted


def _edge_color(accent: Accent, alpha: int) -> QColor:
    tokens = GAME_UI_TOKENS
    if accent == Accent.NEUTRAL:
        return tokens.colors.qcolor(tokens.colors.neutral_edge, alpha)
    return tokens.colors.accent(accent, alpha)


def draw_game_panel(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.NEUTRAL,
    state: InteractionState = InteractionState.NORMAL,
    level: MaterialLevel = MaterialLevel.PANEL,
    radius: float | None = None,
) -> None:
    tokens = GAME_UI_TOKENS
    radius = tokens.geometry.radius_large if radius is None else radius
    base_top = tokens.colors.qcolor(tokens.colors.chassis_light)
    base_mid = tokens.colors.qcolor(tokens.colors.chassis_mid)
    base_bottom = tokens.colors.qcolor(tokens.colors.chassis_shadow)
    if level == MaterialLevel.ELEVATED:
        base_top = base_top.lighter(108)
        base_mid = base_mid.lighter(104)
    if level in {MaterialLevel.INSET, MaterialLevel.TRACK}:
        base_top = tokens.colors.qcolor(tokens.colors.chassis_mid)
        base_mid = tokens.colors.qcolor(tokens.colors.chassis_shadow)
        base_bottom = tokens.colors.qcolor(tokens.colors.recessed_dark)
    if state == InteractionState.PRESSED:
        base_top = base_top.darker(112)
        base_mid = base_mid.darker(112)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, _adjust(base_top, state))
    gradient.setColorAt(0.52, _adjust(base_mid, state))
    gradient.setColorAt(1.0, _adjust(base_bottom, state))
    edge_alpha = 56 if accent == Accent.NEUTRAL else 88
    if state in {InteractionState.HOVER, InteractionState.SELECTED}:
        edge_alpha += 42
    elif state == InteractionState.PRESSED:
        edge_alpha += 18
    painter.setPen(QPen(_edge_color(accent, edge_alpha), tokens.geometry.border_medium if accent == Accent.NEUTRAL else 1.65))
    painter.setBrush(gradient)
    painter.drawPath(_path(rect, radius))

    painter.setPen(QPen(QColor(255, 255, 255, tokens.material.edge_highlight_alpha // 2), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_path(rect.adjusted(3, 3, -3, -3), max(1, radius - 3)))
    if accent != Accent.NEUTRAL:
        painter.setPen(QPen(tokens.colors.accent(accent, 54 if state != InteractionState.PRESSED else 34), 1))
        painter.drawLine(rect.left() + 10, rect.top() + 8, rect.right() - 10, rect.top() + 8)
    draw_glow_edge(painter, rect, accent=accent, state=state, radius=radius)


def draw_inset_surface(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.NEUTRAL,
    state: InteractionState = InteractionState.NORMAL,
    radius: float | None = None,
) -> None:
    tokens = GAME_UI_TOKENS
    radius = tokens.geometry.radius_medium if radius is None else radius
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0.0, tokens.colors.qcolor(tokens.colors.recessed_dark, 218 if state == InteractionState.PRESSED else 188))
    gradient.setColorAt(0.58, tokens.colors.qcolor(tokens.colors.recessed_mid, 210))
    gradient.setColorAt(1.0, tokens.colors.accent(accent, 14 if state != InteractionState.HOVER else 28))
    painter.setPen(QPen(tokens.colors.qcolor(tokens.colors.recessed_edge, 120), 1))
    painter.setBrush(gradient)
    painter.drawPath(_path(rect, radius))


def draw_track_surface(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.NEUTRAL,
    state: InteractionState = InteractionState.NORMAL,
    radius: float | None = None,
) -> None:
    tokens = GAME_UI_TOKENS
    radius = tokens.geometry.radius_large if radius is None else radius
    draw_game_panel(painter, rect, accent=accent, state=state, level=MaterialLevel.TRACK, radius=radius)


def draw_upgrade_surface(
    painter: QPainter,
    rect: QRectF,
    *,
    state: InteractionState = InteractionState.NORMAL,
    radius: float | None = None,
) -> None:
    tokens = GAME_UI_TOKENS
    radius = tokens.geometry.radius_medium if radius is None else radius
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, tokens.colors.accent(Accent.LOCKED, 40 if state != InteractionState.HOVER else 58))
    gradient.setColorAt(0.55, QColor(31, 28, 20, 190))
    gradient.setColorAt(1.0, tokens.colors.accent(Accent.BUILD, 13))
    painter.setPen(QPen(tokens.colors.accent(Accent.LOCKED, 112), tokens.geometry.border_medium))
    painter.setBrush(gradient)
    painter.drawPath(_path(rect, radius))
    painter.setPen(QPen(tokens.colors.accent(Accent.LOCKED, 54), 1, Qt.PenStyle.DashLine))
    painter.drawPath(_path(rect.adjusted(6, 6, -6, -6), max(1, radius - 3)))


def draw_glow_edge(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.NEUTRAL,
    state: InteractionState = InteractionState.NORMAL,
    radius: float | None = None,
) -> None:
    tokens = GAME_UI_TOKENS
    if state == InteractionState.DISABLED:
        return
    if accent == Accent.NEUTRAL and state == InteractionState.NORMAL:
        return
    radius = tokens.geometry.radius_large if radius is None else radius
    alpha = tokens.material.glow_strong_alpha if state in (InteractionState.HOVER, InteractionState.SELECTED) else tokens.material.glow_soft_alpha
    glow = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.68)
    glow.setColorAt(0.0, tokens.colors.accent(accent, alpha // 3))
    glow.setColorAt(0.72, tokens.colors.accent(accent, alpha // 5))
    glow.setColorAt(1.0, tokens.colors.accent(accent, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawPath(_path(rect.adjusted(1, 1, -1, -1), max(1, radius - 1)))
