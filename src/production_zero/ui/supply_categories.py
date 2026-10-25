"""Direct industrial category buttons over the canonical Supply taxonomy."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QGridLayout
from production_zero.ui.game_ui import GameButton, Accent


class SupplyCategoryButtons(QWidget):
    currentTextChanged = Signal(str)
    categories = ('All', 'Resources', 'Energy', 'Factory', 'Freight')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 'All'
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        self.buttons = {}
        self._columns = 0
        for category in self.categories:
            button = GameButton(category.upper(), variant='primary', accent=Accent.NEUTRAL)
            button.setObjectName('supplyCategory' + category)
            button.setMinimumSize(105, 38)
            button.clicked.connect(lambda checked=False, category=category: self.setCurrentText(category))
            self.buttons[category] = button
        self._layout_buttons()
        self._sync()

    def _layout_buttons(self):
        columns = max(1, min(len(self.categories), (self.width() + 6) // 111))
        if columns == self._columns:
            return
        self._columns = columns
        for index, button in enumerate(self.buttons.values()):
            self._grid.addWidget(button, index // columns, index % columns)

    def resizeEvent(self, event):
        self._layout_buttons()
        super().resizeEvent(event)

    def _sync(self):
        for category, button in self.buttons.items():
            selected = category == self._current
            button.setSelected(selected)
            button._accent = Accent.BUILD if selected else Accent.NEUTRAL
            button.update()

    def currentText(self):
        return self._current

    def setCurrentText(self, category):
        # Retained callers can still use the former family names; the visible
        # selector and its results always use the shared Factory category.
        if category in {'Processing', 'Fabrication', 'Assembly'}:
            category = 'Factory'
        if category not in self.categories or category == self._current:
            return
        self._current = category
        self._sync()
        self.currentTextChanged.emit(category)

    def setCurrentIndex(self, index):
        self.setCurrentText(self.categories[index])

    def count(self):
        return len(self.categories)

    def itemText(self, index):
        return self.categories[index]
