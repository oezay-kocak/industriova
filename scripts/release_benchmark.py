"""Identical standalone production/card/save workloads for release comparisons."""
from __future__ import annotations

import argparse
from dataclasses import replace
from importlib.resources import files
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter
import tracemalloc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QGridLayout, QWidget
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import FactoryHall, HallSlot, MachineProductionState
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.ui.main_window import _create_initial_state
from production_zero.ui.factory_view_v2 import FactoryV2MachineCard


def measure(action, repetitions=7):
    values = []
    for _ in range(repetitions):
        start = perf_counter()
        action()
        values.append((perf_counter() - start) * 1000)
    return round(median(values), 3)


def run(output):
    app = QApplication.instance() or QApplication([])
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    results = []
    for count in (10, 50, 100, 500):
        state = _create_initial_state(resources, definitions)
        state.cards.clear()
        state.halls.clear()
        state.resource_sites.clear()
        state.energy_plants.clear()
        state.machine_production.clear()
        state.warehouse_capacity = 1e15
        machine = definitions["machine.extractor"]
        option = next(o for o in machine.available_production_options if o.output_resource == "iron_ore")
        definition_set = dict(definitions)
        definition_set["energy.solar_array"] = replace(definitions["energy.solar_array"], base_power_output=1e12)
        solar = create_card_instance("benchmark-power", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)
        state.cards[solar.card_id] = solar
        state.energy_plants["power"] = FactoryHall("power", "Power", 1, slots=[HallSlot(0, solar.card_id)], board_kind="energy")
        host = QWidget()
        layout = QGridLayout(host)
        widgets = []
        for index in range(count):
            card = create_card_instance(f"benchmark-{index}", machine.definition_id, CardKind.MACHINE, Rarity.COMMON)
            state.cards[card.card_id] = card
            slot = HallSlot(0, card.card_id)
            state.resource_sites[card.card_id] = FactoryHall(card.card_id, "Benchmark", 1, slots=[slot], board_kind="resources")
            production = MachineProductionState(card.card_id, option.output_resource, option.production_id)
            state.machine_production[card.card_id] = production
            widget = FactoryV2MachineCard(slot, card, machine, production, state)
            layout.addWidget(widget, index // 10, index % 10)
            widgets.append(widget)
        engine = SimulationEngine(definition_set, utc_now=lambda: 1792324800.0)
        engine.advance_time(state, 1)
        host.resize(host.sizeHint())
        host.show()
        app.processEvents()
        pixmap = QPixmap(host.size())
        render_ms = measure(lambda: host.render(pixmap))
        def update_cards():
            for widget in widgets:
                widget.set_data(widget._slot, widget._card, widget._definition, widget._production_state, state)
            app.processEvents()
        refresh_ms = measure(update_cards)
        tick_ms = measure(lambda: engine.advance_time(state, 1))
        for series in state.history.series.values():
            series.values = [float(i) for i in range(240)]
        snapshot_ms = measure(lambda: snapshot_game_state(state))
        snapshot = snapshot_game_state(state)
        encoding_ms = measure(lambda: encode_snapshot(snapshot), 3)
        payload = encode_snapshot(snapshot)
        store = SQLiteSaveStore(output.parent / f"benchmark-{count}.sqlite")
        store.initialize()
        commit_ms = measure(lambda: store.save_payload("company", payload), 3)
        full_save_ms = measure(lambda: store.save_payload("company", encode_snapshot(snapshot_game_state(state))), 3)
        load_ms = measure(lambda: store.load("company"), 3)
        results.append(dict(cards=count, render_ms=render_ms, refresh_ms=refresh_ms, tick_ms=tick_ms, snapshot_ms=snapshot_ms, encoding_ms=encoding_ms, commit_ms=commit_ms, full_save_ms=full_save_ms, load_ms=load_ms, payload_bytes=len(payload)))
        host.close()
        host.deleteLater()
        app.processEvents()
        print(json.dumps(results[-1]), flush=True)
    output.write_text(json.dumps({"method": "median; same process; offscreen Qt; 240 history samples; 7 repetitions (encode/commit/load: 3)", "results": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(args.output)
