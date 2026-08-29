from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QWidget

from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS


class GameIcon(str, Enum):
    CASH = "cash"
    ENERGY = "energy"
    STORAGE = "storage"
    BUILD = "build"
    LOCK = "lock"
    HALL = "hall"
    EXPANSION = "expansion"
    IRON_ORE = "iron_ore"
    IRON = "iron"
    COPPER_ORE = "copper_ore"
    COPPER = "copper"
    COAL = "coal"
    STEEL = "steel"
    FREIGHT = "freight"
    MARKET = "market"
    CONTRACTS = "contracts"
    PACKS = "packs"
    INVENTORY = "inventory"


class MachineIcon(str, Enum):
    SOLAR_ARRAY = "solar_array"
    WIND_TURBINE = "wind_turbine"
    EXTRACTOR = "extractor"
    PROCESSOR = "processor"
    ASSEMBLER = "assembler"
    COAL_POWER = "coal_power"
    GAS_POWER = "gas_power"
    NUCLEAR_POWER = "nuclear_power"


_ICON_ACCENTS: dict[GameIcon, Accent] = {
    GameIcon.CASH: Accent.CASH,
    GameIcon.ENERGY: Accent.ENERGY,
    GameIcon.STORAGE: Accent.STORAGE,
    GameIcon.BUILD: Accent.BUILD,
    GameIcon.LOCK: Accent.LOCKED,
    GameIcon.HALL: Accent.STORAGE,
    GameIcon.EXPANSION: Accent.LOCKED,
    GameIcon.IRON_ORE: Accent.NEUTRAL,
    GameIcon.IRON: Accent.STORAGE,
    GameIcon.COPPER_ORE: Accent.WARNING,
    GameIcon.COPPER: Accent.WARNING,
    GameIcon.COAL: Accent.NEUTRAL,
    GameIcon.STEEL: Accent.STORAGE,
    GameIcon.FREIGHT: Accent.ENERGY,
    GameIcon.MARKET: Accent.CASH,
    GameIcon.CONTRACTS: Accent.SUCCESS,
    GameIcon.PACKS: Accent.RARE,
    GameIcon.INVENTORY: Accent.STORAGE,
}


def icon_accent(icon: GameIcon) -> Accent:
    return _ICON_ACCENTS.get(icon, Accent.NEUTRAL)


