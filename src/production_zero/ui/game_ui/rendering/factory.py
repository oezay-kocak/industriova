from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient

from production_zero.ui.game_ui.icons import GameIcon, MachineIcon, draw_game_icon, draw_machine_icon
from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS
from production_zero.ui.freight_art import FREIGHT_ASSETS, draw_freight_art
from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, draw_machine_art


def _accent(accent: Accent, alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.accent(accent, alpha)


def _neutral_edge(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.neutral_edge, alpha)


def _neutral_edge_secondary(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.neutral_edge_secondary, alpha)


def _neutral_edge_highlight(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.neutral_edge_highlight, alpha)


def _safety_yellow(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.safety_yellow, alpha)


def _area_anchor_red(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.area_anchor_red, alpha)


def _warning_orange(alpha: int) -> QColor:
    return GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.warning_orange, alpha)


def _point(rect: QRectF, x: float, y: float) -> QPointF:
    return QPointF(rect.left() + rect.width() * x, rect.top() + rect.height() * y)


def _chassis_path(rect: QRectF, chamfer: float) -> QPainterPath:
    chamfer = max(5.0, min(chamfer, rect.width() * 0.2, rect.height() * 0.2))
    path = QPainterPath()
    path.moveTo(rect.left() + chamfer, rect.top())
    path.lineTo(rect.right() - chamfer * 0.68, rect.top())
    path.lineTo(rect.right(), rect.top() + chamfer * 0.86)
    path.lineTo(rect.right(), rect.bottom() - chamfer)
    path.lineTo(rect.right() - chamfer, rect.bottom())
    path.lineTo(rect.left() + chamfer * 0.72, rect.bottom())
    path.lineTo(rect.left(), rect.bottom() - chamfer * 0.72)
    path.lineTo(rect.left(), rect.top() + chamfer)
    path.closeSubpath()
    return path


def _machine_chassis_path(rect: QRectF) -> QPainterPath:
    cut = max(6.0, min(rect.width(), rect.height()) * 0.075)
    tab = rect.width() * 0.12
    path = QPainterPath()
    path.moveTo(rect.left() + cut, rect.top())
    path.lineTo(rect.right() - cut * 0.8, rect.top())
    path.lineTo(rect.right(), rect.top() + cut * 0.9)
    path.lineTo(rect.right(), rect.bottom() - cut * 1.15)
    path.lineTo(rect.right() - cut * 1.15, rect.bottom())
    path.lineTo(rect.left() + cut * 0.75, rect.bottom())
    path.lineTo(rect.left(), rect.bottom() - cut)
    path.lineTo(rect.left(), rect.top() + tab)
    path.lineTo(rect.left() + cut * 0.55, rect.top() + tab - cut * 0.62)
    path.lineTo(rect.left() + cut * 0.55, rect.top() + cut * 0.74)
    path.closeSubpath()
    return path


def _dock_path(rect: QRectF, cut: float) -> QPainterPath:
    cut = max(3.5, min(cut, rect.width() * 0.08, rect.height() * 0.12))
    path = QPainterPath()
    path.moveTo(rect.left() + cut, rect.top())
    path.lineTo(rect.right() - cut, rect.top())
    path.lineTo(rect.right(), rect.top() + cut)
    path.lineTo(rect.right(), rect.bottom() - cut)
    path.lineTo(rect.right() - cut, rect.bottom())
    path.lineTo(rect.left() + cut, rect.bottom())
    path.lineTo(rect.left(), rect.bottom() - cut)
    path.lineTo(rect.left(), rect.top() + cut)
    path.closeSubpath()
    return path


def draw_hazard_stripes(
    painter: QPainter,
    rect: QRectF,
    *,
    primary: QColor | None = None,
    secondary: QColor | None = None,
    stripe_width: float = 10,
    reverse: bool = False,
    radius: float = 0,
) -> None:
    primary = _safety_yellow(235) if primary is None else primary
    secondary = QColor(7, 8, 7, 236) if secondary is None else secondary
    painter.save()
    clip = QPainterPath()
    if radius > 0:
        clip.addRoundedRect(rect, radius, radius)
    else:
        clip.addRect(rect)
    painter.setClipPath(clip)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(secondary)
    painter.drawRect(rect)
    painter.setBrush(QColor(255, 255, 255, 18))
    painter.drawRect(rect.adjusted(0, 0, 0, -rect.height() * 0.72))
    painter.setPen(QPen(primary, stripe_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    span = rect.width() + rect.height()
    start = rect.left() - rect.height()
    step = stripe_width * 2.2
    count = int(span / step) + 4
    for index in range(count):
        x = start + index * step
        if reverse:
            painter.drawLine(QPointF(x, rect.top()), QPointF(x + rect.height(), rect.bottom()))
        else:
            painter.drawLine(QPointF(x, rect.bottom()), QPointF(x + rect.height(), rect.top()))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(0, 0, 0, 118), 1))
    painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius if radius > 0 else 1, radius if radius > 0 else 1)
    painter.restore()


