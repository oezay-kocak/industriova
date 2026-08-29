from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from production_zero.ui.game_ui.icons import GameIcon, GameIconWidget, draw_game_icon
from production_zero.ui.game_ui.materials import draw_game_panel, draw_inset_surface, draw_track_surface, draw_upgrade_surface
from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS, InteractionState, MaterialLevel


class _InteractivePaintWidget(QWidget):
    clicked = Signal()

    def __init__(self, *, accent: Accent = Accent.NEUTRAL, selected: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = accent
        self._hovered = False
        self._pressed = False
        self._selected = selected
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @property
    def accent(self) -> Accent:
        return self._accent

    @property
    def selected(self) -> bool:
        return self._selected

    def setSelected(self, selected: bool) -> None:  # noqa: N802
        self._selected = selected
        self.update()

    def interaction_state(self) -> InteractionState:
        if not self.isEnabled():
            return InteractionState.DISABLED
        if self._pressed:
            return InteractionState.PRESSED
        if self._selected:
            return InteractionState.SELECTED
        if self._hovered:
            return InteractionState.HOVER
        return InteractionState.NORMAL

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._pressed = True
            self.update()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if was_pressed and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            return
        super().mouseReleaseEvent(event)


class GamePanel(QFrame):
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        *,
        accent: Accent = Accent.NEUTRAL,
        level: MaterialLevel = MaterialLevel.PANEL,
        selected: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._level = level
        self._selected = selected
        self.setObjectName("gamePanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumSize(180, 118)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)
        if title:
            label = QLabel(title.upper())
            label.setObjectName("gamePanelTitle")
            label.setFont(GAME_UI_TOKENS.typography.section_title())
            label.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.text_primary}; background: transparent;")
            layout.addWidget(label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("gamePanelSubtitle")
            sub.setFont(GAME_UI_TOKENS.typography.secondary_label())
            sub.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.text_secondary}; background: transparent;")
            layout.addWidget(sub)
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        layout.addLayout(self._content_layout)
        layout.addStretch(1)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_game_panel(
                painter,
                QRectF(1, 1, self.width() - 2, self.height() - 2),
                accent=self._accent,
                state=InteractionState.SELECTED if self._selected else InteractionState.NORMAL,
                level=self._level,
            )
        finally:
            painter.end()
        super().paintEvent(event)


class GameButton(_InteractivePaintWidget):
    def __init__(self, text: str, *, variant: str = "secondary", accent: Accent | None = None, parent: QWidget | None = None) -> None:
        variant_accents = {
            "primary": Accent.BUILD,
            "secondary": Accent.NEUTRAL,
            "destructive": Accent.DANGER,
            "upgrade": Accent.LOCKED,
        }
        super().__init__(accent=accent or variant_accents.get(variant, Accent.NEUTRAL), parent=parent)
        self._text = text
        self._variant = variant
        self.setObjectName("gameButton")
        self.setMinimumSize(112, 38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def variant(self) -> str:
        return self._variant

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            state = self.interaction_state()
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            if self._variant == "primary" and self.accent == Accent.BUILD:
                body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                if state == InteractionState.PRESSED:
                    body.setColorAt(0.0, QColor("#c89305"))
                    body.setColorAt(0.48, GAME_UI_TOKENS.colors.accent(Accent.BUILD, 232))
                    body.setColorAt(1.0, QColor("#745200"))
                else:
                    body.setColorAt(0.0, QColor("#fff06f"))
                    body.setColorAt(0.44, GAME_UI_TOKENS.colors.accent(Accent.BUILD, 246))
                    body.setColorAt(0.78, QColor("#c88f00"))
                    body.setColorAt(1.0, QColor("#111008"))
                painter.setPen(QPen(QColor(7, 8, 7, 238), 2))
                painter.setBrush(body)
                painter.drawRoundedRect(rect, GAME_UI_TOKENS.geometry.radius_medium, GAME_UI_TOKENS.geometry.radius_medium)
                painter.setPen(QPen(QColor(255, 246, 210, 174 if state == InteractionState.HOVER else 118), 1))
                painter.drawLine(rect.left() + 9, rect.top() + 6, rect.right() - 9, rect.top() + 6)
                painter.setPen(QPen(QColor(0, 0, 0, 150), 1))
                painter.drawLine(rect.left() + 9, rect.bottom() - 5, rect.right() - 9, rect.bottom() - 5)
            else:
                draw_game_panel(
                    painter,
                    rect,
                    accent=self.accent,
                    state=state,
                    level=MaterialLevel.ELEVATED if self._variant in {"primary", "upgrade"} else MaterialLevel.PANEL,
                    radius=GAME_UI_TOKENS.geometry.radius_medium,
                )
            text_color = "#10120a" if self._variant == "primary" and self.accent == Accent.BUILD else GAME_UI_TOKENS.colors.text_primary
            color = GAME_UI_TOKENS.colors.qcolor(text_color, 105 if state == InteractionState.DISABLED else 255)
            painter.setPen(color)
            if self._variant == "primary" and self.accent == Accent.BUILD:
                font = GAME_UI_TOKENS.typography.industrial_title()
                font.setPointSize(12 if self.height() <= 38 else 14)
                font.setWeight(font.Weight.Black)
                painter.setFont(font)
                while font.pointSize() > 10 and painter.fontMetrics().horizontalAdvance(self._text.upper()) > self.width() - 18:
                    font.setPointSize(font.pointSize() - 1)
                    painter.setFont(font)
            else:
                painter.setFont(GAME_UI_TOKENS.typography.status_label())
            painter.drawText(QRectF(8, 0, self.width() - 16, self.height()), Qt.AlignmentFlag.AlignCenter, self._text.upper())
        finally:
            painter.end()


class ResourceChip(QFrame):
    def __init__(self, icon: GameIcon, name: str, value: str, rate: str = "", *, accent: Accent | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._accent = accent or Accent.NEUTRAL
        self.setObjectName("resourceChip")
        self.setMinimumSize(150, 54)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(9)
        icon_widget = GameIconWidget(icon, accent=accent)
        icon_widget.setFixedSize(34, 34)
        layout.addWidget(icon_widget)
        text = QVBoxLayout()
        text.setSpacing(1)
        name_label = QLabel(name.upper())
        name_label.setObjectName("resourceChipName")
        name_label.setFont(GAME_UI_TOKENS.typography.micro_label())
        name_label.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.text_secondary}; background: transparent;")
        value_label = QLabel(value)
        value_label.setObjectName("resourceChipValue")
        value_label.setFont(GAME_UI_TOKENS.typography.section_title())
        value_label.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.text_primary}; background: transparent;")
        text.addWidget(name_label)
        text.addWidget(value_label)
        if rate:
            rate_label = QLabel(rate)
            rate_label.setObjectName("resourceChipRate")
            rate_label.setFont(GAME_UI_TOKENS.typography.micro_label())
            rate_label.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.cash}; background: transparent;")
            text.addWidget(rate_label)
        layout.addLayout(text, 1)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_inset_surface(painter, QRectF(1, 1, self.width() - 2, self.height() - 2), accent=self._accent)
        finally:
            painter.end()
        super().paintEvent(event)


