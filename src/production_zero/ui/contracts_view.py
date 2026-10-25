from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from production_zero.core.commands import (AcceptContract, CommandBus, CancelContract,
    SetContractPriority, SetRegularContractAutoRepeat)
from production_zero.core.contracts import CONTRACT_KIND_LABELS, CONTRACT_KINDS, CONTRACT_REQUIREMENT_COUNTS, DAILY, REGULAR, WEEKLY, contract_requirements_for_products, initialize_contracts, seconds_until_contract_reset
from production_zero.core.definitions import CardDefinition
from production_zero.core.production_values import ContractProductOption, eligible_contract_products
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.contract_product import ContractProductButton
from production_zero.ui.game_ui import Accent
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.resource_tiles import RESOURCE_TILE_WIDTH, ResourceSelectionGridHost, ResourceSelectionTile, configure_resource_selection_grid_host, configure_resource_selection_scroll
from production_zero.ui.secondary_views import ResourceBrowser, SecondaryViewHeader, style_secondary
from production_zero.ui.widget_lifecycle import clear_layout_safely
from production_zero.ui.theme import Theme
from production_zero.ui.pz_controls import RaisedPZButton


CONTRACT_SECTION_TITLES = {
    REGULAR: "REGULAR CONTRACTS",
    DAILY: "DAILY CONTRACTS",
    WEEKLY: "WEEKLY CONTRACTS",
}


class ContractProductTile(ResourceSelectionTile):
    selected = Signal(str)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.selected.emit(str(self.property("resourceId")))
        super().mouseReleaseEvent(event)


class ContractProductGridHost(ResourceSelectionGridHost):
    resized = Signal()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.resized.emit()


