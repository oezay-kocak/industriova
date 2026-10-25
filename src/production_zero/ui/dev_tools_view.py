from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.cards import RARITY_BONUS_RANGES_TENTHS, create_card_instance
from production_zero.core.commands import AddCard, AddCash, AddIndustrialScrap, AddResource, CommandBus, ConsumeResource, GrantPack, SetCash, UnlockProductionLine
from production_zero.core.definitions import CardDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.market import MARKET_EVENT_SECONDS
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK
from production_zero.core.resources import ResourceDefinition
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState
from production_zero.persistence.dev_save_store import DevJsonSaveStore, DevSaveError, IncompatibleSaveVersionError, InvalidSaveError, SaveNotFoundError


CARD_OPTIONS = {
    "Extractor": ("machine.extractor", CardKind.MACHINE),
    "Drilling Rig": ("machine.drilling", CardKind.MACHINE),
    "Harvester": ("machine.agriculture", CardKind.MACHINE),
    "Processor": ("machine.processor", CardKind.MACHINE),
    "Fabricator": ("machine.fabricator", CardKind.MACHINE),
    "Assembler": ("machine.assembler", CardKind.MACHINE),
    "Solar Array": ("energy.solar_array", CardKind.ENERGY),
    "Freight Truck": ("freight.truck", CardKind.FREIGHT),
    "Freight Train": ("freight.train", CardKind.FREIGHT),
    "Cargo Ship": ("freight.ship", CardKind.FREIGHT),
    "Cargo Aircraft": ("freight.aircraft", CardKind.FREIGHT),
}