def draw_game_icon(painter: QPainter, icon: GameIcon, rect: QRectF, *, accent: Accent | None = None, disabled: bool = False) -> None:
    tokens = GAME_UI_TOKENS
    accent = icon_accent(icon) if accent is None else accent
    color = tokens.colors.accent(accent, 96 if disabled else 230)
    muted = QColor(color)
    muted.setAlpha(82 if disabled else 118)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(muted, max(1.0, rect.width() * 0.045)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(rect.adjusted(rect.width() * 0.08, rect.height() * 0.08, -rect.width() * 0.08, -rect.height() * 0.08))
    inner = rect.adjusted(rect.width() * 0.2, rect.height() * 0.2, -rect.width() * 0.2, -rect.height() * 0.2)
    painter.setPen(QPen(color, max(1.2, rect.width() * 0.055), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if icon == GameIcon.CASH:
        painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
        painter.drawLine(inner.center().x(), inner.top(), inner.center().x(), inner.bottom())
        painter.drawArc(inner.adjusted(0, 0, 0, 0), 35 * 16, 290 * 16)
    elif icon == GameIcon.ENERGY:
        points = [
            inner.left() + inner.width() * 0.55,
            inner.top(),
            inner.left() + inner.width() * 0.22,
            inner.center().y(),
            inner.left() + inner.width() * 0.5,
            inner.center().y(),
            inner.left() + inner.width() * 0.38,
            inner.bottom(),
            inner.right() - inner.width() * 0.18,
            inner.center().y() - inner.height() * 0.08,
            inner.left() + inner.width() * 0.55,
            inner.center().y() - inner.height() * 0.08,
        ]
        painter.drawPolyline(QPolygonF([rect.topLeft().__class__(points[i], points[i + 1]) for i in range(0, len(points), 2)]))
    elif icon == GameIcon.STORAGE:
        painter.drawRoundedRect(inner, 4, 4)
        painter.drawLine(inner.left(), inner.top() + inner.height() * 0.35, inner.right(), inner.top() + inner.height() * 0.35)
        painter.drawLine(inner.left(), inner.top() + inner.height() * 0.68, inner.right(), inner.top() + inner.height() * 0.68)
    elif icon == GameIcon.BUILD:
        painter.drawLine(inner.center().x(), inner.top(), inner.center().x(), inner.bottom())
        painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
    elif icon == GameIcon.LOCK:
        body = QRectF(inner.left(), inner.center().y() - inner.height() * 0.08, inner.width(), inner.height() * 0.55)
        painter.drawRoundedRect(body, 4, 4)
        painter.drawArc(QRectF(inner.left() + inner.width() * 0.18, inner.top(), inner.width() * 0.64, inner.height() * 0.66), 0, 180 * 16)
    elif icon == GameIcon.HALL:
        painter.drawRect(QRectF(inner.left(), inner.center().y(), inner.width(), inner.height() * 0.38))
        painter.drawPolyline(QPolygonF([
            inner.bottomLeft().__class__(inner.left(), inner.center().y()),
            inner.bottomLeft().__class__(inner.left() + inner.width() * 0.25, inner.top() + inner.height() * 0.35),
            inner.bottomLeft().__class__(inner.left() + inner.width() * 0.45, inner.center().y()),
            inner.bottomLeft().__class__(inner.left() + inner.width() * 0.7, inner.top() + inner.height() * 0.35),
            inner.bottomLeft().__class__(inner.right(), inner.center().y()),
        ]))
    elif icon == GameIcon.EXPANSION:
        painter.drawRect(inner.adjusted(inner.width() * 0.12, inner.height() * 0.12, -inner.width() * 0.12, -inner.height() * 0.12))
        painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
        painter.drawLine(inner.center().x(), inner.top(), inner.center().x(), inner.bottom())
    elif icon in (GameIcon.IRON_ORE, GameIcon.COPPER_ORE, GameIcon.COAL):
        painter.setBrush(tokens.colors.accent(accent, 70 if disabled else 128))
        painter.drawPolygon(QPolygonF([
            inner.topLeft().__class__(inner.left() + inner.width() * 0.2, inner.top() + inner.height() * 0.35),
            inner.topLeft().__class__(inner.left() + inner.width() * 0.45, inner.top() + inner.height() * 0.1),
            inner.topLeft().__class__(inner.right() - inner.width() * 0.16, inner.top() + inner.height() * 0.32),
            inner.topLeft().__class__(inner.right() - inner.width() * 0.25, inner.bottom() - inner.height() * 0.12),
            inner.topLeft().__class__(inner.left() + inner.width() * 0.18, inner.bottom() - inner.height() * 0.2),
        ]))
    elif icon in (GameIcon.IRON, GameIcon.COPPER, GameIcon.STEEL):
        painter.drawRoundedRect(inner.adjusted(inner.width() * 0.08, inner.height() * 0.24, -inner.width() * 0.08, -inner.height() * 0.24), 4, 4)
        painter.drawLine(inner.left() + inner.width() * 0.25, inner.center().y(), inner.right() - inner.width() * 0.25, inner.center().y())
    elif icon == GameIcon.FREIGHT:
        painter.drawRoundedRect(QRectF(inner.left(), inner.center().y() - inner.height() * 0.1, inner.width(), inner.height() * 0.38), 4, 4)
        painter.drawEllipse(QRectF(inner.left() + inner.width() * 0.12, inner.bottom() - inner.height() * 0.22, inner.width() * 0.18, inner.height() * 0.18))
        painter.drawEllipse(QRectF(inner.right() - inner.width() * 0.3, inner.bottom() - inner.height() * 0.22, inner.width() * 0.18, inner.height() * 0.18))
    elif icon == GameIcon.MARKET:
        painter.drawLine(inner.left(), inner.bottom(), inner.right(), inner.bottom())
        painter.drawPolyline(QPolygonF([
            inner.topLeft().__class__(inner.left() + inner.width() * 0.1, inner.bottom() - inner.height() * 0.2),
            inner.topLeft().__class__(inner.left() + inner.width() * 0.4, inner.top() + inner.height() * 0.3),
            inner.topLeft().__class__(inner.left() + inner.width() * 0.62, inner.center().y()),
            inner.topLeft().__class__(inner.right() - inner.width() * 0.08, inner.top() + inner.height() * 0.12),
        ]))
    elif icon == GameIcon.CONTRACTS:
        painter.drawRoundedRect(inner, 4, 4)
        painter.drawLine(inner.left() + inner.width() * 0.22, inner.top() + inner.height() * 0.34, inner.right() - inner.width() * 0.15, inner.top() + inner.height() * 0.34)
        painter.drawLine(inner.left() + inner.width() * 0.22, inner.top() + inner.height() * 0.58, inner.right() - inner.width() * 0.25, inner.top() + inner.height() * 0.58)
    elif icon == GameIcon.PACKS:
        painter.drawRoundedRect(inner, 5, 5)
        painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
        painter.drawLine(inner.center().x(), inner.top(), inner.center().x(), inner.bottom())
    else:
        painter.drawRoundedRect(inner, 4, 4)
    painter.restore()


def _copy_color(color: QColor, alpha: int | None = None) -> QColor:
    copy = QColor(color)
    if alpha is not None:
        copy.setAlpha(alpha)
    return copy


def _point(rect: QRectF, x: float, y: float) -> QPointF:
    return QPointF(rect.left() + rect.width() * x, rect.top() + rect.height() * y)


def _rect(rect: QRectF, x: float, y: float, width: float, height: float) -> QRectF:
    return QRectF(rect.left() + rect.width() * x, rect.top() + rect.height() * y, rect.width() * width, rect.height() * height)


def _stroke(rect: QRectF, scale: float = 0.042) -> float:
    return max(1.15, min(rect.width(), rect.height()) * scale)


def _material_colors(accent: Accent, disabled: bool) -> dict[str, QColor]:
    tokens = GAME_UI_TOKENS
    alpha = 88 if disabled else 255
    return {
        "accent": tokens.colors.accent(accent, 96 if disabled else 226),
        "accent_soft": tokens.colors.accent(accent, 34 if disabled else 78),
        "body_top": tokens.colors.qcolor("#263f49", alpha),
        "body_bottom": tokens.colors.qcolor("#0c171d", alpha),
        "body_edge": tokens.colors.qcolor("#9ad7e6", 44 if disabled else 112),
        "body_shadow": tokens.colors.qcolor("#020608", 108 if disabled else 206),
        "cut": tokens.colors.qcolor("#eef9f5", 48 if disabled else 140),
        "dark_cut": tokens.colors.qcolor("#03080b", 110 if disabled else 184),
        "glass": tokens.colors.qcolor("#d8f8ff", 32 if disabled else 86),
    }


def _draw_emblem_backplate(painter: QPainter, rect: QRectF, colors: dict[str, QColor], radius: float) -> None:
    glow = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.62)
    glow.setColorAt(0.0, colors["accent_soft"])
    glow.setColorAt(0.72, QColor(8, 18, 23, 18))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(rect.adjusted(-rect.width() * 0.08, -rect.height() * 0.06, rect.width() * 0.08, rect.height() * 0.1))

    panel = QLinearGradient(rect.topLeft(), rect.bottomRight())
    panel.setColorAt(0.0, QColor(39, 64, 73, 184))
    panel.setColorAt(0.48, QColor(12, 27, 34, 218))
    panel.setColorAt(1.0, QColor(4, 9, 13, 232))
    painter.setBrush(panel)
    painter.setPen(QPen(QColor(226, 248, 246, 32), max(1.0, _stroke(rect, 0.024))))
    painter.drawRoundedRect(rect, radius, radius)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(colors["accent_soft"], max(1.0, _stroke(rect, 0.016))))
    painter.drawRoundedRect(rect.adjusted(rect.width() * 0.08, rect.height() * 0.08, -rect.width() * 0.08, -rect.height() * 0.08), radius * 0.58, radius * 0.58)


def _draw_body_rect(painter: QPainter, rect: QRectF, colors: dict[str, QColor], radius_scale: float = 0.08) -> None:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, colors["body_top"])
    gradient.setColorAt(0.58, QColor(18, 33, 40, colors["body_top"].alpha()))
    gradient.setColorAt(1.0, colors["body_bottom"])
    radius = max(2.0, min(rect.width(), rect.height()) * radius_scale)
    painter.setBrush(gradient)
    painter.setPen(QPen(colors["body_edge"], max(1.0, _stroke(rect, 0.038))))
    painter.drawRoundedRect(rect, radius, radius)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 30), max(1.0, _stroke(rect, 0.016))))
    painter.drawLine(rect.left() + rect.width() * 0.14, rect.top() + rect.height() * 0.2, rect.right() - rect.width() * 0.14, rect.top() + rect.height() * 0.2)