class ContractProductPicker(QFrame):
    product_selected = Signal(str)
    back_requested = Signal()

    def __init__(self, products, resources, unavailable: set[str], current_name: str, parent=None, *, purpose_label="CONTRACT ELIGIBLE") -> None:
        super().__init__(parent)
        self.setObjectName("contractProductPicker")
        style_secondary(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        current = QLabel(f"Current: {current_name or 'Not selected'}")
        current.setObjectName("productionCurrentLabel")
        back = QPushButton("Back")
        back.setObjectName("contractProductPickerBack")
        back.clicked.connect(self.back_requested.emit)
        title = "SELECT CONTRACT PRODUCT" if purpose_label == "CONTRACT ELIGIBLE" else "SELECT PRODUCT"
        layout.addWidget(SecondaryViewHeader(title, current, back))
        self.search = QLineEdit()
        self.search.setObjectName("contractProductSearch")
        self.search.setPlaceholderText("SEARCH ELIGIBLE PRODUCTS")
        scroll = QScrollArea()
        scroll.setObjectName("contractProductScroll")
        scroll.setWidgetResizable(True)
        configure_resource_selection_scroll(scroll)
        host = ContractProductGridHost()
        host.setObjectName("contractProductGrid")
        configure_resource_selection_grid_host(host)
        grid = QGridLayout(host)
        grid.setSpacing(10)
        self._grid = grid
        self._grid_host = host
        self._columns = 0
        self.tiles: list[ContractProductTile] = []
        self._products = tuple(products)
        self._resources = resources
        self._unavailable = set(unavailable)
        self._purpose_label = purpose_label
        self._lazy = purpose_label == "CUMULATIVE PRODUCTION" and len(self._products) > 128
        self._tiles_by_id = {}
        self._laying_out = False
        self._layout_key = None
        if not self._lazy:
            for product in self._products:
                self._tile_for(product)
        self._layout_tiles()
        scroll.setWidget(host)
        self._scroll = scroll
        if self._lazy:
            scroll.verticalScrollBar().valueChanged.connect(lambda *_: self._layout_tiles())
        host.resized.connect(self._layout_tiles)
        category = QComboBox()
        category.setObjectName("contractProductCategoryFilter")
        category.addItem("ALL")
        layout.addWidget(ResourceBrowser(self.search, category, scroll, {}), 1)
        self.search.textChanged.connect(self._filter)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout_tiles()

    def _tile_for(self, product):
        tile = self._tiles_by_id.get(product.resource_id)
        if tile is not None:
            return tile
        resource = self._resources.get(product.resource_id)
        tile = ContractProductTile(
            resource_id=product.resource_id, title=product.name,
            subtitle=resource.category if resource else "PRODUCTION RESOURCE",
            icon_key=resource.icon_key if resource and resource.icon_key else resource_icon_key(product.resource_id),
            accent_key=resource.accent_key if resource and resource.accent_key else resource_accent_key(product.resource_id),
            detail=self._purpose_label,
            status="ALREADY SELECTED" if product.resource_id in self._unavailable else "")
        tile.setProperty("unavailable", product.resource_id in self._unavailable)
        tile.setProperty("searchName", product.name.lower())
        tile.setEnabled(product.resource_id not in self._unavailable)
        tile.selected.connect(self._choose)
        self.tiles.append(tile)
        self._tiles_by_id[product.resource_id] = tile
        return tile

    def _layout_tiles(self, *, force=False) -> None:
        if self._laying_out:
            return
        width = self._grid_host.width() or self.width()
        columns = max(2, min(8, width // (RESOURCE_TILE_WIDTH + self._grid.horizontalSpacing())))
        scroll = getattr(self, "_scroll", None)
        offset = scroll.verticalScrollBar().value() if scroll else 0
        viewport_height = scroll.viewport().height() if scroll else 650
        # Same fixed tile/grid geometry; nonvisible cells retain their size.
        row_height = 188 + self._grid.verticalSpacing()
        first = max(0, offset // row_height - 1) if self._lazy else 0
        last = (offset + viewport_height) // row_height + 2 if self._lazy else len(self._products)
        query = self.search.text().strip().lower()
        key = (columns, query, first, last)
        if key == self._layout_key and not force:
            return
        self._laying_out = True
        try:
            self._layout_key = key
            self._columns = columns
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item.widget() is not None:
                    item.widget().hide()
            for row in range(self._grid.rowCount() + 1):
                self._grid.setRowStretch(row, 0)
            for column in range(self._grid.columnCount() + 1):
                self._grid.setColumnStretch(column, 0)
            products = [p for p in self._products if not query or query in p.name.lower() or query in p.resource_id.replace("_", " ").lower()]
            for index, product in enumerate(products):
                row, column = divmod(index, columns)
                if first <= row <= last:
                    tile = self._tile_for(product)
                    self._grid.addWidget(tile, row, column)
                    tile.show()
                else:
                    self._grid.addItem(QSpacerItem(RESOURCE_TILE_WIDTH, 188, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed), row, column)
            self._grid.setRowStretch((len(products) + columns - 1) // columns, 1)
            self._grid.setColumnStretch(columns, 1)
        finally:
            self._laying_out = False

    def _matches_query(self, tile, text):
        query = text.strip().lower()
        return not query or query in str(tile.property("resourceId")).replace("_", " ").lower() or query in str(tile.property("searchName"))

    def _filter(self, text: str) -> None:
        if self._lazy:
            self._scroll.verticalScrollBar().setValue(0)
        for tile in self.tiles:
            tile.setVisible(self._matches_query(tile, text))
        self._layout_tiles(force=True)

    def _choose(self, resource_id: str) -> None:
        self.product_selected.emit(resource_id)


class ContractsHeader(MainTabHeader):
    def __init__(self, state: GameState) -> None:
        super().__init__(
            object_name="contractsHeader",
            title="CONTRACTS",
            subtitle="DELIVERY / OBJECTIVES",
            title_object_name="contractsHeroTitle",
            subtitle_object_name="contractsHeroSubtitle",
            accent=Accent.SUCCESS,
        )
        self._state = state
        self._daily_value = self._metric("DAILY RESET", "")
        self._weekly_value = self._metric("WEEKLY RESET", "")
        self.add_status_module(self._daily_value[0])
        self.add_status_module(self._weekly_value[0])
        self.refresh()

    def refresh(self) -> None:
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
        self.setObjectName("contractsView")
        self._state = state
        self._command_bus = command_bus
        self._definitions = definitions
        self._resources = resources
        self._on_state_changed = on_state_changed
        self._content_signature: tuple | None = None
        self._content_rebuild_count = 0
        self._selected_products: dict[tuple[str, str], list[str | None]] = {}
        self._selection_controls: dict[tuple[str, str], dict] = {}
        self._quoted_rewards: dict[tuple[str,str],tuple[float,float]] = {}
        self._eligible_product_cache: dict[float, tuple[ContractProductOption, ...]] = {}
        self._product_picker: ContractProductPicker | None = None
        self._auto_repeat_requested = False

        layout = QVBoxLayout(self)
        self._root_layout = layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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
        self._content_layout.setContentsMargins(8, 6, 8, 6)
        self._content_layout.setSpacing(8)
        scroll.setWidget(self._content)
        self._board_scroll = scroll
        layout.addWidget(scroll, 1)
        self.refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_board()

    def _fit_board(self) -> None:
        compact = self.height() < 725
        self._header.setFixedHeight(84 if compact else 116)
        self._header.header_layout.setContentsMargins(24, 10 if compact else 25, 24, 10 if compact else 24)
        self._content_layout.setContentsMargins(8, 2 if compact else 6, 8, 2 if compact else 6)
        for panel in self._content.findChildren(QFrame, "contractPanel"):
            panel.layout().setContentsMargins(10, 4 if compact else 8, 10, 4 if compact else 8)
            panel.layout().setSpacing(4 if compact else 8)
        for card in self._content.findChildren(QFrame, "contractCard"):
            card.setMinimumHeight(270)
            card.setMaximumHeight(16777215)

    def refresh(self) -> None:
        initialize_contracts(self._state, self._definitions)
        self._header.refresh()
        self._update_active_contract_widgets()
        self._update_contract_preferences()
        self._eligible_product_cache = {}
        signature = self._build_content_signature()
        if signature == self._content_signature:
            return
        self._content_signature = signature
        self._content_rebuild_count += 1
        self._selection_controls = {}
        self._clear_layout(self._content_layout)

        for kind in CONTRACT_KINDS:
            self._content_layout.addWidget(self._build_kind_panel(kind))
        self._content_signature = self._build_content_signature()
        self._fit_board()

    def show_frontscreen(self):
        self._close_product_picker()
        if any(any(value is not None for value in values) for values in self._selected_products.values()):
            self._selected_products.clear()
            self._content_signature = None

    def reset_for_state_change(self) -> None:
        self._close_product_picker()
        self._selected_products.clear()
        self._auto_repeat_requested = False
        self._selection_controls.clear()
        self._quoted_rewards.clear()
        self._eligible_product_cache.clear()
        self._content_signature = None
        self.refresh()

    def _build_content_signature(self) -> tuple:
        sections = []
        for kind in CONTRACT_KINDS:
            active = self._state.contracts.active.get(kind)
            active_signature = None
            if active is not None:
                active_signature = (
                    active.offer.contract_id,
                    active.status,
                    active.offer.reward_cash,
                )
            offers = tuple(
                (
                    offer.contract_id,
                    offer.kind,
                    offer.name,
                    tuple(sorted((resource_id, round(amount, 4)) for resource_id, amount in offer.requirements.items())),
                    round(offer.reward_cash, 4),
                    round(offer.reward_xp, 4),
                    offer.period_index,
                    round(offer.expires_at, 4) if offer.expires_at is not None else None,
                    round(offer.production_value_budget, 4) if offer.production_value_budget is not None else None,
                    offer.selected_resource_id,
                    tuple(self._selected_products.get((kind, offer.contract_id), ())),
                    tuple(
                        (product.resource_id, round(product.required_amount, 4))
                        for product in self._eligible_products_for_offer(offer)
                    ),
                    self._card_state(kind, offer.contract_id),
                )
                for offer in self._state.contracts.offers.get(kind, [])
            )
            sections.append((kind, active_signature, offers))
        return (self._state.market.market_tick, self._state.company.level, frozenset(self._state.research.unlocked_node_ids), tuple(sorted(self._state.research.specializations.items())), *sections)

    def _update_active_contract_widgets(self) -> None:
        for kind, active in self._state.contracts.active.items():
            card = next(
                (
                    card for card in self._content.findChildren(QFrame, "contractCard")
                    if card.property("kind") == kind
                    and card.property("contractId") == active.offer.contract_id
                    and card.property("state") == "active"
                ),
                None,
            )
            if card is None:
                continue
            for row in card.findChildren(QFrame, "contractRequirementRow"):
                resource_id = row.property("resourceId")
                required = active.offer.requirements.get(resource_id, 0.0)
                delivered = min(required, active.delivered.get(resource_id, 0.0))
                row.setProperty("fulfilled", delivered >= required)
                amount_label = row.findChild(QLabel, "contractRequirementAmount")
                if amount_label is not None:
                    from production_zero.ui.contract_product import contract_quantity_text
                    amount_label.setText(f"{contract_quantity_text(delivered)} / {contract_quantity_text(required)}")
                    amount_label.setToolTip(f"{delivered:,.2f} / {required:,.2f}")
                    amount_label.setProperty("deliveredAmount", delivered)
                    amount_label.setProperty("fulfilled", delivered >= required)
                    amount_label.setProperty("progressPermille", round(1000 * delivered / required) if required else 0)
                row.style().unpolish(row)
                row.style().polish(row)
                row.update()

    def _build_kind_panel(self, kind: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractPanel")
        panel.setProperty("kind", kind)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel(CONTRACT_SECTION_TITLES[kind])
        title.setObjectName("contractSectionTitle")
        subtitle = QLabel(self._section_subtitle(kind))
        subtitle.setObjectName("contractSectionSubtitle")
        title.setMaximumHeight(22)
        subtitle.setMaximumHeight(20)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)
        priority = QPushButton()
        priority.setObjectName('contractPriorityButton')
        priority.setProperty('kind', kind)
        priority.setFixedSize(102, 28)
        priority.setStyleSheet('font-size: 11px; font-weight: 900;')
        priority.setToolTip('Priority 2 first, then Priority 1, then Even. Equal priorities share cargo equally. Cargo already in transit keeps its destination.')
        priority.clicked.connect(lambda checked=False, k=kind: self._cycle_priority(k))
        self._set_priority_button(priority, kind)
        if kind == REGULAR:
            offer = next(iter(self._state.contracts.offers.get(REGULAR, ())), None)
            header.addWidget(self._build_regular_auto_button(offer.contract_id if offer else None))
        header.addWidget(priority)
        layout.addLayout(header)

        for offer in self._state.contracts.offers.get(kind, []):
            layout.addWidget(self._build_offer_panel(kind, offer.contract_id), 1)
        return panel

    def _build_offer_panel(self, kind: str, contract_id: str) -> QFrame:
        offer = next(offer for offer in self._state.contracts.offers[kind] if offer.contract_id == contract_id)
        active = self._state.contracts.active.get(kind)
        display_offer = active.offer if active is not None and active.offer.contract_id == contract_id else offer
        card_state = self._card_state(kind, contract_id)
        delivered = active.delivered if active is not None and active.offer.contract_id == contract_id else {}
        panel = QFrame()
        panel.setObjectName("contractCard")
        panel.setProperty("state", card_state.lower())
        panel.setProperty("kind", kind)
        panel.setProperty("contractId", contract_id)
        panel.setMinimumHeight(270)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(3)

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

        if kind == REGULAR:
            self._add_regular_auto_status(layout)

        if not display_offer.requirements and display_offer.production_value_budget is not None:
            selection = self._product_selection_panel(kind, offer)
            selection.setEnabled(card_state == "AVAILABLE")
            layout.addWidget(selection, 1)
        else:
            layout.addWidget(self._requirements_panel(display_offer.requirements, delivered), 1)
        quoted_xp = display_offer.reward_xp
        cash = display_offer.reward_cash
        if card_state == "AVAILABLE":
            from production_zero.core.modifiers import contract_cash_quote
            requirements = dict(display_offer.requirements)
            if not requirements:
                selected = self._complete_selection(kind, offer)
                if selected is not None:
                    requirements = contract_requirements_for_products(
                        self._state, offer, self._definitions, selected
                    )
            from production_zero.core.contracts import contract_reward_quote
            cash, quoted_xp = contract_reward_quote(self._state, offer, self._definitions, requirements) if requirements else (0., 0.)
        rewards = self._rewards_panel(kind, cash, quoted_xp if card_state == "AVAILABLE" else display_offer.reward_xp)
        self._quoted_rewards[kind,contract_id] = (cash,quoted_xp if card_state == "AVAILABLE" else display_offer.reward_xp)
        rewards.setToolTip("Daily +20% / Weekly +40% over fixed goods value with existing Research. Accepted cash/XP/RP stay fixed. Quantities assume resumed powered chains, clear warehouse space and assigned Freight.")
        layout.addWidget(rewards, 1)

        footer = QFrame()
        footer.setObjectName("contractActionFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(8)
        if card_state == "ACTIVE":
            button = QPushButton("CANCEL")
            button.setObjectName("cancelContractButton")
            button.setEnabled(active is not None and active.status == "active")
            button.clicked.connect(lambda checked=False, contract_kind=kind: self._cancel(contract_kind))
            footer_layout.addWidget(button)
        elif card_state == "AVAILABLE":
            button = QPushButton("ACCEPT CONTRACT")
            button.setObjectName("acceptContractButton")
            button.setEnabled(
                bool(offer.requirements)
                or (
                    offer.production_value_budget is not None
                    and self._complete_selection(kind, offer) is not None
                )
            )
            button.clicked.connect(lambda checked=False, contract_kind=kind, cid=contract_id: self._accept(contract_kind, cid))
            footer_layout.addWidget(button)
            controls = self._selection_controls.get((kind, contract_id))
            if controls is not None:
                controls["accept"] = button
                controls["cash"] = next(
                    label for label in rewards.findChildren(QLabel, "contractRewardLabel")
                    if label.parent().property("rewardKind") == "cash"
                )
                controls["xp"] = next(label for label in rewards.findChildren(QLabel, "contractRewardLabel") if label.parent().property("rewardKind") == "xp")
                self._update_selection_controls(kind, contract_id)
        elif card_state == "COMPLETED":
            button = QPushButton("COMPLETED")
            button.setObjectName("claimContractButton")
            button.setEnabled(False)
            footer_layout.addWidget(button)
        else:
            button = QPushButton("ACCEPT CONTRACT")
            button.setObjectName("acceptContractButton")
            button.setEnabled(False)
            footer_layout.addWidget(button)
        button.setMinimumHeight(60)
        button.setStyleSheet("font-size: 20px; font-weight: 900;")
        layout.addWidget(footer)
        return panel

    def _product_selection_panel(self, kind: str, offer) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractRequirements")
        panel.setMinimumHeight(150)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title = QLabel("CHOOSE PRODUCTS")
        title.setObjectName("contractChooseProductTitle")
        layout.addWidget(title)

        inline = QFrame()
        inline.setObjectName("contractRequirementsInline")
        inline.setMinimumHeight(126)
        inline.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row = QHBoxLayout(inline)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        products = self._eligible_products_for_offer(offer)
        if not products or not self._has_enough_eligible_products(offer):
            needed = CONTRACT_REQUIREMENT_COUNTS[offer.kind]
            empty = QLabel(f"Requires {needed} eligible unique products")
            empty.setObjectName("contractRequirementLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            empty.setStyleSheet("font-size: 20px; font-weight: 900;")
            row.addWidget(empty, 1)
            layout.addWidget(inline)
            return panel

        key = (kind, offer.contract_id)
        self._selected_products.setdefault(key, [None] * CONTRACT_REQUIREMENT_COUNTS[offer.kind])
        combos: list[QComboBox] = []
        amounts: list[QLabel] = []
        for selector_index in range(CONTRACT_REQUIREMENT_COUNTS[offer.kind]):
            requirement = QFrame()
            requirement.setObjectName("contractRequirementChoice")
            requirement_layout = QHBoxLayout(requirement)
            requirement_layout.setContentsMargins(0, 0, 0, 0)
            requirement_layout.setSpacing(3)
            combo = QComboBox()
            combo.setObjectName("contractProductSelect")
            combo.setProperty("selectorIndex", selector_index)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            combo.addItem(f"PRODUCT {selector_index + 1}", None)
            for product in products:
                combo.addItem(product.name, product.resource_id)
            combo.hide()
            slot_button = ContractProductButton(f"PRODUCT {selector_index + 1}", expanded=True)
            slot_button.setObjectName("contractProductSlot")
            slot_button.setProperty("selectorIndex", selector_index)
            slot_button.clicked.connect(
                lambda checked=False, contract_kind=kind, contract_id=offer.contract_id,
                selection_index=selector_index: self._open_product_picker(contract_kind, contract_id, selection_index)
            )
            amount = slot_button.amount
            combo.currentIndexChanged.connect(
                lambda index, contract_kind=kind, contract_id=offer.contract_id,
                selection_index=selector_index, widget=combo: self._select_product(
                    contract_kind, contract_id, selection_index, widget.itemData(index)
                )
            )
            requirement_layout.addWidget(slot_button, 1)
            requirement_layout.addWidget(combo)
            row.addWidget(requirement, 1)
            combos.append(combo)
            slot_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            amounts.append(amount)
        self._selection_controls[key] = {
            "offer": offer,
            "products": products,
            "combos": combos,
            "buttons": [choice.findChild(QPushButton, "contractProductSlot") for choice in inline.findChildren(QFrame, "contractRequirementChoice")],
            "amounts": amounts,
        }
        self._update_selection_controls(kind, offer.contract_id)
        layout.addWidget(inline)
        return panel

    def _requirements_panel(self, requirements: dict[str, float], delivered: dict[str, float]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractRequirements")
        panel.setMinimumHeight(150)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title = QLabel("REQUIREMENTS")
        title.setObjectName("contractBlockTitle")
        title.setMaximumHeight(22)
        layout.addWidget(title)

        inline = QFrame()
        inline.setObjectName("contractRequirementsInline")
        inline.setMinimumHeight(126)
        inline.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        requirements_row = QHBoxLayout(inline)
        requirements_row.setContentsMargins(0, 0, 0, 0)
        requirements_row.setSpacing(6)
        for resource_id, required in requirements.items():
            name = self._resources[resource_id].name if resource_id in self._resources else resource_id.replace("_", " ").title()
            amount = min(required, delivered.get(resource_id, 0.0))
            row = QFrame()
            row.setObjectName("contractRequirementRow")
            row.setProperty("resourceId", resource_id)
            row.setProperty("fulfilled", amount >= required)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            module = ContractProductButton(expanded=True)
            module.set_product(resource_id, name, required, delivered=amount)
            module.setEnabled(False)
            row_layout.addWidget(module)
            requirements_row.addWidget(row, 1)
        layout.addWidget(inline)
        return panel

    def _rewards_panel(self, kind: str, cash: float, xp: float) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contractRewards")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rewards = [("cash", "$", f"{cash:,.0f}"), ("xp", "XP", f"{xp:,.0f}")]
        if kind == DAILY:
            rewards.append(("research", "RP", "+1"))
        elif kind == WEEKLY:
            rewards.append(("research", "RP", "+3"))
        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(5)
        for reward_kind, icon_text, reward in rewards:
            chip = QFrame()
            chip.setObjectName("contractRewardChip")
            chip.setProperty("rewardKind", reward_kind)
            chip.setProperty("contractKind", kind)
            chip_layout = QHBoxLayout(chip)
            chip.setMinimumHeight(72)
            chip_layout.setContentsMargins(10, 10, 10, 10)
            chip_layout.setSpacing(6)
            chip_layout.addStretch(1)
            icon = QLabel(icon_text)
            icon.setObjectName("contractRewardIcon")
            icon.setStyleSheet("font-size: 16px; font-weight: 900;")
            label = QLabel(reward)
            label.setObjectName("contractRewardLabel")
            label.setStyleSheet("font-size: 24px; font-weight: 900;")
            if reward_kind in ("cash", "xp"):
                self._set_reward_value(label, cash if reward_kind == "cash" else xp)
            chip_layout.addWidget(icon)
            chip_layout.addWidget(label)
            chip_layout.addStretch(1)
            chips.addWidget(chip, 1)
        layout.addLayout(chips)
        return panel

    @staticmethod
    def _set_reward_value(label, value):
        text = f"{value:,.0f}"
        if value >= 1e6:
            from production_zero.ui.freight_statistics import compact_rate
            text = compact_rate(value).removesuffix("/min")
        label.setText(text)
        label.setProperty("rewardAmount", value)
        label.setToolTip(f"Exact accepted quote: {value:,.2f}")
        label.setAccessibleName(f"{value:,.2f}")

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
        offer = next((offer for offer in self._state.contracts.offers[kind] if offer.contract_id == contract_id), None)
        if offer is None:
            self.refresh()
            return
        selected = self._complete_selection(kind, offer)
        auto_check = self._content.findChild(RaisedPZButton, 'regularAutoRepeatButton')
        try:
            self._command_bus.dispatch(
                AcceptContract(
                    kind,
                    contract_id,
                    self._definitions,
                    selected[0] if selected else None,
                    selected,
                    expected_reward=self._quoted_rewards.get((kind,contract_id)),
                    auto_repeat=kind == REGULAR and auto_check is not None and auto_check.isChecked(),
                )
            )
        except ValueError:
            self.setToolTip("Contract offer changed. Review the current preview.")
            self.refresh()
            return
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _select_product(self, kind: str, contract_id: str, selection_index: int, resource_id: str | None) -> None:
        key = (kind, contract_id)
        selections = self._selected_products[key]
        if resource_id is not None and resource_id in (
            selected for index, selected in enumerate(selections) if index != selection_index
        ):
            self._update_selection_controls(kind, contract_id)
            return
        selections[selection_index] = resource_id
        self._update_selection_controls(kind, contract_id)
        self._content_signature = self._build_content_signature()

    def _open_product_picker(self, kind: str, contract_id: str, selection_index: int) -> None:
        key = (kind, contract_id)
        controls = self._selection_controls[key]
        unavailable = {
            resource_id for index, resource_id in enumerate(self._selected_products[key])
            if index != selection_index and resource_id is not None
        }
        selected_id = self._selected_products[key][selection_index]
        product_by_id = {product.resource_id: product for product in controls["products"]}
        picker = ContractProductPicker(
            controls["products"], self._resources, unavailable,
            product_by_id[selected_id].name if selected_id in product_by_id else "",
            self,
        )
        picker.setProperty("contractKind", kind)
        picker.setProperty("contractId", contract_id)
        picker.setProperty("selectorIndex", selection_index)
        picker.product_selected.connect(lambda resource_id: self._choose_embedded_product(kind, contract_id, selection_index, resource_id))
        picker.back_requested.connect(self._close_product_picker)
        self._product_picker = picker
        self._board_scroll.hide()
        self._root_layout.addWidget(picker, 1)
        picker.show()

    def _choose_embedded_product(self, kind: str, contract_id: str, selection_index: int, resource_id: str) -> None:
        self._select_product(kind, contract_id, selection_index, resource_id)
        self._close_product_picker()

    def _close_product_picker(self) -> None:
        picker = self._product_picker
        if picker is not None:
            self._root_layout.removeWidget(picker)
            picker.hide()
            picker.setParent(None)
            picker.deleteLater()
        self._product_picker = None
        self._board_scroll.show()

    def _update_selection_controls(self, kind: str, contract_id: str) -> None:
        key = (kind, contract_id)
        controls = self._selection_controls.get(key)
        if controls is None:
            return
        offer = controls["offer"]
        products = controls["products"]
        selections = self._selected_products[key]
        product_by_id = {product.resource_id: product for product in products}
        complete = self._complete_selection(kind, offer)
        requirements = (contract_requirements_for_products(self._state, offer, self._definitions, complete)
                        if complete is not None else {})

        for selection_index, (combo, amount) in enumerate(zip(controls["combos"], controls["amounts"])):
            combo.blockSignals(True)
            selected = selections[selection_index]
            combo.setCurrentIndex(combo.findData(selected) if selected is not None else 0)
            sibling_selections = {
                resource_id for index, resource_id in enumerate(selections)
                if index != selection_index and resource_id is not None
            }
            model = combo.model()
            for item_index in range(1, combo.count()):
                item = model.item(item_index)
                if item is not None:
                    item.setEnabled(combo.itemData(item_index) not in sibling_selections)
            combo.blockSignals(False)
            button = controls["buttons"][selection_index]
            button.setText(product_by_id[selected].name.upper() if selected in product_by_id else f"PRODUCT {selection_index + 1}")
            button.setProperty("selected", selected is not None)
            button.style().unpolish(button)
            button.style().polish(button)
            required = requirements.get(selected, 0.)
            button.set_product(selected, product_by_id[selected].name if selected in product_by_id else button.placeholder, required)
            if complete is None:
                amount.setText('—')
                amount.setProperty('requiredAmount', None)
                hint = f'{button.name.text()} · Select all products to see final quantities.'
                button.setToolTip(hint)
                button.setAccessibleName(hint)
                amount.setToolTip('Select all products to see final quantities.')
            else:
                amount.setToolTip(f'{required:,.2f}')
        if "accept" in controls:
            controls["accept"].setEnabled(complete is not None)
        if "cash" in controls:
            from production_zero.core.modifiers import contract_cash_quote
            requirements = (
                contract_requirements_for_products(self._state, offer, self._definitions, complete)
                if complete is not None else {}
            )
            from production_zero.core.contracts import contract_reward_quote
            cash, quoted_xp = contract_reward_quote(self._state, offer, self._definitions, requirements) if requirements else (0., 0.)
            self._set_reward_value(controls["cash"], cash)
            if "xp" in controls:
                from production_zero.core.contracts import contract_work_xp_quote
                xp = quoted_xp if requirements else 0
                self._set_reward_value(controls["xp"], xp)
            self._quoted_rewards[kind,contract_id] = (cash,xp)

    def _cancel(self, kind: str) -> None:
        self._command_bus.dispatch(CancelContract(kind, self._definitions))
        if kind == REGULAR:
            self._auto_repeat_requested = False
        self._selected_products = {key: value for key, value in self._selected_products.items() if key[0] != kind}
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _build_regular_auto_button(self, contract_id):
        auto = RaisedPZButton('AUTO REPEAT', variant='secondary')
        auto.setObjectName('regularAutoRepeatButton')
        auto.setCheckable(True)
        auto.setFixedSize(104, 28)
        auto.setStyleSheet('font-size: 11px; font-weight: 900;')
        auto.setToolTip('Automatically accept each new Regular Contract with the same products. Quantities and rewards are recalculated for each new Contract. Cancel stops auto repeat.')
        auto.setProperty('contractId', contract_id)
        active = self._state.contracts.active.get(REGULAR)
        self._set_auto_button_state(auto, self._state.contracts.regular_auto.enabled if active or self._state.contracts.regular_auto.enabled else self._auto_repeat_requested)
        auto.clicked.connect(lambda enabled, cid=contract_id: self._toggle_regular_auto(enabled, cid))
        return auto

    @staticmethod
    def _set_auto_button_state(button, enabled):
        button.setChecked(enabled)
        button.variant = 'primary' if enabled else 'secondary'
        button.setProperty('pzButtonVariant', button.variant)
        button.update()

    def _add_regular_auto_status(self, layout):
        status = QLabel(self._auto_status_text())
        status.setToolTip(status.text())
        status.setObjectName('regularAutoRepeatStatus')
        status.setStyleSheet(f'color: {Theme.TEXT}; font-size: 11px; font-weight: 600;')
        status.setWordWrap(True)
        status.setMaximumHeight(44)
        layout.addWidget(status)

    def _set_priority_button(self, button, kind):
        value = self._state.contracts.priorities.get(kind, 0)
        button.setText('EVEN' if value == 0 else f'PRIORITY {value}')
        button.setProperty('priority', value)
        button.setAccessibleName(f'{CONTRACT_KIND_LABELS[kind]} priority: {button.text()}')

    def _cycle_priority(self, kind):
        current = self._state.contracts.priorities.get(kind, 0)
        self._command_bus.dispatch(SetContractPriority(kind, (current + 1) % 3))
        self._update_contract_preferences()
        if self._on_state_changed is not None:
            self._on_state_changed()

    def _auto_status_text(self):
        auto = self._state.contracts.regular_auto
        if auto.enabled:
            return 'AUTO PAUSED · ' + auto.pause_reason if auto.pause_reason else 'AUTO ON · Repeats with the same products'
        return 'AUTO SELECTED · Starts when accepted' if self._auto_repeat_requested else 'AUTO OFF'

    def _update_contract_preferences(self):
        for button in self._content.findChildren(QPushButton, 'contractPriorityButton'):
            self._set_priority_button(button, button.property('kind'))
        auto = self._state.contracts.regular_auto
        active = self._state.contracts.active.get(REGULAR)
        for check in self._content.findChildren(RaisedPZButton, 'regularAutoRepeatButton'):
            check.blockSignals(True)
            self._set_auto_button_state(check, auto.enabled if active or auto.enabled else self._auto_repeat_requested)
            check.blockSignals(False)
        for label in self._content.findChildren(QLabel, 'regularAutoRepeatStatus'):
            label.setText(self._auto_status_text())
            label.setToolTip(label.text())

    def _toggle_regular_auto(self, enabled, contract_id):
        active = self._state.contracts.active.get(REGULAR)
        if active is not None or (not enabled and self._state.contracts.regular_auto.enabled):
            try:
                self._command_bus.dispatch(SetRegularContractAutoRepeat(enabled, contract_id if active else None))
            except ValueError as error:
                self.setToolTip(str(error))
                self._update_contract_preferences()
                return
            if self._on_state_changed is not None:
                self._on_state_changed()
        self._auto_repeat_requested = enabled
        self._update_contract_preferences()

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

    def _eligible_products_for_offer(self, offer) -> tuple[ContractProductOption, ...]:
        if offer.production_value_budget is None:
            return ()
        from production_zero.core.contracts import contract_value_calculator
        if offer.production_value_budget not in self._eligible_product_cache:
            self._eligible_product_cache[offer.production_value_budget] = eligible_contract_products(
                self._state,
                self._definitions,
                offer.production_value_budget,
                calculator=contract_value_calculator(self._state,self._definitions),
            )
        products = self._eligible_product_cache[offer.production_value_budget]
        return tuple(p for p in products if p.resource_id in offer.capacity_rates) if offer.balance_version else products

    def _complete_selection(self, kind: str, offer) -> tuple[str, ...] | None:
        selections = self._selected_products.get((kind, offer.contract_id), [])
        required_count = CONTRACT_REQUIREMENT_COUNTS[offer.kind]
        if len(selections) != required_count or any(resource_id is None for resource_id in selections):
            return None
        selected = tuple(resource_id for resource_id in selections if resource_id is not None)
        eligible = {product.resource_id for product in self._eligible_products_for_offer(offer)}
        if len(set(selected)) != required_count or any(resource_id not in eligible for resource_id in selected):
            return None
        return selected

    def _has_enough_eligible_products(self, offer) -> bool:
        return len({product.resource_id for product in self._eligible_products_for_offer(offer)}) >= CONTRACT_REQUIREMENT_COUNTS[offer.kind]

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
