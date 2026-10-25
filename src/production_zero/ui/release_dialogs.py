"""Confirmation dialogs built from the existing material panels and PZ controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox
from production_zero.ui.material_frame import MaterialFrame
from production_zero.ui.pz_controls import RaisedPZButton
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS


class IndustrialDialog(QDialog):
    def __init__(self, title, text, parent=None, *, accept_text="YES – CONFIRM", quantity=None, price=0.):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QDialog { background: transparent; } QLabel { color: #101713; background: transparent; }")
        self.setMinimumWidth(540)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = MaterialFrame(parent=self)
        outer.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        heading = QLabel(title.upper())
        heading.setObjectName("industrialDialogTitle")
        font = GAME_UI_TOKENS.typography.industrial_title()
        font.setPointSize(23)
        font.setWeight(font.Weight.Black)
        heading.setFont(font)
        heading.setStyleSheet("color: #101713; background: transparent;")
        layout.addWidget(heading)
        self.message = QLabel(text)
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setStyleSheet("color: #18201d; background: transparent;")
        font = GAME_UI_TOKENS.typography.industrial_label()
        font.setPointSize(14)
        font.setWeight(font.Weight.Bold)
        self.message.setFont(font)
        layout.addWidget(self.message)
        self.quantity = None
        if quantity is not None:
            self.quantity = QSpinBox()
            self.quantity.setObjectName("machinePurchaseQuantity")
            self.quantity.setRange(1, max(1, quantity))
            self.quantity.setMinimumHeight(34)
            self.quantity.setFont(font)
            layout.addWidget(self.quantity)
            quick = QHBoxLayout()
            for value in (1, 5, 10, quantity):
                button = RaisedPZButton(f"×{value}", variant="secondary")
                button.setMinimumHeight(32)
                button.clicked.connect(lambda checked=False, n=value: self.quantity.setValue(n))
                quick.addWidget(button)
            layout.addLayout(quick)
            self.total = QLabel()
            self.total.setStyleSheet("color: #18201d; background: transparent;")
            self.total.setFont(font)
            self.quantity.valueChanged.connect(lambda n: self.total.setText(f"Total price: ${n * price:,.2f}"))
            self.total.setText(f"Total price: ${price:,.2f}")
            layout.addWidget(self.total)
        buttons = QHBoxLayout()
        self.accept_button = GameButton(accept_text, variant="primary", accent=Accent.BUILD)
        self.reject_button = GameButton("NO – CANCEL", variant="primary", accent=Accent.DANGER)
        for button in (self.accept_button, self.reject_button):
            button.setMinimumSize(230, 48)
        self.accept_button.clicked.connect(self.accept)
        self.reject_button.clicked.connect(self.reject)
        buttons.addWidget(self.accept_button)
        buttons.addWidget(self.reject_button)
        layout.addLayout(buttons)
        self.reject_button.setFocus()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        # At high DPI the material frame can initially size a wrapped label
        # from its unconstrained hint. Respect its actual laid-out width.
        self.message.setMinimumHeight(self.message.heightForWidth(self.message.width()))
        self.adjustSize()


def confirm(parent, title, text, accept_text="YES – CONFIRM"):
    dialog = IndustrialDialog(title, text, parent, accept_text=accept_text)
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        dialog.deleteLater()


def inform(parent, title, text):
    dialog = IndustrialDialog(title, text, parent, accept_text="OK")
    dialog.reject_button.hide()
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()


class InventoryPurchaseDialog(IndustrialDialog):
    """A quoted purchase intent; its UUID survives repeated confirmation."""
    def __init__(self, name, rarity, unit_price, cash, maximum, parent=None, *, quantity_selectable=True):
        from uuid import uuid4
        super().__init__("Purchase to inventory", f"{name} · MK1 · {rarity}\nUnit price: ${unit_price:,.2f}\nAvailable cash: ${cash:,.2f}\nCards remain in Inventory until manually installed.", parent,
                         accept_text="PURCHASE TO INVENTORY")
        self.operation_id = uuid4().hex
        self.purchase_command = None
        content = self.layout().itemAt(0).widget().layout()
        self.quantity = None
        self.max_button = None
        if quantity_selectable:
            self.quantity = QSpinBox()
            self.quantity.setObjectName("machinePurchaseQuantity")
            self.quantity.setRange(1 if maximum else 0, maximum)
            self.quantity.setMinimumHeight(38)
            self.quantity.setStyleSheet("color: #18201d; background: #eee8d0; font-size: 18px;")
            self.quantity.setEnabled(maximum > 0)
            row = QHBoxLayout()
            label = QLabel("QUANTITY")
            row.addWidget(label)
            row.addWidget(self.quantity, 1)
            self.max_button = GameButton("MAX", accent=Accent.BUILD)
            self.max_button.setObjectName("purchaseMax")
            self.max_button.setMinimumHeight(38)
            self.max_button.clicked.connect(lambda: self.quantity.setValue(maximum))
            self.max_button.setEnabled(maximum > 0)
            self.max_button.setToolTip(f"{maximum:,} affordable card(s); maximum 10,000 per Common purchase.")
            row.addWidget(self.max_button)
            content.insertLayout(2, row)
        self.total = QLabel()
        self.total.setObjectName("purchaseTotal")
        self.total.setStyleSheet("color: #18201d; background: transparent; font-size: 18px; font-weight: bold;")
        content.insertWidget(3 if quantity_selectable else 2, self.total)
        def update_total(n):
            self.total.setText(f"TOTAL: ${n * unit_price:,.2f}")
            self.accept_button.setEnabled(n > 0 and maximum > 0)
        if self.quantity is not None:
            self.quantity.valueChanged.connect(update_total)
            update_total(self.quantity.value())
        else:
            update_total(1)