def draw_panel_bolt(painter: QPainter, center: QPointF, *, radius: float = 3.2, dark: bool = True) -> None:
    painter.save()
    head = QRadialGradient(center, radius * 1.45)
    if dark:
        head.setColorAt(0.0, QColor(74, 76, 70, 238))
        head.setColorAt(0.58, QColor(22, 24, 22, 248))
        head.setColorAt(1.0, QColor(3, 4, 4, 255))
    else:
        head.setColorAt(0.0, QColor(238, 235, 220, 238))
        head.setColorAt(0.58, QColor(124, 126, 116, 238))
        head.setColorAt(1.0, QColor(26, 28, 26, 250))
    painter.setPen(QPen(QColor(255, 255, 246, 78), 0.8))
    painter.setBrush(head)
    painter.drawEllipse(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2))
    painter.setPen(QPen(QColor(0, 0, 0, 136), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(center.x() - radius * 0.52, center.y()), QPointF(center.x() + radius * 0.52, center.y()))
    painter.restore()


def draw_panel_bolts(painter: QPainter, rect: QRectF, *, inset: float = 10, radius: float = 3.2, dark: bool = True) -> None:
    for x, y in (
        (rect.left() + inset, rect.top() + inset),
        (rect.right() - inset, rect.top() + inset),
        (rect.left() + inset, rect.bottom() - inset),
        (rect.right() - inset, rect.bottom() - inset),
    ):
        draw_panel_bolt(painter, QPointF(x, y), radius=radius, dark=dark)


def draw_surface_wear(painter: QPainter, rect: QRectF, *, seed: int = 0, density: int = 5, dark: bool = True) -> None:
    density = max(0, min(density, 9))
    if density == 0:
        return
    painter.save()
    color = QColor(27, 30, 28, 26 if dark else 18)
    highlight = QColor(255, 255, 246, 18 if dark else 10)
    painter.setPen(QPen(color, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for index in range(density):
        mixed = (seed * 31 + index * 47) % 100
        edge_bias = 0.18 if index % 3 else 0.08
        x = rect.left() + rect.width() * (0.12 + ((mixed * 0.0073) % 0.76))
        y = rect.top() + rect.height() * (edge_bias + (((mixed + index * 19) * 0.011) % 0.66))
        length = rect.width() * (0.035 + ((mixed % 7) * 0.008))
        painter.drawLine(QPointF(x, y), QPointF(min(rect.right() - 8, x + length), y + ((index % 3) - 1) * 0.8))
        if index % 2 == 0:
            painter.setPen(QPen(highlight, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(x + 1, y - 1), QPointF(min(rect.right() - 8, x + length * 0.72), y - 1))
            painter.setPen(QPen(color, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.restore()


def draw_panel_seam(painter: QPainter, start: QPointF, end: QPointF, *, accent: Accent = Accent.NEUTRAL, alpha: int = 42) -> None:
    painter.save()
    painter.setPen(QPen(QColor(0, 0, 0, alpha + 28), 1))
    painter.drawLine(start, end)
    painter.setPen(QPen(QColor(255, 255, 246, max(12, alpha // 2)), 1))
    painter.drawLine(QPointF(start.x(), start.y() - 1), QPointF(end.x(), end.y() - 1))
    if accent != Accent.NEUTRAL:
        painter.setPen(QPen(_accent(accent, max(10, alpha // 2)), 1))
        painter.drawLine(QPointF(start.x(), start.y() + 1), QPointF(end.x(), end.y() + 1))
    painter.restore()


def draw_industrial_edge(painter: QPainter, rect: QRectF, *, radius: float = 10, inset: float = 2) -> None:
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 246, 72), 1))
    painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), max(1, radius - inset), max(1, radius - inset))
    painter.setPen(QPen(QColor(0, 0, 0, 116), 1))
    painter.drawRoundedRect(rect.adjusted(inset + 2, inset + 2, -inset - 2, -inset - 2), max(1, radius - inset - 2), max(1, radius - inset - 2))
    painter.restore()


def draw_warning_plate(painter: QPainter, rect: QRectF, *, text: str, selected: bool = True) -> QRectF:
    path = _dock_path(rect.adjusted(0.5, 0.5, -0.5, -0.5), 5)
    body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    body.setColorAt(0.0, QColor(226, 48, 34, 252 if selected else 208))
    body.setColorAt(0.5, _area_anchor_red(252 if selected else 210))
    body.setColorAt(1.0, QColor(82, 16, 12, 255 if selected else 226))
    painter.setPen(QPen(QColor(50, 20, 16, 230), 1.6))
    painter.setBrush(body)
    painter.drawPath(path)
    painter.setPen(QPen(QColor(255, 238, 220, 78), 1))
    painter.drawPath(_dock_path(rect.adjusted(4, 4, -4, -4), 3))

    draw_surface_wear(painter, rect.adjusted(9, 5, -9, -5), seed=21, density=3, dark=True)
    for x in (rect.left() + 11, rect.right() - 15):
        draw_panel_bolt(painter, QPointF(x + 2, rect.center().y()), radius=2.4, dark=True)

    font = GAME_UI_TOKENS.typography.industrial_title()
    font.setPointSize(15)
    painter.setFont(font)
    painter.setPen(QColor("#fff6e8"))
    painter.drawText(rect.adjusted(24, 0, -24, 0), Qt.AlignmentFlag.AlignCenter, text)
    return rect


def draw_build_corner_brackets(painter: QPainter, rect: QRectF, *, hover: bool = False) -> None:
    strength = 1.0 if hover else 0.0
    color = _safety_yellow(218 + int(strength * 24))
    length = min(rect.width(), rect.height()) * 0.18
    inset = 9.0
    dot_size = 3.6
    painter.save()
    painter.setPen(QPen(QColor(0, 0, 0, 150), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    for x_dir, y_dir in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = rect.left() + inset if x_dir > 0 else rect.right() - inset
        y = rect.top() + inset if y_dir > 0 else rect.bottom() - inset
        painter.drawLine(QPointF(x, y), QPointF(x + length * x_dir, y))
        painter.drawLine(QPointF(x, y), QPointF(x, y + length * y_dir))
    painter.setPen(QPen(color, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    for x_dir, y_dir in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = rect.left() + inset if x_dir > 0 else rect.right() - inset
        y = rect.top() + inset if y_dir > 0 else rect.bottom() - inset
        painter.drawLine(QPointF(x, y), QPointF(x + length * x_dir, y))
        painter.drawLine(QPointF(x, y), QPointF(x, y + length * y_dir))
        painter.setBrush(QColor(18, 20, 17, 230))
        painter.setPen(QPen(_safety_yellow(190), 1))
        painter.drawEllipse(QRectF(x - dot_size / 2, y - dot_size / 2, dot_size, dot_size))
        painter.setPen(QPen(color, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    painter.restore()


def draw_slot_hazard_footer(painter: QPainter, rect: QRectF, *, hover: bool = False) -> QRectF:
    footer = QRectF(rect.left() + 10, rect.bottom() - 22, rect.width() - 20, 11)
    draw_hazard_stripes(
        painter,
        footer,
        primary=_safety_yellow(235 if not hover else 255),
        secondary=QColor(8, 9, 7, 246),
        stripe_width=7,
        radius=2,
    )
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
    painter.drawRoundedRect(footer.adjusted(0.5, 0.5, -0.5, -0.5), 2, 2)
    painter.restore()
    return footer


def draw_lock_warning_frame(painter: QPainter, rect: QRectF, *, enabled: bool = False) -> QRectF:
    frame = QRectF(rect.center().x() - 31, rect.top() + 40, 62, 56)
    path = _dock_path(frame, 7)
    painter.save()
    glow = QRadialGradient(frame.center(), frame.width() * 0.88)
    glow.setColorAt(0.0, _warning_orange(74 if enabled else 52))
    glow.setColorAt(0.62, QColor(0, 0, 0, 18))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(frame.adjusted(-10, -8, 10, 9))
    body = QLinearGradient(frame.topLeft(), frame.bottomRight())
    body.setColorAt(0.0, QColor(66, 30, 24, 232 if enabled else 208))
    body.setColorAt(0.58, QColor(25, 19, 17, 238))
    body.setColorAt(1.0, QColor(8, 9, 8, 248))
    painter.setBrush(body)
    painter.setPen(QPen(_warning_orange(210 if enabled else 174), 1.7))
    painter.drawPath(path)
    painter.setPen(QPen(_warning_orange(118 if enabled else 86), 1))
    painter.drawPath(_dock_path(frame.adjusted(5, 5, -5, -5), 4))
    painter.restore()
    return frame


def draw_status_led(painter: QPainter, rect: QRectF, *, active: bool = True) -> QRectF:
    panel = _dock_path(rect.adjusted(0.5, 0.5, -0.5, -0.5), 4)
    body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    body.setColorAt(0.0, QColor(10, 15, 15, 232))
    body.setColorAt(1.0, QColor(3, 5, 5, 248))
    painter.setPen(QPen(_neutral_edge_highlight(112), 1))
    painter.setBrush(body)
    painter.drawPath(panel)
    led_color = _accent(Accent.SUCCESS, 235 if active else 90)
    glow = QRadialGradient(_point(rect, 0.18, 0.5), rect.height() * 0.9)
    glow.setColorAt(0.0, _accent(Accent.SUCCESS, 90 if active else 28))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawPath(panel)
    painter.setBrush(led_color)
    painter.drawEllipse(QRectF(rect.left() + 9, rect.center().y() - 3.2, 6.4, 6.4))
    font = GAME_UI_TOKENS.typography.micro_label()
    font.setPointSize(8)
    painter.setFont(font)
    painter.setPen(QColor("#c9f7d8") if active else QColor("#72827b"))
    painter.drawText(rect.adjusted(21, 0, -9, 0), Qt.AlignmentFlag.AlignCenter, "ACTIVE" if active else "IDLE")
    return rect


def draw_atmospheric_color_wash(painter: QPainter, rect: QRectF, *, strength: int = 1, radius: float = 14) -> None:
    strength = max(0, min(strength, 3))
    if strength == 0:
        return
    painter.setPen(Qt.PenStyle.NoPen)

    alpha = 7 + strength * 5
    zones = (
        (Accent.EXTRACTOR, 0.00, 0.34, alpha + 3),
        (Accent.STORAGE, 0.14, 0.52, alpha - 1),
        (Accent.PROCESSOR, 0.34, 0.72, alpha + 2),
        (Accent.ENERGY, 0.58, 0.90, alpha - 2),
        (Accent.LOCKED, 0.76, 1.00, alpha + 1),
    )
    for accent, start, end, zone_alpha in zones:
        wash = QLinearGradient(rect.topLeft(), rect.topRight())
        mid = (start + end) / 2
        wash.setColorAt(0.0, QColor(0, 0, 0, 0))
        wash.setColorAt(max(0.0, start - 0.08), QColor(0, 0, 0, 0))
        wash.setColorAt(mid, _accent(accent, max(3, zone_alpha)))
        wash.setColorAt(min(1.0, end + 0.08), QColor(0, 0, 0, 0))
        wash.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(wash)
        painter.drawRoundedRect(rect, radius, radius)

    vertical = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    vertical.setColorAt(0.0, QColor(255, 255, 255, 2 + strength))
    vertical.setColorAt(0.42, QColor(0, 0, 0, 0))
    vertical.setColorAt(1.0, QColor(0, 0, 0, 18 + strength * 4))
    painter.setBrush(vertical)
    painter.drawRoundedRect(rect, radius, radius)


def draw_industrial_base_surface(
    painter: QPainter,
    rect: QRectF,
    *,
    strength: int = 1,
    radius: float = 14,
    role: str = "surface",
    variant: int = 0,
) -> None:
    strength = max(0, min(strength, 3))
    if strength == 0:
        return

    clip = QPainterPath()
    clip.addRoundedRect(rect, radius, radius)
    painter.save()
    painter.setClipPath(clip)
    painter.setPen(Qt.PenStyle.NoPen)

    palettes = {
        "command": (QColor(230, 228, 216, 150), QColor(158, 161, 150, 118), QColor(62, 67, 62, 138), Accent.STORAGE),
        "hall": (QColor(226, 225, 214, 142), QColor(156, 160, 150, 118), QColor(60, 66, 62, 142), Accent.STORAGE),
        "board": (QColor(218, 220, 211, 136), QColor(142, 151, 146, 116), QColor(45, 53, 51, 148), Accent.PROCESSOR),
        "track": (QColor(180, 185, 180, 96), QColor(82, 93, 94, 118), QColor(16, 23, 24, 162), Accent.PROCESSOR),
        "track-alt": (QColor(188, 187, 176, 94), QColor(83, 92, 88, 116), QColor(16, 23, 23, 162), Accent.STORAGE),
        "surface": (QColor(220, 221, 211, 136), QColor(146, 154, 149, 116), QColor(51, 59, 57, 150), Accent.STORAGE),
    }
    layout_key = role if role in palettes else "surface"
    if layout_key == "track" and variant % 2:
        layout_key = "track-alt"
    top, mid, bottom, tint = palettes[layout_key]

    body = QLinearGradient(rect.topLeft(), rect.bottomRight())
    body.setColorAt(0.0, top)
    body.setColorAt(0.45, mid)
    body.setColorAt(1.0, bottom)
    painter.setBrush(body)
    painter.drawRoundedRect(rect, radius, radius)

    sheen = QLinearGradient(rect.topLeft(), rect.topRight())
    sheen.setColorAt(0.0, QColor(255, 255, 248, 9 + strength * 3))
    sheen.setColorAt(0.44, _accent(tint, 2 + strength))
    sheen.setColorAt(1.0, QColor(0, 0, 0, 24 + strength * 4))
    painter.setBrush(sheen)
    painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), max(2, radius - 4), max(2, radius - 4))

    vertical_depth = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    vertical_depth.setColorAt(0.0, QColor(255, 255, 248, 6 + strength * 2))
    vertical_depth.setColorAt(0.34, QColor(255, 255, 255, 1))
    vertical_depth.setColorAt(1.0, QColor(0, 0, 0, 38 + strength * 5))
    painter.setBrush(vertical_depth)
    painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), max(2, radius - 6), max(2, radius - 6))

    inset = rect.adjusted(4.5, 4.5, -4.5, -4.5)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 248, 16 + strength * 2), 1))
    painter.drawRoundedRect(inset, max(2, radius - 5), max(2, radius - 5))
    draw_surface_wear(painter, rect.adjusted(10, 8, -10, -8), seed=len(role) * 17 + variant * 11, density=2 + strength, dark=True)
    painter.restore()


def draw_distinct_material_zones(
    painter: QPainter,
    rect: QRectF,
    *,
    strength: int = 1,
    radius: float = 14,
    role: str = "surface",
    variant: int = 0,
) -> None:
    strength = max(0, min(strength, 3))
    if strength == 0:
        return
    clip = QPainterPath()
    clip.addRoundedRect(rect, radius, radius)
    painter.save()
    painter.setClipPath(clip)
    painter.setPen(Qt.PenStyle.NoPen)
    alpha = 8 + strength * 4
    layouts = {
        "board": (
            (Accent.EXTRACTOR, 0.05, 0.13, 0.26, 0.46, alpha + 6),
            (Accent.PROCESSOR, 0.39, 0.09, 0.30, 0.42, alpha + 7),
            (Accent.STORAGE, 0.18, 0.62, 0.31, 0.24, alpha + 1),
            (Accent.ENERGY, 0.71, 0.22, 0.19, 0.28, max(6, alpha - 2)),
            (Accent.LOCKED, 0.79, 0.67, 0.15, 0.20, max(6, alpha - 1)),
        ),
        "hall": (
            (Accent.STORAGE, 0.04, 0.10, 0.28, 0.36, alpha + 2),
            (Accent.EXTRACTOR, 0.12, 0.56, 0.24, 0.27, alpha + 5),
            (Accent.PROCESSOR, 0.48, 0.16, 0.27, 0.42, alpha + 6),
            (Accent.ENERGY, 0.68, 0.57, 0.21, 0.22, max(6, alpha - 2)),
        ),
        "track": (
            (Accent.PROCESSOR, 0.09, 0.14, 0.28, 0.38, alpha + 7),
            (Accent.EXTRACTOR, 0.30, 0.58, 0.23, 0.23, alpha + 5),
            (Accent.STORAGE, 0.54, 0.18, 0.21, 0.30, alpha + 1),
            (Accent.ENERGY, 0.73, 0.47, 0.18, 0.24, max(6, alpha - 3)),
            (Accent.LOCKED, 0.84, 0.16, 0.11, 0.19, max(5, alpha - 4)),
        ),
        "track-alt": (
            (Accent.EXTRACTOR, 0.07, 0.48, 0.24, 0.27, alpha + 6),
            (Accent.STORAGE, 0.25, 0.16, 0.25, 0.31, alpha + 1),
            (Accent.PROCESSOR, 0.50, 0.39, 0.28, 0.31, alpha + 7),
            (Accent.ENERGY, 0.69, 0.13, 0.17, 0.22, max(6, alpha - 2)),
            (Accent.LOCKED, 0.82, 0.61, 0.13, 0.18, max(5, alpha - 4)),
        ),
        "command": (
            (Accent.STORAGE, 0.21, 0.22, 0.18, 0.44, max(5, alpha - 3)),
            (Accent.PROCESSOR, 0.51, 0.14, 0.20, 0.35, max(5, alpha - 2)),
            (Accent.CASH, 0.80, 0.50, 0.12, 0.24, max(5, alpha - 4)),
        ),
        "surface": (
            (Accent.EXTRACTOR, 0.08, 0.18, 0.24, 0.38, alpha + 4),
            (Accent.STORAGE, 0.26, 0.58, 0.25, 0.24, alpha),
            (Accent.PROCESSOR, 0.50, 0.16, 0.25, 0.34, alpha + 5),
            (Accent.ENERGY, 0.73, 0.52, 0.18, 0.22, max(6, alpha - 3)),
        ),
    }
    layout_key = role if role in layouts else "surface"
    if layout_key == "track" and variant % 2:
        layout_key = "track-alt"

    for index, (accent, x, y, width, height, zone_alpha) in enumerate(layouts[layout_key]):
        jitter = ((variant + index * 2) % 5 - 2) * 0.012
        zone = QRectF(
            rect.left() + rect.width() * max(0.0, min(0.92, x + jitter)),
            rect.top() + rect.height() * y,
            rect.width() * width,
            rect.height() * height,
        )
        material = QLinearGradient(zone.topLeft(), zone.bottomRight())
        material.setColorAt(0.0, _accent(accent, zone_alpha))
        material.setColorAt(0.52, _accent(accent, max(4, zone_alpha - 7)))
        material.setColorAt(1.0, QColor(0, 0, 0, 4))
        painter.setBrush(material)
        painter.drawRoundedRect(zone, max(4.0, radius * 0.42), max(4.0, radius * 0.42))

        blend = QRadialGradient(zone.center(), max(zone.width(), zone.height()) * 0.72)
        blend.setColorAt(0.0, _accent(accent, max(4, zone_alpha - 4)))
        blend.setColorAt(0.64, QColor(0, 0, 0, 0))
        blend.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(blend)
        painter.drawRoundedRect(zone.adjusted(-zone.width() * 0.16, -zone.height() * 0.2, zone.width() * 0.16, zone.height() * 0.2), radius, radius)

    grain = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grain.setColorAt(0.0, QColor(255, 255, 255, 4 + strength))
    grain.setColorAt(0.44, QColor(0, 0, 0, 0))
    grain.setColorAt(1.0, QColor(0, 0, 0, 18 + strength * 3))
    painter.setBrush(grain)
    painter.drawRoundedRect(rect, radius, radius)
    painter.restore()


def draw_utility_chassis(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.ENERGY,
    active: bool = False,
    warning: bool = False,
    opacity_boost: int = 0,
) -> QRectF:
    panel = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    cut = 4 if panel.height() < 78 else 6
    path = _dock_path(panel, cut)
    body = QLinearGradient(panel.topLeft(), panel.bottomRight())
    body.setColorAt(0.0, QColor(38, 45, 45, min(255, (168 if active else 146) + opacity_boost)))
    body.setColorAt(0.48, QColor(17, 24, 24, min(255, 222 + opacity_boost)))
    body.setColorAt(1.0, QColor(7, 10, 10, min(255, 244 + opacity_boost)))
    edge = Accent.WARNING if warning else accent
    painter.setPen(QPen(_neutral_edge_highlight(88 if active or warning else 56), 1.15))
    painter.setBrush(body)
    painter.drawPath(path)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_accent(edge, 32 if active or warning else 22))
    painter.drawRoundedRect(QRectF(panel.left() + 4, panel.top() + 10, 3, panel.height() - 20), 1.5, 1.5)
    if active and not warning:
        painter.setBrush(_accent(Accent.SUCCESS, 92))
        painter.drawRoundedRect(QRectF(panel.right() - 18, panel.top() + 11, 8, 2), 1, 1)

    sheen = QLinearGradient(panel.topLeft(), panel.topRight())
    sheen.setColorAt(0.0, QColor(255, 255, 255, 18 if active or warning else 12))
    sheen.setColorAt(0.52, _accent(edge, 18 if active or warning else 8))
    sheen.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(sheen)
    painter.drawRoundedRect(panel.adjusted(6, 6, -6, -panel.height() * 0.58), 3, 3)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_neutral_edge_highlight(26), 1))
    painter.drawPath(_dock_path(panel.adjusted(3, 3, -3, -3), max(4, cut - 3)))
    return panel


def draw_command_chassis(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.ENERGY,
    selected: bool = False,
    compact: bool = False,
    rank: bool = False,
) -> QRectF:
    panel = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    cut = 4 if compact else 6
    path = _dock_path(panel, cut)
    body = QLinearGradient(panel.topLeft(), panel.bottomRight())
    if rank:
        body.setColorAt(0.0, QColor(33, 32, 25, 224))
        body.setColorAt(0.48, QColor(15, 15, 12, 240))
        body.setColorAt(1.0, QColor(5, 5, 4, 252))
    else:
        body.setColorAt(0.0, QColor(34, 40, 40, 224 if selected else 206))
        body.setColorAt(0.52, QColor(13, 18, 18, 242))
        body.setColorAt(1.0, QColor(4, 6, 6, 252))
    painter.setPen(QPen(_accent(accent, 142 if selected else 96), 1.45))
    painter.setBrush(body)
    painter.drawPath(path)

    glow = QRadialGradient(_point(panel, 0.15, 0.18), max(panel.width(), panel.height()) * 0.76)
    glow.setColorAt(0.0, _accent(accent, 24 if selected else 13))
    glow.setColorAt(0.62, QColor(255, 255, 255, 3))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawPath(path)

    cap = QRectF(panel.left() + 11, panel.top() + 7, panel.width() - 22, 3)
    painter.setBrush(_accent(accent, 164 if selected else 108))
    painter.drawRoundedRect(cap, 1.5, 1.5)
    painter.setPen(QPen(QColor(255, 255, 246, 46 if selected else 30), 1))
    painter.drawLine(QPointF(panel.left() + 13, panel.top() + 12), QPointF(panel.right() - 13, panel.top() + 12))
    painter.setPen(Qt.PenStyle.NoPen)
    if accent in {Accent.ENERGY, Accent.BUILD, Accent.CASH, Accent.STORAGE, Accent.PROCESSOR}:
        painter.setBrush(_accent(accent, 230 if selected else 166))
        painter.drawRoundedRect(QRectF(panel.right() - 16, panel.top() + 14, 5, 5), 2.5, 2.5)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_neutral_edge_highlight(26), 1))
    painter.drawRoundedRect(panel.adjusted(4, 4, -4, -4), 5, 5)
    draw_industrial_edge(painter, panel, radius=6, inset=2)
    draw_panel_bolts(painter, panel, inset=7, radius=2.1, dark=True)
    draw_surface_wear(painter, panel.adjusted(12, 10, -12, -10), seed=37 + int(compact) * 13 + int(rank) * 23, density=2, dark=True)
    return panel


def draw_selection_chassis(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.ENERGY,
    selected: bool = False,
    disabled: bool = False,
) -> QRectF:
    panel = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    path = _dock_path(panel, 4)
    alpha = 54 if selected else 26
    if disabled:
        alpha = 14
    body = QLinearGradient(panel.topLeft(), panel.bottomRight())
    body.setColorAt(0.0, _accent(accent, alpha if selected else max(8, alpha // 2)))
    body.setColorAt(0.46, QColor(18, 23, 24, 158 if not disabled else 98))
    body.setColorAt(1.0, QColor(5, 7, 8, 210 if not disabled else 132))
    painter.setPen(QPen(_accent(accent, 90) if selected else _neutral_edge(48), 1))
    painter.setBrush(body)
    painter.drawPath(path)
    if selected:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_accent(accent, 88))
        painter.drawRoundedRect(QRectF(panel.left() + 4, panel.top() + 8, 3, panel.height() - 16), 1.5, 1.5)
    return panel


def draw_game_surface(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent = Accent.ENERGY,
    depth: int = 1,
    radius: float = 18,
    role: str = "surface",
    variant: int = 0,
) -> None:
    base = QLinearGradient(rect.topLeft(), rect.bottomRight())
    base.setColorAt(0.0, QColor(226, 224, 214, 212 + depth * 10))
    base.setColorAt(0.38, QColor(169, 171, 160, 224))
    base.setColorAt(1.0, QColor(74, 82, 78, 238))
    edge = QColor(68, 73, 68, 144 + depth * 18) if accent == Accent.NEUTRAL else _accent(accent, 28 + depth * 8)
    painter.setPen(QPen(edge, 1.25))
    painter.setBrush(base)
    painter.drawRoundedRect(rect, radius, radius)

    draw_industrial_base_surface(
        painter,
        rect.adjusted(4, 4, -4, -4),
        strength=max(1, min(3, depth + 1)),
        radius=max(2, radius - 5),
        role=role,
        variant=variant,
    )

    falloff = QLinearGradient(rect.topLeft(), rect.topRight())
    falloff.setColorAt(0.0, QColor(255, 255, 246, 8 + depth * 3))
    falloff.setColorAt(0.56, QColor(0, 0, 0, 0))
    falloff.setColorAt(1.0, QColor(0, 0, 0, 30 + depth * 5))
    painter.setBrush(falloff)
    painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), max(2, radius - 6), max(2, radius - 6))
    draw_industrial_edge(painter, rect, radius=radius, inset=2)
    if rect.width() > 220:
        draw_panel_seam(
            painter,
            QPointF(rect.left() + rect.width() * 0.12, rect.top() + 10),
            QPointF(rect.left() + rect.width() * 0.12, rect.bottom() - 10),
            alpha=28,
        )
    draw_panel_bolts(painter, rect, inset=11, radius=2.8, dark=True)


def draw_hall_control_assembly(painter: QPainter, rect: QRectF, *, variant: int = 0) -> None:
    """Paint the full Hall KPI row as one metallic gameplay control assembly."""
    panel = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    path = _chassis_path(panel, 12)
    painter.save()
    metal = QLinearGradient(panel.topLeft(), panel.bottomRight())
    metal.setColorAt(0.0, QColor(76, 82, 79, 242))
    metal.setColorAt(0.36, QColor(35, 42, 41, 248))
    metal.setColorAt(0.68, QColor(14, 19, 19, 253))
    metal.setColorAt(1.0, QColor(5, 7, 7, 255))
    painter.setPen(QPen(_neutral_edge_highlight(128), 1.6))
    painter.setBrush(metal)
    painter.drawPath(path)

    painter.setPen(Qt.PenStyle.NoPen)
    top_reflection = QLinearGradient(panel.topLeft(), panel.topRight())
    top_reflection.setColorAt(0.0, QColor(255, 255, 246, 30))
    top_reflection.setColorAt(0.44, QColor(255, 255, 255, 8))
    top_reflection.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(top_reflection)
    painter.drawPath(_chassis_path(panel.adjusted(6, 5, -6, -panel.height() * 0.72), 8))

    inner = panel.adjusted(8, 8, -8, -8)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(0, 0, 0, 176), 1.2))
    painter.drawPath(_chassis_path(inner, 8))
    painter.setPen(QPen(QColor(246, 244, 229, 44), 1))
    painter.drawLine(QPointF(panel.left() + 18, panel.top() + 10), QPointF(panel.right() - 18, panel.top() + 10))
    painter.setPen(QPen(QColor(0, 0, 0, 156), 1))
    painter.drawLine(QPointF(panel.left() + 18, panel.bottom() - 11), QPointF(panel.right() - 18, panel.bottom() - 11))

    accent_bar_rect = QRectF(panel.left() + 18, panel.top() + 13, panel.width() * 0.56, 3)
    accent_bar = QLinearGradient(accent_bar_rect.topLeft(), accent_bar_rect.topRight())
    accent_bar.setColorAt(0.0, _accent(Accent.ENERGY, 104))
    accent_bar.setColorAt(0.58, _accent(Accent.STORAGE, 58))
    accent_bar.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent_bar)
    painter.drawRoundedRect(accent_bar_rect, 1.5, 1.5)
    draw_panel_bolts(painter, panel, inset=10, radius=2.7, dark=True)
    draw_surface_wear(painter, panel.adjusted(14, 12, -14, -12), seed=151 + variant * 17, density=2, dark=True)
    painter.restore()