def _draw_body_polygon(painter: QPainter, points: list[QPointF], colors: dict[str, QColor], stroke_rect: QRectF) -> None:
    polygon = QPolygonF(points)
    gradient = QLinearGradient(stroke_rect.topLeft(), stroke_rect.bottomRight())
    gradient.setColorAt(0.0, colors["body_top"])
    gradient.setColorAt(1.0, colors["body_bottom"])
    painter.setBrush(gradient)
    painter.setPen(QPen(colors["body_edge"], max(1.0, _stroke(stroke_rect, 0.04)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolygon(polygon)


def _draw_accent_core(painter: QPainter, rect: QRectF, colors: dict[str, QColor], *, ellipse: bool = False) -> None:
    gradient = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.68)
    gradient.setColorAt(0.0, _copy_color(colors["glass"], min(220, colors["glass"].alpha() + 80)))
    gradient.setColorAt(0.38, colors["accent"])
    gradient.setColorAt(1.0, colors["accent_soft"])
    painter.setBrush(gradient)
    painter.setPen(QPen(colors["accent"], max(1.0, _stroke(rect, 0.035))))
    if ellipse:
        painter.drawEllipse(rect)
    else:
        painter.drawRoundedRect(rect, max(2.0, min(rect.width(), rect.height()) * 0.16), max(2.0, min(rect.width(), rect.height()) * 0.16))


def _draw_extractor_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    tower = _rect(rect, 0.34, 0.14, 0.32, 0.28)
    _draw_body_rect(painter, tower, colors, 0.12)
    bit = [
        _point(rect, 0.25, 0.43),
        _point(rect, 0.75, 0.43),
        _point(rect, 0.62, 0.72),
        _point(rect, 0.5, 0.88),
        _point(rect, 0.38, 0.72),
    ]
    _draw_body_polygon(painter, bit, colors, rect)
    painter.setPen(QPen(colors["accent"], _stroke(rect, 0.045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.5, 0.19), _point(rect, 0.5, 0.83))
    painter.setPen(QPen(colors["dark_cut"], _stroke(rect, 0.032), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.39, 0.58), _point(rect, 0.61, 0.58))
    painter.drawLine(_point(rect, 0.43, 0.69), _point(rect, 0.57, 0.69))


def _draw_processor_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    core = _rect(rect, 0.24, 0.24, 0.52, 0.52)
    _draw_body_rect(painter, core, colors, 0.1)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.044), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.08, 0.5), QPointF(core.left(), core.center().y()))
    painter.drawLine(QPointF(core.right(), core.center().y()), _point(rect, 0.92, 0.5))
    _draw_accent_core(painter, _rect(rect, 0.39, 0.33, 0.22, 0.22), colors, ellipse=True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(colors["dark_cut"], _stroke(rect, 0.038), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawEllipse(_rect(rect, 0.33, 0.53, 0.15, 0.15))
    painter.drawEllipse(_rect(rect, 0.52, 0.53, 0.15, 0.15))


def _draw_assembler_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.037), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.24, 0.28), _point(rect, 0.5, 0.62))
    painter.drawLine(_point(rect, 0.76, 0.28), _point(rect, 0.5, 0.62))
    painter.drawLine(_point(rect, 0.5, 0.16), _point(rect, 0.5, 0.62))
    for block in (_rect(rect, 0.13, 0.17, 0.21, 0.2), _rect(rect, 0.395, 0.06, 0.21, 0.2), _rect(rect, 0.67, 0.17, 0.21, 0.2)):
        _draw_body_rect(painter, block, colors, 0.12)
    diamond_rect = _rect(rect, 0.32, 0.55, 0.36, 0.34)
    diamond = [_point(diamond_rect, 0.5, 0.0), _point(diamond_rect, 1.0, 0.48), _point(diamond_rect, 0.5, 1.0), _point(diamond_rect, 0.0, 0.48)]
    _draw_body_polygon(painter, diamond, colors, rect)
    _draw_accent_core(painter, _rect(rect, 0.43, 0.64, 0.14, 0.13), colors)


