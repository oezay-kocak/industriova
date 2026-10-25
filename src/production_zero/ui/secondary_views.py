"""Presentation shared only by Factory and Freight secondary workspaces."""
from functools import lru_cache
from importlib.resources import files
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from production_zero.ui.resource_icons import ResourceIconWidget, resource_icon_key, resource_accent_key
from production_zero.data.definitions import load_resource_definitions
from production_zero.ui.theme import Theme


@lru_cache(maxsize=1)
def browser_resource_metadata():
    return load_resource_definitions(files('production_zero.data').joinpath('resource_definitions.json'))


def browser_category(resource_id, stage=None):
    resource = browser_resource_metadata().get(resource_id)
    return (resource.category or 'General') if resource else 'General'


class RecipeInputButton(QPushButton):
    """Input links may contract without forcing the native window wider."""
    def __init__(self, text):
        super().__init__(text)
        self._full_text = text

    def minimumSizeHint(self):  # noqa: N802
        return QSize(50, 34)

    def sizeHint(self):  # noqa: N802
        return QSize(min(180, self.fontMetrics().horizontalAdvance(self._full_text) + 28), 34)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        text = self.fontMetrics().elidedText(self._full_text, Qt.TextElideMode.ElideRight, max(0, self.width() - 28))
        self.setText(text)
        self.setToolTip(self._full_text if text != self._full_text else '')


def retain_grid_tiles(grid, resource_ids):
    """Reuse still-visible tiles during filtering and reflow; dispose only removed rows."""
    retained = {}
    while grid.count():
        widget = grid.takeAt(0).widget()
        if widget is None:
            continue
        key = widget.property('resourceId')
        if key in resource_ids:
            retained[key] = widget
        else:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
    for row in range(grid.rowCount()):
        grid.setRowStretch(row, 0)
    for column in range(grid.columnCount()):
        grid.setColumnStretch(column, 0)
    return retained