def draw_production_track(painter: QPainter, rect: QRectF, *, active: bool = True, variant: int = 0) -> None:
    draw_game_surface(painter, rect, accent=Accent.NEUTRAL, depth=0, radius=18, role="track", variant=variant)
    floor = QLinearGradient(rect.topLeft(), rect.bottomRight())
    floor.setColorAt(0.0, QColor(18, 22, 21, 184))
    floor.setColorAt(0.34, QColor(8, 11, 11, 204))
    floor.setColorAt(1.0, QColor(1, 2, 2, 230))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(floor)
    painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), 14, 14)
    focus = QRadialGradient(_point(rect, 0.22, 0.5), rect.width() * 0.44)
    focus.setColorAt(0.0, QColor(238, 232, 212, 5))
    focus.setColorAt(0.48, QColor(255, 255, 255, 2))
    focus.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(focus)
    painter.drawRoundedRect(rect.adjusted(8, 8, -8, -8), 12, 12)
    draw_panel_seam(painter, QPointF(rect.left() + 16, rect.top() + 18), QPointF(rect.right() - 16, rect.top() + 18), alpha=34)
    rail_top = QRectF(rect.left() + 10, rect.top() + 12, rect.width() - 20, 5)
    rail_bottom = QRectF(rect.left() + 10, rect.bottom() - 17, rect.width() - 20, 5)
    rail = QLinearGradient(rail_top.topLeft(), rail_top.bottomLeft())
    rail.setColorAt(0.0, QColor(246, 244, 229, 78))
    rail.setColorAt(0.5, QColor(91, 99, 94, 94))
    rail.setColorAt(1.0, QColor(0, 0, 0, 146))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(rail)
    painter.drawRoundedRect(rail_top, 2, 2)
    painter.drawRoundedRect(rail_bottom, 2, 2)
    painter.setPen(QPen(QColor(0, 0, 0, 154), 1))
    painter.drawLine(QPointF(rect.left() + 12, rect.top() + 19), QPointF(rect.right() - 12, rect.top() + 19))
    painter.drawLine(QPointF(rect.left() + 12, rect.bottom() - 20), QPointF(rect.right() - 12, rect.bottom() - 20))


