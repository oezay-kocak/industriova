from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from production_zero.core.commands import AddCash, AddIndustrialScrap, AddResource, BuildHall, CommandBus, SetCash, SetResourceCapacity
from production_zero.core.state import FactoryHall, GameState
from production_zero.persistence.dev_save_store import (
    DEV_SAVE_FILENAME,
    SAVE_VERSION,
    DevJsonSaveStore,
    IncompatibleSaveVersionError,
    InvalidSaveError,
    SaveNotFoundError,
)
from production_zero.ui.dev_tools_view import DevToolsView


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _state() -> GameState:
    state = GameState(rng_seed=1201)
    bus = CommandBus(state)
    bus.dispatch(AddCash(500))
    bus.dispatch(SetResourceCapacity("iron_ore", 300))
    bus.dispatch(AddResource("iron_ore", 75))
    bus.dispatch(AddIndustrialScrap(12))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=3)))
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


def test_dev_json_save_creates_versioned_file(tmp_path: Path) -> None:
    state = _state()
    store = DevJsonSaveStore(tmp_path)

    path = store.save(state)

    assert path == tmp_path / DEV_SAVE_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["save_version"] == SAVE_VERSION
    assert payload["state"]["cash"]["amount"] == 500
    assert payload["state"]["resources"]["iron_ore"]["amount"] == 75


def test_dev_json_save_loads_saved_state(tmp_path: Path) -> None:
    state = _state()
    store = DevJsonSaveStore(tmp_path)
    store.save(state)

    loaded = store.load()

    assert loaded.rng_seed == 1201
    assert loaded.cash.amount == 500
    assert loaded.resources["iron_ore"].amount == 75
    assert loaded.resources["iron_ore"].capacity == 300
    assert loaded.scrap.amount == 12
    assert loaded.halls["hall-1"].name == "Starter Hall"


def test_dev_json_save_load_restores_state_after_mutation(tmp_path: Path) -> None:
    state = _state()
    bus = CommandBus(state)
    store = DevJsonSaveStore(tmp_path)
    store.save(state)

    bus.dispatch(SetCash(9999))
    bus.dispatch(AddResource("iron_ore", 200))
    state.scrap.amount = 0
    loaded = store.load()
    _copy_state(state, loaded)

    assert state.cash.amount == 500
    assert state.resources["iron_ore"].amount == 75
    assert state.scrap.amount == 12


def test_dev_json_save_missing_file_is_handled(tmp_path: Path) -> None:
    store = DevJsonSaveStore(tmp_path)

    try:
        store.load()
    except SaveNotFoundError:
        pass
    else:
        raise AssertionError("Missing save should raise SaveNotFoundError.")


def test_dev_json_save_corrupt_json_is_handled(tmp_path: Path) -> None:
    store = DevJsonSaveStore(tmp_path)
    store.path.write_text("{not-json", encoding="utf-8")

    try:
        store.load()
    except InvalidSaveError:
        pass
    else:
        raise AssertionError("Corrupt save should raise InvalidSaveError.")


def test_dev_json_save_unknown_version_is_handled(tmp_path: Path) -> None:
    store = DevJsonSaveStore(tmp_path)
    store.path.write_text(json.dumps({"save_version": 999, "state": {}}), encoding="utf-8")

    try:
        store.load()
    except IncompatibleSaveVersionError:
        pass
    else:
        raise AssertionError("Unknown save version should raise IncompatibleSaveVersionError.")


def test_dev_tools_save_load_buttons_roundtrip_state(tmp_path: Path) -> None:
    _app()
    state = _state()
    bus = CommandBus(state)
    store = DevJsonSaveStore(tmp_path)
    refresh_count = 0

    def refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1

    view = DevToolsView(
        state,
        bus,
        definitions={},
        resources={},
        simulation=None,
        refresh_callback=refresh,
        pause_callback=lambda: None,
        resume_callback=lambda: None,
        is_paused=lambda: False,
        reset_callback=lambda: None,
        load_state_callback=lambda loaded_state: _copy_state(state, loaded_state),
        save_store=store,
    )

    buttons = {button.text(): button for button in view.findChildren(QPushButton)}
    assert {"SAVE GAME", "LOAD GAME"} <= set(buttons)

    buttons["SAVE GAME"].click()
    bus.dispatch(SetCash(42))
    buttons["LOAD GAME"].click()

    assert state.cash.amount == 500
    assert refresh_count == 1
    assert view.findChild(QLabel, "devSaveStatus").text().startswith("Loaded:")


def test_dev_tools_missing_save_reports_status(tmp_path: Path) -> None:
    _app()
    state = _state()
    view = DevToolsView(
        state,
        CommandBus(state),
        definitions={},
        resources={},
        simulation=None,
        refresh_callback=lambda: None,
        pause_callback=lambda: None,
        resume_callback=lambda: None,
        is_paused=lambda: False,
        reset_callback=lambda: None,
        load_state_callback=lambda loaded_state: _copy_state(state, loaded_state),
        save_store=DevJsonSaveStore(tmp_path),
    )

    view._load_game()

    assert view.findChild(QLabel, "devSaveStatus").text() == "No save found"