def _draw_solar_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    panel = _rect(rect, 0.12, 0.28, 0.76, 0.42)
    _draw_body_rect(painter, panel, colors, 0.055)
    painter.setPen(QPen(colors["accent"], _stroke(rect, 0.03), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for x in (0.36, 0.58):
        painter.drawLine(QPointF(panel.left() + panel.width() * x, panel.top() + panel.height() * 0.08), QPointF(panel.left() + panel.width() * x, panel.bottom() - panel.height() * 0.08))
    painter.drawLine(QPointF(panel.left() + panel.width() * 0.08, panel.center().y()), QPointF(panel.right() - panel.width() * 0.08, panel.center().y()))
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.04), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(panel.center().x(), panel.bottom()), _point(rect, 0.5, 0.88))
    painter.setPen(QPen(colors["glass"], _stroke(rect, 0.026), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.24, 0.15), _point(rect, 0.34, 0.22))
    painter.drawLine(_point(rect, 0.5, 0.09), _point(rect, 0.5, 0.2))
    painter.drawLine(_point(rect, 0.76, 0.15), _point(rect, 0.66, 0.22))


def _draw_wind_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    hub = _point(rect, 0.5, 0.42)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.052), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(hub.x(), hub.y() + rect.height() * 0.12), _point(rect, 0.5, 0.9))
    blades = [
        [_point(rect, 0.47, 0.39), _point(rect, 0.5, 0.08), _point(rect, 0.57, 0.36)],
        [_point(rect, 0.54, 0.43), _point(rect, 0.88, 0.57), _point(rect, 0.58, 0.52)],
        [_point(rect, 0.46, 0.45), _point(rect, 0.18, 0.66), _point(rect, 0.41, 0.52)],
    ]
    for blade in blades:
        _draw_body_polygon(painter, blade, colors, rect)
    _draw_accent_core(painter, _rect(rect, 0.41, 0.33, 0.18, 0.18), colors, ellipse=True)