def draw_machine_card(
    painter: QPainter,
    rect: QRectF,
    *,
    accent: Accent,
    rarity_accent: Accent = Accent.COMMON,
    flash: bool = False,
    hover: bool = False,
    active: bool = False,
) -> None:
    path = _machine_chassis_path(rect)
    lift = 1.0 if hover else 0.0
    body = QLinearGradient(rect.topLeft(), rect.bottomRight())
    body.setColorAt(0.0, QColor(126, 124, 111, 246))
    body.setColorAt(0.34, QColor(72, 76, 72, 252))
    body.setColorAt(1.0, QColor(22, 25, 24, 255))
    painter.setPen(QPen(_neutral_edge_highlight(86 + int(lift * 18)), 1.55))
    painter.setBrush(body)
    painter.drawPath(path)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_accent(accent, 62 + int(lift * 22)))
    painter.drawRoundedRect(QRectF(rect.left() + 3, rect.top() + rect.height() * 0.16, 5, rect.height() * 0.68), 2, 2)

    top_rect = QRectF(rect.left() + 8, rect.top() + 6, rect.width() - 16, 46)
    top = QLinearGradient(top_rect.topLeft(), top_rect.topRight())
    top.setColorAt(0.0, _accent(accent, 42 + int(lift * 14)))
    top.setColorAt(0.46, QColor(255, 255, 255, 13))
    top.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(top)
    painter.drawRoundedRect(top_rect, 5, 5)

    core_shadow = QRadialGradient(_point(rect, 0.52, 0.48), rect.width() * 0.66)
    core_shadow.setColorAt(0.0, QColor(255, 255, 255, 8 + int(lift * 5)))
    core_shadow.setColorAt(0.62, QColor(0, 0, 0, 0))
    core_shadow.setColorAt(1.0, QColor(0, 0, 0, 92))
    painter.setBrush(core_shadow)
    painter.drawPath(path)

    rare = {
        Accent.UNCOMMON: QColor(101, 216, 143, 72),
        Accent.RARE: QColor(127, 154, 164, 74),
        Accent.EPIC: QColor(177, 135, 255, 94),
        Accent.LEGENDARY: QColor(242, 194, 91, 104),
    }.get(rarity_accent, QColor(255, 255, 255, 28))
    painter.setBrush(rare)
    painter.drawRoundedRect(QRectF(rect.left() + 18, rect.top() + 8, rect.width() - 36, 3), 1.5, 1.5)

    if active:
        painter.setBrush(_accent(Accent.SUCCESS, 58))
        painter.drawRoundedRect(QRectF(rect.left() + 14, rect.bottom() - 10, rect.width() - 28, 3), 1.5, 1.5)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_neutral_edge_highlight(34 + int(lift * 12)), 1))
    painter.drawPath(_machine_chassis_path(rect.adjusted(5, 5, -5, -5)))
    draw_surface_wear(painter, rect.adjusted(14, 12, -14, -12), seed=53, density=2, dark=True)
    if flash:
        painter.setPen(QPen(QColor(216, 240, 106, 176), 2))
        painter.drawPath(_machine_chassis_path(rect.adjusted(3, 3, -3, -3)))


