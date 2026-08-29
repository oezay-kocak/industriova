from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from production_zero.ui.theme import Theme


ACCENT_COLORS = {
    "iron": "#9aa3ad",
    "copper": "#c77946",
    "coal": "#2b3135",
    "oil": "#15191c",
    "gas": "#4db6ac",
    "wood": "#8b6f45",
    "grain": "#d6b85c",
    "crop": "#8fbf5a",
    "cotton": "#d9e2e8",
    "crystal": "#8fd3ff",
    "chemical": "#6ec6ff",
    "metal": "#aab4bd",
    "electronics": "#54d6a2",
    "component": "#b3c0c8",
    "battery": "#9fd356",
    "food": "#d6a45c",
    "truck": "#e0b733",
    "vehicle": "#7ea6d8",
    "rail": "#8795a1",
    "ship": "#6aa5c8",
    "aircraft": "#9bb8ef",
    "space": "#b7a6ff",
    "medical": "#ef7f8f",
    "telecom": "#74d0e4",
    "default": Theme.RESOURCE,
}


KNOWN_ICON_KEYS = {
    "ore_chunk",
    "ore_iron",
    "ore_copper",
    "ore_gold",
    "ore_lithium",
    "ore_uranium",
    "ore_rare_earth",
    "coal_chunk",
    "oil_drop",
    "flame",
    "log",
    "wheat",
    "corn",
    "cotton",
    "fruit",
    "latex",
    "crystal",
    "sand",
    "stone_block",
    "salt_crystal",
    "sulfur_crystal",
    "graphite_block",
    "ingot",
    "flask",
    "chip",
    "battery",
    "package",
    "gear",
    "vehicle",
    "rail",
    "ship",
    "aircraft",
    "satellite",
    "medical",
    "signal",
    "hex",
}


def resource_icon_key(resource_id: str) -> str:
    rid = resource_id.lower()
    specific = {
        "iron_ore": "ore_iron",
        "copper_ore": "ore_copper",
        "gold_ore": "ore_gold",
        "lithium_ore": "ore_lithium",
        "uranium_ore": "ore_uranium",
        "rare_earth_ore": "ore_rare_earth",
        "fruit": "fruit",
        "natural_rubber": "latex",
        "silica_sand": "sand",
        "limestone": "stone_block",
        "salt": "salt_crystal",
        "sulfur": "sulfur_crystal",
        "graphite": "graphite_block",
    }
    if rid in specific:
        return specific[rid]
    if "oil" in rid or "bitumen" in rid:
        return "oil_drop"
    if "gas" in rid or "hydrogen" in rid:
        return "flame"
    if "timber" in rid or "lumber" in rid or "wood" in rid:
        return "log"
    if "wheat" in rid or "flour" in rid or "grain" in rid:
        return "wheat"
    if "corn" in rid:
        return "corn"
    if "cotton" in rid or "textile" in rid or "fabric" in rid or "clothing" in rid:
        return "cotton"
    if "coal" in rid:
        return "coal_chunk"
    if any(token in rid for token in ("quartz", "salt", "silica", "crystal", "gypsum", "fluorspar", "borate")):
        return "crystal"
    if "ore" in rid:
        return "ore_chunk"
    if any(token in rid for token in ("steel", "iron", "copper", "aluminum", "titanium", "zinc", "lead", "nickel", "gold", "silver", "palladium", "platinum", "vanadium", "alloy")):
        return "ingot"
    if any(token in rid for token in ("acid", "chemical", "chlorine", "ammonia", "polymer", "resin", "rubber", "feedstock", "lubricant")):
        return "flask"
    if any(token in rid for token in ("semiconductor", "chip", "cpu", "processor", "memory", "computing", "electronics", "sensor", "control", "display")):
        return "chip"
    if "battery" in rid or "cell" in rid or "storage" in rid:
        return "battery"
    if any(token in rid for token in ("food", "sugar", "fruit", "soy", "nutrition", "meal", "beverage", "bakery", "potato")):
        return "package"
    if any(token in rid for token in ("component", "motor", "gear", "pump", "compressor", "turbine", "bearing", "hydraulic")):
        return "gear"
    if any(token in rid for token in ("vehicle", "truck", "automotive", "tire")):
        return "vehicle"
    if "rail" in rid or "train" in rid or "locomotive" in rid:
        return "rail"
    if any(token in rid for token in ("ship", "marine", "vessel", "tanker", "boat")):
        return "ship"
    if any(token in rid for token in ("aircraft", "aerospace", "avionics", "jet")):
        return "aircraft"
    if any(token in rid for token in ("satellite", "rocket", "orbital", "space")):
        return "satellite"
    if any(token in rid for token in ("medical", "diagnostic", "surgical")):
        return "medical"
    if any(token in rid for token in ("telecom", "network", "router", "radio")):
        return "signal"
    return "hex"


