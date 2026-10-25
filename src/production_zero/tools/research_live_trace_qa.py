"""Continuous event-loop tracing with a developed, long-history QA company."""
import argparse
from importlib.resources import files
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabWidget
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.history import MetricSeries
from production_zero.core.research import grant_research_points, purchase_research, research_catalog
from production_zero.core.progression import production_options
from production_zero.core.state import FactoryHall
from production_zero.core.contracts import DAILY, accept_contract
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow, _create_initial_state
from production_zero.ui.research_view import ResearchView
from production_zero.ui.research_trace import TracedApplication
from production_zero.ui.event_feed import FeedEvent


def developed_state(samples):
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    state = _create_initial_state(resources, definitions)
    state.company.level = 120
    state.cash.amount = 2_000_000
    state.warehouse_capacity = 10_000_000
    state.production_progress.unlocked_production_ids.update(p.production_id for p in production_options(definitions))
    state.production_progress.pending_unlock_ids.clear()
    for index, (collection, did, kind, count) in enumerate((
        (state.resource_sites, "machine.extractor", CardKind.MACHINE, 3),
        (state.halls, "machine.processor", CardKind.MACHINE, 3),
        (state.energy_plants, "energy.solar_array", CardKind.ENERGY, 2),
    )):
        for unit in range(count):
            hall = FactoryHall(f"qa-{index}-{unit}", f"QA Unit {index}-{unit}", 6)
            collection[hall.hall_id] = hall
            for slot_index, slot in enumerate(hall.slots):
                cid = f"qa-card-{index}-{unit}-{slot_index}"
                card = create_card_instance(cid, did, kind, Rarity.COMMON)
                state.cards[cid] = card
                slot.card_id = cid
                if kind == CardKind.MACHINE:
                    options = definitions[did].available_production_options
                    option = options[0]
                    state.ensure_machine_production(cid, option.output_resource, option.production_id)
    from production_zero.tools.economy_stress_test import _install_stress_contract_freight_fleet
    _install_stress_contract_freight_fleet(state)
    for rid, stock in state.resources.items():
        stock.amount = 1000
        state.production_progress.lifetime_produced[rid] = 100000
    offer = state.contracts.offers[DAILY][0]
    accept_contract(state, DAILY, offer.contract_id, definitions, selected_resource_id="iron_ore")
    grant_research_points(state, 200, "Developed QA")
    for node in research_catalog()[1].values():
        if node.tree_id in ("industry.electronics", "company.storage") and node.row <= 6:
            purchase_research(state, node.id)
    purchase_research(state, "company.general.s1.major")
    state.communications.add_unlocks([p.production_id for p in production_options(definitions)][:30])
    state.communications.pending_activity.clear()
    # Simulation writes these exact three metrics for all resources every 250 ms.
    # 14,400 points represents one hour, well below the existing 86,400-point cap.
    for rid, stock in state.resources.items():
        for prefix, value in (("resource", stock.amount), ("rate.production", 0.0), ("rate.consumption", 0.0)):
            metric = f"{prefix}.{rid}"
            state.history.series[metric] = MetricSeries(metric, values=[value] * samples)
    for metric, value in (("cash", state.cash.amount), ("energy.generated", 1000.), ("energy.consumed", 100.)):
        state.history.series[metric] = MetricSeries(metric, values=[value] * samples)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/research-live-trace/before")
    parser.add_argument("--samples", type=int, default=14400)
    parser.add_argument("--reference-ui-json", action="store_true",
                        help="Replay the pre-fix UI-thread encoding for comparison.")
    parser.add_argument("--idle-control", action="store_true",
                        help="Trace the same timers without purchasing or saving.")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    state = developed_state(args.samples)
    store = SQLiteSaveStore(output / "qa-company.sqlite")
    store.initialize()
    store.save("company", state)
    del state
    if args.reference_ui_json:
        def reference_save(self, *, wait=False):
            from production_zero.persistence.sqlite_store import serialize_game_state
            self._save_writer.submit(json.dumps(serialize_game_state(self._session_state), sort_keys=True))
            return self._save_writer.poll(wait=True) is None if wait else True
        MainWindow._save_session = reference_save
    app = TracedApplication([], output / "purchases.jsonl")
    if args.idle_control:
        app.research_trace.WINDOW_MS = 10000
    _load_qa_fonts()
    window = MainWindow(development_mode=False, save_store=store)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    for i in range(10):
        window._event_feed.push(FeedEvent("research", f"QA history event {i}"))
    def click():
        if args.idle_control:
            app.research_trace.begin("idle-control")
        else:
            QTest.mouseClick(view.canvas.buttons["company.general.s1.n1"], Qt.MouseButton.LeftButton)
        QTimer.singleShot(3500, done)
    def done():
        if app.research_trace.record is not None:
            QTimer.singleShot(500, done)
            return
        meta = dict(platform=app.platformName(), samples_per_series=args.samples,
                    history_series=len(view._state.history.series), cards=len(view._state.cards),
                    owned_research=len(view._state.research.unlocked_node_ids),
                    unlocked_products=len(view._state.production_progress.unlocked_production_ids),
                    sqlite_bytes=store._path.stat().st_size)
        (output / "state.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        window.close()
        app.quit()
    QTimer.singleShot(1500, click)
    app.exec()
    app.research_trace.close()
    record = app.research_trace.completed[-1]
    print(json.dumps(dict(heartbeat_ms=record["max_heartbeat_gap_ms"], stages=record["stages"], gc=record["gc"], slow_events=record["slow_events"][:5])))


if __name__ == "__main__":
    main()