def style_secondary(panel):
    # Scoped V2 workstation language shared by Factory/Freight secondary views.
    panel.setProperty("secondaryShell", True)
    panel.setStyleSheet(f"""
        QWidget {{ background: transparent; color: {Theme.TEXT}; }}
        QFrame {{ border: none; }}
        QFrame[secondaryShell="true"] {{ background: {Theme.PRODUCTION_GUIDE_CANVAS}; border: 2px solid {Theme.GUIDE_CHASSIS_DARK}; border-radius: 12px; }}
        QFrame#secondaryViewHeader {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.GUIDE_HEADER_START}, stop:0.58 {Theme.GUIDE_HEADER_MID}, stop:1 {Theme.GUIDE_HEADER_END}); border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 7px; }}
        QFrame#secondaryControlDeck, QFrame#freightSelectionFilters {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 6px; }}
        QFrame#secondaryContentChassis, QFrame#secondaryTechnicalChassis {{ background: {Theme.SURFACE_2}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 8px; }}
        QLabel {{ background: transparent; color: {Theme.MUTED}; border: none; font-size: 13px; }}
        QLabel#emptyStateTitle {{ font-family: {Theme.INDUSTRIAL_FONT}; font-size: 20px; font-weight: 900; color: {Theme.TEXT}; }}
        QLabel#emptyStateMessage {{ font-family: "Segoe UI"; font-size: 14px; color: {Theme.MUTED}; }}
        QLabel#sectionLabel, QLabel#secondaryTitle, QLabel#productionGuideTitle {{ color: {Theme.TEXT}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 22px; font-weight: 900; }}
        QLabel#productionGuideSubtitle {{ color: {Theme.MUTED}; font-family: "Segoe UI"; font-size: 13px; font-weight: 600; }}
        QLineEdit {{ background: {Theme.SURFACE_0}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 2px solid {Theme.SURFACE_0}; border-radius: 4px; color: {Theme.TEXT}; padding: 8px 11px; font-size: 13px; min-height: 20px; selection-background-color: rgba(255, 210, 31, 70); }}
        QLineEdit:hover {{ border-color: {Theme.SURFACE_HOVER}; }}
        QLineEdit:focus {{ background: {Theme.SURFACE_1}; border-color: {Theme.SAFETY_YELLOW}; }}
        QComboBox {{ background: {Theme.SURFACE_1}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER_STRONG}; padding: 7px; }}
        QPushButton[secondaryAction="true"] {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Theme.SURFACE_INTERACTIVE}, stop:1 {Theme.SURFACE_1}); color: {Theme.TEXT}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 5px; padding: 8px 14px; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 13px; font-weight: 900; }}
        QPushButton[secondaryAction="true"]:hover {{ background: {Theme.SURFACE_HOVER}; border-color: {Theme.SAFETY_YELLOW}; color: {Theme.SAFETY_YELLOW}; }}
        QPushButton[secondaryAction="true"]:pressed {{ background: {Theme.SURFACE_0}; border-bottom-width: 1px; padding-top: 10px; }}
        QPushButton[secondaryAction="true"]:disabled {{ background: {Theme.SURFACE_1}; color: {Theme.DIM}; border-color: {Theme.BORDER}; }}
        QPushButton#chainInspectorBackButton, QPushButton#productionGuideUnlockTreeButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:1 #d39b00); color: {Theme.SURFACE_0}; border: 1px solid #fff2a3; border-bottom: 3px solid #8c6500; }}
        QPushButton#chainInspectorBackButton:hover, QPushButton#productionGuideUnlockTreeButton:hover {{ background: #ffe76a; color: {Theme.SURFACE_0}; border-color: #fff7c7; }}
        QPushButton#chainInspectorBackButton:pressed, QPushButton#productionGuideUnlockTreeButton:pressed {{ background: #c7960d; color: {Theme.SURFACE_0}; border-bottom-width: 1px; padding-top: 10px; }}
        QPushButton#productionGuideStageButton {{ background: {Theme.SURFACE_3}; color: {Theme.MUTED}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 2px solid {Theme.SURFACE_0}; border-radius: 3px; padding: 7px 10px; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 900; }}
        QPushButton#productionGuideStageButton:hover {{ background: {Theme.SURFACE_HOVER}; color: {Theme.TEXT}; }}
        QPushButton#productionGuideStageButton:checked {{ background: {Theme.SAFETY_YELLOW}; color: {Theme.SURFACE_0}; border-color: {Theme.SURFACE_0}; }}
        QPushButton[utilityAction="true"] {{ background: {Theme.SURFACE_3}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 2px solid {Theme.SURFACE_0}; border-radius: 4px; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 16px; font-weight: 900; min-width: 34px; min-height: 26px; }}
        QPushButton[utilityAction="true"]:hover {{ background: {Theme.SURFACE_HOVER}; color: {Theme.SAFETY_YELLOW}; border-color: {Theme.SAFETY_YELLOW}; }}
        QPushButton[utilityAction="true"]:pressed {{ background: {Theme.SURFACE_0}; border-bottom-width: 1px; }}
        QPushButton[utilityAction="true"]:disabled {{ background: {Theme.SURFACE_1}; color: {Theme.DIM}; border-color: {Theme.BORDER}; }}
        QPushButton#resourceCategoryButton {{ padding: 0; background: {Theme.SURFACE_3}; border: 1px solid {Theme.BORDER_STRONG}; }}
        QPushButton#resourceCategoryButton:checked {{ border: 2px solid {Theme.SAFETY_YELLOW}; color: {Theme.SAFETY_YELLOW}; }}
        QScrollArea, QWidget#resourceSelectionViewport, QWidget#productionGuideGridHost, QWidget#usedInDetailGridHost {{ background: {Theme.SURFACE_1}; border: none; }}
        QFrame#productionGuideView QScrollArea#productionGuideScroll, QFrame#productionGuideView QWidget#productionGuideGridHost {{ background: {Theme.SURFACE_1}; }}
        QScrollArea#resourceCategoryRail {{ background: transparent; }}
        QFrame#productionSelectionTile, QFrame#resourceSelectionTile, QFrame#productionGuideTile, QFrame#freightAssignmentResourceTile,
        QFrame#chainResourceBox, QFrame#guideRecipeRow {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Theme.SURFACE_INTERACTIVE}, stop:0.5 {Theme.SURFACE_3}, stop:1 {Theme.SURFACE_1}); border: 1px solid {Theme.BORDER_STRONG}; border-top: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 4px; }}
        QFrame#productionSelectionTile:hover, QFrame#resourceSelectionTile:hover, QFrame#productionGuideTile:hover, QFrame#freightAssignmentResourceTile:hover, QFrame#guideRecipeRow:hover {{ background: {Theme.SURFACE_HOVER}; border-color: {Theme.SAFETY_YELLOW}; }}
        QFrame#productionSelectionTile[current="true"], QFrame#resourceSelectionTile[selected="true"], QFrame#freightAssignmentResourceTile[selected="true"] {{ border: 2px solid {Theme.SAFETY_YELLOW}; }}
        QFrame#resourceSelectionIconHost {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER}; border-radius: 4px; }}
        QFrame#productionSelectionTile QLabel, QFrame#resourceSelectionTile QLabel, QFrame#productionGuideTile QLabel, QFrame#freightAssignmentResourceTile QLabel,
        QFrame#chainInspectorFlowShell QLabel, QFrame#guideRecipeRow QLabel {{ color: {Theme.TEXT}; }}
        QLabel#productionTileName, QLabel#resourceSelectionTileName, QLabel#productionGuideTileName, QLabel#freightAssignmentTileName {{ font-size: 14px; font-weight: bold; }}
        QFrame#productionSelectionTile QLabel#productionTileCurrent, QFrame#productionGuideTile QLabel#productionGuideUnlock {{ font-family: "Bahnschrift"; font-size: 11px; color: {Theme.SAFETY_YELLOW}; }}
        QFrame#chainInspectorFlowShell, QWidget#chainInspectorStageHost, QWidget#chainStageNodeHost {{ background: {Theme.SURFACE_1}; border: none; }}
        QGraphicsView#chainInspectorCanvas {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER_STRONG}; border-radius: 6px; }}
        QFrame#guideRecipeDetails {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.SURFACE_3}, stop:1 {Theme.SURFACE_1}); border: 1px solid {Theme.BORDER_STRONG}; border-left: 3px solid {Theme.SAFETY_YELLOW}; border-radius: 6px; }}
        QFrame#chainSummaryProduct {{ background: transparent; border: none; }}
        QLabel#chainSummaryProductName {{ color: {Theme.TEXT}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 18px; font-weight: 900; }}
        QLabel#chainSummaryMachineFamily {{ color: {Theme.MUTED}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 800; }}
        QFrame#chainSummaryRateBlock {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER}; border-radius: 4px; }}
        QLabel#chainSummaryRateLabel {{ background: transparent; color: {Theme.TEXT}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 11px; font-weight: 900; }}
        QLabel#chainSummaryRateValue {{ background: transparent; color: {Theme.SAFETY_YELLOW}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 16px; font-weight: 900; }}
        QLabel#chainStageTitle {{ font-size: 16px; font-weight: 900; }}
        QLabel#chainResourceName {{ color: #f5f7f2; font-size: 16px; font-weight: 900; }}
        QFrame#chainInspectorFlowShell QLabel#chainMachineFamily {{ color: #b9c5c1; font-size: 12px; font-weight: 800; }}
        QFrame#chainInspectorFlowShell QFrame#chainResourceInputs {{ background: transparent; border: none; }}
        QFrame#chainInspectorFlowShell QPushButton#guideRecipeInputLink {{ background: transparent; color: #c7d0cd; border: none; padding: 0; text-align: left; font-family: "Segoe UI"; font-size: 12px; font-weight: 700; }}
        QFrame#chainInspectorFlowShell QPushButton#guideRecipeInputLink:hover {{ color: {Theme.SAFETY_YELLOW}; }}
        QFrame#chainResourceDivider {{ background: {Theme.BORDER}; border: none; }}
        QFrame#chainInspectorFlowShell QLabel#chainResourceAmount {{ font-family: {Theme.INDUSTRIAL_FONT}; font-size: 15px; color: {Theme.SAFETY_YELLOW}; font-weight: 900; }}
        QFrame#guideRecipeRow QLabel#guideRecipeDetail, QFrame#guideRecipeRow QLabel#guideRecipeRate {{ font-size: 15px; color: {Theme.SAFETY_YELLOW}; font-weight: 900; }}
        QPushButton#guideRecipeLink {{ text-align: left; padding: 0; background: transparent; border: none; color: {Theme.TEXT}; font-size: 16px; font-weight: bold; }}
        QLabel[secondaryTextRole="metadata"] {{ font-size: 13px; font-weight: 800; }}
        QLabel[secondaryTextRole="status"] {{ font-family: "Bahnschrift"; font-size: 11px; font-weight: 800; }}
        QPushButton#guideUsedInOpenButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Theme.SURFACE_INTERACTIVE}, stop:1 {Theme.SURFACE_1}); border: 1px solid {Theme.BORDER_STRONG}; border-left: 3px solid {Theme.SAFETY_YELLOW}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 5px; }}
        QPushButton#guideUsedInOpenButton:hover {{ background: {Theme.SURFACE_HOVER}; border-color: {Theme.SAFETY_YELLOW}; }}
        QPushButton#guideUsedInOpenButton:pressed {{ background: {Theme.SURFACE_0}; border-bottom-width: 1px; }}
        QLabel#usedInActionEyebrow {{ color: {Theme.MUTED}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 10px; font-weight: 900; }}
        QLabel#usedInActionCount {{ color: {Theme.TEXT}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 15px; font-weight: 900; }}
        QLabel#usedInActionChevron {{ color: {Theme.SAFETY_YELLOW}; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 18px; font-weight: 900; }}
    """)


