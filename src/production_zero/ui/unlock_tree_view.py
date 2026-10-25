from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsObject,
    QGraphicsPathItem,
    QHBoxLayout,
    QLineEdit,
    QWidget,
    QPushButton,
    QVBoxLayout,
)

from production_zero.core.definitions import CardDefinition
from production_zero.core.enums import MachineType
from production_zero.core.progression import (
    ProductionUnlockRequirement,
    initial_production_ids,
    production_options,
    unlock_requirements_for,
)
from production_zero.core.state import GameState
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.secondary_views import SecondaryViewHeader, secondary_action_button, style_secondary
from production_zero.ui.theme import Theme
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView


PLAYER_STAGE_LABELS = {
    MachineType.EXTRACTOR: "PRIMARY PRODUCTION",
    MachineType.DRILLING: "PRIMARY PRODUCTION",
    MachineType.AGRICULTURE: "PRIMARY PRODUCTION",
    MachineType.PROCESSOR: "PROCESSING",
    MachineType.FABRICATOR: "MANUFACTURING",
    MachineType.ASSEMBLER: "ASSEMBLY",
}
STAGE_FILTERS = (
    ("PRIMARY PRODUCTION", "PRIMARY PRODUCTION"),
    ("PROCESSING", "PROCESSING"),
    ("MANUFACTURING", "MANUFACTURING"),
    ("ASSEMBLY", "ASSEMBLY"),
)
DEPTH_LABELS = ("ROOTS / START", "PROCESSING", "MANUFACTURING", "ASSEMBLY")
NODE_WIDTH = 236.0
NODE_HEIGHT = 94.0
COLUMN_GAP = 118.0
ROW_GAP = 18.0
LANE_GAP = 18.0
MAX_ROWS_PER_LANE = 22
TOP_MARGIN = 54.0
SIDE_MARGIN = 24.0


@dataclass(frozen=True, slots=True)
class UnlockTreeNode:
    resource_id: str
    production_id: str
    name: str
    stage: MachineType
    required_level: int
    requirements: tuple[ProductionUnlockRequirement, ...]
    depth: int
    begins_unlocked: bool
    children: tuple[str, ...]
    icon_key: str
    accent_key: str


@dataclass(frozen=True, slots=True)
class UnlockTreeEdge:
    source_resource_id: str
    target_resource_id: str
    required_quantity: float


@dataclass(frozen=True, slots=True)
class UnlockTreeGraph:
    nodes: dict[str, UnlockTreeNode]
    edges: tuple[UnlockTreeEdge, ...]
    roots: tuple[str, ...]
    maximum_depth: int


def build_unlock_tree_graph(definitions: dict[str, CardDefinition]) -> UnlockTreeGraph:
    """Project runtime unlock requirements into a deterministic directed graph."""
    options = production_options(definitions)
    by_output = {option.output_resource: option for option in options}
    requirements = {resource_id: unlock_requirements_for(option) for resource_id, option in by_output.items()}
    children: dict[str, list[str]] = defaultdict(list)
    edges: list[UnlockTreeEdge] = []
    indegree = {resource_id: 0 for resource_id in by_output}
    for target, target_requirements in requirements.items():
        for requirement in target_requirements:
            if requirement.resource_id not in by_output:
                raise ValueError(f"Missing unlock prerequisite production: {requirement.resource_id}")
            children[requirement.resource_id].append(target)
            indegree[target] += 1
            edges.append(UnlockTreeEdge(requirement.resource_id, target, requirement.quantity))

    roots = tuple(sorted(resource_id for resource_id, degree in indegree.items() if degree == 0))
    queue = deque(roots)
    depth = {resource_id: 0 for resource_id in roots}
    remaining = dict(indegree)
    while queue:
        resource_id = queue.popleft()
        for child in sorted(children[resource_id]):
            depth[child] = max(depth.get(child, 0), depth[resource_id] + 1)
            remaining[child] -= 1
            if remaining[child] == 0:
                queue.append(child)
    if len(depth) != len(by_output):
        raise ValueError("Unlock progression must be an acyclic graph with reachable roots")

    initial = initial_production_ids()
    nodes: dict[str, UnlockTreeNode] = {}
    for resource_id, option in by_output.items():
        nodes[resource_id] = UnlockTreeNode(
            resource_id=resource_id,
            production_id=option.production_id,
            name=option.name,
            stage=option.stage,
            required_level=1,
            requirements=requirements[resource_id],
            depth=depth[resource_id],
            begins_unlocked=option.production_id in initial,
            children=tuple(sorted(children[resource_id])),
            icon_key=option.icon_key or resource_icon_key(resource_id),
            accent_key=option.accent_key or resource_accent_key(resource_id),
        )
    return UnlockTreeGraph(
        nodes=nodes,
        edges=tuple(sorted(edges, key=lambda edge: (edge.source_resource_id, edge.target_resource_id))),
        roots=roots,
        maximum_depth=max(depth.values(), default=0),
    )


