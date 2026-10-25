"""Small interactions composed from the existing industrial materials and buttons."""
from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QFontMetricsF
from PySide6.QtWidgets import QDialog, QLineEdit, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QToolButton
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
from production_zero.ui.card_hover import card_hover_icon


def rename_building(parent, current, apply):
    dialog = IndustrialDialog("Rename building", "Enter the new building name.", parent, accept_text="YES – SAVE")
    field = QLineEdit(current)
    field.setObjectName("buildingNameInput")
    field.setMaxLength(80)
    field.setMinimumHeight(38)
    dialog.layout().itemAt(0).widget().layout().insertWidget(2, field)
    field.selectAll()
    QTimer.singleShot(0, field.setFocus)
    try:
        if dialog.exec() == QDialog.DialogCode.Accepted and field.text().strip():
            apply(field.text().strip())
    finally:
        dialog.deleteLater()


def building_title_layout(name, font, rect):
    """One font/rectangle for both the painted title and its adjacent pencil."""
    metrics = QFontMetricsF(font)
    visible = metrics.elidedText(name.upper(), Qt.TextElideMode.ElideRight, max(0, rect.width() - 40))
    pencil = QRectF(rect.left() + metrics.horizontalAdvance(visible) + 8,
                    rect.center().y() - 16, 32, 32)
    return visible, pencil


class RenameToolButton(QToolButton):
    """Small vector pencil, independent of optional symbol-font coverage."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(45)
        painter.setPen(QPen(QColor('#eff8f4'), 1.3))
        painter.setBrush(QColor('#9fb6a6'))
        painter.drawRect(QRectF(-3,-10,6,15))
        painter.drawLine(QPointF(-3,-7),QPointF(3,-7))
        painter.drawPolygon(QPolygonF([QPointF(-3,5),QPointF(3,5),QPointF(0,10)]))
        painter.end()


class TitleRenameFilter(QObject):
    def __init__(self, widget, callback):
        super().__init__(widget)
        self.callback = callback
        self.pencil = RenameToolButton(widget)
        self.pencil.setObjectName("renameBuildingButton")
        self.pencil.setFixedSize(32, 32)
        self.pencil.setToolTip("Rename building")
        self.pencil.setAccessibleName("Rename building")
        self.pencil.setStyleSheet("QToolButton {color: #eff8f4; background: #243630; border: 1px solid #60766b; border-radius: 4px;} QToolButton:hover {background: #3b5747;}")
        self.pencil.clicked.connect(callback)
        self._place_pencil(widget)
        self.pencil.show()
        widget.setCursor(Qt.CursorShape.ArrowCursor)
        # Preserve the header's full name and P6 delivery tooltip.
        # The pencil provides its own explicit Rename tooltip.
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Paint, QEvent.Type.FontChange):
            self._place_pencil(obj)
        return False

    def _place_pencil(self, widget):
        _font, _text, rect = widget.rename_title_layout()
        self.pencil.move(round(rect.x()), round(rect.y()))


def bind_building_tree(tree, rename, sell):
    tree.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    class TreeInput(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.RightButton:
                item = tree.itemAt(event.position().toPoint())
                if item is not None:sell(item.data(0, Qt.ItemDataRole.UserRole))
                return True
            return False
    tree._name_filter = TreeInput(tree)
    tree.viewport().installEventFilter(tree._name_filter)
    # Left clicks navigate throughout the row. Renaming belongs to the pencil.


class BuildingChoiceDialog(IndustrialDialog):
    def __init__(self, parent, title, choices, cash):
        super().__init__(title, "Select a type. Construction requires confirmation with BUY.", parent, accept_text="BUY")
        self.setObjectName("buildingChoiceDialog")
        self.selected_type = None
        self.setMinimumWidth(48 + len(choices) * 194)
        self.accept_button.setEnabled(False)
        self.reject_button.setText("CANCEL")
        frame = self.layout().itemAt(0).widget()
        layout = frame.layout()
        # Keep the top-right cancellation visible even when options are not chosen.
        top = QHBoxLayout()
        heading = layout.takeAt(0).widget()
        top.addWidget(heading, 1)
        layout.insertLayout(0, top)
        layout.itemAt(layout.count()-1).layout().removeWidget(self.reject_button)
        top.addWidget(self.reject_button)
        self.reject_button.setMinimumSize(112, 38)
        self.reject_button.setMaximumWidth(130)
        row = QHBoxLayout()
        self.options = {}
        for key, label, definition, cost in choices:
            from production_zero.ui.material_frame import MaterialFrame
            panel = MaterialFrame()
            panel.setObjectName("buildingChoiceOption")
            box = QVBoxLayout(panel)
            box.setContentsMargins(10, 16, 10, 14)
            box.setSpacing(12)
            icon = card_hover_icon(definition, size=82)
            icon.setStyleSheet("background: transparent; border: 0;")
            box.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)
            button = GameButton(label, variant="primary", accent=Accent.NEUTRAL)
            button.setObjectName("buildingTypeOption")
            button.setProperty("buildingType", key)
            button.setMinimumSize(170, 48)
            box.addWidget(button)
            price = QLabel(f"${cost:,.2f}")
            price.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = GAME_UI_TOKENS.typography.industrial_label()
            font.setPointSize(14)
            font.setBold(True)
            price.setFont(font)
            box.addWidget(price)
            def select(checked=False, key=key, cost=cost):
                self.selected_type = key
                for option_key, option in self.options.items():
                    option.setSelected(option_key == key)
                    option._accent = Accent.DANGER if option_key == key else Accent.NEUTRAL
                    option.update()
                self.accept_button.setText(f"BUY · ${cost:,.2f}")
                self.accept_button.setEnabled(cash >= cost)
                self.message.setText("Building will be constructed after confirmation." if cash >= cost else "Insufficient Cash")
            button.clicked.connect(select)
            self.options[key] = button
            row.addWidget(panel)
        layout.insertLayout(layout.count()-1, row)


def pause_button(parent, ids, state, command_bus, refresh, *, name="buildingPauseButton", scope=None, command=None):
    button = GameButton("PAUSE", variant="primary", accent=Accent.DANGER)
    button.setObjectName(name)
    button.setFixedSize(76, 38)
    button._pause_ids = ids
    def update():
        current = tuple(cid for cid in ids() if cid in state.cards)
        paused = scope() if scope else bool(current) and all(state.cards[cid].paused for cid in current)
        button.setText("RESUME" if paused else "PAUSE")
        button._accent = Accent.BUILD if paused else Accent.DANGER
        button.setEnabled(scope is not None or bool(current))
    button.refresh_pause = update
    def toggle():
        from production_zero.core.commands import PauseMachines
        current = tuple(cid for cid in ids() if cid in state.cards)
        if scope is not None:
            command_bus.dispatch(command(not scope()))
            update()
            refresh()
        elif current:
            command_bus.dispatch(PauseMachines(current, not all(state.cards[cid].paused for cid in current)))
            update()
            refresh()
    button.clicked.connect(toggle)
    update()
    return button
