from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QProgressBar, QPushButton, QTabWidget, QVBoxLayout, QWidget

from production_zero.config import DEVELOPMENT_MODE, FACTORY_VIEW_V2_ENABLED
from production_zero.core.cards import CardInstance
from production_zero.core.commands import AddCard, AddCash, AddResource, BuildHall, CommandBus, ExpandInventoryStorage, RecordMetric, SelectMachineProduction
from production_zero.core.contracts import initialize_contracts
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.resources import ResourceDefinition, create_resource_inventory
from production_zero.core.state import FactoryHall, GameState
from production_zero.core.storage_upgrades import MAX_INVENTORY_STORAGE_LEVEL, inventory_storage_upgrade_cost
from production_zero.core.supply import refresh_supply
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.charts_view import ChartsView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.event_feed import EventFeedController, EventFeedWidget
from production_zero.ui.factory_view import FactoryView
from production_zero.ui.factory_view_v2 import FactoryCommandDeckWidget, FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.market_view import MarketView
from production_zero.ui.packs_view import PacksView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET
from production_zero.services.local import LocalLeaderboardService


class CompanyProgressWidget(QFrame):
    def __init__(self, state: GameState) -> None:
        super().__init__()
        self._state = state
        self.setObjectName("companyProgressPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self._label = QLabel()
        self._label.setObjectName("companyLevelLabel")
        self._xp_label = QLabel()
        self._xp_label.setObjectName("companyXpLabel")
        self._bar = QProgressBar()
        self._bar.setObjectName("companyXpProgress")
        self._bar.setTextVisible(False)
        layout.addWidget(self._label)
        layout.addWidget(self._xp_label)
        layout.addWidget(self._bar)
        self.refresh()

    def refresh(self) -> None:
        company = self._state.company
        required = company.xp_to_next_level
        self._label.setText(f"LEVEL {company.level} · {company.current_title.upper()}")
        self._xp_label.setText(f"{company.current_xp:,.0f} / {required:,.0f} XP")
        self._bar.setRange(0, max(1, round(required)))
        self._bar.setValue(round(company.current_xp))


TOPBAR_RESOURCE_IDS = ("iron_ore", "iron", "copper_ore", "copper", "coal", "steel")


class ResponsiveMainTabWidget(QTabWidget):
    """Keep hidden tab pages from becoming a hard native window minimum."""

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(min(hint.width(), 1180), min(hint.height(), 650))


class GlobalHeaderWidget(QFrame):
    def __init__(
        self,
        state: GameState,
        definition_count: int,
        resource_definitions: dict[str, ResourceDefinition],
        command_bus: CommandBus | None = None,
        on_state_changed=None,
    ) -> None:
        super().__init__()
        self._state = state
        self._resource_definitions = resource_definitions
        self._command_bus = command_bus
        self._on_state_changed = on_state_changed
        self._resource_amount_labels: dict[str, QLabel] = {}
        self.setObjectName("globalHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        title_panel = QFrame()
        title_panel.setObjectName("commandDeckTitlePanel")
        title_block = QVBoxLayout(title_panel)
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(3)
        deck_label = QLabel("COMMAND DECK")
        deck_label.setObjectName("commandDeckLabel")
        title = QLabel("Production Zero")
        title.setObjectName("title")
        subtitle = QLabel(f"{definition_count} cards · {len(resource_definitions)} resources · deterministic industry")
        subtitle.setObjectName("subtitle")
        title_block.addWidget(deck_label)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addWidget(title_panel)

        economy_cluster = QFrame()
        economy_cluster.setObjectName("topbarEconomyCluster")
        economy_layout = QHBoxLayout(economy_cluster)
        economy_layout.setContentsMargins(8, 8, 8, 8)
        economy_layout.setSpacing(8)

        self._cash_panel = QFrame()
        self._cash_panel.setObjectName("cashStatusPanel")
        cash_layout = QHBoxLayout(self._cash_panel)
        cash_layout.setContentsMargins(11, 7, 12, 8)
        cash_layout.setSpacing(8)
        cash_icon = QLabel("$")
        cash_icon.setObjectName("cashStatusIcon")
        cash_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cash_text = QVBoxLayout()
        cash_text.setContentsMargins(0, 0, 0, 0)
        cash_text.setSpacing(1)
        cash_title = QLabel("CASH")
        cash_title.setObjectName("cashStatusTitle")
        self._cash_amount = QLabel()
        self._cash_amount.setObjectName("cashStatusAmount")
        cash_text.addWidget(cash_title)
        cash_text.addWidget(self._cash_amount)
        cash_layout.addWidget(cash_icon)
        cash_layout.addLayout(cash_text)
        economy_layout.addWidget(self._cash_panel)

        self._energy_panel = QFrame()
        self._energy_panel.setObjectName("energyStatusPanel")
        energy_layout = QHBoxLayout(self._energy_panel)
        energy_layout.setContentsMargins(11, 7, 12, 8)
        energy_layout.setSpacing(8)
        energy_icon = QLabel("MW")
        energy_icon.setObjectName("energyStatusIcon")
        energy_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        energy_text = QVBoxLayout()
        energy_text.setContentsMargins(0, 0, 0, 0)
        energy_text.setSpacing(2)
        energy_title = QLabel("ENERGY")
        energy_title.setObjectName("energyStatusTitle")
        self._energy_amount = QLabel()
        self._energy_amount.setObjectName("energyStatusAmount")
        self._energy_bar = QProgressBar()
        self._energy_bar.setObjectName("energyStatusProgress")
        self._energy_bar.setTextVisible(False)
        energy_text.addWidget(energy_title)
        energy_text.addWidget(self._energy_amount)
        energy_text.addWidget(self._energy_bar)
        energy_layout.addWidget(energy_icon)
        energy_layout.addLayout(energy_text)
        economy_layout.addWidget(self._energy_panel)

        self._storage_panel = QFrame()
        self._storage_panel.setObjectName("resourceStoragePanel")
        storage_layout = QHBoxLayout(self._storage_panel)
        storage_layout.setContentsMargins(11, 7, 12, 8)
        storage_layout.setSpacing(8)
        storage_icon = QLabel("ST")
        storage_icon.setObjectName("resourceStorageIcon")
        storage_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        storage_text = QVBoxLayout()
        storage_text.setContentsMargins(0, 0, 0, 0)
        storage_text.setSpacing(2)
        storage_title = QLabel("RESOURCE STORAGE")
        storage_title.setObjectName("resourceStorageTitle")
        self._storage_amount = QLabel()
        self._storage_amount.setObjectName("resourceStorageAmount")
        self._storage_button = QPushButton()
        self._storage_button.setObjectName("expandResourceStorageButton")
        self._storage_button.clicked.connect(self._expand_resource_storage)
        storage_text.addWidget(storage_title)
        storage_text.addWidget(self._storage_amount)
        storage_text.addWidget(self._storage_button)
        storage_layout.addWidget(storage_icon)
        storage_layout.addLayout(storage_text)
        economy_layout.addWidget(self._storage_panel)
        layout.addWidget(economy_cluster)

        resource_strip = QFrame()
        resource_strip.setObjectName("topbarResourceStrip")
        resource_layout = QHBoxLayout(resource_strip)
        resource_layout.setContentsMargins(0, 0, 0, 0)
        resource_layout.setSpacing(6)
        for resource_id in TOPBAR_RESOURCE_IDS:
            if resource_id not in resource_definitions:
                continue
            chip = QFrame()
            chip.setObjectName("topbarResourceChip")
            chip.setProperty("resourceId", resource_id)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(8, 5, 8, 5)
            chip_layout.setSpacing(6)
            marker = QLabel("+")
            marker.setObjectName("topbarResourceMarker")
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(0)
            name = QLabel(resource_definitions[resource_id].name)
            name.setObjectName("topbarResourceName")
            amount = QLabel()
            amount.setObjectName("topbarResourceAmount")
            text_layout.addWidget(name)
            text_layout.addWidget(amount)
            chip_layout.addWidget(marker)
            chip_layout.addLayout(text_layout)
            self._resource_amount_labels[resource_id] = amount
            resource_layout.addWidget(chip)
        layout.addWidget(resource_strip, 1)

        self._company_progress = CompanyProgressWidget(state)
        layout.addWidget(self._company_progress)
        self.refresh()

    def refresh(self) -> None:
        self._cash_amount.setText(f"${self._state.cash.amount:,.0f}")
        self._refresh_energy()
        self._refresh_storage()
        self._refresh_resource_chips()
        self._company_progress.refresh()

    def highlight_cash_gain(self, previous_cash: float, current_cash: float) -> None:
        self._cash_amount.setText(f"${current_cash:,.0f}")
        self._cash_panel.setProperty("cashPulse", True)
        self._cash_panel.style().unpolish(self._cash_panel)
        self._cash_panel.style().polish(self._cash_panel)
        QTimer.singleShot(360, self._clear_cash_highlight)

    def _clear_cash_highlight(self) -> None:
        self._cash_panel.setProperty("cashPulse", False)
        self._cash_panel.style().unpolish(self._cash_panel)
        self._cash_panel.style().polish(self._cash_panel)

    def _refresh_energy(self) -> None:
        consumed = self._state.energy.consumed
        generated = self._state.energy.generated
        self._energy_amount.setText(f"{consumed:.0f} / {generated:.0f} MW")
        if generated <= 0 and consumed > 0:
            state = "overloaded"
            percent = 100
        elif generated <= 0:
            state = "stable"
            percent = 0
        else:
            ratio = consumed / generated
            percent = round(min(1.0, max(0.0, ratio)) * 100)
            if ratio >= 1.0:
                state = "overloaded"
            elif ratio >= 0.82:
                state = "strained"
            else:
                state = "stable"
        self._energy_panel.setProperty("energyState", state)
        self._energy_bar.setProperty("energyState", state)
        self._energy_bar.setRange(0, 100)
        self._energy_bar.setValue(percent)
        for widget in (self._energy_panel, self._energy_bar):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _refresh_storage(self) -> None:
        amount = sum(stock.amount for stock in self._state.resources.values())
        capacity = sum(stock.capacity for stock in self._state.resources.values())
        self._storage_amount.setText(f"{amount:.0f} / {capacity:.0f}")
        if self._command_bus is None or not self._resource_definitions:
            self._storage_button.setText("Storage")
            self._storage_button.setEnabled(False)
            return
        if self._state.inventory_storage_level >= MAX_INVENTORY_STORAGE_LEVEL:
            self._storage_button.setText("Max")
            self._storage_button.setEnabled(False)
            return
        cost = inventory_storage_upgrade_cost(self._state.inventory_storage_level)
        self._storage_button.setText(f"Expand ${cost:,.0f}")
        self._storage_button.setEnabled(self._state.cash.amount >= cost)

    def _refresh_resource_chips(self) -> None:
        for resource_id, label in self._resource_amount_labels.items():
            stock = self._state.resources.get(resource_id)
            label.setText(f"{stock.amount:,.0f}" if stock is not None else "0")

    def _expand_resource_storage(self) -> None:
        if self._command_bus is None or not self._resource_definitions:
            return
        self._command_bus.dispatch(ExpandInventoryStorage(self._resource_definitions))
        self.refresh()
        if self._on_state_changed is not None:
            self._on_state_changed()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Production Zero")

        definitions_path = files("production_zero.data").joinpath("game_definitions.json")
        definitions = load_card_definitions(definitions_path)
        resources_path = files("production_zero.data").joinpath("resource_definitions.json")
        resource_definitions = load_resource_definitions(resources_path)

        state = _create_initial_state(resource_definitions, definitions)
        bus = CommandBus(state)

        root = QWidget()
        self._root_widget = root
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header_cls = FactoryCommandDeckWidget if FACTORY_VIEW_V2_ENABLED else GlobalHeaderWidget
        global_header = header_cls(
            state,
            len(definitions),
            resource_definitions,
            bus,
            lambda: _refresh_views(factory_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header),
        )
        self._global_header = global_header
        event_feed = EventFeedWidget(root)
        self._event_feed = event_feed
        event_feed_controller = EventFeedController(state, event_feed, global_header.highlight_cash_gain)
        tabs = ResponsiveMainTabWidget()
        tabs.setObjectName("mainTabs")
        factory_view = FactoryViewV2(state, bus, definitions) if FACTORY_VIEW_V2_ENABLED else FactoryView(state, bus, definitions)
        freight_view = FreightView(state, bus, definitions, resource_definitions)
        inventory_view = InventoryView(
            state,
            definitions,
            resource_definitions,
            bus,
            lambda: _refresh_views(factory_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header),
        )
        charts_view = ChartsView(state, resource_definitions)
        market_view = MarketView(state, resource_definitions)
        contracts_view = ContractsView(state, bus, definitions, resource_definitions, global_header.refresh)
        supply_view = SupplyView(state, bus, definitions, lambda: _refresh_views(factory_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header))
        packs_view = PacksView(state, bus, definitions, lambda: _refresh_views(factory_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header))
        leaderboard_view = LeaderboardView(LocalLeaderboardService(state))
        tabs.addTab(factory_view, "Factory")
        tabs.addTab(freight_view, "Freight")
        tabs.addTab(inventory_view, "Inventory")
        tabs.addTab(charts_view, "Charts")
        tabs.addTab(market_view, "Market")
        tabs.addTab(contracts_view, "Contracts")
        tabs.addTab(supply_view, "Industrial Supply")
        tabs.addTab(packs_view, "Packs")
        tabs.addTab(leaderboard_view, "Leaderboard")
        if DEVELOPMENT_MODE:
            tabs.addTab(
                DevToolsView(
                    state,
                    bus,
                    definitions,
                    resource_definitions,
                    factory_view._simulation,
                    lambda: _refresh_views(factory_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header),
                    factory_view.pause_simulation,
                    factory_view.resume_simulation,
                    factory_view.is_simulation_paused,
                    lambda: _copy_state(state, _create_initial_state(resource_definitions, definitions)),
                ),
                "Dev",
            )
        factory_view.set_simulation_advanced_callback(
            lambda: _refresh_active_runtime_view(
                tabs,
                freight_view,
                event_feed_controller,
                charts_view,
                market_view,
                contracts_view,
                supply_view,
                packs_view,
                leaderboard_view,
                global_header,
            )
        )

        layout.addWidget(global_header)
        layout.addWidget(tabs, 1)
        self.setCentralWidget(root)
        root.installEventFilter(self)
        self._position_event_feed()

        self.setStyleSheet(APP_STYLESHEET)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is getattr(self, "_root_widget", None) and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.LayoutRequest,
            QEvent.Type.Show,
        }:
            QTimer.singleShot(0, self._position_event_feed)
        return super().eventFilter(watched, event)

    def _position_event_feed(self) -> None:
        if not hasattr(self, "_event_feed") or not hasattr(self, "_root_widget"):
            return
        feed = self._event_feed
        root = self._root_widget
        header = self._global_header
        width = min(420, max(320, root.width() // 3))
        feed.setFixedWidth(width)
        feed.adjustSize()
        x = max(18, root.width() - width - 18)
        y = header.geometry().bottom() + 10
        feed.move(x, y)
        feed.raise_()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        screen = self.screen()
        if screen is None:
            return hint
        available = screen.availableGeometry()
        return QSize(min(hint.width(), available.width()), min(hint.height(), available.height()))

    def sizeHint(self) -> QSize:  # noqa: N802
        hint = super().sizeHint()
        screen = self.screen()
        if screen is None:
            return hint
        available = screen.availableGeometry()
        return QSize(min(hint.width(), available.width()), min(hint.height(), available.height()))

def _create_initial_state(resource_definitions, definitions) -> GameState:
    state = GameState(rng_seed=1001, resources=create_resource_inventory(resource_definitions))
    bus = CommandBus(state)
    bus.dispatch(AddCash(1250))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)))
    for card_id, definition_id, card_kind in (
        ("test-drill-common-001", "machine.extractor.mk1", CardKind.MACHINE),
        ("test-drill-common-002", "machine.extractor.mk1", CardKind.MACHINE),
        ("test-drill-common-003", "machine.extractor.mk1", CardKind.MACHINE),
        ("test-solar-common-001", "energy.solar_array.mk1", CardKind.ENERGY),
        ("test-furnace-common-001", "machine.processor.mk1", CardKind.MACHINE),
        ("test-blast-furnace-common-001", "machine.processor.mk1", CardKind.MACHINE),
    ):
        bus.dispatch(
            AddCard(
                CardInstance(
                    card_id=card_id,
                    definition_id=definition_id,
                    card_kind=card_kind,
                    rarity=Rarity.COMMON,
                    output_bonus_percent=0.0,
                    power_bonus_percent=0.0,
                )
            )
        )
    bus.dispatch(AddResource("iron_ore", 145))
    bus.dispatch(AddResource("coal", 70))
    bus.dispatch(AddResource("copper_ore", 88))
    bus.dispatch(SelectMachineProduction("test-blast-furnace-common-001", "recipe.processor.steel", "steel"))
    initialize_contracts(state)
    refresh_supply(state, definitions)
    for sample in (900, 940, 1010, 1100, 1180, 1250):
        bus.dispatch(RecordMetric("cash", sample))
    for sample in (2, 4, 7, 9, 8, 11):
        bus.dispatch(RecordMetric("energy.consumed", sample))
    for sample in (40, 52, 78, 101, 130, 145):
        bus.dispatch(RecordMetric("resource.iron_ore", sample))
    return state