def draw_machine_icon_stage(
    painter: QPainter,
    rect: QRectF,
    *,
    icon: MachineIcon,
    accent: Accent,
) -> None:
    shadow = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.8)
    shadow.setColorAt(0.0, _accent(accent, 18))
    shadow.setColorAt(0.7, QColor(0, 0, 0, 92))
    shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shadow)
    painter.drawEllipse(rect.adjusted(-8, -4, 8, 12))
    stage = QLinearGradient(rect.topLeft(), rect.bottomRight())
    stage.setColorAt(0.0, QColor(49, 49, 45, 144))
    stage.setColorAt(0.5, QColor(18, 19, 18, 210))
    stage.setColorAt(1.0, QColor(6, 6, 5, 240))
    painter.setBrush(stage)
    painter.drawRoundedRect(rect, 8, 8)
    draw_machine_icon(painter, icon, rect.adjusted(0, -7, 0, -7), accent=accent)


_PROTOTYPE_FAMILY_COLORS: dict[str, QColor] = {
    "extractor": QColor("#d8a642"),
    "drilling": QColor("#d8a642"),
    "agriculture": QColor("#d8a642"),
    "processor": QColor("#5d94aa"),
    "fabricator": QColor("#df6b2f"),
    "assembly": QColor("#c83a2b"),
    "assembler": QColor("#c83a2b"),
    "energy": QColor("#ffd21f"),
    "solar": QColor("#ffd21f"),
    "wind": QColor("#d8e2e8"),
    "coal": QColor("#727d82"),
    "gas": QColor("#4db6ac"),
    "nuclear": QColor("#b9f05a"),
    "transport": QColor("#25b9e8"),
    "truck": QColor("#ffd21f"),
    "train": QColor(GAME_UI_TOKENS.colors.train),
    "ship": QColor("#25b9e8"),
    "aircraft": QColor("#9bb8ef"),
}


