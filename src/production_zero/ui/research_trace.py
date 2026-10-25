"""Opt-in purchase + post-click event-loop diagnostics; no release logging.

Set PRODUCTION_ZERO_RESEARCH_TRACE to a JSONL path before launching the app.
One record covers the callback and the following two seconds of real Qt events.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import gc
import json
import os
from pathlib import Path
from time import perf_counter_ns
from threading import get_ident

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QApplication


class ResearchTrace(QObject):
    WINDOW_MS = 2000

    def __init__(self, app, path):
        super().__init__(app)
        self.app, self.path = app, Path(path)
        self.ui_thread = get_ident()
        self.record = None
        self.completed = []
        self._patches = []
        self._workers = 0
        self._worker_ended_ns = 0
        self._gc_starts = {}
        self._writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pz-trace")
        self._heartbeat_last = perf_counter_ns()
        self.heartbeat = QTimer(self)
        self.heartbeat.setTimerType(Qt.TimerType.PreciseTimer)
        self.heartbeat.setInterval(16)
        self.heartbeat.timeout.connect(self._beat)
        self.heartbeat.start()
        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.timeout.connect(self.finish)
        gc.callbacks.append(self._gc)
        self._install()

    def _beat(self):
        now = perf_counter_ns()
        if self.record is not None:
            gap = (now - self._heartbeat_last) / 1e6
            self.record["heartbeat"].append(dict(start_ms=(self._heartbeat_last - self.record["start_ns"]) / 1e6, gap_ms=gap))
        self._heartbeat_last = now

    def begin(self, node_id):
        if self.record is not None:
            self.finish(force=True)
        start = perf_counter_ns()
        objects = len(gc.get_objects())
        self.record = dict(kind="RESEARCH_PURCHASE_TRACE", node_id=node_id, start_ns=start,
                           stages={}, intervals=[], events=Counter(), slow_events=[], heartbeat=[], gc=[],
                           gc_before=gc.get_stats(), objects_before=objects, assets_before=self._assets(),
                           subscribers=Counter(), paint_regions=[], diagnostic_begin_ms=(perf_counter_ns() - start) / 1e6)
        self.finish_timer.start(self.WINDOW_MS)

    def stage(self, name, start, duration):
        record = self.record
        if record is None:
            return
        ms = duration / 1e6
        aggregate = record["stages"].setdefault(name, dict(calls=0, total_ms=0, max_ms=0))
        aggregate["calls"] += 1
        aggregate["total_ms"] += ms
        aggregate["max_ms"] = max(aggregate["max_ms"], ms)
        if ms >= 1 and len(record["intervals"]) < 1500:
            record["intervals"].append(dict(stage=name, start_ms=(start - record["start_ns"]) / 1e6, duration_ms=ms))

    def _wrap(self, owner, attr, name, *, purchase=False, subscriber=False, worker=False):
        original = getattr(owner, attr)
        @wraps(original)
        def measured(*args, **kwargs):
            if worker:
                # Track even a save that starts before a purchase, so a queued
                # purchase cannot end its trace while an older save is active.
                self._workers += 1
                start = perf_counter_ns()
                try:
                    return original(*args, **kwargs)
                finally:
                    self.stage(name, start, perf_counter_ns() - start)
                    self._workers -= 1
                    self._worker_ended_ns = perf_counter_ns()
            if purchase:
                self.begin(str(args[1]))
            if self.record is None or get_ident() != self.ui_thread:
                return original(*args, **kwargs)
            start = perf_counter_ns()
            if subscriber:
                self.record["subscribers"][name] += 1
            try:
                return original(*args, **kwargs)
            finally:
                self.stage(name, start, perf_counter_ns() - start)
                if purchase:
                    self.finish_timer.start(self.WINDOW_MS)
        self._patches.append((owner, attr, original))
        setattr(owner, attr, measured)

    def _install(self):
        from production_zero.core import research, modifiers, commands, simulation
        from production_zero.persistence import sqlite_store, session_writer
        from production_zero.ui import main_window, research_view, research_specialization, event_feed, factory_view, factory_view_v2, market_view, contracts_view, resource_icons
        targets = [
            (json, "dumps", "json_encoding"),
            (research_view.ResearchView, "_purchase", "purchase_callback"),
            (research_view.ResearchView, "_purchase_specialization", "specialization_callback"),
            (commands.CommandBus, "dispatch", "command_dispatch"),
            (research, "purchase_research", "state_mutation"),
            (research, "purchase_specialization", "specialization_mutation"),
            (modifiers, "_research_modifiers", "modifier_cache_lookup_rebuild"),
            (research_view, "node_state", "prerequisite_state"),
            (research_view.ResearchView, "refresh", "research_header_and_refresh"),
            (research_view.ResearchTreeCanvas, "refresh", "affected_node_and_connector_updates"),
            (research_view.ResearchNodeButton, "refresh", "node_tooltip_accessibility_presentation"),
            (research_specialization.SpecializationButton, "refresh", "specialization_presentation"),
            (research_view.ResearchTreeCanvas, "connection_segments", "connector_geometry"),
            (research_view.ResearchTreeCanvas, "paintEvent", "canvas_paint"),
            (research_view.ResearchNodeButton, "paintEvent", "node_paint"),
            (research_view.ResearchTreeCanvas, "_position_specializations", "canvas_layout_activate"),
            (factory_view_v2.FactoryCommandDeckWidget, "refresh", "global_header_refresh"),
            (main_window.MainWindow, "_save_session", "save_request"),
            (sqlite_store, "serialize_game_state", "save_snapshot_serialization"),
            (session_writer, "snapshot_game_state", "save_snapshot_detach"),
            (session_writer.SessionWriter, "_write", "save_worker_encode_and_commit"),
            (session_writer.SessionWriter, "submit", "save_queue_enqueue"),
            (session_writer.SessionWriter, "poll", "save_completion_poll"),
            (event_feed.EventFeedController, "observe", "event_feed_observe"),
            (event_feed.EventFeedWidget, "_tick", "event_feed_timer"),
            (event_feed.EventFeedWidget, "_present_next", "ticker_presentation"),
            (event_feed.EventFeedWidget, "refresh_communications", "inbox_stylesheet_polish"),
            (event_feed.EventFeedWidget, "_show_history", "history_open"),
            (event_feed.EventFeedWidget, "_show_inbox", "inbox_open"),
            (factory_view.FactoryViewBase, "_advance_simulation", "simulation_timer_and_subscribers"),
            (simulation.SimulationEngine, "advance_time", "simulation_core"),
            (factory_view.FactoryViewBase, "_refresh_runtime_widgets", "factory_runtime_widgets"),
            (main_window, "_refresh_active_runtime_view", "active_runtime_subscriber"),
            (main_window, "_refresh_views", "full_views_subscriber"),
            (market_view.MarketView, "refresh", "market_refresh_subscriber"),
            (contracts_view.ContractsView, "refresh", "contracts_refresh_subscriber"),
            (resource_icons.ResourceIconWidget, "paintEvent", "resource_icon_paint"),
        ]
        for owner, attr, name in targets:
            self._wrap(owner, attr, name, purchase=name in ("purchase_callback", "specialization_callback"), subscriber="subscriber" in name, worker=name == "save_worker_encode_and_commit")

    @staticmethod
    def _assets():
        from production_zero.ui import resource_art
        return {name: getattr(resource_art, name).cache_info()._asdict()
                for name in ("resource_raster_image", "_scaled_resource_raster")}

    def _gc(self, phase, info):
        generation = info["generation"]
        if phase == "start":
            self._gc_starts[generation] = perf_counter_ns()
        elif self.record is not None:
            start = self._gc_starts.pop(generation, perf_counter_ns())
            self.record["gc"].append(dict(generation=generation, start_ms=(start - self.record["start_ns"]) / 1e6,
                                           duration_ms=(perf_counter_ns() - start) / 1e6, collected=info["collected"]))

    def notify(self, receiver, event, callback):
        if self.record is None:
            start = perf_counter_ns()
            result = callback(receiver, event)
            if self.record is not None and event.type() == QEvent.Type.MouseButtonRelease:
                self.stage("button_click_dispatch", start, perf_counter_ns() - start)
            return result
        start = perf_counter_ns()
        kind = event.type().name
        identity = f"{type(receiver).__name__}:{receiver.objectName()}"
        if event.type() in (QEvent.Type.Paint, QEvent.Type.LayoutRequest, QEvent.Type.Resize,
                            QEvent.Type.PolishRequest, QEvent.Type.StyleChange, QEvent.Type.UpdateRequest,
                            QEvent.Type.Timer, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonPress):
            self.record["events"][f"{kind}:{identity}"] += 1
        if event.type() == QEvent.Type.Paint and len(self.record["paint_regions"]) < 200:
            rect = event.region().boundingRect()
            self.record["paint_regions"].append(dict(widget=identity, region=[rect.x(), rect.y(), rect.width(), rect.height()],
                                                     widget_size=[receiver.width(), receiver.height()]))
        try:
            return callback(receiver, event)
        finally:
            duration = (perf_counter_ns() - start) / 1e6
            if self.record is not None and duration >= 5:
                self.record["slow_events"].append(dict(event=kind, receiver=identity, start_ms=(start - self.record["start_ns"]) / 1e6, duration_ms=duration))

    def finish(self, *, force=False):
        if not force and (self._workers or (self.record is not None and self._worker_ended_ns
                                          and perf_counter_ns() - self._worker_ended_ns < self.WINDOW_MS * 1e6)):
            self.finish_timer.start(500)
            return
        self._beat()
        record, self.record = self.record, None
        if record is None:
            return
        self.finish_timer.stop()
        record["window_ms"] = (perf_counter_ns() - record.pop("start_ns")) / 1e6
        record["gc_after"] = gc.get_stats()
        record["object_count_delta"] = len(gc.get_objects()) - record.pop("objects_before")
        record["assets_after"] = self._assets()
        record["max_heartbeat_gap_ms"] = max((h["gap_ms"] for h in record["heartbeat"]), default=0)
        worst = max(record["heartbeat"], key=lambda h: h["gap_ms"], default=None)
        record["worst_gap_operations"] = [
            item for item in record["intervals"] if worst
            and item["start_ms"] < worst["start_ms"] + worst["gap_ms"]
            and item["start_ms"] + item["duration_ms"] > worst["start_ms"]
        ]
        record["slow_events"] = sorted(record["slow_events"], key=lambda item: item["duration_ms"], reverse=True)[:30]
        self.completed.append(record)
        self._writer.submit(self._write, record)

    def _write(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")

    def close(self):
        self.finish(force=True)
        self.heartbeat.stop()
        gc.callbacks.remove(self._gc)
        for owner, attr, original in reversed(self._patches):
            setattr(owner, attr, original)
        self._writer.shutdown(wait=True)


class TracedApplication(QApplication):
    def __init__(self, args, path):
        self.research_trace = None
        super().__init__(args)
        self.research_trace = ResearchTrace(self, path)

    def notify(self, receiver, event):
        trace = self.research_trace
        if trace is None:
            return super().notify(receiver, event)
        return trace.notify(receiver, event, super().notify)


def diagnostic_application(args):
    path = os.environ.get("PRODUCTION_ZERO_RESEARCH_TRACE")
    return TracedApplication(args, path) if path else QApplication(args)