def secondary_action_button(text, object_name):
    button = QPushButton(text)
    button.setObjectName(object_name)
    button.setProperty("secondaryAction", True)
    return button


def secondary_utility_button(text, object_name):
    button = QPushButton(text)
    button.setObjectName(object_name)
    button.setProperty("utilityAction", True)
    return button


class StageFilterBar(QFrame):
    """Direct V2 tabs backed by the guide's existing stage-filter values."""
    def __init__(self, options, current_value, changed):
        super().__init__()
        self.setObjectName("productionGuideStageFilter")
        self._current_value = current_value
        self._changed = changed
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for label, value in options:
            button = QPushButton(label)
            button.setObjectName("productionGuideStageButton")
            button.setProperty("filterValue", value)
            button.setCheckable(True)
            button.setChecked(value == current_value)
            button.clicked.connect(lambda checked=False, value=value: self._select(value) if checked else None)
            self.group.addButton(button)
            self.buttons.append(button)
            row.addWidget(button)

    def select_value(self, value):
        for button in self.buttons:
            if button.property("filterValue") == value:
                button.click()
                return

    def _select(self, value):
        self._current_value = value
        self._changed(value)

    def setCurrentText(self, value):  # noqa: N802 - compatibility with the former model control
        self.select_value(value)

    def currentText(self):  # noqa: N802 - compatibility with the former model control
        return self._current_value


