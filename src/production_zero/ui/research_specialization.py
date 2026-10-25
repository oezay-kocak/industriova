"""Industry side slots and the shared PZ resource-tile selection workflow."""
from PySide6.QtCore import QEvent, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout

from production_zero.core.research import research_catalog, research_domains, research_products, specialization_state
from production_zero.ui.game_ui.icons import GameIcon, draw_game_icon
from production_zero.ui.game_ui.tokens import Accent
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_tiles import RESOURCE_TILE_WIDTH, ResourceSelectionTile, ResourceSelectionGridHost, configure_resource_selection_scroll
from production_zero.ui.secondary_views import SecondaryViewHeader, secondary_action_button
from production_zero.ui.theme import Theme
from production_zero.ui.pz_controls import paint_module_surface
from production_zero.ui.game_ui.rendering.factory import draw_lock_warning_frame


class SpecializationButton(QPushButton):
    def __init__(self, slot, state, opened):
        super().__init__()
        self.slot, self._state = slot, state
        from production_zero.ui.research_hover import bind_research_hover
        bind_research_hover(self,state,slot.tree_id,slot.id)
        self.setObjectName("researchSpecializationSlot")
        self.setProperty("slotId", slot.id)
        self.setFixedSize(176, 184)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon = None
        self._product_id = None
        self._render_signature = None
        self.clicked.connect(lambda: opened(slot.id))
        self.refresh()

    def refresh(self):
        status = specialization_state(self._state.research, self.slot)
        product_id = self._state.research.specializations.get(self.slot.id)
        signature = (status, product_id)
        if self._render_signature == signature:
            return False
        self._render_signature = signature
        self.setProperty("researchState", status)
        self.setProperty("resourceId", product_id or "")
        if product_id != self._product_id:
            if self.icon is not None:
                self.icon.hide()
                self.icon.deleteLater()
                self.icon = None
            if product_id:
                self.icon = ResourceIconWidget(product_id, size=48)
                self.icon.setParent(self)
                self.icon.move(64, 25)
                self.icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                self.icon.show()
            self._product_id = product_id
        name = research_products()[product_id]["name"] if product_id else "Choose product"
        self.setAccessibleName(f"Specialization: {name}; {status}; +{self.slot.value_bonus * 100:g}% exact product value; 1 RP")
        self.setToolTip(f"{name}\n+{self.slot.value_bonus * 100:g}% exact product value. Costs 1 RP.\nRequires {research_catalog()[1][self.slot.major_node_id].name}. Selection is locked until Full Respec.")
        self.update()
        return True

    def locked_stack_layout(self):
        # A centered 97 px stack inside the unchanged 176 x 184 chassis.
        top = (self.height() - 97) / 2
        return (QRectF(10, top, 156, 18),
                QRectF(self.width() / 2 - 24.8, top + 26, 49.6, 44.8),
                QRectF(10, top + 79, 156, 18))

    def text_blocks(self):
        status = self.property("researchState")
        selected = status == "unlocked"
        name = research_products()[self._product_id]["name"].upper() if selected else "LOCKED" if status == "locked" else "CHOOSE PRODUCT"
        title_rect, _, locked_rect = self.locked_stack_layout()
        return (
            ("SPECIALIZATION", 14 if status == "locked" else 13, title_rect if status == "locked" else QRectF(10, 9, 156, 17), False),
            (name, 13 if status == "locked" else 12, locked_rect if status == "locked" else QRectF(10, 77, 156, 40), True),
            (f"+{self.slot.value_bonus * 100:.1f}%" if selected else "1 RP" if status != "locked" else "", 23, QRectF(10, 119, 156, 29), False),
            ("PRODUCT VALUE" if selected else "", 10, QRectF(10, 148, 156, 14), False),
            ("RESEARCHED" if selected else "NEED 1 RP" if status == "unfunded" else "", 11, QRectF(10, 164, 156, 15), False),
        )

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        status = self.property("researchState")
        accent = QColor(Theme.RESOURCE if status == "unlocked" else Theme.SAFETY_YELLOW if status == "available" else "#df6b2f" if status == "locked" else "#9da3a8")
        path = QPainterPath()
        path.moveTo(2, 2)
        path.lineTo(163, 2)
        path.lineTo(174, 13)
        path.lineTo(174, 182)
        path.lineTo(13, 182)
        path.lineTo(2, 171)
        path.closeSubpath()
        paint_module_surface(painter, path)
        painter.setPen(QPen(accent, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        if status == "locked":
            painter.save()
            _, lock_rect, _ = self.locked_stack_layout()
            painter.translate(lock_rect.center().x(), lock_rect.top())
            painter.scale(.8, .8)
            housing = draw_lock_warning_frame(painter, QRectF(-80, -40, 160, 140), enabled=True)
            draw_game_icon(painter, GameIcon.LOCK, housing.adjusted(13, 9, -13, -9), accent=Accent.LOCKED)
            painter.restore()
        elif not self._product_id:
            draw_game_icon(painter, GameIcon.BUILD, QRectF(64, 28, 48, 48), accent=Accent.BUILD)
        for text, pixels, rect, wrap in self.text_blocks():
            font = QFont("Bahnschrift")
            font.setWeight(QFont.Weight.Black if status == "locked" else QFont.Weight.ExtraBold)
            font.setPixelSize(pixels)
            painter.setFont(font)
            painter.setPen(accent if pixels == 23 or status == "locked" else QColor("#f2f2f0"))
            flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            painter.drawText(rect, flags | Qt.TextFlag.TextWordWrap if wrap else flags, text)
        if self.hasFocus():
            painter.setPen(QPen(accent, 1, Qt.PenStyle.DashLine))
            painter.drawRect(7, 7, 162, 170)
        painter.end()


class SpecializationProductTile(ResourceSelectionTile):
    selected_product = Signal(str)

    def __init__(self, product, industry, count, projected_bonus):
        super().__init__(resource_id=product["id"], title=product["name"], subtitle=industry,
                         icon_key=product["icon_key"], accent_key=product["accent_key"],
                         detail=f"Selected in {count} slots", status=f"AFTER: +{projected_bonus * 100:g}%  /  1 RP")
        self.setAccessibleName(f"{product['name']}; {industry}; currently {count} specializations; after selection +{projected_bonus * 100:g}% product value; costs 1 RP")

    def mousePressEvent(self, event):  # noqa: N802
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.selected_product.emit(self.property("resourceId"))
        super().mousePressEvent(event)

    def keyPressEvent(self, event):  # noqa: N802
        if self.isEnabled() and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.selected_product.emit(self.property("resourceId"))
        else:
            super().keyPressEvent(event)


class SpecializationPicker(QFrame):
    def __init__(self, slot, state, selected, back):
        super().__init__()
        self.slot, self._state = slot, state
        self.setObjectName("researchSpecializationPicker")
        self.setStyleSheet(f"""
            QFrame#researchSpecializationPicker {{ background: #14171a; border: 1px solid #646a70; border-radius: 7px; }}
            QWidget {{ font-family: Bahnschrift; color: #f2f2f0; }}
            QLabel {{ background: transparent; border: none; color: #c1c4c7; font-size: 13px; }}
            QFrame#secondaryViewHeader {{ background: #303438; border-bottom: 2px solid #646a70; border-radius: 5px; }}
            QLabel#secondaryTitle {{ color: #f2f2f0; font-size: 24px; font-weight: 900; }}
            QPushButton {{ background: {Theme.SAFETY_YELLOW}; color: #111417; border: 1px solid #bc9310; border-radius: 4px; padding: 8px 16px; font-size: 13px; font-weight: 900; }}
            QPushButton:hover {{ background: #ffe46b; }}
            QLineEdit {{ background: #23272b; color: #f2f2f0; border: 1px solid #7e8388; border-radius: 4px; padding: 8px 11px; font-size: 14px; }}
            QLineEdit:focus {{ border-color: {Theme.SAFETY_YELLOW}; }}
            QFrame#resourceSelectionTile {{ background: #23272b; border: 1px solid #646a70; border-radius: 8px; }}
            QFrame#resourceSelectionTile:hover, QFrame#resourceSelectionTile:focus {{ border-color: {Theme.SAFETY_YELLOW}; background: #303438; }}
            QLabel#resourceSelectionTileName {{ color: #f2f2f0; font-size: 13px; font-weight: 900; }}
            QLabel#resourceSelectionTileSubtitle, QLabel#resourceSelectionTileDetail {{ color: #c1c4c7; font-size: 11px; font-weight: 700; }}
            QLabel#resourceSelectionTileStatus {{ background: #34383c; color: {Theme.SAFETY_YELLOW}; border: 1px solid #646a70; border-radius: 4px; font-size: 10px; font-weight: 800; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        tree = research_catalog()[0][slot.tree_id]
        self.back_button = secondary_action_button("BACK", "specializationBackButton")
        self.back_button.clicked.connect(back)
        layout.addWidget(SecondaryViewHeader("SELECT SPECIALIZATION", tree.name, self.back_button))
        self.search = QLineEdit()
        self.search.setPlaceholderText("SEARCH PRODUCTS...")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.message = QLabel("Choose a product for 1 RP. Duplicate selections stack; changes require Full Respec.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        configure_resource_selection_scroll(self.scroll)
        self.host = ResourceSelectionGridHost()
        self.grid = QGridLayout(self.host)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.tiles = {}
        products = research_products()
        for rid in sorted((rid for rid, domain in research_domains().items() if domain == tree.id.removeprefix("industry.")), key=lambda rid: products[rid]["name"]):
            count = sum(product == rid for product in state.research.specializations.values())
            tile = SpecializationProductTile(products[rid], tree.name, count, (count + 1) * slot.value_bonus)
            tile.selected_product.connect(selected)
            self.tiles[rid] = tile
        self.scroll.setWidget(self.host)
        self.scroll.viewport().installEventFilter(self)
        layout.addWidget(self.scroll, 1)
        self.empty = QLabel("No matching products")
        self.empty.hide()
        layout.addWidget(self.empty)
        self.search.textChanged.connect(self._filter)
        self._columns = 0
        self._filter()

    def _filter(self):
        query = self.search.text().strip().casefold()
        self.visible_product_ids = [rid for rid in self.tiles if query in research_products()[rid]["name"].casefold() or query in rid.casefold()]
        self._reflow()
        self.scroll.verticalScrollBar().setValue(0)

    def _reflow(self):
        columns = max(1, (self.scroll.viewport().width() - 16 + 10) // (RESOURCE_TILE_WIDTH + 10))
        while self.grid.count():
            self.grid.takeAt(0)
        for tile in self.tiles.values():
            tile.hide()
        for index, rid in enumerate(self.visible_product_ids):
            tile = self.tiles[rid]
            self.grid.addWidget(tile, index // columns, index % columns)
            tile.show()
        self._columns = columns
        self.empty.setVisible(not self.visible_product_ids)

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._reflow()
        return super().eventFilter(watched, event)

    def sizeHint(self):  # noqa: N802
        return QSize(800, 550)
