from __future__ import annotations

from importlib.resources import files
from dataclasses import fields

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QSizePolicy, QTabBar, QTabWidget, QVBoxLayout, QWidget

from production_zero.config import CHARTS_ENABLED, DEVELOPMENT_MODE
from production_zero.core.cards import CardInstance
from production_zero.core.commands import AddCard, AddCash, AddResource, BuildHall, CommandBus, RecordMetric, SelectMachineProduction
from production_zero.core.contracts import initialize_contracts
from production_zero.core.progression import initialize_production_progress
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.resources import create_resource_inventory
from production_zero.core.state import FactoryHall, GameState
from production_zero.core.supply import refresh_supply
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.charts_view import ChartsView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.event_feed import EventFeedController, EventFeedWidget
from production_zero.ui.factory_view_v2 import FactoryCommandDeckWidget, FactoryViewV2
from production_zero.ui.production_board_views import ResourcesViewV2, EnergyViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.market_view import MarketView
from production_zero.ui.research_view import ResearchView
from production_zero.ui.packs_view import PacksView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET
from production_zero.services.local import LocalLeaderboardService
from production_zero.core.player_profile import local_profile, member_profile, leaderboard_profile
from production_zero.ui.player_profile import PlayerProfileView


NAVIGATION_WIDTH_STRETCH = 50
TICKER_WIDTH_STRETCH = 50
NAVIGATION_TAB_HORIZONTAL_INSET = 8