def unlock_tree_node_state(state: GameState, graph: UnlockTreeGraph, node: UnlockTreeNode) -> str:
    if node.production_id in state.production_progress.unlocked_production_ids:
        return "unlocked"
    unlocked_resources = {
        item.resource_id
        for item in graph.nodes.values()
        if item.production_id in state.production_progress.unlocked_production_ids
    }
    return "current" if all(requirement.resource_id in unlocked_resources for requirement in node.requirements) else "locked"
def node_requirement_lines(state: GameState, graph: UnlockTreeGraph, node: UnlockTreeNode) -> tuple[str, ...]:
    state_name = unlock_tree_node_state(state, graph, node)
    if state_name == "unlocked":
        return ("UNLOCKED",)
    lines: list[str] = []
    for requirement in node.requirements:
        source = graph.nodes[requirement.resource_id]
        current = state.production_progress.lifetime_produced.get(requirement.resource_id, 0.0)
        if current < requirement.quantity:
            lines.append(f"{source.name.upper()} {current:g} / {requirement.quantity:g}")
    return tuple(lines) or ("LOCKED",)


@lru_cache(maxsize=1)
def _icon_background():
    # QWidget.render used to include the unparented icon widget's background.
    # Resolve that existing palette once, preserving pixels without 353 widgets.
    probe = QWidget()
    probe.ensurePolished()
    color = probe.palette().window().color()
    probe.deleteLater()
    return color


@lru_cache(maxsize=512)
def _render_icon(resource_id: str, icon_key: str, accent_key: str) -> QPixmap:
    from production_zero.ui.resource_art import draw_resource_raster, has_resource_raster
    pixmap = QPixmap(38, 38)
    pixmap.fill(Qt.GlobalColor.transparent)
    if has_resource_raster(resource_id):
        pixmap.fill(_icon_background())
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_resource_raster(painter, QRectF(0, 0, 38, 38), resource_id)
        painter.end()
    else:
        widget = ResourceIconWidget(resource_id, icon_key, accent_key, 38)
        widget.render(pixmap)
        widget.deleteLater()
    return pixmap