_PROTOTYPE_RARITY_COLORS: dict[str, QColor] = {
    "COMMON": QColor("#9ca8a4"),
    "UNCOMMON": QColor("#65d88f"),
    "RARE": QColor("#ffd21f"),
    "EPIC": QColor("#b187ff"),
    "LEGENDARY": QColor("#df6b2f"),
}


_PROTOTYPE_FAMILY_LABELS: dict[str, str] = {
    "extractor": "EXTRACT",
    "drilling": "DRILL",
    "agriculture": "GROW",
    "processor": "PROCESS",
    "fabricator": "FABRICATE",
    "assembly": "ASSEMBLE",
    "assembler": "ASSEMBLE",
    "energy": "ENERGY",
    "solar": "SOLAR",
    "wind": "WIND",
    "coal": "COAL",
    "gas": "GAS",
    "nuclear": "NUCLEAR",
    "transport": "FREIGHT",
    "truck": "TRUCK",
    "train": "RAIL",
    "ship": "SHIP",
    "aircraft": "AIR",
}


_BLOCK_GLYPHS: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("10010", "10010", "10010", "11111", "00010", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("01111", "10100", "10100", "01110", "00101", "00101", "11110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "·": ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
    "…": ("00000", "00000", "00000", "00000", "00000", "10101", "10101"),
    ">": ("10000", "01000", "00100", "00010", "00100", "01000", "10000"),
}


def _draw_prototype_block_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    color: QColor,
    *,
    max_cell: float = 2.0,
    align=Qt.AlignmentFlag.AlignLeft,
) -> None:
    text = text.upper()
    columns = sum(3 if char == " " else 6 for char in text)
    if columns <= 0:
        return
    cell = max(0.8, min(max_cell, rect.width() / columns, rect.height() / 7.0))
    text_width = columns * cell
    if align & Qt.AlignmentFlag.AlignHCenter:
        x = rect.left() + max(0.0, (rect.width() - text_width) / 2.0)
    else:
        x = rect.left()
    y = rect.top()
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    for char in text:
        if char == " ":
            x += cell * 3
            continue
        glyph = _BLOCK_GLYPHS.get(char)
        if glyph is None:
            x += cell * 6
            continue
        for row, line in enumerate(glyph):
            for col, bit in enumerate(line):
                if bit == "1":
                    painter.drawRect(QRectF(x + col * cell, y + row * cell, cell * 0.78, cell * 0.78))
        x += cell * 6
    painter.restore()


def _prototype_family_color(family: str, disabled: bool) -> QColor:
    color = QColor(_PROTOTYPE_FAMILY_COLORS.get(family.lower(), QColor("#ffd21f")))
    if disabled:
        color = color.darker(165)
        color.setAlpha(160)
    return color


def _prototype_rarity_color(meta: str, disabled: bool) -> QColor:
    normalized = meta.upper()
    rarity = next((name for name in ("LEGENDARY", "UNCOMMON", "COMMON", "RARE", "EPIC") if name in normalized), "COMMON")
    color = QColor(_PROTOTYPE_RARITY_COLORS[rarity])
    if disabled:
        color = color.darker(160)
        color.setAlpha(132)
    return color


def _prototype_family_label(family: str) -> str:
    return _PROTOTYPE_FAMILY_LABELS.get(family.lower(), family.replace("_", " ").upper()[:9])




