"""Session-persistent movable resource drawer using the existing resource list."""
from PySide6.QtCore import Qt, QEvent, QPoint, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSizeGrip
from production_zero.ui.material_frame import MaterialFrame
from production_zero.core.state import FactoryHall
from production_zero.ui.resource_categories import research_category
from production_zero.ui.resource_overview import ResourceOverviewGrid


class OverlayResizeGrip(QSizeGrip):
    """Resize this drawer, never the containing main window."""
    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setPen(QPen(QColor('#ffd21f'), 2))
        for offset in (4, 9, 14):
            painter.drawLine(self.width() - offset, self.height() - 3, self.width() - 3, self.height() - offset)
        painter.end()
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._initial_size = self.parentWidget().size()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_origin'):
            delta = event.globalPosition().toPoint() - self._origin
            parent = self.parentWidget()
            parent.resize(self._initial_size.width() + delta.x(), self._initial_size.height() + delta.y())
            parent._fit_parent()
            event.accept()


class GlobalResourcesOverlay(MaterialFrame):
    def __init__(self, state, definitions, resources, parent):
        super().__init__(parent=parent)
        from production_zero.ui.factory_view_v2 import FactoryV2ResourceDrawer
        self.setObjectName("globalResourcesOverlay")
        self.setMinimumSize(400, 380)
        self.resize(1080, 620)
        self._drag_offset = None
        self._state = state
        self._resources = resources
        layout = QVBoxLayout(self)
        self.drawer = FactoryV2ResourceDrawer(
            state, definitions, FactoryHall("global", "Global Resources", 0),
            summary_factory=lambda scroll: ResourceOverviewGrid(state, definitions, resources, scroll_area=scroll),
        )
        parent.installEventFilter(self)
        self.drawer.close_button.clicked.connect(self.hide)
        self.drawer.installEventFilter(self)
        self.drawer.setMouseTracking(True)
        self.drawer.findChild(QLabel, 'factoryV2DrawerTitle').setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.search = QLineEdit()
        self.search.setPlaceholderText("SEARCH RESOURCES / RESEARCH CATEGORY")
        self.category = QComboBox()
        self.category.addItem("All Research categories", "")
        for category in sorted({research_category(rid) for rid in resources} - {''}):
            self.category.addItem(category, category)
        self.drawer.layout().insertWidget(1, self.search)
        self.drawer.layout().insertWidget(2, self.category)
        self.search.textChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.drawer)
        bottom = QHBoxLayout()
        caption = QLabel('PLAN: configured flow · DELIVERED: actual Freight, last 60s')
        caption.setWordWrap(True)
        caption.setStyleSheet('color: #14242a; font-size: 10px;')
        bottom.addWidget(caption, 1)
        self.grip = OverlayResizeGrip(self)
        self.grip.setObjectName('globalResourcesResizeGrip')
        self.grip.setToolTip('Drag to resize the resource overview')
        self.grip.setFixedSize(22, 22)
        bottom.addWidget(self.grip)
        layout.addLayout(bottom)
        self.drawer._set_inventory_mode(True)
        self.move(130, 130)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setObjectName('globalResourcesRefreshTimer')
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self.refresh)
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self._fit_parent()
            self.show()
            self.raise_()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh()
        self._refresh_timer.start()

    def hideEvent(self, event):  # noqa: N802
        self._refresh_timer.stop()
        super().hideEvent(event)

    def refresh(self, *args):
        self.drawer.summary.search_text = self.search.text().strip().casefold()
        self.drawer.summary.category_id = self.category.currentData()
        if self.isVisible():
            self.drawer.refresh()

    def _fit_parent(self):
        bounds = self.parentWidget().size()
        self.setMaximumSize(max(self.minimumWidth(), bounds.width() - 16), max(self.minimumHeight(), bounds.height() - 16))
        self.move(max(0, min(self.x(), bounds.width() - self.width())), max(0, min(self.y(), bounds.height() - self.height())))

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._fit_parent()
        if watched is self.drawer:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton and event.position().y() < 55:
                self._drag_offset = event.globalPosition().toPoint() - self.mapToGlobal(QPoint(0, 0))
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_offset is not None:
                point = self.parentWidget().mapFromGlobal(event.globalPosition().toPoint() - self._drag_offset)
                self.move(max(0, min(point.x(), self.parentWidget().width() - self.width())), max(0, min(point.y(), self.parentWidget().height() - 45)))
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
        return super().eventFilter(watched, event)