class UsedInNavigationButton(QPushButton):
    def __init__(self, count):
        super().__init__()
        self._logical_text = f"USED IN\n{count} {'PRODUCT' if count == 1 else 'PRODUCTS'}  >"
        self.setObjectName("guideUsedInOpenButton")
        self.setAccessibleName(f"Used in {count} {'product' if count == 1 else 'products'}")
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 7, 10, 7)
        row.setSpacing(8)
        text = QVBoxLayout()
        text.setSpacing(0)
        eyebrow = QLabel("USED IN")
        eyebrow.setObjectName("usedInActionEyebrow")
        amount = QLabel(f"{count} {'PRODUCT' if count == 1 else 'PRODUCTS'}")
        amount.setObjectName("usedInActionCount")
        chevron = QLabel("›")
        chevron.setObjectName("usedInActionChevron")
        for label in (eyebrow, amount, chevron):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(eyebrow)
        text.addWidget(amount)
        row.addLayout(text, 1)
        row.addWidget(chevron)

    def text(self):
        return self._logical_text


class SecondaryViewHeader(QFrame):
    def __init__(self, title, subtitle, back):
        super().__init__()
        self.setObjectName('secondaryViewHeader')
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 12, 10)
        text = QVBoxLayout()
        title = QLabel(title) if isinstance(title, str) else title
        if not title.objectName():
            title.setObjectName('secondaryTitle')
        title.setWordWrap(True)
        text.addWidget(title)
        subtitle = QLabel(subtitle) if isinstance(subtitle, str) else subtitle
        subtitle.setWordWrap(True)
        text.addWidget(subtitle)
        row.addLayout(text, 1)
        row.addWidget(back, 0, Qt.AlignmentFlag.AlignTop)