def _copy_state(target: GameState, source: GameState) -> None:
    target.rng_seed = source.rng_seed
    target.tick = source.tick
    target.cash = source.cash
    target.resources = source.resources
    target.energy = source.energy
    target.market = source.market
    target.history = source.history
    target.cards = source.cards
    target.halls = source.halls
    target.machine_production = source.machine_production
    target.auto_sell = source.auto_sell
    target.contracts = source.contracts
    target.company = source.company
    target.supply = source.supply
    target.packs = source.packs
    target.scrap = source.scrap
    target.statistics = source.statistics
    target.freight = source.freight
    target.inventory_storage_level = source.inventory_storage_level


def _refresh_views(
    factory_view: FactoryView,
    freight_view: FreightView,
    inventory_view: InventoryView,
    charts_view: ChartsView,
    market_view: MarketView,
    contracts_view: ContractsView,
    supply_view: SupplyView,
    packs_view: PacksView,
    leaderboard_view: LeaderboardView,
    global_header: GlobalHeaderWidget,
) -> None:
    factory_view.refresh_view()
    freight_view.refresh()
    inventory_view.refresh()
    charts_view.refresh()
    market_view.refresh()
    contracts_view.refresh()
    supply_view.refresh()
    packs_view.refresh()
    leaderboard_view.refresh()
    global_header.refresh()


def _refresh_active_runtime_view(
    tabs: QTabWidget,
    freight_view: FreightView,
    event_feed_controller: EventFeedController,
    charts_view: ChartsView,
    market_view: MarketView,
    contracts_view: ContractsView,
    supply_view: SupplyView,
    packs_view: PacksView,
    leaderboard_view: LeaderboardView,
    global_header: GlobalHeaderWidget,
) -> None:
    event_feed_controller.observe()
    global_header.refresh()
    current = tabs.currentWidget()
    if current is freight_view:
        freight_view.refresh_runtime()
    elif current is charts_view:
        charts_view.refresh()
    elif current is market_view:
        market_view.refresh()
    elif current is contracts_view:
        contracts_view.refresh()
    elif current is supply_view:
        supply_view.refresh()
    elif current is packs_view:
        packs_view.refresh()
    elif current is leaderboard_view:
        leaderboard_view.refresh()
