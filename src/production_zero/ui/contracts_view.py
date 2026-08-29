from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from production_zero.core.commands import AcceptContract, CommandBus, DeliverAvailableToContract
from production_zero.core.contracts import CONTRACT_KIND_LABELS, CONTRACT_KINDS, DAILY, REGULAR, WEEKLY, initialize_contracts, seconds_until_contract_reset
from production_zero.core.definitions import CardDefinition
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.game_ui import Accent, MaterialLevel, draw_game_panel, draw_track_surface
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.widget_lifecycle import clear_layout_safely


CONTRACT_SECTION_TITLES = {
    REGULAR: "REGULAR CONTRACTS",
    DAILY: "DAILY CONTRACTS",
    WEEKLY: "WEEKLY CONTRACTS",
}


class ContractsHeader(QFrame):
    def __init__(self, state: GameState) -> None:
        super().__init__()
        self._state = state
        self.setObjectName("contractsHeader")
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 25, 32, 24)
        layout.setSpacing(18)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(1)
        title = QLabel("CONTRACTS")
        title.setObjectName("contractsHeroTitle")
        subtitle = QLabel("DELIVERY / OBJECTIVES")
        subtitle.setObjectName("contractsHeroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column, 1)

        self._active_value = self._metric("ACTIVE", "0")
        self._daily_value = self._metric("DAILY RESET", "")
        self._weekly_value = self._metric("WEEKLY RESET", "")
        layout.addWidget(self._active_value[0])
        layout.addWidget(self._daily_value[0])
        layout.addWidget(self._weekly_value[0])
        self.refresh()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=16)
        draw_track_surface(painter, rect.adjusted(14, 13, -14, -13), accent=Accent.SUCCESS, radius=11)
        painter.end()
        super().paintEvent(event)

    def refresh(self) -> None:
        active_count = sum(1 for contract in self._state.contracts.active.values() if contract.status == "active")
        self._active_value[1].setText(str(active_count))
        self._daily_value[1].setText(self._reset_text(DAILY))
        self._weekly_value[1].setText(self._reset_text(WEEKLY))

    def _metric(self, label_text: str, value_text: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("contractsHeaderMetric")
        tile.setMinimumSize(142, 58)
        tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        label = QLabel(label_text)
        label.setObjectName("contractsMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("contractsMetricValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return tile, value

    def _reset_text(self, kind: str) -> str:
        seconds = seconds_until_contract_reset(self._state, kind) or 0.0
        total_minutes = int(seconds // 60)
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60
        if days > 0:
            return f"{days}D {hours}H"
        if hours > 0:
            return f"{hours}H {minutes}M"
        return f"{minutes}M"


class ContractsView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        resources: dict[str, ResourceDefinition],
        on_state_changed=None,
    ) -> None:
        super().__init__()
        self._state = state
        self._command_bus = command_bus
        self._definitions = definitions
        self._resources = resources
        self._on_state_changed = on_state_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._header = ContractsHeader(state)
        layout.addWidget(self._header)

        scroll = QScrollArea()
        scroll.setObjectName("contractsBoardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setObjectName("contractsBoard")
        self._content_layout = QHBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        scroll.setWidget(self._content)
        layout.addWidget(scroll, 1)
        self.refresh()

    def refresh(self) -> None:
        initialize_contracts(self._state)
        self._header.refresh()
        self._clear_layout(self._content_layout)

        for kind in CONTRACT_KINDS:
            self._content_layout.addWidget(self._build_kind_panel(kind))

    def _build_kind_panel(self, kind: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractPanel")
        panel.setProperty("kind", kind)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel(CONTRACT_SECTION_TITLES[kind])
        title.setObjectName("contractSectionTitle")
        subtitle = QLabel(self._section_subtitle(kind))
        subtitle.setObjectName("contractSectionSubtitle")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)
        layout.addLayout(header)

        for offer in self._state.contracts.offers.get(kind, []):
            layout.addWidget(self._build_offer_panel(kind, offer.contract_id))
        layout.addStretch(1)
        return panel

    def _build_offer_panel(self, kind: str, contract_id: str) -> QFrame:
        offer = next(offer for offer in self._state.contracts.offers[kind] if offer.contract_id == contract_id)
        active = self._state.contracts.active.get(kind)
        card_state = self._card_state(kind, contract_id)
        delivered = active.delivered if active is not None and active.offer.contract_id == contract_id else {}
        panel = QFrame()
        panel.setObjectName("contractCard")
        panel.setProperty("state", card_state.lower())
        panel.setProperty("kind", kind)
        panel.setProperty("contractId", contract_id)
        panel.setFixedHeight(168)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)
        title = QLabel(offer.name)
        title.setObjectName("contractCardTitle")
        title.setWordWrap(True)
        title.setMaximumHeight(30)
        state = QLabel(card_state)
        state.setObjectName("contractCardStatus")
        state.setProperty("state", card_state.lower())
        top.addWidget(title, 1)
        top.addWidget(state)
        layout.addLayout(top)

        layout.addWidget(self._requirements_panel(offer.requirements, delivered))
        layout.addWidget(self._rewards_panel(kind, offer.reward_cash, offer.reward_xp))

        footer = QFrame()
        footer.setObjectName("contractActionFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(8)
        if card_state == "ACTIVE":
            deliver = QPushButton("DELIVER AVAILABLE")
            deliver.setObjectName("deliverContractButton")
            deliver.setEnabled(active is not None and active.status == "active")
            deliver.clicked.connect(lambda checked=False, contract_kind=kind: self._deliver_available(contract_kind))
            footer_layout.addWidget(deliver)
        elif card_state == "AVAILABLE":
            button = QPushButton("ACCEPT CONTRACT")
            button.setObjectName("acceptContractButton")
            button.setEnabled(True)
            button.clicked.connect(lambda checked=False, contract_kind=kind, cid=contract_id: self._accept(contract_kind, cid))
            footer_layout.addWidget(button)
        elif card_state == "COMPLETED":
            button = QPushButton("CLAIM REWARD")
            button.setObjectName("claimContractButton")
            button.setEnabled(False)
            footer_layout.addWidget(button)
        else:
            button = QPushButton("ACCEPT CONTRACT")
            button.setObjectName("acceptContractButton")
            button.setEnabled(False)
            footer_layout.addWidget(button)
        layout.addWidget(footer)
        return panel

    def _requirements_panel(self, requirements: dict[str, float], delivered: dict[str, float]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractRequirements")
        panel.setFixedHeight(42)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title = QLabel("REQUIREMENTS")
        title.setObjectName("contractBlockTitle")
        layout.addWidget(title)

        inline = QFrame()
        inline.setObjectName("contractRequirementsInline")
        inline.setFixedHeight(20)
        inline.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        requirements_row = QHBoxLayout(inline)
        requirements_row.setContentsMargins(0, 0, 0, 0)
        requirements_row.setSpacing(6)
        for resource_id, required in requirements.items():
            name = self._resources[resource_id].name if resource_id in self._resources else resource_id.replace("_", " ").title()
            amount = min(required, delivered.get(resource_id, 0.0))
            row = QFrame()
            row.setObjectName("contractRequirementRow")
            row.setProperty("fulfilled", amount >= required)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            resource = self._resources.get(resource_id)
            icon = ResourceIconWidget(
                resource_id,
                (resource.icon_key if resource is not None and resource.icon_key else resource_icon_key(resource_id)),
                (resource.accent_key if resource is not None and resource.accent_key else resource_accent_key(resource_id)),
                size=18,
            )
            icon.setObjectName("resourceIcon")
            icon.setFixedSize(19, 19)
            label = QLabel(name.upper())
            label.setObjectName("contractRequirementLabel")
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            amount_label = QLabel(f"{amount:,.0f} / {required:,.0f}")
            amount_label.setObjectName("contractRequirementAmount")
            amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount_label.setMinimumWidth(58)
            amount_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            amount_label.setProperty("deliveredAmount", amount)
            amount_label.setProperty("requiredAmount", required)
            amount_label.setProperty("progressPermille", int((amount / max(1.0, required)) * 1000))
            if amount >= required:
                amount_label.setProperty("fulfilled", True)
            row_layout.addWidget(icon)
            row_layout.addWidget(label, 1)
            row_layout.addWidget(amount_label)
            requirements_row.addWidget(row, 1)
        layout.addWidget(inline)
        return panel

    def _rewards_panel(self, kind: str, cash: float, xp: float) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractRewards")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        title = QLabel("REWARDS")
        title.setObjectName("contractBlockTitle")
        layout.addWidget(title)
        rewards = [("cash", "$", f"${cash:,.0f}"), ("xp", "XP", f"{xp:,.0f} XP")]
        if kind == DAILY:
            rewards.append(("pack", "PACK", "Daily Mini Pack"))
        elif kind == WEEKLY:
            rewards.append(("pack", "PACK", "Full Pack"))
        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(5)
        for reward_kind, icon_text, reward in rewards:
            chip = QFrame()
            chip.setObjectName("contractRewardChip")
            chip.setProperty("rewardKind", reward_kind)
            chip.setProperty("contractKind", kind)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(7, 3, 7, 3)
            chip_layout.setSpacing(5)
            icon = QLabel(icon_text)
            icon.setObjectName("contractRewardIcon")
            label = QLabel(reward)
            label.setObjectName("contractRewardLabel")
            chip_layout.addWidget(icon)
            chip_layout.addWidget(label)
            chips.addWidget(chip)
        chips.addStretch(1)
        layout.addLayout(chips)
        return panel

    def _card_state(self, kind: str, contract_id: str) -> str:
        active = self._state.contracts.active.get(kind)
        if active is None:
            return "AVAILABLE"
        if active.offer.contract_id != contract_id:
            return "DISABLED"
        if active.status == "completed":
            return "COMPLETED"
        if active.status == "expired":
            return "EXPIRED"
        return "ACTIVE"

    def _accept(self, kind: str, contract_id: str) -> None:
        self._command_bus.dispatch(AcceptContract(kind, contract_id))
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _deliver_available(self, kind: str) -> None:
        self._command_bus.dispatch(DeliverAvailableToContract(kind, self._definitions))
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _requirements_text(self, requirements: dict[str, float], delivered: dict[str, float]) -> str:
        lines = []
        for resource_id, required in requirements.items():
            name = self._resources[resource_id].name if resource_id in self._resources else resource_id.replace("_", " ").title()
            amount = delivered.get(resource_id, 0.0)
            lines.append(f"{name} {amount:,.0f} / {required:,.0f}")
        return "\n".join(lines)

    def _section_subtitle(self, kind: str) -> str:
        if kind == REGULAR:
            return "Repeatable · No expiration"
        remaining = seconds_until_contract_reset(self._state, kind)
        return f"Resets in {self._format_duration(remaining or 0.0)}"

    def _format_duration(self, seconds: float) -> str:
        total_minutes = int(seconds // 60)
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