def _draw_prototype_pictogram(painter: QPainter, rect: QRectF, *, family: str, disabled: bool = False) -> None:
    if family.lower() in FREIGHT_ASSETS:
        draw_freight_art(painter, rect, family=family.lower(), disabled=disabled)
        return
    if family.lower() in MACHINE_RASTER_ASSETS:
        draw_machine_art(painter, rect, family=family.lower(), disabled=disabled)
        return
    ink = QColor(8, 10, 10, 220 if not disabled else 136)
    accent_ink = QColor(255, 255, 246, 96 if not disabled else 42)
    stroke = max(3.0, min(rect.width(), rect.height()) * 0.055)
    painter.save()
    painter.setPen(QPen(ink, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    family = family.lower()
    energy_icon = {
        "solar": MachineIcon.SOLAR_ARRAY,
        "wind": MachineIcon.WIND_TURBINE,
        "coal": MachineIcon.COAL_POWER,
        "gas": MachineIcon.GAS_POWER,
        "nuclear": MachineIcon.NUCLEAR_POWER,
    }.get(family)
    if energy_icon is not None:
        accent = Accent.LEGENDARY if family == "nuclear" else Accent.WARNING if family in {"coal", "gas"} else Accent.ENERGY
        draw_machine_icon(painter, energy_icon, rect, accent=accent, disabled=disabled)
    elif family == "extractor":
        painter.setPen(QPen(ink, stroke * 1.08, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(_point(rect, 0.23, 0.78), _point(rect, 0.50, 0.20))
        painter.drawLine(_point(rect, 0.50, 0.20), _point(rect, 0.77, 0.78))
        painter.drawLine(_point(rect, 0.33, 0.55), _point(rect, 0.67, 0.55))
        scoop = QPolygonF([_point(rect, 0.38, 0.76), _point(rect, 0.62, 0.76), _point(rect, 0.54, 0.92), _point(rect, 0.46, 0.92)])
        painter.setBrush(ink)
        painter.drawPolygon(scoop)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(accent_ink, max(1.2, stroke * 0.45), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(_point(rect, 0.18, 0.86), _point(rect, 0.36, 0.86))
        painter.drawLine(_point(rect, 0.64, 0.86), _point(rect, 0.82, 0.86))
    elif family == "processor":
        chamber = rect.adjusted(rect.width() * 0.17, rect.height() * 0.20, -rect.width() * 0.17, -rect.height() * 0.18)
        painter.drawRoundedRect(chamber, 5, 5)
        painter.drawLine(_point(rect, 0.23, 0.40), _point(rect, 0.77, 0.40))
        painter.drawLine(_point(rect, 0.23, 0.63), _point(rect, 0.77, 0.63))
        painter.drawEllipse(QRectF(rect.center().x() - rect.width() * 0.12, rect.center().y() - rect.height() * 0.12, rect.width() * 0.24, rect.height() * 0.24))
        painter.setPen(QPen(accent_ink, max(1.2, stroke * 0.45), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(_point(rect, 0.12, 0.52), _point(rect, 0.26, 0.52))
        painter.drawLine(_point(rect, 0.74, 0.52), _point(rect, 0.88, 0.52))
    elif family == "assembly" or family == "assembler":
        left = QRectF(rect.left() + rect.width() * 0.14, rect.top() + rect.height() * 0.34, rect.width() * 0.25, rect.height() * 0.25)
        right = QRectF(rect.left() + rect.width() * 0.61, rect.top() + rect.height() * 0.34, rect.width() * 0.25, rect.height() * 0.25)
        core = QRectF(rect.left() + rect.width() * 0.39, rect.top() + rect.height() * 0.52, rect.width() * 0.22, rect.height() * 0.22)
        painter.drawEllipse(left)
        painter.drawRoundedRect(right, 4, 4)
        painter.drawRoundedRect(core, 4, 4)
        painter.drawLine(_point(left, 0.80, 0.50), _point(core, 0.05, 0.36))
        painter.drawLine(_point(right, 0.20, 0.50), _point(core, 0.95, 0.36))
        painter.setPen(QPen(accent_ink, max(1.2, stroke * 0.45), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(_point(rect, 0.28, 0.82), _point(rect, 0.72, 0.82))
        painter.drawLine(_point(rect, 0.50, 0.22), _point(rect, 0.50, 0.52))
    elif family == "fabricator":
        frame = QRectF(rect.left() + rect.width() * 0.16, rect.top() + rect.height() * 0.19, rect.width() * 0.68, rect.height() * 0.56)
        bed = QRectF(rect.left() + rect.width() * 0.22, rect.top() + rect.height() * 0.74, rect.width() * 0.56, rect.height() * 0.11)
        cutter = QPolygonF([
            _point(rect, 0.39, 0.35),
            _point(rect, 0.61, 0.35),
            _point(rect, 0.50, 0.61),
        ])
        painter.drawRoundedRect(frame, 4, 4)
        painter.drawLine(_point(rect, 0.25, 0.30), _point(rect, 0.75, 0.30))
        painter.setBrush(ink)
        painter.drawPolygon(cutter)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bed, 3, 3)
        painter.setPen(QPen(accent_ink, max(1.0, stroke * 0.42), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(_point(rect, 0.31, 0.66), _point(rect, 0.69, 0.66))
        painter.drawLine(_point(rect, 0.50, 0.61), _point(rect, 0.50, 0.72))
    elif family == "energy":
        bolt = QPolygonF([
            _point(rect, 0.56, 0.16),
            _point(rect, 0.30, 0.54),
            _point(rect, 0.49, 0.54),
            _point(rect, 0.39, 0.86),
            _point(rect, 0.72, 0.44),
            _point(rect, 0.54, 0.44),
        ])
        painter.setBrush(ink)
        painter.drawPolygon(bolt)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif family == "transport":
        chassis = QRectF(rect.left() + rect.width() * 0.14, rect.top() + rect.height() * 0.48, rect.width() * 0.70, rect.height() * 0.16)
        cargo = QRectF(rect.left() + rect.width() * 0.16, rect.top() + rect.height() * 0.30, rect.width() * 0.40, rect.height() * 0.26)
        cab = QRectF(rect.left() + rect.width() * 0.56, rect.top() + rect.height() * 0.36, rect.width() * 0.22, rect.height() * 0.27)
        windshield = QRectF(cab.left() + cab.width() * 0.20, cab.top() + cab.height() * 0.18, cab.width() * 0.46, cab.height() * 0.30)
        wheel_size = rect.width() * 0.16
        left_wheel = QRectF(rect.left() + rect.width() * 0.24, rect.top() + rect.height() * 0.62, wheel_size, wheel_size)
        right_wheel = QRectF(rect.left() + rect.width() * 0.60, rect.top() + rect.height() * 0.62, wheel_size, wheel_size)
        painter.setPen(QPen(ink, stroke * 1.15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawRoundedRect(cargo, 3, 3)
        painter.drawRoundedRect(cab, 3, 3)
        painter.drawLine(_point(chassis, 0.0, 0.5), _point(chassis, 1.0, 0.5))
        painter.setPen(QPen(accent_ink, max(1.0, stroke * 0.42), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(_point(cargo, 0.14, 0.5), _point(cargo, 0.86, 0.5))
        painter.drawRect(windshield)
        painter.setPen(QPen(ink, stroke * 0.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawEllipse(left_wheel)
        painter.drawEllipse(right_wheel)
        painter.drawEllipse(left_wheel.adjusted(wheel_size * 0.28, wheel_size * 0.28, -wheel_size * 0.28, -wheel_size * 0.28))
        painter.drawEllipse(right_wheel.adjusted(wheel_size * 0.28, wheel_size * 0.28, -wheel_size * 0.28, -wheel_size * 0.28))
    painter.restore()


def draw_machine_card_prototype(
    painter: QPainter,
    rect: QRectF,
    *,
    title: str,
    family: str,
    meta: str,
    detail: str,
    secondary: str = "",
    secondary_control: bool = False,
    secondary_hover: bool = False,
    disabled: bool = False,
    active: bool = False,
    hover: bool = False,
) -> None:
    """Paint the shared Factory V2 prototype machine-card language."""
    path = _machine_chassis_path(rect)
    family_color = _prototype_family_color(family, disabled)
    lift = 1.0 if hover and not disabled else 0.0
    painter.save()
    shadow = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    shadow.setColorAt(0.0, QColor(0, 0, 0, 32))
    shadow.setColorAt(1.0, QColor(0, 0, 0, 156))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shadow)
    painter.drawPath(_machine_chassis_path(rect.adjusted(2, 4, 2, 5)))

    body = QLinearGradient(rect.topLeft(), rect.bottomRight())
    body.setColorAt(0.0, QColor(58, 62, 59, 238 if not disabled else 184))
    body.setColorAt(0.42, QColor(18, 23, 23, 248 if not disabled else 208))
    body.setColorAt(1.0, QColor(5, 7, 7, 255 if not disabled else 224))
    edge_color = QColor(family_color)
    edge_color.setAlpha(min(255, edge_color.alpha() + int(lift * 34)))
    painter.setPen(QPen(edge_color, 1.6 if not disabled else 1.1))
    painter.setBrush(body)
    painter.drawPath(path)

    painter.setPen(QPen(QColor(246, 244, 229, 70 if not disabled else 32), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_machine_chassis_path(rect.adjusted(5, 5, -5, -5)))
    draw_surface_wear(painter, rect.adjusted(12, 12, -12, -12), seed=len(title) * 19, density=2, dark=True)
    draw_panel_bolts(painter, rect, inset=10, radius=2.3, dark=True)

    sign = QRectF(rect.left() + 18, rect.top() + 55, rect.width() - 36, rect.height() * 0.42)
    sign_body = QLinearGradient(sign.topLeft(), sign.bottomRight())
    sign_body.setColorAt(0.0, family_color.lighter(118 if hover and not disabled else 114 if not disabled else 104))
    sign_body.setColorAt(0.58, family_color.darker(104))
    sign_body.setColorAt(1.0, family_color.darker(178))
    painter.setPen(QPen(QColor(4, 5, 5, 228), 2))
    painter.setBrush(sign_body)
    painter.drawRoundedRect(sign, 7, 7)
    painter.setPen(QPen(QColor(255, 255, 246, 44 if not disabled else 20), 1))
    painter.drawLine(QPointF(sign.left() + 11, sign.top() + 9), QPointF(sign.right() - 11, sign.top() + 9))
    _draw_prototype_pictogram(painter, sign.adjusted(10, 12, -10, -10), family=family, disabled=disabled)

    header_title = QRectF(rect.left() + 20, rect.top() + 13, rect.width() - 40, 18)
    header_meta = QRectF(rect.left() + 20, rect.top() + 37, rect.width() - 40, 10)
    main_info = QRectF(rect.left() + 16, sign.bottom() + 7, rect.width() - 32, 15)
    secondary_info = QRectF(rect.left() + 16, sign.bottom() + 24, rect.width() - 32, 11)
    detail_color = QColor("#87928e") if detail.upper() == "SELECT" else QColor("#eff8f4")
    if disabled:
        detail_color = QColor("#59645f")
    _draw_prototype_block_text(painter, header_title, title, QColor("#eff8f4") if not disabled else QColor("#78817c"), max_cell=1.9)
    _draw_prototype_block_text(painter, header_meta, meta, family_color.lighter(122) if not disabled else QColor("#7d776c"), max_cell=1.15)
    if detail:
        _draw_prototype_block_text(painter, main_info, detail, detail_color, max_cell=1.45 if detail.upper() != "SELECT" else 1.15, align=Qt.AlignmentFlag.AlignHCenter)
    if secondary:
        if secondary_control:
            control = secondary_info.adjusted(-7, -4, 7, 5)
            control_body = QLinearGradient(control.topLeft(), control.bottomLeft())
            control_body.setColorAt(0.0, QColor(255, 255, 246, 22 if secondary_hover else 12))
            control_body.setColorAt(0.48, QColor(7, 10, 10, 168))
            control_body.setColorAt(1.0, QColor(0, 0, 0, 128))
            control_edge = QColor(family_color)
            control_edge.setAlpha(128 if secondary_hover else 76)
            painter.setPen(QPen(control_edge, 1))
            painter.setBrush(control_body)
            painter.drawRoundedRect(control, 5, 5)
        resource_color = QColor("#eff8f4") if secondary_hover and secondary_control else QColor("#d6e2dd")
        if disabled:
            resource_color = QColor("#59645f")
        _draw_prototype_block_text(painter, secondary_info, secondary, resource_color, max_cell=1.12, align=Qt.AlignmentFlag.AlignHCenter)
    painter.restore()


def draw_status_badge(painter: QPainter, rect: QRectF, *, text: str, accent: Accent) -> QRectF:
    font = painter.font()
    font.setPointSize(7)
    font.setWeight(font.Weight.Black)
    painter.setFont(font)
    width = min(rect.width(), max(66.0, painter.fontMetrics().horizontalAdvance(text) + 30.0))
    pill = QRectF(rect.center().x() - width / 2, rect.top(), width, rect.height())
    color = _accent(accent, 170 if accent in {Accent.SUCCESS, Accent.WARNING, Accent.DANGER} else 96)
    bg = QLinearGradient(pill.topLeft(), pill.bottomLeft())
    bg.setColorAt(0.0, QColor(255, 255, 255, 25))
    bg.setColorAt(1.0, QColor(0, 0, 0, 60))
    painter.setPen(QPen(color, 1))
    painter.setBrush(bg)
    painter.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QRectF(pill.left() + 9, pill.center().y() - 2.2, 4.4, 4.4))
    painter.setPen(QColor("#eff8f4"))
    painter.drawText(pill.adjusted(18, 0, -8, 0), Qt.AlignmentFlag.AlignCenter, text)
    return pill


def draw_build_slot(painter: QPainter, rect: QRectF, *, hover: bool = False, pressed: bool = False) -> QRectF:
    lift = 1.0 if hover else 0.0
    y_shift = 2 if pressed else 0
    pad = rect.adjusted(5, 11 + y_shift, -5, -9 + y_shift)
    path = _machine_chassis_path(pad)
    painter.save()
    shadow = QLinearGradient(pad.topLeft(), pad.bottomLeft())
    shadow.setColorAt(0.0, QColor(0, 0, 0, 30))
    shadow.setColorAt(1.0, QColor(0, 0, 0, 142 if not pressed else 96))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shadow)
    painter.drawPath(_machine_chassis_path(pad.adjusted(2, 4, 2, 5)))
    body = QLinearGradient(pad.topLeft(), pad.bottomRight())
    body.setColorAt(0.0, QColor(48, 55, 54, 242 + int(lift * 8)))
    body.setColorAt(0.42, QColor(18, 24, 24, 248))
    body.setColorAt(1.0, QColor(5, 7, 7, 255))
    painter.setPen(QPen(_safety_yellow(210 + int(lift * 38)), 2.35))
    painter.setBrush(body)
    painter.drawPath(path)
    painter.setPen(QPen(_neutral_edge_highlight(86 + int(lift * 34)), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_machine_chassis_path(pad.adjusted(4, 4, -4, -4)))
    painter.setPen(QPen(QColor(255, 246, 210, 54 + int(lift * 22)), 1))
    painter.drawLine(QPointF(pad.left() + 18, pad.top() + 12), QPointF(pad.right() - 18, pad.top() + 12))
    shine = QLinearGradient(pad.topLeft(), pad.topRight())
    shine.setColorAt(0.0, QColor(255, 255, 255, 20 + int(lift * 10)))
    shine.setColorAt(0.5, _safety_yellow(14 + int(lift * 14)))
    shine.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shine)
    painter.drawPath(_machine_chassis_path(pad.adjusted(5, 5, -5, -pad.height() * 0.72)))
    draw_surface_wear(painter, pad.adjusted(13, 15, -13, -28), seed=71, density=3, dark=True)
    draw_build_corner_brackets(painter, pad, hover=hover)
    draw_panel_bolts(painter, pad, inset=12, radius=2.4, dark=True)

    stage_side = min(pad.width() * 0.58, pad.height() * 0.34)
    stage = QRectF(pad.center().x() - stage_side / 2, pad.top() + pad.height() * 0.22, stage_side, stage_side)
    glow = QRadialGradient(stage.center(), stage_side * 0.72)
    glow.setColorAt(0.0, _safety_yellow(48 + int(lift * 44)))
    glow.setColorAt(0.68, QColor(0, 0, 0, 0))
    painter.setBrush(glow)
    painter.drawEllipse(stage.adjusted(-10, -10, 10, 10))
    painter.setBrush(QColor(9, 12, 12, 222 if not pressed else 242))
    painter.setPen(QPen(_safety_yellow(212 + int(lift * 32)), 3.2))
    painter.drawEllipse(stage)
    painter.setPen(QPen(_safety_yellow(244 if hover else 226), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    center = stage.center()
    arm = stage_side * 0.26
    painter.drawLine(QPointF(center.x() - arm, center.y()), QPointF(center.x() + arm, center.y()))
    painter.drawLine(QPointF(center.x(), center.y() - arm), QPointF(center.x(), center.y() + arm))
    draw_slot_hazard_footer(painter, pad, hover=hover)
    painter.restore()
    return stage


def draw_locked_slot(painter: QPainter, rect: QRectF, *, enabled: bool = False) -> QRectF:
    module = rect.adjusted(13, 23, -13, -23)
    path = _dock_path(module, 8)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 96 if enabled else 72))
    painter.drawPath(_dock_path(module.adjusted(2, 4, 2, 5), 8))
    body = QLinearGradient(module.topLeft(), module.bottomRight())
    body.setColorAt(0.0, QColor(42, 47, 46, 228 if enabled else 200))
    body.setColorAt(0.54, QColor(17, 22, 21, 238 if enabled else 216))
    body.setColorAt(1.0, QColor(5, 7, 7, 250))
    painter.setPen(QPen(_warning_orange(204 if enabled else 154), 1.85))
    painter.setBrush(body)
    painter.drawPath(path)
    painter.setPen(QPen(_neutral_edge_highlight(52 if enabled else 34), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(_dock_path(module.adjusted(4, 4, -4, -4), 5))
    painter.setPen(QPen(QColor(255, 226, 202, 36 if enabled else 24), 1))
    painter.drawLine(QPointF(module.left() + 16, module.top() + 22), QPointF(module.right() - 16, module.top() + 22))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_warning_orange(84 if enabled else 58))
    painter.drawRoundedRect(QRectF(module.left() + 12, module.top() + 12, module.width() - 24, 4), 2, 2)
    painter.setBrush(_warning_orange(82 if enabled else 56))
    painter.drawRoundedRect(QRectF(module.left() + 12, module.bottom() - 18, module.width() - 24, 4), 2, 2)
    draw_surface_wear(painter, module.adjusted(13, 18, -13, -22), seed=89, density=3, dark=True)
    draw_panel_bolts(painter, module, inset=9, radius=2.2, dark=True)
    lock_frame = draw_lock_warning_frame(painter, module, enabled=enabled)
    icon = lock_frame.adjusted(13, 9, -13, -9)
    draw_game_icon(painter, GameIcon.LOCK, icon, accent=Accent.LOCKED, disabled=not enabled)
    painter.restore()
    return module
