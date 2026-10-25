from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QPushButton,
    QWidget,
)
from shiboken6 import isValid as is_qt_object_valid


class ZoomPanGraphicsView(QGraphicsView):
    """Small widget-scene viewport with bounded zoom, direct pan, and fit."""

    zoom_changed = Signal(float)
    background_clicked = Signal()

    def __init__(
        self,
        *,
        object_prefix: str,
        minimum_zoom: float = 0.35,
        maximum_zoom: float = 1.75,
        scene_padding: float = 24.0,
    ) -> None:
        super().__init__()
        self._prefix = object_prefix
        self._minimum_zoom = minimum_zoom
        self._maximum_zoom = maximum_zoom
        self._scene_padding = scene_padding
        self._zoom = 1.0
        self._fit_active = True
        self._fit_call_count = 0
        self._proxy: QGraphicsProxyWidget | None = None
        self._content: QWidget | None = None
        self._content_bounds: QRectF | None = None
        self._panning = False
        self._pan_moved = False
        self._pan_origin = QPoint()

        self.setObjectName(f"{object_prefix}Canvas")
        self.setScene(QGraphicsScene(self))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    @property
    def minimum_zoom(self) -> float:
        return self._minimum_zoom

    @property
    def maximum_zoom(self) -> float:
        return self._maximum_zoom

    @property
    def fit_call_count(self) -> int:
        return self._fit_call_count

    @property
    def content_widget(self) -> QWidget | None:
        return self._content

    def set_content_widget(self, content: QWidget) -> None:
        self.scene().clear()
        self._content_bounds = None
        self._content = content
        content.adjustSize()
        content.resize(content.sizeHint())
        self._proxy = self.scene().addWidget(content)
        self._proxy.setPos(0, 0)
        self._refresh_scene_rect()
        self._fit_active = True
        QTimer.singleShot(0, self.fit_to_view)

    def set_scene_content_rect(self, bounds: QRectF, *, auto_fit: bool = True) -> None:
        """Fit scene-native content while preserving the shared viewport behavior."""
        self._proxy = None
        self._content = None
        self._content_bounds = QRectF(bounds)
        padding = self._scene_padding
        self.setSceneRect(self._content_bounds.adjusted(-padding, -padding, padding, padding))
        self._fit_active = auto_fit
        if auto_fit:
            QTimer.singleShot(0, self.fit_to_view)

    def _refresh_scene_rect(self) -> None:
        if self._proxy is None:
            if self._content_bounds is not None:
                padding = self._scene_padding
                self.setSceneRect(self._content_bounds.adjusted(-padding, -padding, padding, padding))
            return
        if self._content is not None:
            self._content.layout().activate()
            self._content.adjustSize()
            self._proxy.resize(self._content.size())
        padding = self._scene_padding
        self.setSceneRect(self._proxy.sceneBoundingRect().adjusted(-padding, -padding, padding, padding))

    def fit_to_view(self) -> None:
        if not is_qt_object_valid(self):
            return
        if (self._proxy is None and self._content_bounds is None) or self.viewport().width() <= 1 or self.viewport().height() <= 1:
            return
        self._refresh_scene_rect()
        bounds = self.sceneRect()
        available_width = max(1.0, self.viewport().width() - 18.0)
        available_height = max(1.0, self.viewport().height() - 18.0)
        scale = min(1.0, available_width / bounds.width(), available_height / bounds.height())
        scale = max(self._minimum_zoom, min(self._maximum_zoom, scale))
        self.setTransform(QTransform().scale(scale, scale))
        self._zoom = scale
        self.centerOn(bounds.center())
        self._fit_active = True
        self._fit_call_count += 1
        self._update_zoom_display()

    def set_zoom(self, zoom: float, anchor: QPoint | None = None) -> None:
        target = max(self._minimum_zoom, min(self._maximum_zoom, zoom))
        if abs(target - self._zoom) < 0.0001:
            return
        anchor_point = anchor or self.viewport().rect().center()
        scene_before = self.mapToScene(anchor_point)
        center_before = self.mapToScene(self.viewport().rect().center())
        factor = target / self._zoom
        self.scale(factor, factor)
        scene_after = self.mapToScene(anchor_point)
        self.centerOn(center_before + (scene_before - scene_after))
        self._zoom = target
        self._fit_active = False
        self._update_zoom_display()

    def zoom_by_steps(self, steps: int, anchor: QPoint | None = None) -> None:
        self.set_zoom(self._zoom * (1.12 ** steps), anchor)

    def pan_by(self, delta: QPointF) -> None:
        center = self.mapToScene(self.viewport().rect().center())
        self.centerOn(center + delta)
        self._fit_active = False

    def _update_zoom_display(self) -> None:
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event) -> None:  # noqa: N802
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.set_zoom(self._zoom * (1.12 ** steps), event.position().toPoint())
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._interactive_content_widget_at(event.position().toPoint()) is not None:
                super().mousePressEvent(event)
                return
            scene_item = self.itemAt(event.position().toPoint())
            if self._proxy is None and scene_item is not None and scene_item.data(0):
                super().mousePressEvent(event)
                return
            self._panning = True
            self._pan_moved = False
            self._pan_origin = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def _interactive_content_widget_at(self, viewport_position: QPoint) -> QPushButton | None:
        if self._proxy is None or self._content is None:
            return None
        proxy_position = self._proxy.mapFromScene(self.mapToScene(viewport_position)).toPoint()
        child = self._content.childAt(proxy_position)
        while child is not None and child is not self._content:
            if isinstance(child, QPushButton):
                return child
            child = child.parentWidget()
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            current = event.position().toPoint()
            pixel_delta = current - self._pan_origin
            if pixel_delta.manhattanLength() > 2:
                self._pan_moved = True
            self._pan_origin = current
            self.pan_by(QPointF(-pixel_delta.x() / self._zoom, -pixel_delta.y() / self._zoom))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if not self._pan_moved:
                self.background_clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fit_active:
            QTimer.singleShot(0, self.fit_to_view)