class StatusBadge(QFrame):
    def __init__(self, text: str, *, accent: Accent = Accent.SUCCESS, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("statusBadge")
        self.setMinimumSize(82, 24)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(5)
        self._dot = QLabel("")
        self._dot.setObjectName("statusBadgeDot")
        self._dot.setFixedSize(6, 6)
        self._dot.setStyleSheet(f"background: {GAME_UI_TOKENS.colors.accent(accent).name()}; border-radius: 3px;")
        label = QLabel(text.upper())
        label.setObjectName("statusBadgeText")
        label.setFont(GAME_UI_TOKENS.typography.status_label())
        label.setStyleSheet(f"color: {GAME_UI_TOKENS.colors.accent(accent).name()}; background: transparent;")
        layout.addWidget(self._dot)
        layout.addWidget(label, 1)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_inset_surface(painter, QRectF(1, 1, self.width() - 2, self.height() - 2), accent=self._accent, radius=8)
        finally:
            painter.end()
        super().paintEvent(event)


class BuildSlotWidget(_InteractivePaintWidget):
    def __init__(self, title: str = "Build Slot", subtitle: str = "Install module", parent: QWidget | None = None) -> None:
        super().__init__(accent=Accent.BUILD, parent=parent)
        self._title = title
        self._subtitle = subtitle
        self.setObjectName("buildSlotWidget")
        self.setMinimumSize(132, 132)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _stage_rect(self, rect: QRectF) -> QRectF:
        side = min(rect.width() * 0.58, rect.height() * 0.38)
        return QRectF(rect.center().x() - side / 2, rect.top() + rect.height() * 0.16, side, side)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_game_panel(painter, rect, accent=Accent.BUILD, state=self.interaction_state(), level=MaterialLevel.INSET, radius=12)
            stage = self._stage_rect(rect)
            draw_inset_surface(painter, stage, accent=Accent.BUILD, state=self.interaction_state(), radius=14)
            painter.setPen(QPen(GAME_UI_TOKENS.colors.accent(Accent.BUILD, 72), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(stage.adjusted(5, 5, -5, -5), 10, 10)
            draw_game_icon(painter, GameIcon.BUILD, stage.adjusted(stage.width() * 0.25, stage.height() * 0.25, -stage.width() * 0.25, -stage.height() * 0.25), accent=Accent.BUILD)
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_primary))
            painter.setFont(GAME_UI_TOKENS.typography.card_title())
            painter.drawText(QRectF(rect.left() + 8, rect.top() + rect.height() * 0.62, rect.width() - 16, 18), Qt.AlignmentFlag.AlignCenter, self._title.upper())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
            painter.setFont(GAME_UI_TOKENS.typography.micro_label())
            painter.drawText(QRectF(rect.left() + 8, rect.top() + rect.height() * 0.75, rect.width() - 16, 16), Qt.AlignmentFlag.AlignCenter, self._subtitle)
        finally:
            painter.end()


class LockedUpgradeWidget(_InteractivePaintWidget):
    def __init__(self, title: str = "Upgrade Bay", cost: str = "$250", cta: str = "Unlock", parent: QWidget | None = None) -> None:
        super().__init__(accent=Accent.LOCKED, parent=parent)
        self._title = title
        self._cost = cost
        self._cta = cta
        self.setObjectName("lockedUpgradeWidget")
        self.setMinimumSize(132, 132)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_upgrade_surface(painter, rect, state=self.interaction_state(), radius=12)
            icon_rect = QRectF(rect.center().x() - 18, rect.top() + 18, 36, 36)
            draw_game_icon(painter, GameIcon.LOCK, icon_rect, accent=Accent.LOCKED)
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_primary))
            painter.setFont(GAME_UI_TOKENS.typography.card_title())
            painter.drawText(QRectF(rect.left() + 8, rect.top() + 60, rect.width() - 16, 18), Qt.AlignmentFlag.AlignCenter, self._title.upper())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.cash))
            painter.setFont(GAME_UI_TOKENS.typography.section_title())
            painter.drawText(QRectF(rect.left() + 8, rect.top() + 80, rect.width() - 16, 20), Qt.AlignmentFlag.AlignCenter, self._cost)
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
            painter.setFont(GAME_UI_TOKENS.typography.micro_label())
            painter.drawText(QRectF(rect.left() + 8, rect.top() + 103, rect.width() - 16, 16), Qt.AlignmentFlag.AlignCenter, self._cta.upper())
        finally:
            painter.end()