class ResourceCategoryRail(QScrollArea):
    """The hidden combo remains the filter model; only the icon rail is shown."""
    def __init__(self, model, resources):
        super().__init__()
        self.setObjectName('resourceCategoryRail')
        self.setFixedWidth(76)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        column = QVBoxLayout(host)
        column.setContentsMargins(4, 0, 4, 0)
        column.setSpacing(8)
        self.buttons = []
        model.setParent(host)
        model.hide()
        for index in range(model.count()):
            category = model.itemText(index)
            button = QPushButton('ALL' if category == 'All' else '')
            button.setObjectName('resourceCategoryButton')
            button.setProperty('category', category)
            button.setToolTip('All resources' if category == 'All' else category)
            button.setAccessibleName(button.toolTip())
            button.setFixedSize(52, 52)
            button.setCheckable(True)
            button.setChecked(index == model.currentIndex())
            if category != 'All':
                rid = resources.get(category)
                if rid:
                    icon = ResourceIconWidget(rid, resource_icon_key(rid), resource_accent_key(rid), size=32)
                    icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    icon_row = QHBoxLayout(button)
                    icon_row.setContentsMargins(9, 9, 9, 9)
                    icon_row.addWidget(icon)
                else:
                    button.setText(category[:3].upper())
            button.clicked.connect(lambda checked=False, i=index: model.setCurrentIndex(i))
            self.buttons.append(button)
            column.addWidget(button)
        column.addStretch(1)
        model.currentIndexChanged.connect(self._select)
        self.setWidget(host)

    def _select(self, index):
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)


class ResourceBrowser(QWidget):
    def __init__(self, search, category, scroll, representatives, extra_filter=None):
        super().__init__()
        self.setObjectName('resourceBrowser')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QFrame()
        controls.setObjectName("secondaryControlDeck")
        toolbar = QHBoxLayout(controls)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(8)
        search.setPlaceholderText('SEARCH RESOURCES')
        search.setMaximumWidth(540)
        toolbar.addWidget(search, 1)
        if extra_filter is not None:
            toolbar.addWidget(extra_filter)
        toolbar.addStretch(1)
        layout.addWidget(controls)
        chassis = QFrame()
        chassis.setObjectName("secondaryContentChassis")
        body = QHBoxLayout(chassis)
        body.setContentsMargins(9, 9, 9, 9)
        body.setSpacing(9)
        body.addWidget(scroll, 1)
        body.addWidget(ResourceCategoryRail(category, representatives))
        layout.addWidget(chassis, 1)