class DevToolsView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        resources: dict[str, ResourceDefinition],
        simulation: SimulationEngine,
        refresh_callback: Callable[[], None],
        pause_callback: Callable[[], None],
        resume_callback: Callable[[], None],
        is_paused: Callable[[], bool],
        reset_callback: Callable[[], None],
        load_state_callback: Callable[[GameState], None],
        save_store: DevJsonSaveStore | None = None,
        session_save_callback: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__()
        self._state = state
        self._bus = command_bus
        self._definitions = definitions
        self._resources = resources
        self._simulation = simulation
        self._refresh_callback = refresh_callback
        self._pause_callback = pause_callback
        self._resume_callback = resume_callback
        self._is_paused = is_paused
        self._reset_callback = reset_callback
        self._load_state_callback = load_state_callback
        self._save_store = save_store or DevJsonSaveStore()
        self._session_save_callback = session_save_callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._panel("Persistence", self._build_persistence_controls()))
        layout.addWidget(self._panel("Time Controls", self._build_time_controls()))
        layout.addWidget(self._panel("Economy / Resources", self._build_economy_controls()))
        layout.addWidget(self._panel("Cards / Progression", self._build_card_controls()))
        layout.addWidget(self._panel("Research", self._build_research_controls()))
        layout.addStretch(1)

    def _build_research_controls(self) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._button("Grant 25 RP", lambda: self._research_dev("grant")))
        row.addWidget(self._button("Clear Research Cooldown", lambda: self._research_dev("cooldown")))
        row.addWidget(self._button("Refund Research Allocation", lambda: self._research_dev("reset")))
        return widget

    def _research_dev(self, action: str) -> None:
        from production_zero.core.research import grant_research_points
        if action == "grant":
            grant_research_points(self._state, 25, "Dev tools")
        elif action == "cooldown":
            self._state.research.respec_available_at = 0.0
            self._state.research.cooldown_notified = True
        elif action == "reset":
            self._state.research.unlocked_node_ids.clear()
            self._state.research.legacy_lane_node_ids.clear()
            self._state.research.specializations.clear()
        self._refresh_callback()

    def _panel(self, title: str, content: QWidget) -> QFrame:
        panel = QFrame()
        panel.setObjectName("devPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        label = QLabel(title.upper())
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        layout.addWidget(content)
        return panel

    def _build_time_controls(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for label, seconds in (
            ("+5 Minutes", 300),
            ("+1 Hour", 3_600),
            ("+1 Day", 86_400),
            ("+3 Days", 259_200),
        ):
            layout.addWidget(self._button(label, lambda checked=False, s=seconds: self._advance_time(s)))
        layout.addWidget(self._button("Market Tick Now", lambda: self._advance_to_market_tick()))
        layout.addWidget(self._button("Next Event", lambda: self._advance_to_next_event()))
        layout.addWidget(self._button("Pause / Resume", lambda: self._toggle_pause()))
        return widget

    def _build_economy_controls(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self._cash_amount = QSpinBox()
        self._cash_amount.setRange(0, 1_000_000)
        self._cash_amount.setValue(1000)
        layout.addWidget(QLabel("Cash"), 0, 0)
        layout.addWidget(self._cash_amount, 0, 1)
        layout.addWidget(self._button("Add Cash", lambda: self._add_cash()), 0, 2)
        layout.addWidget(self._button("Set Cash", lambda: self._set_cash()), 0, 3)

        self._resource_select = QComboBox()
        for resource in self._resources.values():
            self._resource_select.addItem(resource.name, resource.resource_id)
        self._resource_amount = QSpinBox()
        self._resource_amount.setRange(0, 1_000_000)
        self._resource_amount.setValue(100)
        self._scrap_amount = QSpinBox()
        self._scrap_amount.setRange(0, 1_000_000)
        self._scrap_amount.setValue(100)
        layout.addWidget(QLabel("Resource"), 1, 0)
        layout.addWidget(self._resource_select, 1, 1)
        layout.addWidget(self._resource_amount, 1, 2)
        layout.addWidget(self._button("Add", lambda: self._add_resource()), 1, 3)
        layout.addWidget(self._button("Fill", lambda: self._fill_resource()), 1, 4)
        layout.addWidget(self._button("Clear", lambda: self._clear_resource()), 1, 5)
        layout.addWidget(QLabel("Industrial Scrap"), 2, 0)
        layout.addWidget(self._scrap_amount, 2, 1)
        layout.addWidget(self._button("Add Scrap", lambda: self._add_scrap()), 2, 2)
        return widget

    def _build_card_controls(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self._card_select = QComboBox()
        self._card_select.addItems(list(CARD_OPTIONS))
        self._card_rarity = QComboBox()
        for rarity in Rarity:
            self._card_rarity.addItem(rarity.value.title(), rarity)
        self._card_bonus_tenths = QSpinBox()
        self._card_bonus_tenths.setSuffix(" /10%")
        self._card_bonus_tenths.setRange(0, 0)
        self._card_count = QSpinBox()
        self._card_count.setRange(1, 100)
        self._card_count.setValue(1)
        self._card_rarity.currentIndexChanged.connect(self._refresh_card_bonus_range)
        layout.addWidget(QLabel("Test Card"), 0, 0)
        layout.addWidget(self._card_select, 0, 1)
        layout.addWidget(QLabel("Rarity"), 0, 2)
        layout.addWidget(self._card_rarity, 0, 3)
        layout.addWidget(QLabel("Bonus"), 0, 4)
        layout.addWidget(self._card_bonus_tenths, 0, 5)
        layout.addWidget(QLabel("Count"), 0, 6)
        layout.addWidget(self._card_count, 0, 7)
        layout.addWidget(self._button("Create", lambda: self._create_cards()), 0, 8)
        layout.addWidget(self._button("Create Upgrade Test", lambda: self._create_upgrade_test()), 0, 10)
        layout.addWidget(self._button("Unlock Lines", lambda: self._unlock_all_lines()), 1, 0)
        layout.addWidget(self._button("Reset Test State", lambda: self._reset()), 1, 1)
        self._refresh_card_bonus_range()
        return widget

    def _button(self, label: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("devButton")
        button.clicked.connect(callback)
        return button

    def _build_persistence_controls(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button("NEW GAME", self._new_game))
        layout.addWidget(self._button("SAVE GAME", lambda: self._save_game()))
        layout.addWidget(self._button("LOAD GAME", lambda: self._load_game()))
        self._save_status = QLabel(f"Slot: {self._save_store.path.as_posix()}")
        self._save_status.setObjectName("devSaveStatus")
        layout.addWidget(self._save_status, 1)
        return widget

    def _set_save_status(self, text: str) -> None:
        self._save_status.setText(text)

    def _new_game(self) -> None:
        answer = QMessageBox.question(
            self, "New Game",
            "Start a new company? This replaces your current progress and autosave. "
            "Use SAVE GAME first to keep a manual backup you can restore with LOAD GAME.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            saved = self._reset()
            self._set_save_status("New game started" if saved is not False else "New game in memory; autosave failed. Save again before closing.")

    def _save_game(self) -> None:
        try:
            path = self._save_store.save(self._state)
        except DevSaveError:
            self._set_save_status("Save failed")
            return
        except OSError:
            self._set_save_status("Save failed")
            return
        self._set_save_status(f"Saved: {path.as_posix()}")
        if self._session_save_callback is not None and not self._session_save_callback():
            self._set_save_status("Manual backup saved; company autosave failed")

    def _load_game(self) -> None:
        try:
            loaded_state = self._save_store.load()
        except SaveNotFoundError:
            self._set_save_status("No save found")
            return
        except IncompatibleSaveVersionError:
            self._set_save_status("Load failed: incompatible save")
            return
        except (InvalidSaveError, DevSaveError, OSError):
            self._set_save_status("Load failed")
            return
        self._load_state_callback(loaded_state)
        self._refresh_callback()
        self._set_save_status(f"Loaded: {self._save_store.path.as_posix()}")

    def _advance_time(self, seconds: float) -> None:
        self._simulation.advance_time(self._state, seconds)
        self._refresh_callback()

    def _advance_to_market_tick(self) -> None:
        seconds = max(0.0, self._state.market.next_market_tick_seconds - self._state.market.elapsed_seconds)
        self._advance_time(seconds)

    def _advance_to_next_event(self) -> None:
        current_window = int(self._state.market.elapsed_seconds // MARKET_EVENT_SECONDS)
        target = (current_window + 1) * MARKET_EVENT_SECONDS
        self._advance_time(max(0.0, target - self._state.market.elapsed_seconds))

    def _toggle_pause(self) -> None:
        if self._is_paused():
            self._resume_callback()
        else:
            self._pause_callback()
        self._refresh_callback()

    def _add_cash(self) -> None:
        self._bus.dispatch(AddCash(self._cash_amount.value()))
        self._refresh_callback()

    def _set_cash(self) -> None:
        self._bus.dispatch(SetCash(self._cash_amount.value()))
        self._refresh_callback()

    def _add_resource(self) -> None:
        self._bus.dispatch(AddResource(self._resource_select.currentData(), self._resource_amount.value()))
        self._refresh_callback()

    def _add_scrap(self) -> None:
        self._bus.dispatch(AddIndustrialScrap(self._scrap_amount.value()))
        self._refresh_callback()

    def _fill_resource(self) -> None:
        stock = self._state.ensure_resource(self._resource_select.currentData())
        self._bus.dispatch(AddResource(self._resource_select.currentData(), stock.free_capacity))
        self._refresh_callback()

    def _clear_resource(self) -> None:
        stock = self._state.ensure_resource(self._resource_select.currentData())
        if stock.amount > 0:
            self._bus.dispatch(ConsumeResource(self._resource_select.currentData(), stock.amount))
        self._refresh_callback()

    def _create_cards(self) -> None:
        definition_id, card_kind = CARD_OPTIONS[self._card_select.currentText()]
        rarity = Rarity(self._card_rarity.currentData())
        for _ in range(self._card_count.value()):
            self._bus.dispatch(
                AddCard(
                    create_card_instance(
                        card_id=self._next_dev_card_id(),
                        definition_id=definition_id,
                        card_kind=card_kind,
                        rarity=rarity,
                        bonus_tenths=self._card_bonus_tenths.value(),
                    )
                )
            )
        self._refresh_callback()

    def _create_craft_set(self) -> None:
        from production_zero.core.crafting import CRAFT_INPUT_COUNT

        original_count = self._card_count.value()
        self._card_count.setValue(CRAFT_INPUT_COUNT)
        self._create_cards()
        self._card_count.setValue(original_count)

    def _create_upgrade_test(self) -> None:
        self._bus.dispatch(AddIndustrialScrap(100))
        self._bus.dispatch(
            AddCard(
                create_card_instance(
                    card_id=self._next_dev_card_id(),
                    definition_id="machine.extractor",
                    card_kind=CardKind.MACHINE,
                    rarity=Rarity.RARE,
                    bonus_tenths=94,
                )
            )
        )
        self._refresh_callback()

    def _next_dev_card_id(self) -> str:
        index = len(self._state.cards) + 1
        card_id = f"dev-card-{index:04d}"
        while card_id in self._state.cards:
            index += 1
            card_id = f"dev-card-{index:04d}"
        return card_id

    def _refresh_card_bonus_range(self) -> None:
        rarity = Rarity(self._card_rarity.currentData())
        lower, upper = RARITY_BONUS_RANGES_TENTHS[rarity]
        self._card_bonus_tenths.setRange(lower, upper)
        self._card_bonus_tenths.setValue(lower)

    def _unlock_all_lines(self) -> None:
        original_cash = self._state.cash.amount
        board_units = (
            ("factory", self._state.halls),
            ("resources", self._state.resource_sites),
            ("energy", self._state.energy_plants),
        )
        for board_kind, units in board_units:
            for hall in units.values():
                for line in hall.production_lines:
                    if not line.unlocked:
                        self._state.cash.amount = max(self._state.cash.amount, line.unlock_cost)
                        self._bus.dispatch(UnlockProductionLine(hall.hall_id, line.line_id, board_kind))
        self._state.cash.amount = original_cash
        self._refresh_callback()

    def _reset(self) -> bool | None:
        result = self._reset_callback()
        self._refresh_callback()
        return result

    def _grant_pack(self, pack_type: str) -> None:
        self._bus.dispatch(GrantPack(pack_type, "dev"))
        self._refresh_callback()