def resource_accent_key(resource_id: str) -> str:
    rid = resource_id.lower()
    if "iron" in rid or "steel" in rid:
        return "iron"
    if "copper" in rid:
        return "copper"
    if "coal" in rid:
        return "coal"
    if "oil" in rid or "bitumen" in rid:
        return "oil"
    if "gas" in rid or "hydrogen" in rid:
        return "gas"
    if "timber" in rid or "lumber" in rid or "wood" in rid:
        return "wood"
    if "wheat" in rid or "corn" in rid or "flour" in rid:
        return "grain"
    if "cotton" in rid:
        return "cotton"
    if any(token in rid for token in ("fruit", "soy", "potato", "rapeseed", "sugar", "food", "nutrition")):
        return "crop"
    if any(token in rid for token in ("quartz", "salt", "silica", "gypsum", "fluorspar", "borate")):
        return "crystal"
    if any(token in rid for token in ("acid", "chemical", "polymer", "resin", "rubber", "chlorine", "ammonia")):
        return "chemical"
    if any(token in rid for token in ("chip", "cpu", "semiconductor", "electronics", "computing", "sensor", "control")):
        return "electronics"
    if "battery" in rid or "cell" in rid or "storage" in rid:
        return "battery"
    if "rail" in rid or "train" in rid:
        return "rail"
    if "ship" in rid or "marine" in rid or "vessel" in rid:
        return "ship"
    if "aircraft" in rid or "aerospace" in rid:
        return "aircraft"
    if "satellite" in rid or "rocket" in rid or "orbital" in rid:
        return "space"
    if "medical" in rid or "diagnostic" in rid:
        return "medical"
    if "telecom" in rid or "network" in rid or "radio" in rid:
        return "telecom"
    if "component" in rid:
        return "component"
    return "default"


def resource_accent_color(resource_id_or_accent: str) -> str:
    accent = resource_id_or_accent if resource_id_or_accent in ACCENT_COLORS else resource_accent_key(resource_id_or_accent)
    return ACCENT_COLORS.get(accent, ACCENT_COLORS["default"])


def resource_category(resource_id: str, stage: str | None = None) -> str:
    rid = resource_id.lower()
    if stage == "extractor":
        if "ore" in rid or rid in {"coal", "graphite"}:
            return "Ores / Metals"
        if any(token in rid for token in ("limestone", "gypsum", "clay", "kaolin", "quartz", "salt", "sulfur", "fluorspar", "borate", "phosphate", "potash", "magnesite", "silica")):
            return "Minerals"
        if "oil" in rid or "gas" in rid:
            return "Oil & Gas"
        if "timber" in rid or "rubber" in rid:
            return "Forestry"
        return "Agriculture"
    if any(token in rid for token in ("food", "wheat", "corn", "soy", "fruit", "sugar", "nutrition", "bakery", "beverage")):
        return "Food & Agriculture"
    if any(token in rid for token in ("chemical", "acid", "polymer", "resin", "rubber", "hydrogen", "gas")):
        return "Chemicals"
    if any(token in rid for token in ("chip", "cpu", "semiconductor", "electronics", "computing", "sensor", "network", "telecom")):
        return "Electronics"
    if any(token in rid for token in ("battery", "solar", "wind", "reactor", "turbine", "energy", "storage", "fuel")):
        return "Energy"
    if any(token in rid for token in ("vehicle", "rail", "ship", "aircraft", "aerospace", "satellite", "rocket")):
        return "Transport"
    if any(token in rid for token in ("medical", "diagnostic", "surgical")):
        return "Medical"
    if "component" in rid or "equipment" in rid or "machine" in rid:
        return "Components"
    return "Materials"


