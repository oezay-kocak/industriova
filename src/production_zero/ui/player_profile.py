"""One embedded, read-only company profile for every player entry point."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QWidget

from production_zero.ui.inventory_history_chart import InventoryHistoryChart
from production_zero.ui.consortium_view import EmbeddedConsortiumDialog
from production_zero.ui.game_ui import Accent, GamePanel, MaterialLevel
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.pz_controls import RaisedPZButton
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.theme import Theme
from production_zero.ui.material_frame import RecessedPanel


def text(value, name="profileText"):
    label = QLabel(value)
    label.setObjectName(name)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


class PlayerProfileView(EmbeddedConsortiumDialog):
    def __init__(self, profile, resources, parent):
        super().__init__(parent, "playerProfileOverlay", 900)
        self.profile = profile
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.panel.setObjectName("playerProfileChassis")
        self.panel.setMaximumHeight(700)
        self.setStyleSheet(f"""
            QFrame#playerProfileOverlay {{ background: rgba(6,13,16,198); }}
            QFrame#playerProfileChassis {{ background: {Theme.SECONDARY_SHELL_GRADIENT}; border: 2px solid {Theme.BORDER_STRONG}; border-radius: 10px; }}
            QLabel#profileText {{ color: {Theme.TEXT}; background: transparent; font-size: 13px; }}
            QLabel#profileValue {{ color: {Theme.TEXT}; background: transparent; font-size: 24px; font-weight: 900; }}
            QLabel#profileSource {{ color: #111417; background: transparent; font-size: 11px; font-weight: 700; padding-left: 2px; }}
            QFrame#gamePanel, QFrame#profileHeader {{ background: transparent; border: 0; }}
            QScrollArea#profileScroll, QWidget#profileBody {{ background: transparent; border: 0; }}
        """)
        layout = self.panel_layout
        header = MainTabHeader(object_name="profileHeader", title="PLAYER PROFILE",
                               subtitle=f"LEVEL {profile.level} · {profile.title.upper()}",
                               title_object_name="leaderboardHeroTitle", subtitle_object_name="leaderboardHeroSubtitle", accent=Accent.NEUTRAL)
        close = RaisedPZButton("CLOSE", variant="destructive")
        close.setFixedSize(88, 32)
        close.clicked.connect(self.close)
        header.add_status_module(close)
        layout.addWidget(header)
        layout.addWidget(text(profile.source, "profileSource"))
        scroll = QScrollArea()
        scroll.setObjectName("profileScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("profileBody")
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        identity = RecessedPanel("COMPANY", level=MaterialLevel.INSET)
        identity.setMinimumHeight(86)
        identity.layout().setContentsMargins(16, 10, 16, 10)
        identity.content_layout.addWidget(text(profile.name, "profileValue"))
        affiliation = profile.consortium or "Consortium membership unavailable"
        if profile.role:
            affiliation += " · " + profile.role.replace("_", " ").upper()
        identity.content_layout.addWidget(text(affiliation))
        grid.addWidget(identity, 0, 0, 1, 2)
        for column, (label, value) in enumerate((("LIFETIME EARNINGS", None if profile.earnings is None else f"${profile.earnings:,.0f}"),
                                                ("LIFETIME PRODUCTION", None if profile.lifetime_production is None else f"{profile.lifetime_production:,.0f} units"))):
            panel = RecessedPanel(label, level=MaterialLevel.INSET)
            panel.setMinimumHeight(82)
            panel.content_layout.addWidget(text(value or "Unavailable", "profileValue"))
            grid.addWidget(panel, 1, column)
        highlight = RecessedPanel("PRODUCTION HIGHLIGHT", level=MaterialLevel.INSET, accent=Accent.NEUTRAL)
        if profile.resource_id:
            resource = resources.get(profile.resource_id)
            row = QHBoxLayout()
            row.addWidget(ResourceIconWidget(profile.resource_id, size=64))
            row.addWidget(text(resource.name if resource else profile.resource_id.replace("_", " "), "profileValue"), 1)
            highlight.content_layout.addLayout(row)
            highlight.content_layout.addWidget(text(f"{profile.resource_amount:,.0f} units produced · lifetime leader"))
        else:
            highlight.content_layout.addWidget(text("No production recorded yet" if profile.lifetime_production == 0 else "Production statistics unavailable"))
        if profile.contribution is not None:
            highlight.content_layout.addWidget(text(f"CONSORTIUM CONTRIBUTION  {profile.contribution:,.0f}"))
        grid.addWidget(highlight, 2, 0)
        graph = RecessedPanel("INVENTORY HISTORY", level=MaterialLevel.INSET)
        if profile.stock_resource_id:
            resource = resources.get(profile.stock_resource_id)
            stock_row = QHBoxLayout()
            stock_row.addWidget(ResourceIconWidget(profile.stock_resource_id, size=32))
            stock_name = text(resource.name if resource else profile.stock_resource_id.replace("_", " "))
            stock_name.setStyleSheet("color: #edf6f2; font-size: 13px; font-weight: 800; background: transparent;")
            stock_row.addWidget(stock_name, 1)
            quantity = text(f"{profile.stock_amount:,.0f} UNITS")
            quantity.setStyleSheet("color: #ffd21f; font-size: 13px; font-weight: 900; background: transparent;")
            stock_row.addWidget(quantity)
            graph.content_layout.addLayout(stock_row)
            graph.content_layout.addWidget(InventoryHistoryChart(profile.inventory_history, profile.inventory_history_now, profile.stock_amount), 1)
        else:
            graph.content_layout.addWidget(text("Global storage is empty." if profile.stock_amount == 0 else "Inventory data unavailable for this company."))
        grid.addWidget(graph, 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        self.panel.setFixedHeight(min(700, parent.window().height() - 48))

    def eventFilter(self, watched, event):
        result = super().eventFilter(watched, event)
        if hasattr(self, "panel"):
            self.panel.setFixedWidth(min(900, self.parentWidget().width() - 48))
            self.panel.setFixedHeight(min(700, self.parentWidget().height() - 48))
        return result
