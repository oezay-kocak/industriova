"""Shared compact product object for personal and Consortium contracts."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from production_zero.ui.game_ui import Accent, InteractionState, draw_inset_surface
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_tiles import ElidedResourceLabel
from production_zero.ui.theme import Theme


def contract_quantity_text(amount):
    if amount >= 1e6:
        from production_zero.ui.freight_statistics import compact_rate
        return compact_rate(amount).removesuffix("/min")
    return f"{amount:,.0f}"


class ContractProductButton(QPushButton):
    def __init__(self, placeholder="SELECT PRODUCT", *, compact=True, expanded=False):
        super().__init__()
        self.setObjectName("contractProductSlot")
        self.setProperty("contractProductModule", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.expanded = expanded
        self.setMinimumHeight(126) if expanded else self.setFixedHeight(62 if compact else 78)
        if expanded:self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: transparent; border: 0; padding: 0; } QLabel { background: transparent; border: 0; }")
        self.placeholder = placeholder
        self.compact = compact
        self.icon = None
        self.body = QVBoxLayout(self) if compact else QHBoxLayout(self)
        self.body.setContentsMargins(7, 5, 7, 5)
        self.body.setSpacing(2 if compact else 10)
        if expanded:self.body.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.name = ElidedResourceLabel(placeholder)
        self.name.setObjectName("contractProductName")
        self.name.setMinimumWidth(0)
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.name.setStyleSheet(f"color: {Theme.TEXT}; font-size: {13 if expanded else (10 if compact else 14)}px; font-weight: 900;")
        self.amount = QLabel("SELECT PRODUCT")
        self.amount.setObjectName("contractRequirementAmount")
        self.amount.setStyleSheet(f"color: {Theme.SAFETY_YELLOW}; font-size: {22 if expanded else (11 if compact else 15)}px; font-weight: 900;")
        if expanded:
            self.amount.setWordWrap(True)
            self.amount.setMinimumWidth(0)
            self.amount.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.amount.setAlignment(Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignLeft)
        self.details = QVBoxLayout()
        self.details.setSpacing(1)
        self.details.setContentsMargins(0, 0, 0, 0)
        self.details.addWidget(self.name)
        self.details.addWidget(self.amount)
        self.body.addLayout(self.details, 0 if expanded else 1)
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignLeft)
        self.set_product(None, placeholder, 0)
        for label in (self.name, self.amount):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def minimumSizeHint(self):
        return QSize(60 if self.compact else 120, 126 if self.expanded else self.height())

    def sizeHint(self):
        return QSize(100 if self.compact else 240, 126 if self.expanded else self.height())

    def set_product(self, resource_id, name, required, *, delivered=None):
        if self.icon is not None:
            self.body.removeWidget(self.icon)
            self.icon.hide()
            self.icon.deleteLater()
            self.icon = None
        self.setProperty("resourceId", resource_id)
        self.setProperty("selected", resource_id is not None)
        self.setText(name.upper() if resource_id else self.placeholder)
        self.name.setText(self.text())
        self.name.set_tooltip_text(self.text())
        self.amount.setText((contract_quantity_text(required) if delivered is None else f"{contract_quantity_text(delivered)} / {contract_quantity_text(required)}") if resource_id else "SELECT PRODUCT")
        if self.expanded:
            self.amount.setMinimumHeight(self.amount.fontMetrics().height()*(2 if delivered is not None else 1)+2)
        self.amount.setProperty("requiredAmount", required)
        self.amount.setProperty("fulfilled", delivered is not None and delivered >= required)
        if delivered is not None:
            self.amount.setProperty("deliveredAmount", delivered)
            self.amount.setProperty("progressPermille", round(1000 * delivered / required) if required else 0)
        if resource_id:
            self.icon = ResourceIconWidget(resource_id, size=40 if self.expanded else (24 if self.compact else 42))
            self.icon.setObjectName("resourceIcon")
            self.icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.body.insertWidget(0, self.icon, 0, Qt.AlignmentFlag.AlignCenter)
        exact = f"{required:,.2f}" if delivered is None else f"{delivered:,.2f} / {required:,.2f}"
        self.setAccessibleName(f"{self.text()} · {exact}")
        self.setToolTip(self.accessibleName())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Theme.SURFACE_1 if self.isEnabled() else Theme.SURFACE_2))
        painter.drawRoundedRect(rect, 5, 5)
        state = InteractionState.PRESSED if self.isDown() else InteractionState.HOVER if self.underMouse() else InteractionState.NORMAL
        draw_inset_surface(painter, rect, accent=Accent.NEUTRAL, state=state, radius=5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(Theme.SAFETY_YELLOW if self.isEnabled() and (self.underMouse() or self.hasFocus()) else Theme.BORDER_STRONG), 1))
        painter.drawRoundedRect(rect, 5, 5)
        painter.end()
