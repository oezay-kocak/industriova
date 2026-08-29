from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtGui import QColor, QFont


class Accent(str, Enum):
    NEUTRAL = "neutral"
    CASH = "cash"
    ENERGY = "energy"
    EXTRACTOR = "extractor"
    PROCESSOR = "processor"
    STORAGE = "storage"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    BUILD = "build"
    LOCKED = "locked"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class InteractionState(str, Enum):
    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    SELECTED = "selected"
    DISABLED = "disabled"
    WARNING = "warning"
    CRITICAL = "critical"


class MaterialLevel(str, Enum):
    BASE = "base"
    PANEL = "panel"
    ELEVATED = "elevated"
    INSET = "inset"
    TRACK = "track"
    UPGRADE = "upgrade"


@dataclass(frozen=True)
class GameUiColors:
    background: str = "#070c10"
    surface_0: str = "#0a1116"
    surface_1: str = "#121719"
    surface_2: str = "#1a1f20"
    surface_3: str = "#282c2b"
    chassis_light: str = "#d8d6cd"
    chassis_mid: str = "#a7aaa0"
    chassis_shadow: str = "#565d59"
    recessed_dark: str = "#0b1112"
    recessed_mid: str = "#182021"
    recessed_edge: str = "#303b3e"
    panel: str = "#181e1f"
    panel_elevated: str = "#2b302f"
    interactive: str = "#303534"
    interactive_hover: str = "#3d4240"
    edge_highlight: str = "#aaa89f"
    neutral_edge: str = "#58636a"
    neutral_edge_secondary: str = "#3e474d"
    neutral_edge_highlight: str = "#75828a"
    separator: str = "#474946"
    text_primary: str = "#eff8f4"
    text_secondary: str = "#b1c4c0"
    text_muted: str = "#6f837f"
    cash: str = "#7fed18"
    energy: str = "#ffd21f"
    extractor: str = "#b56b3f"
    processor: str = "#5d94aa"
    storage: str = "#25b9e8"
    success: str = "#65d88f"
    safety_yellow: str = "#ffd21f"
    area_anchor_red: str = "#c83a2b"
    warning: str = "#df6b2f"
    warning_orange: str = "#df6b2f"
    danger: str = "#f06f73"
    build: str = "#ffd21f"
    locked: str = "#df6b2f"
    rare: str = "#b187ff"

    def qcolor(self, value: str, alpha: int | None = None) -> QColor:
        color = QColor(value)
        if alpha is not None:
            color.setAlpha(alpha)
        return color

    def accent(self, accent: Accent, alpha: int | None = None) -> QColor:
        mapping = {
            Accent.CASH: self.cash,
            Accent.ENERGY: self.energy,
            Accent.EXTRACTOR: self.extractor,
            Accent.PROCESSOR: self.processor,
            Accent.STORAGE: self.storage,
            Accent.SUCCESS: self.success,
            Accent.WARNING: self.warning,
            Accent.DANGER: self.danger,
            Accent.BUILD: self.build,
            Accent.LOCKED: self.locked,
            Accent.UNCOMMON: self.success,
            Accent.RARE: self.energy,
            Accent.EPIC: self.rare,
            Accent.LEGENDARY: self.warning,
        }
        return self.qcolor(mapping.get(accent, self.separator), alpha)


@dataclass(frozen=True)
class GameUiGeometry:
    radius_small: int = 6
    radius_medium: int = 10
    radius_large: int = 16
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 18
    padding_sm: int = 8
    padding_md: int = 12
    padding_lg: int = 16
    border_thin: float = 1.0
    border_medium: float = 1.35
    header_height: int = 38
    card_width: int = 164
    card_height: int = 190


@dataclass(frozen=True)
class GameUiMaterial:
    gradient_soft: int = 18
    gradient_strong: int = 34
    edge_highlight_alpha: int = 92
    inset_alpha: int = 24
    glow_soft_alpha: int = 34
    glow_strong_alpha: int = 72
    disabled_alpha: int = 82


@dataclass(frozen=True)
class GameUiTypography:
    family: str = "Bahnschrift Condensed, Bahnschrift SemiCondensed, Agency FB, Arial Narrow, Bahnschrift, Segoe UI"

    def brand_display(self) -> QFont:
        font = QFont(self.family, 24, QFont.Weight.Black)
        font.setStretch(68)
        return font

    def industrial_title(self) -> QFont:
        font = QFont(self.family, 15, QFont.Weight.Black)
        font.setStretch(72)
        return font

    def industrial_label(self) -> QFont:
        font = QFont(self.family, 9, QFont.Weight.Black)
        font.setStretch(84)
        return font

    def display_value(self) -> QFont:
        font = QFont(self.family, 18, QFont.Weight.Black)
        font.setStretch(84)
        return font

    def section_title(self) -> QFont:
        font = QFont(self.family, 12, QFont.Weight.Black)
        font.setStretch(74)
        return font

    def card_title(self) -> QFont:
        font = QFont(self.family, 10, QFont.Weight.Black)
        font.setStretch(82)
        return font

    def secondary_label(self) -> QFont:
        return QFont("Segoe UI", 9, QFont.Weight.DemiBold)

    def micro_label(self) -> QFont:
        font = QFont(self.family, 7, QFont.Weight.Bold)
        font.setStretch(90)
        return font

    def status_label(self) -> QFont:
        font = QFont(self.family, 8, QFont.Weight.Black)
        font.setStretch(84)
        return font


@dataclass(frozen=True)
class GameUiTokens:
    colors: GameUiColors = GameUiColors()
    geometry: GameUiGeometry = GameUiGeometry()
    material: GameUiMaterial = GameUiMaterial()
    typography: GameUiTypography = GameUiTypography()


GAME_UI_TOKENS = GameUiTokens()