class WideNavigationTabBar(QTabBar):
    """Fill the navigation region with near-equal, non-clipping tabs."""

    def tabSizeHint(self, index: int) -> QSize:  # noqa: N802
        hint = super().tabSizeHint(index)
        widths = self._filled_tab_widths()
        return QSize(widths[index] if index < len(widths) else hint.width(), hint.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())

    def _filled_tab_widths(self) -> list[int]:
        count = self.count()
        if count <= 0:
            return []
        minimums = [
            self.fontMetrics().horizontalAdvance(self.tabText(index)) + NAVIGATION_TAB_HORIZONTAL_INSET
            for index in range(count)
        ]
        available = max(self.width(), sum(minimums))
        low = min(minimums)
        high = max(max(minimums), available // count)
        while low < high:
            candidate = (low + high + 1) // 2
            if sum(max(minimum, candidate) for minimum in minimums) <= available:
                low = candidate
            else:
                high = candidate - 1
        widths = [max(minimum, low) for minimum in minimums]
        remainder = available - sum(widths)
        for index in sorted(range(count), key=lambda candidate: (widths[candidate], candidate))[:remainder]:
            widths[index] += 1
        return widths


class ResponsiveMainTabWidget(QTabWidget):
    """Keep hidden tab pages from becoming a hard native window minimum."""

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        # Reserve space for the 138 px command deck, root margins and navigation.
        # Pages retain readable minima inside their own scroll areas.
        hint = super().minimumSizeHint()
        return QSize(min(hint.width(), 1180), min(hint.height(), 480))

    def tabInserted(self, index: int) -> None:  # noqa: N802
        super().tabInserted(index)
        if hasattr(self, "_navigation_bar"):
            self._navigation_bar.insertTab(index, self.tabText(index))
        self.tabBar().hide()

    def tabRemoved(self, index: int) -> None:  # noqa: N802
        super().tabRemoved(index)
        if hasattr(self, "_navigation_bar"):
            self._navigation_bar.removeTab(index)

    def build_navigation_row(self, ticker: EventFeedWidget) -> QFrame:
        row = QFrame()
        row.setObjectName("mainNavigationRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        navigation = WideNavigationTabBar()
        navigation.setObjectName("mainNavigationTabs")
        navigation_font = QFont("Bahnschrift")
        navigation_font.setPixelSize(12)
        navigation_font.setWeight(QFont.Weight.Black)
        navigation_font.setStretch(QFont.Stretch.Condensed)
        navigation.setFont(navigation_font)
        navigation.setProperty("equalWidthFill", True)
        navigation.setExpanding(True)
        navigation.setUsesScrollButtons(False)
        navigation.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        for index in range(self.count()):
            navigation.addTab(self.tabText(index))
        navigation.setCurrentIndex(self.currentIndex())
        navigation.currentChanged.connect(self.setCurrentIndex)
        self.currentChanged.connect(navigation.setCurrentIndex)
        self._navigation_bar = navigation
        self._ticker = ticker
        ticker.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(navigation, NAVIGATION_WIDTH_STRETCH)
        layout.addWidget(ticker, TICKER_WIDTH_STRETCH)
        row.setFixedHeight(max(navigation.sizeHint().height(), ticker.height()))
        self.tabBar().hide()
        return row


class MainWindow(QMainWindow):
    def __init__(self, *, charts_enabled: bool | None = None, development_mode: bool | None = None, save_store=None) -> None:
        super().__init__()
        self.setWindowTitle("Industriova")
        charts_enabled = CHARTS_ENABLED if charts_enabled is None else charts_enabled
        development_mode = DEVELOPMENT_MODE if development_mode is None else development_mode

        definitions_path = files("production_zero.data").joinpath("game_definitions.json")
        definitions = load_card_definitions(definitions_path)
        resources_path = files("production_zero.data").joinpath("resource_definitions.json")
        resource_definitions = load_resource_definitions(resources_path)

        state = _create_initial_state(resource_definitions, definitions)
        self._save_store = save_store
        if save_store is not None:
            save_store.initialize()
            try:
                state = save_store.load("company")
            except KeyError:
                pass
        self._session_state = state
        bus = CommandBus(state)

        root = QWidget()
        self._root_widget = root
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)

        global_header = FactoryCommandDeckWidget(
            state,
            len(definitions),
            resource_definitions,
            bus,
            lambda: _refresh_views(resources_view, factory_view, energy_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header),
        )
        self._global_header = global_header
        from production_zero.ui.global_resources import GlobalResourcesOverlay
        self._global_resources = GlobalResourcesOverlay(state, definitions, resource_definitions, root)
        global_header.resources_requested.connect(self._global_resources.toggle)
        tabs = ResponsiveMainTabWidget()
        tabs.setObjectName("mainTabs")
        factory_view = FactoryViewV2(state, bus, definitions)
        resources_view = ResourcesViewV2(state, bus, definitions)
        energy_view = EnergyViewV2(state, bus, definitions)
        freight_view = FreightView(state, bus, definitions, resource_definitions)
        inventory_view = InventoryView(state, definitions, resource_definitions, bus,
            lambda: _refresh_views(resources_view, factory_view, energy_view, freight_view, inventory_view, charts_view,
                market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header), release_mode=True)
        charts_view = ChartsView(state, resource_definitions) if charts_enabled else None
        market_view = None
        contracts_view = ContractsView(state, bus, definitions, resource_definitions, global_header.refresh)
        consortium_view = ConsortiumView(state, definitions, resource_definitions, lambda: (self._save_session(), global_header.refresh()))
        supply_view = SupplyView(state, bus, definitions, lambda: _refresh_views(resources_view, factory_view, energy_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header))
        packs_view = None
        leaderboard_view = LeaderboardView(LocalLeaderboardService(state))
        def card_operation_changed():
            for view in (inventory_view, supply_view):
                view.setProperty("uiDirty", True)
            global_header.refresh()
        for board in (resources_view, factory_view, energy_view, freight_view):
            board._card_operation_changed = card_operation_changed
        def open_supply(category):
            supply_view.show_common(category)
            tabs.setCurrentWidget(supply_view)
        for board in (resources_view, factory_view, energy_view, freight_view):
            board.supply_requested.connect(open_supply)
        self._profile_view = None
        def open_profile(profile):
            if self._profile_view is not None:
                self._profile_view.close()
            view = PlayerProfileView(profile, resource_definitions, self)
            self._profile_view = view
            view.closed.connect(lambda: setattr(self, "_profile_view", None))
            view.show()
        self.open_player_profile = open_profile
        global_header.profile_requested.connect(lambda: open_profile(local_profile(state)))
        consortium_view.profile_requested.connect(lambda consortium, member: open_profile(member_profile(state, consortium, member)))
        leaderboard_view.profile_requested.connect(lambda entry: open_profile(leaderboard_profile(state, entry)))
        tabs.addTab(resources_view, "Resources")
        tabs.addTab(factory_view, "Factory")
        tabs.addTab(energy_view, "Energy")
        tabs.addTab(freight_view, "Freight")
        tabs.addTab(supply_view, "Industrial Supply")
        tabs.addTab(inventory_view, "Inventory")
        if charts_view is not None:
            tabs.addTab(charts_view, "Charts")
        tabs.addTab(contracts_view, "Contracts")
        tabs.addTab(consortium_view, "Consortium")
        # Research updates its own widgets. Hidden quote screens refresh on entry,
        # not by rebuilding their product controls during every RP click.
        research_view = ResearchView(state, bus, lambda: (self._save_session(), global_header.refresh()))
        tabs.addTab(research_view, "Research")
        tabs.currentChanged.connect(lambda index: _refresh_entered_view(tabs.widget(index)))
        tabs.addTab(leaderboard_view, "Leaderboard")
        def replace_state(loaded_state):
            if self._profile_view is not None:
                self._profile_view.close()
            from PySide6.QtWidgets import QDialog
            for dialog in self.findChildren(QDialog):
                dialog.reject()
            from production_zero.ui.consortium_view import EmbeddedConsortiumDialog
            for dialog in self.findChildren(EmbeddedConsortiumDialog):
                dialog.close()
            event_feed.close_panels()
            self._global_resources.hide()
            self._global_resources.search.clear()
            self._global_resources.category.setCurrentIndex(0)
            _copy_state(state, loaded_state)
            bus._history.clear()
            for board in (resources_view, factory_view, energy_view):
                board.reset_for_state_change()
            freight_view.reset_for_state_change()
            contracts_view.reset_for_state_change()
            research_view._close_picker()
            research_view._scroll_positions.clear()
            research_view.select_tree("company.general")
            consortium_view._workspace_signature = None
            consortium_view._render_signature = None
            consortium_view._directory_policy = None
            consortium_view._draft_products = {kind: [None] * len(values) for kind, values in consortium_view._draft_products.items()}
            consortium_view._selected_member_id = None
            consortium_view._close_product_picker()
            inventory_view.reset_for_state_change()
            supply_view.reset_for_state_change()
            event_feed.clear_events()
            event_feed_controller.reset_baseline()
            research_view.refresh()
            consortium_view.refresh()
            _refresh_views(resources_view, factory_view, energy_view, freight_view, inventory_view, charts_view,
                           market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header)
            saved = self._save_session(wait=True)
            factory_view.resume_simulation()
            return saved

        if development_mode:
            tabs.addTab(
                DevToolsView(
                    state,
                    bus,
                    definitions,
                    resource_definitions,
                    factory_view._simulation,
                    lambda: _refresh_views(resources_view, factory_view, energy_view, freight_view, inventory_view, charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view, global_header),
                    factory_view.pause_simulation,
                    factory_view.resume_simulation,
                    factory_view.is_simulation_paused,
                    lambda: replace_state(_create_initial_state(resource_definitions, definitions)),
                    replace_state,
                    session_save_callback=lambda: self._save_session(wait=True),
                ),
                "Dev",
            )
        event_feed = EventFeedWidget(state=state, definitions=definitions)
        self._event_feed = event_feed
        event_feed_controller = EventFeedController(state, event_feed, global_header.highlight_cash_gain, definitions)
        event_feed.move_communication_buttons(global_header._communication_layout)
        navigation_row = tabs.build_navigation_row(event_feed)
        def close_navigation_overlays(_):
            self._global_resources.hide()
            event_feed.close_panels()
            if self._profile_view is not None:
                self._profile_view.close()
        tabs.currentChanged.connect(close_navigation_overlays)
        consortium_view.freight_requested.connect(lambda: tabs.setCurrentWidget(freight_view))
        event_feed.navigate_requested.connect(
            lambda resource_id: self._focus_unlock_tree(tabs, resources_view, resource_id)
        )
        factory_view.set_simulation_advanced_callback(
            lambda: _refresh_active_runtime_view(
                tabs,
                resources_view,
                factory_view,
                energy_view,
                freight_view,
                event_feed_controller,
                charts_view,
                market_view,
                contracts_view,
                consortium_view,
                supply_view,
                packs_view,
                leaderboard_view,
                global_header,
            )
        )

        layout.addWidget(global_header)
        layout.addWidget(navigation_row)
        layout.addWidget(tabs, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(APP_STYLESHEET)
        if self._save_store is not None:
            from production_zero.persistence.session_writer import SessionWriter
            self._save_writer = SessionWriter(self._save_store)
            self._save_poll_timer = QTimer(self)
            self._save_poll_timer.setInterval(250)
            self._save_poll_timer.timeout.connect(self._poll_saves)
            self._save_poll_timer.start()
            self._save_timer = QTimer(self)
            self._save_timer.setInterval(30_000)
            self._save_timer.timeout.connect(self._save_session)
            self._save_timer.start()

    def _poll_saves(self):
        error = self._save_writer.poll()
        if error:
            self.statusBar().showMessage(f"Company save failed: {error}. Progress remains in memory; the next save will retry.")
        return error

    def _save_session(self, *, wait=False):
        if self._save_store is not None:
            from production_zero.persistence.session_writer import snapshot_game_state
            try:
                payload = snapshot_game_state(self._session_state)
                self._save_writer.submit(payload)
                if wait:
                    error = self._save_writer.poll(wait=True)
                    if error:
                        raise error
            except Exception as exc:
                self.statusBar().showMessage(f"Company save failed: {exc}. Progress remains in memory.")
                return False
        return True

    def closeEvent(self, event):  # noqa: N802
        if not self._save_session(wait=True):
            event.ignore()
            return
        if hasattr(self, "_save_writer"):
            self._save_timer.stop()
            self._save_poll_timer.stop()
            self._save_writer.shutdown()
        super().closeEvent(event)

    def _focus_unlock_tree(self, tabs: QTabWidget, resources_view: ResourcesViewV2, resource_id: str) -> None:
        tabs.setCurrentWidget(resources_view)
        resources_view._open_unlock_tree()
        tree = resources_view._cached_unlock_tree_panel
        if tree is not None:
            tree.focus_resource(resource_id)

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
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=3, max_lines=5, start_unlocked_lines=1)))
    state.resource_sites["site-1"] = FactoryHall(
        "site-1", "Mining Complex 1", 1, board_kind="resources", max_lines=3, specialization="machine.extractor",
        max_slots_per_line=10, start_unlocked_lines=1, start_slots_per_line=1,
    )
    for site_id, name, specialization in (
        ('site-2', 'Drilling Field 1', 'machine.drilling'),
        ('site-3', 'Agricultural Estate 1', 'machine.agriculture'),
    ):
        state.resource_sites[site_id] = FactoryHall(
            site_id, name, 1, board_kind='resources', max_lines=3,
            specialization=specialization, max_slots_per_line=10,
            start_unlocked_lines=1, start_slots_per_line=1,
        )
    state.energy_plants["plant-1"] = FactoryHall(
        "plant-1", "Plant 1", 1, board_kind="energy", max_lines=3,
        max_slots_per_line=5, start_unlocked_lines=1, start_slots_per_line=1,
    )
    for card_id, definition_id, card_kind in (
        ("test-drill-common-001", "machine.extractor", CardKind.MACHINE),
        ("test-drill-common-002", "machine.extractor", CardKind.MACHINE),
        ("test-drill-common-003", "machine.extractor", CardKind.MACHINE),
        ("test-solar-common-001", "energy.solar_array", CardKind.ENERGY),
        ("test-furnace-common-001", "machine.processor", CardKind.MACHINE),
        ("test-blast-furnace-common-001", "machine.processor", CardKind.MACHINE),
        ("starter-truck-common-001", "freight.truck", CardKind.FREIGHT),
        ("starter-truck-common-002", "freight.truck", CardKind.FREIGHT),
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
    initialize_production_progress(state, definitions)
    initialize_contracts(state, definitions)
    refresh_supply(state, definitions)
    for sample in (900, 940, 1010, 1100, 1180, 1250):
        bus.dispatch(RecordMetric("cash", sample))
    for sample in (2, 4, 7, 9, 8, 11):
        bus.dispatch(RecordMetric("energy.consumed", sample))
    for sample in (40, 52, 78, 101, 130, 145):
        bus.dispatch(RecordMetric("resource.iron_ore", sample))
    return state


def _copy_state(target: GameState, source: GameState) -> None:
    # Keep the shared state object used by views and commands, replacing every
    # subsystem (including research, communications and inventory history).
    for field in fields(GameState):
        setattr(target, field.name, getattr(source, field.name))


def _refresh_views(
    resources_view: ResourcesViewV2,
    factory_view: FactoryViewV2,
    energy_view: EnergyViewV2,
    freight_view: FreightView,
    inventory_view: InventoryView,
    charts_view: ChartsView | None,
    market_view: MarketView,
    contracts_view: ContractsView,
    supply_view: SupplyView,
    packs_view: PacksView,
    leaderboard_view: LeaderboardView,
    global_header: FactoryCommandDeckWidget,
) -> None:
    # Economic commands commit synchronously. Refresh the displayed projection
    # immediately, and defer only invisible projections until their tab is entered.
    tabs = supply_view.window().findChild(QTabWidget, "mainTabs")
    current = tabs.currentWidget() if tabs is not None else None
    for view in (resources_view, factory_view, energy_view, freight_view, inventory_view,
                 charts_view, market_view, contracts_view, supply_view, packs_view, leaderboard_view):
        if view is None:
            continue
        if tabs is None or view is current:
            _refresh_entered_view(view)
        else:
            view.setProperty("uiDirty", True)
    global_header.refresh()


def _refresh_entered_view(view):
    if view is None:
        return
    frontscreen = getattr(view, "show_frontscreen", None)
    if frontscreen is not None:
        frontscreen()
    elif isinstance(view, ResearchView):
        view._close_picker()
        view.review.hide()
        view.notice.hide()
    elif isinstance(view, ChartsView):
        view._show_overview()
    refresh = getattr(view, "refresh_view", None) or getattr(view, "refresh", None)
    if refresh is not None:
        refresh()
    view.setProperty("uiDirty", False)


def _refresh_active_runtime_view(
    tabs: QTabWidget,
    resources_view: ResourcesViewV2,
    factory_view: FactoryViewV2,
    energy_view: EnergyViewV2,
    freight_view: FreightView,
    event_feed_controller: EventFeedController,
    charts_view: ChartsView | None,
    market_view: MarketView,
    contracts_view: ContractsView,
    consortium_view: ConsortiumView,
    supply_view: SupplyView,
    packs_view: PacksView,
    leaderboard_view: LeaderboardView,
    global_header: FactoryCommandDeckWidget,
) -> None:
    event_feed_controller.observe()
    if not tabs.isVisible():
        return
    global_header.refresh()
    current = tabs.currentWidget()
    if current is resources_view:
        resources_view.refresh_runtime()
    elif current is factory_view:
        factory_view.refresh_runtime()
    elif current is energy_view:
        energy_view.refresh_runtime()
    elif current is freight_view:
        freight_view.refresh_runtime()
    elif charts_view is not None and current is charts_view:
        charts_view.refresh()
    elif current is market_view:
        if market_view is not None:
            market_view.refresh()
    elif current is contracts_view:
        contracts_view.refresh()
    elif current is consortium_view:
        consortium_view.refresh()
    elif current is supply_view:
        supply_view.refresh()
    elif current is packs_view:
        if packs_view is not None:
            packs_view.refresh()
    elif current is leaderboard_view:
        leaderboard_view.refresh()
    elif isinstance(current, ResearchView):
        current.refresh()