class UnlockTreeNodeItem(QGraphicsObject):
    selected = Signal(str)

    def __init__(self, state: GameState, graph: UnlockTreeGraph, node: UnlockTreeNode, *, context: bool) -> None:
        super().__init__()
        self.node = node
        self._state = state
        self._graph = graph
        self._context = context
        self._selected = False
        self._related = False
        self._search_match = False
        self._state_name = "locked"
        self._requirement_lines: tuple[str, ...] = ()
        self._price_text = ''
        # Only icons that actually enter the viewport need decoding/rasterizing.
        self._icon = None
        self.setAcceptHoverEvents(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setData(0, node.resource_id)
        self.refresh_state()

    def boundingRect(self) -> QRectF:  # noqa: N802
        return QRectF(0, 0, NODE_WIDTH, NODE_HEIGHT)

    @property
    def state_name(self) -> str:
        return self._state_name

    @property
    def requirement_lines(self) -> tuple[str, ...]:
        return self._requirement_lines

    def set_emphasis(self, *, selected: bool, related: bool, search_match: bool) -> None:
        if (self._selected, self._related, self._search_match) == (selected, related, search_match):
            return
        self._selected = selected
        self._related = related
        self._search_match = search_match
        self.update()

    def refresh_state(self) -> None:
        from production_zero.ui.resource_prices import base_price_text, price_tooltip
        state_name = unlock_tree_node_state(self._state, self._graph, self.node)
        lines = node_requirement_lines(self._state, self._graph, self.node)
        price = base_price_text(self.node.resource_id, self._state, compact=True)
        tooltip = price_tooltip(self._state, self.node.resource_id)
        from production_zero.ui.resource_categories import research_category
        self.setToolTip(self.node.name + '\nResearch: ' + research_category(self.node.resource_id) + '\n' + tooltip)
        if (state_name, lines, price) == (self._state_name, self._requirement_lines, self._price_text):
            return
        self._state_name, self._requirement_lines = state_name, lines
        self._price_text = price
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.boundingRect().adjusted(1, 1, -1, -1)
        fills = {
            "unlocked": QColor("#25343a"),
            "current": QColor("#35321f"),
            "locked": QColor("#171c1e"),
            "level_gated": QColor("#211c1a"),
        }
        borders = {
            "unlocked": QColor(Theme.RESOURCE),
            "current": QColor(Theme.SAFETY_YELLOW),
            "locked": QColor(Theme.BORDER),
            "level_gated": QColor(Theme.WARNING_ORANGE),
        }
        fill = fills[self._state_name]
        border = borders[self._state_name]
        if self._context and not (self._selected or self._related or self._search_match):
            fill = fill.darker(125)
            border = QColor(Theme.DIM)
        if self._selected or self._search_match:
            border = QColor(Theme.SAFETY_YELLOW)
        painter.setBrush(fill)
        painter.setPen(QPen(border, 3.0 if self._selected or self._search_match else 1.4))
        painter.drawRoundedRect(rect, 6, 6)
        if self._icon is None:
            self._icon = _render_icon(self.node.resource_id, self.node.icon_key, self.node.accent_key)
        painter.drawPixmap(10, 19, self._icon)

        title_rect = QRectF(58, 8, NODE_WIDTH - 68, 22)
        title_font = QFont("Bahnschrift", 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(Theme.TEXT if self._state_name != "locked" else Theme.MUTED))
        title = painter.fontMetrics().elidedText(self.node.name.upper(), Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        painter.setFont(QFont("Bahnschrift", 7, QFont.Weight.DemiBold))
        painter.setPen(QColor(Theme.MUTED))
        painter.drawText(QRectF(58, 29, NODE_WIDTH - 68, 16), PLAYER_STAGE_LABELS[self.node.stage])

        status = self._requirement_lines[0] if self._requirement_lines else "LOCKED"
        if len(self._requirement_lines) > 1:
            status += f"  +{len(self._requirement_lines) - 1}"
        painter.setFont(QFont("Bahnschrift", 8, QFont.Weight.Bold))
        painter.setPen(border if self._state_name != "locked" else QColor(Theme.DIM))
        status = painter.fontMetrics().elidedText(status, Qt.TextElideMode.ElideRight, int(NODE_WIDTH - 68))
        painter.drawText(QRectF(58, 48, NODE_WIDTH - 68, 18), status)
        painter.setFont(QFont('Bahnschrift', 8, QFont.Weight.Bold))
        painter.setPen(QColor(Theme.SAFETY_YELLOW))
        painter.drawText(QRectF(58, 70, NODE_WIDTH - 68, 18), self._price_text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.node.resource_id)
            event.accept()
            return
        super().mousePressEvent(event)


class UnlockTreeEdgeItem(QGraphicsPathItem):
    def __init__(self, edge: UnlockTreeEdge, source: UnlockTreeNodeItem, target: UnlockTreeNodeItem) -> None:
        super().__init__()
        self.edge = edge
        self.source = source
        self.target = target
        self._highlighted = False
        self._trace_active = False
        self.setZValue(-2)
        self.refresh_geometry()
        self.refresh_state()

    def refresh_geometry(self) -> None:
        start = self.source.pos() + QPointF(NODE_WIDTH, NODE_HEIGHT / 2)
        end = self.target.pos() + QPointF(0, NODE_HEIGHT / 2)
        bend = max(34.0, (end.x() - start.x()) * 0.44)
        path = QPainterPath(start)
        path.cubicTo(start + QPointF(bend, 0), end - QPointF(bend, 0), end)
        self.setPath(path)

    def set_trace_state(self, *, highlighted: bool, trace_active: bool) -> None:
        self._highlighted = highlighted
        self._trace_active = trace_active
        self.refresh_state()

    def refresh_state(self) -> None:
        active = self._highlighted or (not self._trace_active and self.target.state_name == "current")
        if self._highlighted:
            color = QColor(Theme.SAFETY_YELLOW)
        elif self.target.state_name == "unlocked":
            color = QColor(Theme.RESOURCE)
        elif active:
            color = QColor(Theme.SAFETY_YELLOW)
        else:
            color = QColor(Theme.DIM)
        color.setAlpha(235 if self._highlighted else (150 if active else 72))
        pen = QPen(color, 2.2 if active else 1.0, Qt.PenStyle.SolidLine)
        opacity = (
            1.0
            if self._highlighted
            else (0.14 if self._trace_active else (0.48 if active else 0.20))
        )
        if self.pen() != pen:
            self.setPen(pen)
        if self.opacity() != opacity:
            self.setOpacity(opacity)
        current = self.source._state.production_progress.lifetime_produced.get(self.edge.source_resource_id, 0.0)
        label = (f"{current:g} / {self.edge.required_quantity:g}"
                 if current < self.edge.required_quantity and
                 (self._highlighted or (not self._trace_active and self.target.state_name == "current"))
                 else None)
        if getattr(self, "_label_signature", None) != label:
            self._label_signature = label
            self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        end = self.path().pointAtPercent(1.0)
        color = self.pen().color()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([end, end + QPointF(-10, -5), end + QPointF(-10, 5)]))
        current = self.source._state.production_progress.lifetime_produced.get(self.edge.source_resource_id, 0.0)
        if current < self.edge.required_quantity and (
            self._highlighted or (not self._trace_active and self.target.state_name == "current")
        ):
            label = f"{current:g} / {self.edge.required_quantity:g}"
            point = self.path().pointAtPercent(0.76)
            painter.setFont(QFont("Bahnschrift", 8, QFont.Weight.Bold))
            text_rect = QRectF(point.x() - 34, point.y() - 18, 68, 15)
            painter.fillRect(text_rect.adjusted(-3, -1, 3, 1), QColor(Theme.SURFACE_0))
            painter.setPen(color)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)