class GameCardFrame(_InteractivePaintWidget):
    def __init__(
        self,
        title: str = "Machine Module",
        primary: str = "Iron",
        status: str = "Running",
        *,
        meta: str = "MK I",
        detail: str = "",
        icon: GameIcon = GameIcon.HALL,
        accent: Accent = Accent.ENERGY,
        status_accent: Accent = Accent.SUCCESS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(accent=accent, parent=parent)
        self._title = title
        self._primary = primary
        self._status = status
        self._meta = meta
        self._detail = detail
        self._icon = icon
        self._status_accent = status_accent
        self.setObjectName("gameCardFrame")
        self.setMinimumSize(GAME_UI_TOKENS.geometry.card_width, GAME_UI_TOKENS.geometry.card_height)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_game_panel(painter, rect, accent=self.accent, state=self.interaction_state(), level=MaterialLevel.ELEVATED, radius=14)
            header = QRectF(rect.left() + 8, rect.top() + 8, rect.width() - 16, 34)
            draw_inset_surface(painter, header, accent=self.accent, radius=9)
            icon_stage = QRectF(rect.left() + 20, rect.top() + 52, rect.width() - 40, 64)
            draw_inset_surface(painter, icon_stage, accent=self.accent, radius=12)
            draw_game_icon(painter, self._icon, QRectF(icon_stage.center().x() - 24, icon_stage.center().y() - 24, 48, 48), accent=self.accent)
            primary_zone = QRectF(rect.left() + 12, rect.top() + 122, rect.width() - 24, 42)
            draw_inset_surface(painter, primary_zone, accent=self.accent, radius=9)
            footer = QRectF(rect.left() + 9, rect.bottom() - 26, rect.width() - 18, 18)
            draw_inset_surface(painter, footer, accent=self._status_accent, radius=7)
            painter.setFont(GAME_UI_TOKENS.typography.card_title())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_primary))
            painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._title.upper())
            painter.setFont(GAME_UI_TOKENS.typography.micro_label())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
            painter.drawText(header.adjusted(8, 13, -8, 0), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, self._meta.upper())
            painter.setFont(GAME_UI_TOKENS.typography.status_label())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_primary))
            painter.drawText(primary_zone.adjusted(4, 0, -4, -14), Qt.AlignmentFlag.AlignCenter, self._primary.upper())
            if self._detail:
                painter.setFont(GAME_UI_TOKENS.typography.micro_label())
                painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
                painter.drawText(primary_zone.adjusted(4, 18, -4, 0), Qt.AlignmentFlag.AlignCenter, self._detail)
            painter.setPen(GAME_UI_TOKENS.colors.accent(self._status_accent))
            painter.drawText(footer, Qt.AlignmentFlag.AlignCenter, self._status.upper())
        finally:
            painter.end()


