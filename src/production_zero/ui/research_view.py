"""A vertical Command Deck workspace generated entirely from Research data."""
from __future__ import annotations

from collections import defaultdict
from math import ceil
from PySide6.QtCore import Qt, QPointF, QRectF, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QSizePolicy

from production_zero.core.commands import PurchaseResearch, PurchaseSpecialization, RespecResearch
from production_zero.core.research import research_catalog, node_state, cooldown_remaining, sync_research_clock, specialization_catalog, specialization_state
from production_zero.ui.research_specialization import SpecializationButton, SpecializationPicker
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_art import RESEARCH_GENERIC_ICON
from production_zero.ui.theme import Theme
from production_zero.ui.pz_controls import RaisedPZButton, RaisedRPBadge, paint_module_surface


class ResearchNodeButton(QPushButton):
    def __init__(self, node, state, purchased):
        super().__init__()
        from production_zero.ui.research_hover import bind_research_hover
        bind_research_hover(self,state,node.tree_id)
        self.node = node
        self._state = state
        self._render_signature = None
        self.setObjectName("researchNode")
        self.setProperty("nodeId", node.id)
        self.setProperty("nodeType", node.node_type)
        self.major = node.node_type == "major"
        self.setMinimumWidth(210 if not self.major else 400)
        self.setMaximumWidth(310 if not self.major else 580)
        self.setFixedHeight(136 if not self.major else 144)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.icon = ResourceIconWidget(node.icon_resource if self.major else RESEARCH_GENERIC_ICON,
                                       size=60 if self.major else 40)
        self.icon.setParent(self)
        self.icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon.move(24 if self.major else 15, 40 if self.major else 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(lambda: purchased(node.id))
        self.refresh()

    def sizeHint(self):  # noqa: N802
        return QSize(540 if self.major else 290, self.height())

    def refresh(self):
        status = node_state(self._state.research, self.node)
        missing = tuple(nid for nid in self.node.prerequisites if nid not in self._state.research.unlocked_node_ids)
        signature = (status, missing)
        if signature == self._render_signature:
            return False
        self._render_signature = signature
        self.setProperty("researchState", status)
        self.setAccessibleName(f"{self.node.name}: {self.node.bonus_text}; {status}; 1 Research Point")
        prerequisites = research_catalog()[1]
        needed = [prerequisites[nid].bonus_text for nid in self.node.prerequisites if nid not in self._state.research.unlocked_node_ids]
        detail = "\nRequires: " + "; ".join(needed) if needed else "\nAll prerequisites met."
        self.setToolTip(self.node.description + "\nCost: 1 RP" + detail)
        self.update()
        return True

    def chassis_path(self, inset=0):
        rect = QRectF(2 + inset, 2 + inset, self.width() - 4 - inset * 2, self.height() - 7 - inset * 2)
        cut = 12 if self.major else 7
        path = QPainterPath(rect.topLeft())
        for point in (QPointF(rect.right() - cut, rect.top()), QPointF(rect.right(), rect.top() + cut),
                      rect.bottomRight(), QPointF(rect.left() + cut, rect.bottom()),
                      QPointF(rect.left(), rect.bottom() - cut)):
            path.lineTo(point)
        path.closeSubpath()
        return path

    def text_blocks(self):
        """One layout shared by painting and the offscreen text-fit audit."""
        status = self.property("researchState")
        x = 102 if self.major else 64
        caption = {"unlocked": "RESEARCHED", "available": "AVAILABLE  /  1 RP",
                   "locked": "LOCKED  /  PREREQUISITES", "unfunded": "READY  /  NEED 1 RP"}[status]
        return (
            (f"MAJOR  /  {self.node.name.upper()}" if self.major else "RESEARCH", 15 if self.major else 13,
             QRectF(18, 12, self.width() - 36, 20), False, "muted"),
            (f"+{self.node.effect_value * 100:g}%", 30 if self.major else 25,
             QRectF(x, 35, self.width() - x - 16, 35), False, "bonus"),
            (self.node.bonus_label, 17 if self.major else 14,
             QRectF(x, 71, self.width() - x - 16, 43), True, "text"),
            (caption, 13 if self.major else 11,
             QRectF(x if self.major else 16, self.height() - 23,
                    self.width() - (x if self.major else 16) - 16, 18), False, "muted"),
        )

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        status = self.property("researchState")
        active, available = status == "unlocked", status == "available"
        accent = QColor(Theme.RESOURCE if active else Theme.SAFETY_YELLOW if available else "#7e8388")
        path = self.chassis_path()
        paint_module_surface(painter, path, light=self.major)
        # Clip the accent into the actual chamfer before drawing one continuous
        # outline. The old unbounded strip overran the lower-left cut corner.
        painter.save()
        painter.setClipPath(self.chassis_path(1))
        painter.fillRect(QRectF(3, 3, 5 if self.major else 3, self.height()), accent)
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(accent, 2 if active or available else 1, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.FlatCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        colors = {"text": QColor("#111417" if self.major else "#f2f2f0"),
                  "muted": QColor("#1d2022" if self.major else "#e3e5e6"),
                  "bonus": QColor("#111417") if self.major else accent if active or available else QColor("#f2f2f0")}
        font = QFont("Bahnschrift")
        font.setBold(True)
        for text, pixels, rect, wrap, role in self.text_blocks():
            font.setWeight(QFont.Weight.Black if self.major or role in ("muted", "text") else QFont.Weight.Bold)
            font.setPixelSize(pixels)
            painter.setFont(font)
            painter.setPen(colors[role])
            flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            if wrap:
                flags |= Qt.TextFlag.TextWordWrap
            painter.drawText(rect, flags, text)
        if self.hasFocus() or (self.underMouse() and available):
            painter.setPen(QPen(accent, 1, Qt.PenStyle.DashLine))
            painter.drawPath(self.chassis_path(8))
        painter.end()


class ResearchTreeCanvas(QWidget):
    SPECIALIZATION_INSET = 42
    SPECIALIZATION_COLUMN_WIDTH = 176
    MINIMUM_CANVAS_WIDTH = 918

    def __init__(self, tree_id, state, purchased, specialization_opened=None):
        super().__init__()
        self.setObjectName("researchTreeCanvas")
        self.setMinimumWidth(self.MINIMUM_CANVAS_WIDTH)
        self._painted_connections = ()
        self.buttons = {}
        self.specialization_buttons = {}
        slots = {slot.major_node_id: slot for slot in specialization_catalog().values() if slot.tree_id == tree_id}
        self._state = state
        rows = defaultdict(list)
        for node in research_catalog()[1].values():
            if node.tree_id == tree_id:
                rows[node.row].append(node)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 30)
        layout.setSpacing(32)
        for row, nodes in sorted(rows.items()):
            host = QWidget()
            outer = QHBoxLayout(host)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(20)
            lanes = QWidget()
            line = QHBoxLayout(lanes)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(20)
            line.addStretch(1)
            for node in sorted(nodes, key=lambda n: n.position):
                button = ResearchNodeButton(node, state, purchased)
                self.buttons[node.id] = button
                line.addWidget(button, 10)
            line.addStretch(1)
            outer.addWidget(lanes, 1)
            # Every row in every tree keeps the same main-lane area. Actual
            # specialization buttons remain canvas children; empty Company
            # columns reserve geometry without creating fake slot widgets.
            side = QWidget()
            side.setObjectName("researchSpecializationReserve")
            side.setFixedWidth(self.SPECIALIZATION_COLUMN_WIDTH)
            outer.addWidget(side, 0, Qt.AlignmentFlag.AlignVCenter)
            major_slot = slots.get(nodes[0].id) if len(nodes) == 1 else None
            if major_slot:
                button = SpecializationButton(major_slot, state, specialization_opened or (lambda sid: None))
                button.setParent(self)
                button.show()
                self.specialization_buttons[major_slot.id] = button
                side.setFixedHeight(button.height())
            layout.addWidget(host)
        end = QLabel("END OF RESEARCH TREE")
        end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        end.setStyleSheet("color: #9b9fa3; font: 12px Bahnschrift;")
        layout.addWidget(end)
        QTimer.singleShot(0, self, self._position_specializations)

    def _position_specializations(self):
        self.layout().activate()
        for button in self.specialization_buttons.values():
            major = self.buttons[button.slot.major_node_id]
            position = major.mapTo(self, major.rect().topLeft())
            button.move(self.width() - 26 - button.width() - self.SPECIALIZATION_INSET,
                        position.y() + (major.height() - button.height()) // 2)
            button.raise_()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._position_specializations()

    def refresh(self):
        updated = []
        for button in self.buttons.values():
            if button.refresh():
                updated.append(button.node.id)
        for button in self.specialization_buttons.values():
            if button.refresh():
                updated.append(button.slot.id)
        self.last_updated_ids = tuple(updated)
        # Redraw changed connector regions; do not invalidate the whole canvas
        # on every clock tick or every purchase.
        old = {(start, end): met for start, end, met in self._painted_connections}
        for start, end, met in self.connection_segments():
            if old.get((start, end)) != met:
                self.update(QRectF(QPointF(*start), QPointF(*end)).normalized().adjusted(-3, -3, 3, 3).toAlignedRect())

    def connection_segments(self):
        """Unique splitter/merge buses and vertical lanes, derived from real edges.

        Each segment carries the prerequisite IDs whose completion lights it.
        Shared stems are emitted once, with no perimeter routes or overpainting.
        """
        segments = []
        owned = self._state.research.unlocked_node_ids

        def anchor(button, bottom):
            point = button.mapTo(self, button.rect().topLeft())
            return (point.x() + button.width() / 2, point.y() + (button.height() - 5 if bottom else 2))

        def add(start, end, required):
            if start != end:
                segments.append((start, end, set(required) <= owned))

        splits = defaultdict(list)
        for button in self.buttons.values():
            parents = [self.buttons[nid] for nid in button.node.prerequisites]
            if not parents:
                continue
            if len(parents) == 1 and parents[0].major:
                splits[parents[0].node.id].append(button)
            elif len(parents) == 1:
                add(anchor(parents[0], True), anchor(button, False), button.node.prerequisites)
            else:
                parents.sort(key=lambda parent: parent.node.position)
                starts = [anchor(parent, True) for parent in parents]
                finish = anchor(button, False)
                bus_y = (starts[0][1] + finish[1]) / 2
                for parent, start in zip(parents, starts):
                    add(start, (start[0], bus_y), [parent.node.id])
                add((starts[0][0], bus_y), (starts[-1][0], bus_y), button.node.prerequisites)
                add((finish[0], bus_y), finish, button.node.prerequisites)
        for nid, children in splits.items():
            start = anchor(self.buttons[nid], True)
            ends = sorted((anchor(child, False) for child in children))
            bus_y = (start[1] + ends[0][1]) / 2
            add(start, (start[0], bus_y), [nid])
            add((ends[0][0], bus_y), (ends[-1][0], bus_y), [nid])
            for end in ends:
                add((end[0], bus_y), end, [nid])
        return segments + self.specialization_segments()

    def specialization_segments(self):
        segments = []
        for button in self.specialization_buttons.values():
            major = self.buttons[button.slot.major_node_id]
            start = major.mapTo(self, major.rect().topLeft())
            end = button.mapTo(self, button.rect().topLeft())
            y = start.y() + major.height() / 2
            segments.append(((start.x() + major.width() - 2, y), (end.x() + 2, y),
                             major.node.id in self._state.research.unlocked_node_ids))
        return segments

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Adapt the industrial board's broad material falloff without its tint/wear.
        # Anchor to the entire canvas, never the viewport or dirty paint region.
        # A shallow diagonal keeps the tonal range visible on this very tall tree.
        background = QLinearGradient(QPointF(0, 0), QPointF(self.width(), self.height() * 0.08))
        background.setColorAt(0.0, QColor("#454749"))
        background.setColorAt(0.45, QColor("#292b2d"))
        background.setColorAt(1.0, QColor("#0c0d0e"))
        painter.fillRect(self.rect(), background)
        segments = self.connection_segments()
        self._painted_connections = tuple(segments)
        for start, end, met in segments:
            painter.setPen(QPen(QColor("#4094b0" if met else "#646a70"), 2,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawLine(QPointF(*start), QPointF(*end))
        painter.end()


class ResearchView(QFrame):
    def __init__(self, state, command_bus, on_changed=None):
        super().__init__()
        self._state, self._bus, self._on_changed = state, command_bus, on_changed
        self.setObjectName("researchView")
        self._tree_id = "company.general"
        self._scroll_positions = {}
        self.navigation_buttons = {}
        self.setStyleSheet(f"""
            QFrame#researchView {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #e9e2d9, stop:0.38 #c6bfb5, stop:1 #797976); border: 1px solid #858a8f; border-radius: 7px; }}
            QWidget {{ font-family: Bahnschrift; background: transparent; }}
            QFrame#researchRail {{ background: transparent; border: none; }}
            QFrame#researchHeader {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f5eee4, stop:0.09 #e4dcd1, stop:0.7 #c5bdb2, stop:1 #92908a); border-bottom: 3px solid #94989c; }}
            QLabel {{ background: transparent; border: none; color: #111417; }}
            QLabel#researchTitle {{ font-size: 29px; font-weight: 900; }}
            QLabel#researchPoints {{ background: {Theme.WARNING_ORANGE}; color: #111417; border: 1px solid #ad4b23; border-radius: 6px; padding: 7px 13px; font-size: 27px; font-weight: 900; }}
            QLabel#researchGroup {{ color: #f0f2f3; font-size: 17px; font-weight: 900; padding: 9px 4px 3px; }}
            QPushButton#researchNavigation {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {Theme.SURFACE_3}, stop:1 {Theme.SURFACE_0}); color: {Theme.TEXT}; text-align: left; padding: 8px 6px 8px 36px; border: 1px solid {Theme.BORDER_STRONG}; border-radius: 5px; border-left: 4px solid {Theme.BORDER}; border-bottom: 2px solid {Theme.SURFACE_0}; font-size: 13px; font-weight: 900; }}
            QPushButton#researchNavigation:hover {{ background: {Theme.SURFACE_HOVER}; border-color: {Theme.MUTED}; }}
            QPushButton#researchNavigation:focus {{ border-color: {Theme.SAFETY_YELLOW}; }}
            QPushButton#researchNavigation:pressed {{ background: {Theme.SURFACE_0}; }}
            QPushButton#researchNavigation:checked {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #41464a, stop:1 #202529); color: #fff3bd; border-left-color: {Theme.SAFETY_YELLOW}; }}
            QPushButton#researchAction {{ background: {Theme.SAFETY_YELLOW}; color: #111417; border: 1px solid #bc9310; border-bottom: 2px solid #98750d; border-radius: 5px; padding: 8px 12px; font-size: 13px; font-weight: 900; }}
            QPushButton#researchAction:hover {{ background: #ffe46b; }}
            QPushButton#researchAction:pressed {{ background: #e8b914; border-bottom-color: #bc9310; }}
            QPushButton#researchAction:disabled {{ color: #64686c; background: #b9bbbd; border-color: #999da1; }}
            QLabel#researchNotice {{ background: #303438; color: #f2f2f0; border: 1px solid #df6b2f; border-radius: 4px; padding: 8px; font-size: 12px; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: #25292d; width: 12px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: #7e8388; min-height: 36px; }}
        """)
        root = QHBoxLayout(self)
        root.setContentsMargins(9, 9, 9, 9)
        root.setSpacing(10)
        from production_zero.ui.material_frame import MaterialFrame
        from production_zero.ui.game_ui import MaterialLevel
        rail = MaterialFrame(level=MaterialLevel.INSET)
        rail.setObjectName("researchRail")
        rail.setFixedWidth(250)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(9, 9, 9, 9)
        # The heading grows by 4 px; use 4 px less inter-widget space so the
        # category viewport and every navigation button retain their position.
        rail_layout.setSpacing(2)
        label = QLabel("RESEARCH &\nDEVELOPMENT")
        label.setObjectName("researchHeading")
        label.setAccessibleName("RESEARCH & DEVELOPMENT")
        label.setStyleSheet("font-size: 24px; font-weight: 900; color: #f0f2f3;")
        rail_layout.addWidget(label)
        rail_scroll = QScrollArea()
        self.navigation_scroll = rail_scroll
        rail_scroll.setObjectName("researchNavigationScroll")
        rail_scroll.setWidgetResizable(True)
        rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        choices = QWidget()
        choices_layout = QVBoxLayout(choices)
        choices_layout.setContentsMargins(0, 0, 3, 0)
        choices_layout.setSpacing(5)
        trees, _ = research_catalog()
        for family, title in (("company", "COMPANY"), ("industry", "INDUSTRIES")):
            group = QLabel(title)
            group.setObjectName("researchGroup")
            choices_layout.addWidget(group)
            for tree in sorted(trees.values(), key=lambda t: t.order):
                if tree.family != family:
                    continue
                button = QPushButton(tree.name.replace("&", "&&"))
                button.setObjectName("researchNavigation")
                button.setProperty("treeId", tree.id)
                button.setMinimumHeight(39)
                button.setCheckable(True)
                button.setToolTip(tree.name)
                from production_zero.ui.research_hover import bind_research_hover
                bind_research_hover(button,self._state,tree.id)
                icon = ResourceIconWidget(tree.icon_resource, size=28)
                icon.setParent(button)
                icon.move(9, 7)
                icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                button.clicked.connect(lambda checked=False, tid=tree.id: self.select_tree(tid))
                self.navigation_buttons[tree.id] = button
                choices_layout.addWidget(button)
        choices_layout.addStretch(1)
        rail_scroll.setWidget(choices)
        rail_layout.addWidget(rail_scroll, 1)
        root.addWidget(rail)
        main = QVBoxLayout()
        main.setSpacing(6)
        header = QFrame()
        header.setObjectName("researchHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 8, 12, 8)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        self.title = QLabel()
        self.title.setObjectName("researchTitle")
        self.title.setMinimumWidth(0)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.summary = QLabel()
        self.summary.setStyleSheet("font-size: 13px; font-weight: 900; color: #303438;")
        copy.addWidget(self.title)
        copy.addWidget(self.summary)
        header_layout.addLayout(copy, 1)
        self.products_button = RaisedPZButton("PRODUCTS", variant="secondary")
        self.products_button.setObjectName("researchCategoryProducts")
        self.products_button.clicked.connect(self._show_category_products)
        header_layout.addWidget(self.products_button)
        self.points = RaisedRPBadge()
        self.points.setObjectName("researchPoints")
        header_layout.addWidget(self.points)
        self.respec_button = self._action("FULL RESPEC", self._review_respec)
        self.respec_button.setToolTip("Return all spent RP. Starts a 24-hour respec cooldown; research purchases remain available.")
        respec_controls = QVBoxLayout()
        respec_controls.setSpacing(3)
        respec_controls.addWidget(self.respec_button)
        self.cooldown = QLabel()
        self.cooldown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cooldown.setStyleSheet("font-size: 11px; font-weight: 700;")
        self.cooldown.hide()
        respec_controls.addWidget(self.cooldown)
        header_layout.addLayout(respec_controls)
        main.addWidget(header)
        self.review = QFrame()
        review_row = QHBoxLayout(self.review)
        review_row.setContentsMargins(8, 0, 0, 0)
        self.review_label = QLabel()
        review_row.addWidget(self.review_label, 1)
        review_row.addWidget(self._action("RETURN ALL RP", self._respec))
        review_row.addWidget(self._action("CANCEL", self.review.hide))
        self.review.hide()
        main.addWidget(self.review)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("researchTreeScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.verticalScrollBar().setSingleStep(44)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.scroll)
        self.picker = None
        main.addWidget(self.pages, 1)
        # Errors are a temporary overlay; no footer consumes tree space.
        self.notice = QLabel(self.scroll.viewport())
        self.notice.setObjectName("researchNotice")
        self.notice.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.notice.hide()
        self.notice_timer = QTimer(self)
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self.notice.hide)
        root.addLayout(main, 1)
        self.canvas = None
        self.select_tree(self._tree_id)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda: self.refresh() if self.isVisible() else None)
        self.timer.start()

    def _action(self, text, callback):
        button = RaisedPZButton(text, variant="primary")
        button.setObjectName("researchAction")
        button.clicked.connect(callback)
        return button

    def select_tree(self, tree_id):
        if tree_id not in research_catalog()[0]:
            raise ValueError("Unknown Research tree")
        if self.canvas is not None:
            self._scroll_positions[self._tree_id] = self.scroll.verticalScrollBar().value()
        self._tree_id = tree_id
        self.products_button.setEnabled(tree_id.startswith("industry."))
        self._close_picker()
        self.review.hide()
        self.notice.hide()
        old = self.scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self.canvas = ResearchTreeCanvas(tree_id, self._state, self._purchase, self._open_specialization)
        self.scroll.setWidget(self.canvas)
        for tid, button in self.navigation_buttons.items():
            button.setChecked(tid == tree_id)
        self.refresh()
        self.navigation_scroll.ensureWidgetVisible(self.navigation_buttons[tree_id])
        QTimer.singleShot(0, self, lambda: self.scroll.verticalScrollBar().setValue(self._scroll_positions.get(self._tree_id, 0)))

    def _show_category_products(self):
        from types import SimpleNamespace
        from importlib.resources import files
        from production_zero.core.research import research_domains
        from production_zero.data.definitions import load_resource_definitions
        from production_zero.ui.contracts_view import ContractProductPicker
        from production_zero.ui.release_dialogs import IndustrialDialog
        resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
        domain = self._tree_id.removeprefix("industry.")
        domains = research_domains()
        products = [SimpleNamespace(resource_id=rid, name=resource.name) for rid, resource in resources.items() if domains.get(rid) == domain]
        dialog = IndustrialDialog("Research products", f"{len(products)} products in {research_catalog()[0][self._tree_id].name}", self)
        dialog.resize(900, 640)
        picker = ContractProductPicker(products, resources, set(), "", purpose_label="RESEARCH CATEGORY")
        picker.product_selected.connect(lambda rid: dialog.message.setText(resources[rid].name + " · " + resources[rid].category))
        picker.back_requested.connect(dialog.reject)
        dialog.layout().itemAt(0).widget().layout().insertWidget(2, picker)
        dialog.accept_button.hide()
        dialog.reject_button.hide()
        dialog.exec()

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "navigation_scroll"):
            QTimer.singleShot(0, self, lambda: self.navigation_scroll.ensureWidgetVisible(self.navigation_buttons[self._tree_id]))

    def refresh(self):
        sync_research_clock(self._state)
        research = self._state.research
        tree = research_catalog()[0][self._tree_id]
        self.title.setText(tree.name.upper())
        self.title.setToolTip(tree.name)
        self.points.setText(f"{research.available:,} RP")
        count = sum(nid in research.unlocked_node_ids for nid in self.canvas.buttons)
        bonus = sum(button.node.effect_value for nid, button in self.canvas.buttons.items() if nid in research.unlocked_node_ids)
        effect = "DOMAIN VALUE" if tree.family == "industry" else next(iter(self.canvas.buttons.values())).node.bonus_label.upper()
        self.summary.setText(f"+{bonus * 100:g}% {effect}  ·  {count} / {len(self.canvas.buttons)} RESEARCHED")
        if self.canvas.specialization_buttons:
            specialized = sum(sid in research.specializations for sid in self.canvas.specialization_buttons)
            self.summary.setText(self.summary.text() + f"  ·  {specialized} / 4 SPECIALIZED")
        remaining = ceil(cooldown_remaining(research))
        self.respec_button.setEnabled(research.spent > 0 and remaining == 0)
        self.cooldown.setText(f"COOLDOWN {remaining // 3600:02d}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}" if remaining else "")
        self.cooldown.setVisible(remaining > 0)
        self.canvas.refresh()
        if self.picker is not None and specialization_state(research, self.picker.slot) in ("locked", "unlocked"):
            self._close_picker()

    def _open_specialization(self, slot_id):
        slot = specialization_catalog()[slot_id]
        status = specialization_state(self._state.research, slot)
        if status in ("locked", "unlocked"):
            self._show_notice("Research the attached Major first." if status == "locked" else "Changing a specialization requires Full Respec.")
            return
        self._close_picker()
        self.review.hide()
        self.picker = SpecializationPicker(slot, self._state,
                                           lambda rid: self._purchase_specialization(slot_id, rid), self._close_picker)
        self.pages.addWidget(self.picker)
        self.pages.setCurrentWidget(self.picker)
        self.picker.search.setFocus()

    def _close_picker(self):
        if self.picker is not None:
            self.pages.setCurrentWidget(self.scroll)
            self.pages.removeWidget(self.picker)
            self.picker.deleteLater()
            self.picker = None

    def _purchase_specialization(self, slot_id, product_id):
        try:
            self._bus.dispatch(PurchaseSpecialization(slot_id, product_id))
        except ValueError as exc:
            if self.picker is not None:
                self.picker.message.setText(str(exc))
        else:
            self._close_picker()
            if self._on_changed:
                self._on_changed()
        self.refresh()

    def _purchase(self, node_id):
        try:
            self._bus.dispatch(PurchaseResearch(node_id))
        except ValueError as exc:
            self._show_notice(str(exc))
        else:
            self.notice.hide()
            if self._on_changed:
                self._on_changed()
        self.refresh()

    def _show_notice(self, message):
        self.notice.setText(message)
        self.notice.adjustSize()
        self.notice.move(12, 10)
        self.notice.raise_()
        self.notice.show()
        self.notice_timer.start(4000)

    def _review_respec(self):
        self._close_picker()
        self.review_label.setText(f"Return all {self._state.research.spent} spent RP? Effects removed; reset cooldown: 24 hours.")
        self.review.show()

    def _respec(self):
        try:
            self._bus.dispatch(RespecResearch())
        except ValueError as exc:
            self._show_notice(str(exc))
        else:
            self._show_notice("All spent RP returned. Choose your new allocation.")
            if self._on_changed:
                self._on_changed()
        self.review.hide()
        self.refresh()