class UnlockTreeStageFilter(QFrame):
    changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("unlockTreeStageFilter")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []
        for label, value in STAGE_FILTERS:
            button = QPushButton(label)
            button.setObjectName("unlockTreeStageButton")
            button.setProperty("filterValue", value)
            button.setCheckable(True)
            button.setFixedWidth(101)
            button.clicked.connect(lambda checked=False, value=value: self.changed.emit(value) if checked else None)
            self.group.addButton(button)
            self.buttons.append(button)
            row.addWidget(button)

    def select_value(self, value: str | None) -> None:
        for button in self.buttons:
            if button.property("filterValue") == value:
                button.click()
                return


class UnlockTreeView(QFrame):
    def __init__(
        self,
        state: GameState,
        definitions: dict[str, CardDefinition],
        back: Callable[[], None],
    ) -> None:
        super().__init__()
        self.setObjectName("unlockTreeView")
        style_secondary(self)
        self.setStyleSheet(self.styleSheet() + self._stylesheet())
        self.state = state
        self.graph = build_unlock_tree_graph(definitions)
        self._stage_filter: str | None = None
        self._selected_resource_id: str | None = None
        self._persistent_focus_id: str | None = None
        self._search_match_id: str | None = None
        self._node_items: dict[str, UnlockTreeNodeItem] = {}
        self._edge_items: list[UnlockTreeEdgeItem] = []
        self._node_pool: dict[str, UnlockTreeNodeItem] = {}
        self._edge_pool = {}
        self._depth_items = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        back_button = secondary_action_button("Back", "unlockTreeBackButton")
        back_button.setProperty("primaryNavigation", True)
        back_button.clicked.connect(lambda checked=False: back())
        layout.addWidget(SecondaryViewHeader("UNLOCK TREE", "Production progression and unlock requirements", back_button))

        controls = QFrame()
        controls.setObjectName("unlockTreeControlDeck")
        control_row = QHBoxLayout(controls)
        control_row.setContentsMargins(10, 8, 10, 8)
        control_row.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("unlockTreeSearchInput")
        self.search.setPlaceholderText("Search unlocks...")
        self.search.setMaximumWidth(280)
        self.search.textChanged.connect(self._search_changed)
        control_row.addWidget(self.search)
        self.stage_filter = UnlockTreeStageFilter()
        self.stage_filter.changed.connect(self._stage_changed)
        control_row.addWidget(self.stage_filter)
        control_row.addStretch(1)
        layout.addWidget(controls)

        self.canvas = ZoomPanGraphicsView(object_prefix="unlockTree", minimum_zoom=0.72, maximum_zoom=1.75)
        self.canvas.setObjectName("unlockTreeCanvas")
        self.canvas.background_clicked.connect(self.clear_selection)
        layout.addWidget(self.canvas, 1)
        self._rebuild_scene()

    def _visible_resources(self) -> set[str]:
        if self._stage_filter is None:
            visible = set(self.graph.nodes)
        else:
            matches = {
                resource_id
                for resource_id, node in self.graph.nodes.items()
                if PLAYER_STAGE_LABELS[node.stage] == self._stage_filter
            }
            visible = set(matches)
            for resource_id in matches:
                visible.update(requirement.resource_id for requirement in self.graph.nodes[resource_id].requirements)
                visible.update(self.graph.nodes[resource_id].children)
        focus_id = self._search_match_id or self._persistent_focus_id
        if focus_id is not None:
            visible.add(focus_id)
            node = self.graph.nodes[focus_id]
            visible.update(requirement.resource_id for requirement in node.requirements)
            visible.update(node.children)
        return visible

    def _ordered_columns(self, visible: set[str]) -> dict[int, list[str]]:
        columns: dict[int, list[str]] = defaultdict(list)
        for resource_id in visible:
            columns[self.graph.nodes[resource_id].depth].append(resource_id)
        for depth in sorted(columns):
            if depth == 0:
                columns[depth].sort(key=lambda rid: (PLAYER_STAGE_LABELS[self.graph.nodes[rid].stage], self.graph.nodes[rid].name, rid))
                continue
            previous_rank = {rid: index for index, rid in enumerate(columns.get(depth - 1, ())) }
            columns[depth].sort(
                key=lambda rid: (
                    sum(previous_rank.get(req.resource_id, len(previous_rank)) for req in self.graph.nodes[rid].requirements)
                    / max(1, len(self.graph.nodes[rid].requirements)),
                    self.graph.nodes[rid].name,
                    rid,
                )
            )
        return columns

    def _rebuild_scene(self) -> None:
        visible = self._visible_resources()
        signature = (frozenset(visible), self._stage_filter)
        if getattr(self, "_layout_signature", None) == signature:
            self.refresh_state()
            self._apply_selection_emphasis()
            return
        self._layout_signature = signature
        scene = self.canvas.scene()
        for item in (*self._node_pool.values(), *self._edge_pool.values()):
            item.hide()
        for pair in self._depth_items.values():
            for item in pair: item.hide()
        self._node_items = {}
        self._edge_items = []
        columns = self._ordered_columns(visible)
        active_depths = sorted(columns)
        max_rows = max((min(MAX_ROWS_PER_LANE, len(column)) for column in columns.values()), default=1)
        scene_height = TOP_MARGIN + max_rows * (NODE_HEIGHT + ROW_GAP)
        band_starts: dict[int, float] = {}
        cursor_x = SIDE_MARGIN
        for depth in active_depths:
            lanes = max(1, (len(columns.get(depth, ())) + MAX_ROWS_PER_LANE - 1) // MAX_ROWS_PER_LANE)
            width = lanes * NODE_WIDTH + max(0, lanes - 1) * LANE_GAP
            band_starts[depth] = cursor_x
            cursor_x += width + COLUMN_GAP
        scene_width = cursor_x - COLUMN_GAP + SIDE_MARGIN

        for depth in active_depths:
            x = band_starts[depth]
            if depth not in self._depth_items:
                title = scene.addSimpleText(DEPTH_LABELS[depth] if depth < len(DEPTH_LABELS) else f"DEPTH {depth}")
                title.setBrush(QColor(Theme.TEXT))
                title.setFont(QFont("Bahnschrift", 13, QFont.Weight.Bold))
                divider = scene.addLine(0, 0, 0, 0, QPen(QColor(Theme.BORDER), 1, Qt.PenStyle.DashLine))
                divider.setZValue(-3)
                self._depth_items[depth] = (title, divider)
            title, divider = self._depth_items[depth]
            title.setPos(x, 12)
            divider.setLine(x - 10, 42, x - 10, scene_height)
            title.show(); divider.show()

        for depth, column in columns.items():
            for index, resource_id in enumerate(column):
                lane = index // MAX_ROWS_PER_LANE
                row = index % MAX_ROWS_PER_LANE
                x = band_starts[depth] + lane * (NODE_WIDTH + LANE_GAP)
                node = self.graph.nodes[resource_id]
                context = self._stage_filter is not None and PLAYER_STAGE_LABELS[node.stage] != self._stage_filter
                item = self._node_pool.get(resource_id)
                if item is None:
                    item = UnlockTreeNodeItem(self.state, self.graph, node, context=context)
                    item.selected.connect(self.select_resource)
                    scene.addItem(item)
                    self._node_pool[resource_id] = item
                if item._context != context:
                    item._context = context
                    item.update()
                item.refresh_state()
                item.show()
                item.setPos(x, TOP_MARGIN + row * (NODE_HEIGHT + ROW_GAP))
                self._node_items[resource_id] = item

        for edge in self.graph.edges:
            source = self._node_items.get(edge.source_resource_id)
            target = self._node_items.get(edge.target_resource_id)
            if source is None or target is None:
                continue
            key = (edge.source_resource_id, edge.target_resource_id)
            item = self._edge_pool.get(key)
            if item is None:
                item = UnlockTreeEdgeItem(edge, source, target)
                self._edge_pool[key] = item
                scene.addItem(item)
            else:
                item.refresh_geometry()
                item.refresh_state()
            item.show()
            self._edge_items.append(item)

        self.canvas.set_scene_content_rect(QRectF(0, 0, scene_width, scene_height), auto_fit=False)
        self._apply_selection_emphasis()
        QTimer.singleShot(0, self.focus_default_region)

    def refresh_state(self) -> None:
        progress = self.state.production_progress
        signature = (self.state.company.level, frozenset(progress.unlocked_production_ids),
                     tuple(progress.lifetime_produced.items()), self.state.research.total_earned,
                     frozenset(self.state.research.unlocked_node_ids), tuple(self.state.research.specializations.items()))
        if getattr(self, "_state_signature", None) == signature:
            return
        self._state_signature = signature
        for item in self._node_items.values():
            item.refresh_state()
        for edge in self._edge_items:
            edge.refresh_state()

    def select_resource(self, resource_id: str) -> None:
        if resource_id not in self.graph.nodes:
            return
        self._selected_resource_id = resource_id
        self._persistent_focus_id = resource_id
        if resource_id not in self._node_items:
            self._rebuild_scene()
            self._selected_resource_id = resource_id
            self._persistent_focus_id = resource_id
            self._apply_selection_emphasis()
        else:
            self._apply_selection_emphasis()

    def focus_resource(self, resource_id: str) -> None:
        """Open the resource's stage and retain it as the cross-stage focus."""
        node = self.graph.nodes.get(resource_id)
        if node is None:
            return
        self._selected_resource_id = resource_id
        self._persistent_focus_id = resource_id
        self._search_match_id = None
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self._stage_filter = PLAYER_STAGE_LABELS[node.stage]
        for button in self.stage_filter.buttons:
            button.setChecked(button.property("filterValue") == self._stage_filter)
        self._rebuild_scene()
        self._selected_resource_id = resource_id
        self._persistent_focus_id = resource_id
        self._apply_selection_emphasis()
        QTimer.singleShot(0, lambda: self._focus_node(resource_id))

    def clear_selection(self) -> None:
        self._selected_resource_id = None
        self._persistent_focus_id = None
        self._search_match_id = None
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self._apply_selection_emphasis()

    def focus_default_region(self) -> None:
        candidates = self._default_focus_resources()
        self._focus_region(candidates, preferred_zoom=0.86)

    def _default_focus_resources(self) -> tuple[str, ...]:
        visible = set(self._node_items)
        current = tuple(
            sorted(
                (resource_id for resource_id in visible if self._node_items[resource_id].state_name == "current"),
                key=lambda resource_id: (
                    self.graph.nodes[resource_id].depth,
                    self.graph.nodes[resource_id].name,
                    resource_id,
                ),
            )
        )
        if current:
            return current
        unlocked = {
            node.resource_id
            for node in self.graph.nodes.values()
            if node.production_id in self.state.production_progress.unlocked_production_ids
        }
        frontier = [
            resource_id
            for resource_id in visible
            if self._node_items[resource_id].state_name == "level_gated"
            and all(requirement.resource_id in unlocked for requirement in self.graph.nodes[resource_id].requirements)
        ]
        if frontier:
            next_level = min(self.graph.nodes[resource_id].required_level for resource_id in frontier)
            return tuple(sorted(
                (resource_id for resource_id in frontier if self.graph.nodes[resource_id].required_level == next_level),
                key=lambda resource_id: (self.graph.nodes[resource_id].depth, self.graph.nodes[resource_id].name, resource_id),
            ))
        starting = tuple(
            sorted(
                (resource_id for resource_id in visible if self.graph.nodes[resource_id].begins_unlocked),
                key=lambda resource_id: (self.graph.nodes[resource_id].name, resource_id),
            )
        )
        if starting:
            return starting
        return (min(visible, key=lambda resource_id: (self.graph.nodes[resource_id].depth, self.graph.nodes[resource_id].name, resource_id)),) if visible else ()

    def _focus_region(self, resource_ids: tuple[str, ...], *, preferred_zoom: float) -> None:
        items = [self._node_items[resource_id] for resource_id in resource_ids if resource_id in self._node_items]
        if not items:
            return
        bounds = items[0].sceneBoundingRect()
        for item in items[1:]:
            bounds = bounds.united(item.sceneBoundingRect())
        viewport = self.canvas.viewport().rect()
        fit_zoom = min(
            preferred_zoom,
            max(1.0, viewport.width() - 80.0) / max(1.0, bounds.width()),
            max(1.0, viewport.height() - 80.0) / max(1.0, bounds.height()),
        )
        self.canvas.set_zoom(max(self.canvas.minimum_zoom, fit_zoom))
        self.canvas.centerOn(bounds.center())

    def _apply_selection_emphasis(self) -> None:
        selected = self._persistent_focus_id
        signature = (selected, self._search_match_id, tuple(self._node_items))
        if getattr(self, "_emphasis_signature", None) == signature:
            return
        self._emphasis_signature = signature
        related: set[str] = set()
        if selected is not None:
            node = self.graph.nodes[selected]
            related.update(requirement.resource_id for requirement in node.requirements)
            related.update(node.children)
        for resource_id, item in self._node_items.items():
            relevant = resource_id == selected or resource_id in related
            item.set_emphasis(
                selected=resource_id == selected,
                related=resource_id in related,
                search_match=resource_id == self._search_match_id,
            )
            item.setOpacity(1.0 if selected is None or relevant else 0.22)
        for edge in self._edge_items:
            edge.set_trace_state(
                highlighted=selected in (edge.edge.source_resource_id, edge.edge.target_resource_id),
                trace_active=selected is not None,
            )

    def _stage_changed(self, stage: object) -> None:
        selected = self._selected_resource_id
        self._stage_filter = stage if isinstance(stage, str) else None
        self._rebuild_scene()
        self._selected_resource_id = selected
        self._persistent_focus_id = selected
        self._apply_selection_emphasis()
        if self._selected_resource_id is not None:
            QTimer.singleShot(0, lambda: self._focus_node(self._selected_resource_id))

    def _search_changed(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            previous = self._search_match_id
            self._search_match_id = None
            if self._selected_resource_id == previous:
                self._selected_resource_id = None
            if self._persistent_focus_id == previous:
                self._persistent_focus_id = None
            if previous is not None and previous not in self._visible_resources():
                self._rebuild_scene()
            else:
                self._apply_selection_emphasis()
            return
        matches = sorted(
            (node for node in self.graph.nodes.values() if query in node.name.lower()),
            key=lambda node: (not node.name.lower().startswith(query), node.name, node.resource_id),
        )
        if not matches:
            return
        match = matches[0].resource_id
        rebuild = match not in self._node_items
        self._search_match_id = match
        self._selected_resource_id = match
        self._persistent_focus_id = match
        if rebuild:
            self._rebuild_scene()
        else:
            self._apply_selection_emphasis()
        QTimer.singleShot(0, lambda resource_id=match: self._focus_node(resource_id))

    def _focus_node(self, resource_id: str) -> None:
        item = self._node_items.get(resource_id)
        if item is None:
            return
        current_zoom = self.canvas.zoom_factor
        target_zoom = current_zoom if 0.9 <= current_zoom <= 1.0 else 0.95
        self.canvas.set_zoom(target_zoom)
        self.canvas.centerOn(item.sceneBoundingRect().center())

    @staticmethod
    def _stylesheet() -> str:
        return f"""
            QGraphicsView#unlockTreeCanvas {{ background: {Theme.SURFACE_1}; border: 1px solid {Theme.BORDER_STRONG}; border-radius: 6px; }}
            QFrame#unlockTreeControlDeck {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.GUIDE_HEADER_START}, stop:0.58 {Theme.GUIDE_HEADER_MID}, stop:1 {Theme.GUIDE_HEADER_END}); border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 3px solid {Theme.SURFACE_0}; border-radius: 7px; }}
            QPushButton#unlockTreeStageButton {{ background: {Theme.SURFACE_3}; color: {Theme.MUTED}; border: 1px solid {Theme.BORDER_STRONG}; border-bottom: 2px solid {Theme.SURFACE_0}; border-radius: 3px; padding: 7px 7px; font-family: {Theme.INDUSTRIAL_FONT}; font-size: 12px; font-weight: 900; }}
            QPushButton#unlockTreeStageButton:hover {{ background: {Theme.SURFACE_HOVER}; color: {Theme.TEXT}; }}
            QPushButton#unlockTreeStageButton:checked {{ background: {Theme.SAFETY_YELLOW}; color: {Theme.SURFACE_0}; border-color: {Theme.SURFACE_0}; }}
            QPushButton#unlockTreeBackButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff06f, stop:0.42 {Theme.SAFETY_YELLOW}, stop:1 #d39b00); color: {Theme.SURFACE_0}; border: 1px solid #fff2a3; border-bottom: 3px solid #8c6500; }}
        """