class ProductionTrack(QFrame):
    def __init__(self, title: str = "Line 01", *, accent: Accent = Accent.ENERGY, slots: int = 4, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._accent = accent
        self._slots = slots
        self.setObjectName("productionTrack")
        self.setMinimumSize(420, 134)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._slot_layout = QHBoxLayout(self)
        self._slot_layout.setContentsMargins(22, 48, 22, 14)
        self._slot_layout.setSpacing(12)

    def add_track_widget(self, widget: QWidget) -> None:
        widget.setParent(self)
        self._slot_layout.addWidget(widget)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_track_surface(painter, rect, accent=self._accent, radius=16)
            painter.setFont(GAME_UI_TOKENS.typography.section_title())
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_primary))
            painter.drawText(QRectF(rect.left() + 16, rect.top() + 8, rect.width() - 32, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._title.upper())
            slot_w = min(72.0, (rect.width() - 44) / max(1, self._slots) - 8)
            y = rect.top() + 44
            x = rect.left() + 18
            if not self.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                for index in range(self._slots):
                    slot = QRectF(x + index * (slot_w + 8), y, slot_w, 62)
                    draw_inset_surface(painter, slot, accent=self._accent, radius=9)
                    painter.setPen(QPen(GAME_UI_TOKENS.colors.accent(self._accent, 48), 1))
                    painter.drawLine(slot.left() + 10, slot.center().y(), slot.right() - 10, slot.center().y())
        finally:
            painter.end()


class GameUiShowcase(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gameUiShowcase")
        self.setMinimumSize(1280, 720)
        layout = QGridLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(16)

        deck = GamePanel("Command Deck", "Primary systems, secondary resources, progression", accent=Accent.ENERGY, level=MaterialLevel.ELEVATED)
        deck.setMinimumHeight(172)
        deck_grid = QGridLayout()
        deck_grid.setContentsMargins(0, 4, 0, 0)
        deck_grid.setHorizontalSpacing(12)
        deck_grid.setVerticalSpacing(10)
        deck_grid.addWidget(ResourceChip(GameIcon.CASH, "Cash", "$12,480", "+420/min", accent=Accent.CASH), 0, 0)
        deck_grid.addWidget(ResourceChip(GameIcon.ENERGY, "Energy", "188 MW", "+35 spare", accent=Accent.ENERGY), 0, 1)
        deck_grid.addWidget(ResourceChip(GameIcon.STORAGE, "Storage", "62%", "4.2k cap", accent=Accent.STORAGE), 0, 2)
        deck_grid.addWidget(ResourceChip(GameIcon.EXPANSION, "Company XP", "Level 8", "740 / 1000", accent=Accent.SUCCESS), 0, 3)
        deck_grid.addWidget(ResourceChip(GameIcon.IRON_ORE, "Iron Ore", "1,240", "+180/min", accent=Accent.NEUTRAL), 1, 0)
        deck_grid.addWidget(ResourceChip(GameIcon.IRON, "Iron", "820", "+90/min", accent=Accent.STORAGE), 1, 1)
        deck_grid.addWidget(ResourceChip(GameIcon.COPPER, "Copper", "510", "+48/min", accent=Accent.WARNING), 1, 2)
        deck_grid.addWidget(ResourceChip(GameIcon.STEEL, "Steel", "260", "+24/min", accent=Accent.STORAGE), 1, 3)
        deck.content_layout.addLayout(deck_grid)
        layout.addWidget(deck, 0, 0, 1, 4)

        controls = GamePanel("Navigation States", "Button material and interaction examples", accent=Accent.BUILD)
        controls.setMinimumWidth(300)
        control_grid = QGridLayout()
        control_grid.setContentsMargins(0, 6, 0, 0)
        control_grid.setHorizontalSpacing(10)
        control_grid.setVerticalSpacing(10)
        primary = GameButton("Build Machine", variant="primary")
        secondary = GameButton("Production Guide", variant="secondary")
        upgrade = GameButton("Upgrade Bay", variant="upgrade")
        destructive = GameButton("Remove Card", variant="destructive")
        disabled = GameButton("No Power", variant="secondary")
        disabled.setEnabled(False)
        selected = GameButton("Selected Hall", variant="primary")
        selected.setSelected(True)
        control_grid.addWidget(primary, 0, 0)
        control_grid.addWidget(secondary, 0, 1)
        control_grid.addWidget(upgrade, 1, 0)
        control_grid.addWidget(destructive, 1, 1)
        control_grid.addWidget(disabled, 2, 0)
        control_grid.addWidget(selected, 2, 1)
        controls.content_layout.addLayout(control_grid)
        layout.addWidget(controls, 1, 0)

        badges = GamePanel("Status Badges", "Runtime state language", accent=Accent.SUCCESS)
        badge_layout = QVBoxLayout()
        badge_layout.setContentsMargins(0, 6, 0, 0)
        badge_layout.setSpacing(8)
        badge_layout.addWidget(StatusBadge("Running", accent=Accent.SUCCESS))
        badge_layout.addWidget(StatusBadge("No Power", accent=Accent.DANGER))
        badge_layout.addWidget(StatusBadge("Storage Full", accent=Accent.WARNING))
        badge_layout.addWidget(StatusBadge("In Transit", accent=Accent.ENERGY))
        badge_layout.addWidget(StatusBadge("Locked", accent=Accent.LOCKED))
        badges.content_layout.addLayout(badge_layout)
        layout.addWidget(badges, 1, 1)

        expansion = LockedUpgradeWidget("Expansion Bay", "$1,250", "Unlock Production Line")
        expansion.setMinimumSize(230, 230)
        layout.addWidget(expansion, 1, 2)

        icons = GamePanel("Procedural Icons", "Geometry-only resource and system symbols", accent=Accent.STORAGE)
        icon_layout = QGridLayout()
        icon_layout.setContentsMargins(0, 8, 0, 0)
        icon_layout.setSpacing(10)
        for index, icon in enumerate((GameIcon.CASH, GameIcon.ENERGY, GameIcon.STORAGE, GameIcon.BUILD, GameIcon.LOCK, GameIcon.HALL, GameIcon.IRON_ORE, GameIcon.IRON, GameIcon.COPPER_ORE, GameIcon.COPPER, GameIcon.COAL, GameIcon.STEEL)):
            widget = GameIconWidget(icon)
            widget.setFixedSize(44, 44)
            icon_layout.addWidget(widget, index // 4, index % 4)
        icons.content_layout.addLayout(icon_layout)
        layout.addWidget(icons, 1, 3)

        cards = GamePanel("Game Cards", "Machine and energy card frame examples", accent=Accent.ENERGY)
        cards.setMinimumHeight(246)
        card_layout = QHBoxLayout()
        card_layout.setContentsMargins(0, 8, 0, 0)
        card_layout.setSpacing(14)
        extractor = GameCardFrame("Extractor", "Iron Ore", "Running", meta="Machine · MK I", detail="Power 12 MW", icon=GameIcon.IRON_ORE, accent=Accent.BUILD, status_accent=Accent.SUCCESS)
        wind = GameCardFrame("Wind Turbine", "+35 MW", "Online", meta="Energy · MK I", detail="No fuel", icon=GameIcon.ENERGY, accent=Accent.ENERGY, status_accent=Accent.SUCCESS)
        nuclear = GameCardFrame("Nuclear Plant", "+500 MW", "Fueled", meta="Energy · MK III", detail="Uranium fuel", icon=GameIcon.ENERGY, accent=Accent.LEGENDARY, status_accent=Accent.WARNING)
        for card in (extractor, wind, nuclear):
            card.setMinimumSize(210, 190)
            card_layout.addWidget(card)
        card_layout.addStretch(1)
        cards.content_layout.addLayout(card_layout)
        layout.addWidget(cards, 2, 0, 1, 4)

        track = ProductionTrack("Production Track · Aluminum Components", accent=Accent.ENERGY, slots=4)
        track.setMinimumHeight(250)
        track.add_track_widget(GameCardFrame("Extractor", "Bauxite", "Running", meta="MK I", detail="+120/min", icon=GameIcon.IRON_ORE, accent=Accent.BUILD, status_accent=Accent.SUCCESS))
        track.add_track_widget(GameCardFrame("Processor", "Aluminum", "Running", meta="MK I", detail="+60/min", icon=GameIcon.STEEL, accent=Accent.STORAGE, status_accent=Accent.SUCCESS))
        track.add_track_widget(BuildSlotWidget("Build Slot", "Add machine"))
        track.add_track_widget(LockedUpgradeWidget("Slot 04", "$350", "Upgrade Bay"))
        layout.addWidget(track, 3, 0, 1, 4)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height())
            painter.fillRect(rect, GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.background))
            painter.setPen(QPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.separator, 38), 1))
            step = 64
            x = 0
            while x < self.width():
                painter.drawLine(x, 0, x, self.height())
                x += step
            y = 0
            while y < self.height():
                painter.drawLine(0, y, self.width(), y)
                y += step
        finally:
            painter.end()
        super().paintEvent(event)

    def render_to_image(self, width: int = 900, height: int = 560, device_pixel_ratio: float = 1.0) -> QImage:
        self.resize(width, height)
        image = QImage(round(width * device_pixel_ratio), round(height * device_pixel_ratio), QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(device_pixel_ratio)
        image.fill(0)
        painter = QPainter(image)
        try:
            self.render(painter, QPoint(0, 0))
        finally:
            painter.end()
        return image