def _draw_coal_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    furnace = _rect(rect, 0.22, 0.34, 0.56, 0.43)
    _draw_body_rect(painter, furnace, colors, 0.1)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.038), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.32, 0.34), _point(rect, 0.32, 0.16))
    painter.drawLine(_point(rect, 0.68, 0.34), _point(rect, 0.68, 0.21))
    chamber = [_point(rect, 0.5, 0.42), _point(rect, 0.66, 0.55), _point(rect, 0.5, 0.68), _point(rect, 0.34, 0.55)]
    painter.setBrush(colors["accent"])
    painter.setPen(QPen(colors["accent"], _stroke(rect, 0.032), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolygon(QPolygonF(chamber))
    painter.setPen(QPen(colors["dark_cut"], _stroke(rect, 0.027), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.43, 0.55), _point(rect, 0.57, 0.55))


def _draw_gas_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    chamber = _rect(rect, 0.21, 0.25, 0.58, 0.58)
    _draw_body_rect(painter, chamber, colors, 0.16)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.038), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.08, 0.54), QPointF(chamber.left(), chamber.center().y()))
    painter.drawLine(QPointF(chamber.right(), chamber.center().y()), _point(rect, 0.92, 0.54))
    flame = [
        _point(rect, 0.5, 0.34),
        _point(rect, 0.63, 0.56),
        _point(rect, 0.51, 0.71),
        _point(rect, 0.38, 0.56),
    ]
    painter.setBrush(colors["accent"])
    painter.setPen(QPen(colors["accent"], _stroke(rect, 0.03), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolygon(QPolygonF(flame))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(colors["glass"], _stroke(rect, 0.022), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(_rect(rect, 0.34, 0.34, 0.32, 0.34), 205 * 16, 132 * 16)


def _draw_nuclear_icon(painter: QPainter, rect: QRectF, colors: dict[str, QColor]) -> None:
    containment = _rect(rect, 0.18, 0.18, 0.64, 0.64)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.052), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawEllipse(containment)
    painter.setPen(QPen(colors["body_edge"], _stroke(rect, 0.035), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(_point(rect, 0.32, 0.25), _point(rect, 0.32, 0.75))
    painter.drawLine(_point(rect, 0.68, 0.25), _point(rect, 0.68, 0.75))
    painter.drawArc(_rect(rect, 0.28, 0.28, 0.44, 0.44), 24 * 16, 132 * 16)
    painter.drawArc(_rect(rect, 0.28, 0.28, 0.44, 0.44), 204 * 16, 132 * 16)
    _draw_accent_core(painter, _rect(rect, 0.39, 0.39, 0.22, 0.22), colors, ellipse=True)


def draw_machine_icon(painter: QPainter, icon: MachineIcon, rect: QRectF, *, accent: Accent = Accent.ENERGY, disabled: bool = False) -> None:
    try:
        icon = icon if isinstance(icon, MachineIcon) else MachineIcon(icon)
    except ValueError:
        icon = MachineIcon.PROCESSOR
    if rect.width() <= 0 or rect.height() <= 0:
        return
    tokens = GAME_UI_TOKENS
    colors = _material_colors(accent, disabled)
    radius = max(5.0, min(rect.width(), rect.height()) * 0.16)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    outer = QRectF(rect).adjusted(rect.width() * 0.04, rect.height() * 0.05, -rect.width() * 0.04, -rect.height() * 0.05)
    inner = outer.adjusted(outer.width() * 0.13, outer.height() * 0.13, -outer.width() * 0.13, -outer.height() * 0.13)
    _draw_emblem_backplate(painter, outer, colors, radius)

    if icon == MachineIcon.SOLAR_ARRAY:
        _draw_solar_icon(painter, inner, colors)
    elif icon == MachineIcon.WIND_TURBINE:
        _draw_wind_icon(painter, inner, colors)
    elif icon == MachineIcon.EXTRACTOR:
        _draw_extractor_icon(painter, inner, colors)
    elif icon == MachineIcon.PROCESSOR:
        _draw_processor_icon(painter, inner, colors)
    elif icon == MachineIcon.ASSEMBLER:
        _draw_assembler_icon(painter, inner, colors)
    elif icon == MachineIcon.COAL_POWER:
        _draw_coal_icon(painter, inner, colors)
    elif icon == MachineIcon.GAS_POWER:
        _draw_gas_icon(painter, inner, colors)
    elif icon == MachineIcon.NUCLEAR_POWER:
        _draw_nuclear_icon(painter, inner, colors)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_copy_color(tokens.colors.qcolor("#eff8f4"), 26 if disabled else 58), max(1.0, _stroke(outer, 0.015))))
    painter.drawRoundedRect(outer.adjusted(outer.width() * 0.045, outer.height() * 0.045, -outer.width() * 0.045, -outer.height() * 0.045), radius * 0.78, radius * 0.78)
    painter.restore()


class GameIconWidget(QWidget):
    def __init__(self, icon: GameIcon, *, accent: Accent | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._accent = accent
        self.setObjectName("gameIcon")
        self.setMinimumSize(28, 28)

    @property
    def icon(self) -> GameIcon:
        return self._icon

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_game_icon(painter, self._icon, rect, accent=self._accent, disabled=not self.isEnabled())
        finally:
            painter.end()