class ResourceIconWidget(QWidget):
    def __init__(self, resource_id: str, icon_key: str | None = None, accent_key: str | None = None, size: int = 42) -> None:
        super().__init__()
        self.resource_id = resource_id
        resolved_icon_key = icon_key or resource_icon_key(resource_id)
        self.icon_key = resolved_icon_key if resolved_icon_key in KNOWN_ICON_KEYS else resource_icon_key(resource_id)
        self.accent_key = accent_key or resource_accent_key(resource_id)
        self.setObjectName("resourceIcon")
        self.setFixedSize(size, size)
        self.setProperty("resourceId", resource_id)
        self.setProperty("iconKey", self.icon_key)
        self.setProperty("accentKey", self.accent_key)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(resource_accent_color(self.accent_key))
        muted = QColor(Theme.MUTED)
        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)
        painter.setPen(QPen(color, 2))
        painter.setBrush(QColor(Theme.PANEL_ALT))
        painter.drawRoundedRect(rect, 6, 6)
        inner = rect.adjusted(8, 8, -8, -8)
        painter.setBrush(color)
        painter.setPen(QPen(color, 2))
        key = self.icon_key
        if key in {"ore_chunk", "ore_iron"}:
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left(), inner.center().y()),
                QPointF(inner.left() + inner.width() * 0.35, inner.top()),
                QPointF(inner.right(), inner.top() + inner.height() * 0.25),
                QPointF(inner.right() - inner.width() * 0.18, inner.bottom()),
                QPointF(inner.left() + inner.width() * 0.18, inner.bottom() - inner.height() * 0.1),
            ]))
            if key == "ore_iron":
                painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
                painter.drawLine(inner.left() + 5, inner.center().y(), inner.right() - 6, inner.center().y() - 3)
        elif key == "ore_copper":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left() + 4, inner.top() + 3),
                QPointF(inner.right() - 3, inner.top() + 7),
                QPointF(inner.right() - 8, inner.bottom() - 2),
                QPointF(inner.left() + 1, inner.bottom() - 8),
            ]))
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
            painter.drawEllipse(inner.adjusted(8, 7, -8, -7))
        elif key == "ore_gold":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top()),
                QPointF(inner.right(), inner.top() + inner.height() * 0.38),
                QPointF(inner.right() - 4, inner.bottom()),
                QPointF(inner.left() + 5, inner.bottom() - 1),
                QPointF(inner.left(), inner.top() + inner.height() * 0.38),
            ]))
            painter.setBrush(QColor(Theme.PANEL_ALT))
            painter.drawEllipse(inner.adjusted(9, 9, -9, -9))
        elif key == "ore_lithium":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left() + 2, inner.top() + 7),
                QPointF(inner.center().x(), inner.top()),
                QPointF(inner.right() - 2, inner.top() + 7),
                QPointF(inner.right() - 6, inner.bottom() - 2),
                QPointF(inner.left() + 6, inner.bottom() - 2),
            ]))
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
            painter.drawLine(inner.center().x(), inner.top() + 4, inner.center().x(), inner.bottom() - 4)
        elif key == "ore_uranium":
            painter.drawEllipse(inner.adjusted(1, 1, -1, -1))
            painter.setBrush(QColor(Theme.PANEL_ALT))
            painter.drawEllipse(inner.adjusted(8, 8, -8, -8))
            painter.setPen(QPen(color, 2))
            painter.drawLine(inner.center().x(), inner.center().y(), inner.center().x(), inner.top() + 2)
            painter.drawLine(inner.center().x(), inner.center().y(), inner.left() + 4, inner.bottom() - 4)
            painter.drawLine(inner.center().x(), inner.center().y(), inner.right() - 4, inner.bottom() - 4)
        elif key == "ore_rare_earth":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top()),
                QPointF(inner.right(), inner.center().y()),
                QPointF(inner.center().x(), inner.bottom()),
                QPointF(inner.left(), inner.center().y()),
            ]))
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
            painter.drawLine(inner.left() + 6, inner.center().y(), inner.right() - 6, inner.center().y())
            painter.drawLine(inner.center().x(), inner.top() + 6, inner.center().x(), inner.bottom() - 6)
        elif key == "coal_chunk":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left(), inner.top() + 7),
                QPointF(inner.left() + 10, inner.top()),
                QPointF(inner.right() - 1, inner.top() + 9),
                QPointF(inner.right() - 6, inner.bottom() - 2),
                QPointF(inner.left() + 4, inner.bottom()),
            ]))
        elif key == "oil_drop":
            painter.drawEllipse(inner.adjusted(2, 8, -2, -1))
            painter.drawPie(inner.adjusted(6, -1, -6, 10), 40 * 16, 100 * 16)
        elif key == "flame":
            painter.drawEllipse(inner.adjusted(5, 9, -5, -1))
            painter.drawLine(inner.center().x(), inner.top(), inner.left() + 5, inner.center().y())
            painter.drawLine(inner.center().x(), inner.top(), inner.right() - 5, inner.center().y())
        elif key == "log":
            painter.drawRoundedRect(inner.adjusted(0, 8, 0, -5), 5, 5)
            painter.setPen(QPen(muted, 1))
            painter.drawLine(inner.left() + 5, inner.center().y(), inner.right() - 5, inner.center().y())
        elif key == "wheat":
            painter.drawLine(inner.center().x(), inner.bottom(), inner.center().x(), inner.top())
            for offset in (3, 8, 13):
                painter.drawLine(inner.center().x(), inner.top() + offset, inner.left() + 5, inner.top() + offset + 5)
                painter.drawLine(inner.center().x(), inner.top() + offset, inner.right() - 5, inner.top() + offset + 5)
        elif key == "corn":
            painter.drawEllipse(inner.adjusted(5, 0, -5, 0))
            painter.setPen(QPen(QColor(Theme.BACKGROUND), 1))
            painter.drawLine(inner.center().x(), inner.top() + 4, inner.center().x(), inner.bottom() - 4)
        elif key == "cotton":
            painter.drawEllipse(inner.adjusted(0, 6, -12, -8))
            painter.drawEllipse(inner.adjusted(8, 0, -4, -10))
            painter.drawEllipse(inner.adjusted(12, 8, 0, -4))
        elif key == "fruit":
            painter.drawEllipse(inner.adjusted(4, 7, -4, -1))
            painter.drawLine(inner.center().x(), inner.top() + 7, inner.center().x() + 4, inner.top())
            painter.drawEllipse(QRectF(inner.center().x() + 2, inner.top(), 8, 5))
        elif key == "latex":
            painter.drawEllipse(inner.adjusted(4, 8, -4, -1))
            painter.drawPie(inner.adjusted(8, 0, -8, 10), 45 * 16, 90 * 16)
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
            painter.drawLine(inner.left() + 7, inner.bottom() - 5, inner.right() - 7, inner.bottom() - 5)
        elif key == "crystal":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top()),
                QPointF(inner.right(), inner.center().y()),
                QPointF(inner.center().x(), inner.bottom()),
                QPointF(inner.left(), inner.center().y()),
            ]))
        elif key == "sand":
            painter.drawEllipse(QRectF(inner.left() + 2, inner.bottom() - 9, inner.width() - 4, 7))
            painter.drawEllipse(QRectF(inner.left() + 7, inner.center().y() - 2, 4, 4))
            painter.drawEllipse(QRectF(inner.center().x(), inner.top() + 7, 3, 3))
            painter.drawEllipse(QRectF(inner.right() - 9, inner.center().y(), 4, 4))
        elif key == "stone_block":
            painter.drawRoundedRect(inner.adjusted(1, 7, -1, -5), 2, 2)
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 1))
            painter.drawLine(inner.left() + 5, inner.top() + 11, inner.right() - 5, inner.top() + 11)
        elif key == "salt_crystal":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top() + 1),
                QPointF(inner.right() - 2, inner.center().y()),
                QPointF(inner.center().x(), inner.bottom() - 1),
                QPointF(inner.left() + 2, inner.center().y()),
            ]))
            painter.setBrush(QColor(Theme.PANEL_ALT))
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top() + 8),
                QPointF(inner.right() - 9, inner.center().y()),
                QPointF(inner.center().x(), inner.bottom() - 8),
                QPointF(inner.left() + 9, inner.center().y()),
            ]))
        elif key == "sulfur_crystal":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left() + 4, inner.top()),
                QPointF(inner.right() - 2, inner.top() + 4),
                QPointF(inner.right() - 7, inner.bottom()),
                QPointF(inner.left(), inner.bottom() - 6),
            ]))
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 2))
            painter.drawLine(inner.left() + 7, inner.top() + 6, inner.right() - 8, inner.bottom() - 7)
        elif key == "graphite_block":
            painter.drawRect(inner.adjusted(3, 4, -3, -4))
            painter.setPen(QPen(QColor(Theme.PANEL_ALT), 1))
            painter.drawLine(inner.left() + 6, inner.top() + 9, inner.right() - 6, inner.top() + 9)
            painter.drawLine(inner.left() + 6, inner.center().y(), inner.right() - 6, inner.center().y())
        elif key == "ingot":
            painter.drawRoundedRect(inner.adjusted(1, 8, -1, -8), 3, 3)
        elif key == "flask":
            painter.drawRect(inner.adjusted(8, 0, -8, -12))
            painter.drawRoundedRect(inner.adjusted(2, 10, -2, 0), 5, 5)
        elif key == "chip":
            painter.drawRect(inner.adjusted(5, 5, -5, -5))
            painter.setPen(QPen(muted, 1))
            for i in range(4):
                y = inner.top() + 6 + i * 5
                painter.drawLine(inner.left(), y, inner.left() + 5, y)
                painter.drawLine(inner.right() - 5, y, inner.right(), y)
        elif key == "battery":
            painter.drawRoundedRect(inner.adjusted(1, 6, -4, -6), 3, 3)
            painter.drawRect(QRectF(inner.right() - 4, inner.center().y() - 4, 4, 8))
        elif key == "package":
            painter.drawRect(inner.adjusted(3, 6, -3, -3))
            painter.setPen(QPen(muted, 1))
            painter.drawLine(inner.left() + 3, inner.top() + 13, inner.right() - 3, inner.top() + 13)
        elif key == "gear":
            painter.drawEllipse(inner.adjusted(3, 3, -3, -3))
            painter.setBrush(QColor(Theme.PANEL_ALT))
            painter.drawEllipse(inner.adjusted(10, 10, -10, -10))
        elif key == "vehicle":
            painter.drawRoundedRect(inner.adjusted(1, 10, -1, -7), 3, 3)
            painter.setBrush(QColor(Theme.PANEL_ALT))
            painter.drawEllipse(QRectF(inner.left() + 5, inner.bottom() - 8, 6, 6))
            painter.drawEllipse(QRectF(inner.right() - 11, inner.bottom() - 8, 6, 6))
        elif key == "rail":
            painter.drawLine(inner.left() + 4, inner.top(), inner.left() + 4, inner.bottom())
            painter.drawLine(inner.right() - 4, inner.top(), inner.right() - 4, inner.bottom())
            painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
        elif key == "ship":
            painter.drawPolygon(QPolygonF([
                QPointF(inner.left(), inner.center().y()),
                QPointF(inner.right(), inner.center().y()),
                QPointF(inner.right() - 7, inner.bottom()),
                QPointF(inner.left() + 6, inner.bottom()),
            ]))
        elif key == "aircraft":
            painter.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
            painter.drawLine(inner.center().x(), inner.top(), inner.center().x(), inner.bottom())
        elif key == "satellite":
            painter.drawRect(inner.adjusted(9, 9, -9, -9))
            painter.drawLine(inner.left(), inner.top(), inner.left() + 10, inner.top() + 10)
            painter.drawLine(inner.right(), inner.bottom(), inner.right() - 10, inner.bottom() - 10)
        elif key == "medical":
            painter.drawRect(inner.adjusted(10, 2, -10, -2))
            painter.drawRect(inner.adjusted(3, 9, -3, -9))
        elif key == "signal":
            painter.drawEllipse(inner.adjusted(9, 9, -9, -9))
            painter.drawArc(inner.adjusted(2, 2, -2, -2), 35 * 16, 110 * 16)
        else:
            painter.drawPolygon(QPolygonF([
                QPointF(inner.center().x(), inner.top()),
                QPointF(inner.right(), inner.top() + inner.height() * 0.25),
                QPointF(inner.right(), inner.bottom() - inner.height() * 0.25),
                QPointF(inner.center().x(), inner.bottom()),
                QPointF(inner.left(), inner.bottom() - inner.height() * 0.25),
                QPointF(inner.left(), inner.top() + inner.height() * 0.25),
            ]))
