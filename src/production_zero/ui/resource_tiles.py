from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.theme import Theme


RESOURCE_TILE_WIDTH = 174
RESOURCE_TILE_HEIGHT = 188
RESOURCE_TILE_ICON_HOST_SIZE = 58
RESOURCE_TILE_ICON_SIZE = 48
RESOURCE_SELECTION_SURFACE_COLOR = QColor(Theme.SURFACE_1)


class ElidedResourceLabel(QLabel):
    def __init__(
        self,
        text: str = "",
        *,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
        tooltip_text: str | None = None,
        forward_tooltip_to_parent: bool = False,
    ) -> None:
        super().__init__(text)
        self._tooltip_text = tooltip_text if tooltip_text is not None else text
        self._forward_tooltip_to_parent = forward_tooltip_to_parent
        self.setWordWrap(False)
        self.setAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)

    def set_tooltip_text(self, text: str) -> None:
        self._tooltip_text = text
        self.refresh_elision_tooltip()

    def refresh_elision_tooltip(self) -> None:
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, max(0, self.width() - 2))
        self._set_elision_tooltip(self._tooltip_text if self._tooltip_text and elided != self.text() else "")

    def _set_elision_tooltip(self, tooltip: str) -> None:
        if self.toolTip() != tooltip:
            self.setToolTip(tooltip)
        if self._forward_tooltip_to_parent and self.parentWidget() is not None:
            parent = self.parentWidget()
            if parent.toolTip() != tooltip:
                parent.setToolTip(tooltip)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.refresh_elision_tooltip()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            self.refresh_elision_tooltip()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setFont(self.font())
            painter.setPen(self.palette().color(self.foregroundRole()))
            metrics = QFontMetrics(self.font())
            text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, max(0, self.width() - 2))
            self._set_elision_tooltip(self._tooltip_text if self._tooltip_text and text != self.text() else "")
            painter.drawText(self.rect(), self.alignment(), text)
        finally:
            painter.end()


class ResourceSelectionTile(QFrame):
    def __init__(
        self,
        *,
        resource_id: str,
        title: str,
        subtitle: str,
        icon_key: str,
        accent_key: str,
        detail: str = "",
        status: str = "",
        object_name: str = "resourceSelectionTile",
        title_object_name: str = "resourceSelectionTileName",
        subtitle_object_name: str = "resourceSelectionTileSubtitle",
        detail_object_name: str = "resourceSelectionTileDetail",
        status_object_name: str = "resourceSelectionTileStatus",
        icon_object_name: str = "resourceIcon",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("resourceId", resource_id)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(RESOURCE_TILE_WIDTH, RESOURCE_TILE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(10)
        icon_host = QFrame()
        icon_host.setObjectName("resourceSelectionIconHost")
        icon_host.setFixedSize(RESOURCE_TILE_ICON_HOST_SIZE, RESOURCE_TILE_ICON_HOST_SIZE)
        icon_layout = QHBoxLayout(icon_host)
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=RESOURCE_TILE_ICON_SIZE)
        icon.setObjectName(icon_object_name)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_layout.addWidget(icon)
        top.addWidget(icon_host)

        text = QVBoxLayout()
        text.setContentsMargins(0, 1, 0, 0)
        text.setSpacing(3)
        name = ElidedResourceLabel(title.upper(), tooltip_text=title, forward_tooltip_to_parent=True)
        name.setObjectName(title_object_name)
        name.setFixedHeight(26)
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(name)
        from production_zero.ui.resource_categories import research_category
        domain = research_category(resource_id)
        self.setProperty('researchCategory', domain)
        category = ElidedResourceLabel((domain or subtitle).upper(), tooltip_text=f'Research: {domain}' if domain else subtitle)
        category.setObjectName(subtitle_object_name)
        category.setProperty("secondaryTextRole", "metadata")
        category.setFixedHeight(19)
        category.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(category)
        layout.addLayout(top)
        layout.addLayout(text)

        detail_label = ElidedResourceLabel(detail.upper() if detail else "")
        detail_label.setObjectName(detail_object_name)
        detail_label.setProperty("secondaryTextRole", "metadata")
        detail_label.setFixedHeight(20)
        detail_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(detail_label)

        status_label = ElidedResourceLabel(status, alignment=Qt.AlignmentFlag.AlignCenter)
        status_label.setObjectName(status_object_name)
        status_label.setProperty("secondaryTextRole", "status")
        status_label.setFixedHeight(28)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(status_label)
        status_label.setVisible(bool(status))

    def update_text(self, object_name: str, text: str) -> None:
        label = self.findChild(ElidedResourceLabel, object_name)
        if label is not None and label.text() != text:
            label.setText(text)
            label.set_tooltip_text(text)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(RESOURCE_TILE_WIDTH, RESOURCE_TILE_HEIGHT)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(RESOURCE_TILE_WIDTH, RESOURCE_TILE_HEIGHT)


class ResourceSelectionGridHost(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), RESOURCE_SELECTION_SURFACE_COLOR)
        finally:
            painter.end()
        super().paintEvent(event)


def add_hidden_label(parent: QWidget, object_name: str, text: str) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    label.hide()
    return label


def configure_resource_selection_scroll(scroll: QScrollArea) -> None:
    viewport = scroll.viewport()
    viewport.setObjectName("resourceSelectionViewport")
    viewport.setAutoFillBackground(False)
    viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


def configure_resource_selection_grid_host(host: QWidget) -> None:
    host.setAutoFillBackground(False)
    host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)


def build_resource_selector_filter_row(search: QLineEdit, category_filter: QComboBox) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(search, 2)
    row.addWidget(category_filter)
    return row


def build_resource_selector_filter_panel(search: QLineEdit, category_filter: QComboBox) -> QFrame:
    panel = QFrame()
    panel.setObjectName("resourceSelectorFilterPanel")
    layout = QHBoxLayout(panel)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(8)
    layout.addWidget(search, 2)
    layout.addWidget(category_filter)
    return panel
