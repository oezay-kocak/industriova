"""Opt-in playtest diagnostics; no prices, progression or simulation rules change."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from functools import wraps
import gc
from importlib.resources import files
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import sqlite3
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import traceback
from zipfile import ZipFile, ZIP_DEFLATED

from PySide6.QtCore import QObject, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea

from production_zero.diagnostics.recorder import PerformanceRecorder, atomic_json


REPORT_README = """INDUSTRIOVA – lokaler Performance-Testbericht

Dieses Paket enthält Messdaten der betreffenden Spielsitzung und – sofern
erfolgreich gespeichert – den letzten vollständigen Spielstand company.sqlite.
baseline.sqlite ist die explizit gesetzte Test-Ausgangslage oder der erste
erfolgreich gesicherte Zustand. Ohne SET TEST START kann dieser noch eine
weitgehend leere Anfangsfirma enthalten. Ein Export verändert keinen Spielstand.

performance*.jsonl: Prozesswerte alle fünf REALEN Sekunden; zugeordnete
Simulations-, Oberflächen-, Speicher- und Befehlszeiten; langsame Qt-Ereignisse;
Ruckler-Markierungen; Fehler. Die aktuelle Datei ist performance.jsonl,
performance.1.jsonl ist ihre unmittelbare Vorgängerdatei, danach .2 und .3.
Die Dateien rotieren bei je acht MiB: maximal ungefähr 32 MiB je Sitzung.
summary.json behält begrenzte Gesamtzähler und Spitzen auch nach Rotation.
session.json enthält Buildkennung, Betriebssystem und technische Umgebungsdaten.

rss_bytes = physischer Prozess-Arbeitsspeicher; private_bytes = privat zugesagter
Speicher. page_faults_total enthält weiche UND harte Seitenfehler und beweist
keine Auslagerung auf eine Festplatte. cpu_one_core_percent bezieht 100 Prozent
auf einen vollständig beschäftigten CPU-Kern; cpu_machine_percent normiert auf
alle logischen Kerne. Kurze CPU-Spitzen zwischen zwei Messungen können fehlen.

ui_heartbeat_gap ist der Abstand eines 100-ms-Oberflächentimers, KEINE Bildrate.
Ein großer Abstand deutet auf verzögerte Ereignisverarbeitung hin. Ein alter
game_summary_age_ms-Wert während eines Hängers bedeutet, dass die letzte sichere
Zusammenfassung aus dem Oberflächen-Thread nicht aktualisiert werden konnte.
Bei mindestens einer halben Sekunde ohne Herzschlag kann blocked_ui_stack den
Python-Aufrufstapel des Oberflächen-Threads zeigen, ohne lokale Variablen.
Timings sind inklusive Unteraufrufen; sie dürfen nicht addiert werden. Die P95
pro Messfenster bezieht sich auf höchstens die letzten 256 erfassten Werte.

SET TEST START sichert nach dem Aufbau die Test-Ausgangslage. F8 markiert einen
bemerkten Ruckler; die Taste kann erst nach Ende einer Blockade verarbeitet werden.
F9 exportiert den aktuellen Bericht im Hintergrund. Neue Exporte ersetzen nur
das Paket dieser Sitzung. Nach normalem Beenden entsteht ebenfalls ein Export.
Bei einem Absturz bleiben die bereits geschriebenen Protokolle im Sitzungsordner;
der reguläre Autosave liegt im benachbarten saves-Ordner. Es wird nichts hochgeladen.

Die Diagnose ist eine Hilfestellung, kein Beweis für eine eindeutige Fehlerursache.
Messung, Export und Kopieren brauchen selbst Rechenzeit und sind entsprechend
gekennzeichnet. Preise, Regeln und Ausbaugrenzen dieses Builds entsprechen dem
aktuellen Spielcode. Vorgeschlagene neue Limits und Preisfaktoren sind NICHT aktiv.
"""


def enabled():
    return os.environ.get("PRODUCTION_ZERO_PERFORMANCE_TEST") == "1"


class PerformanceApplication(QApplication):
    def notify(self, receiver, event):
        probe = getattr(self, "performance_probe", None)
        if probe is None or probe.closed:
            return super().notify(receiver, event)
        start = monotonic()
        try:
            return super().notify(receiver, event)
        finally:
            elapsed = monotonic() - start
            if elapsed >= .1:
                try:
                    if probe.recorder.timing("qt_slow_event", elapsed):
                        probe.recorder.event("qt_slow_event", duration_ms=round(elapsed*1000, 3),
                                             receiver=receiver.metaObject().className(),
                                             object_name=receiver.objectName()[:80], event_type=int(event.type()))
                except Exception:
                    pass


def create_application(args):
    return PerformanceApplication(args)


def backup_database(source, target):
    """SQLite's online backup pins a committed state, including split history."""
    source, target = Path(source), Path(target)
    if not source.is_file():
        return {"included": False, "reason": "No successful save exists yet"}
    temporary = target.with_suffix(".tmp.sqlite")
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                started = monotonic()
                def progress(status, remaining, total):
                    if monotonic() - started > 30:
                        raise TimeoutError("Diagnostic backup timed out")
                src.backup(dst, pages=256, progress=progress, sleep=.02)
                dst.commit()
                if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Diagnostic copy failed its SQLite check")
                row = dst.execute("SELECT state_json FROM saves WHERE slot='company'").fetchone()
                payload = json.loads(row[0]) if row else {}
        temporary.replace(target)
        return {"included": True, "save_simulation_seconds": payload.get("market", {}).get("elapsed_seconds"),
                "cards": len(payload.get("cards", {})), "bytes": target.stat().st_size}
    finally:
        if temporary.exists():
            temporary.unlink()


class PerformanceProbe(QObject):
    def __init__(self, app, save_path, *, directory=None, recorder_options=None):
        super().__init__(app)
        from production_zero.config import APP_VERSION
        self.app = app
        self.save_path = Path(save_path)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        root = Path(directory) if directory is not None else self.save_path.parent.parent / "diagnostics"
        self.directory = root / f"session-{stamp}-{secrets.token_hex(3)}"
        build_path = files("production_zero.data").joinpath("performance_build.json")
        build = json.loads(build_path.read_text(encoding="utf-8")) if build_path.is_file() else {"source_run": True}
        metadata = {"application_version": APP_VERSION, "build": build,
                    "python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
                    "logical_cpu_count": os.cpu_count(), "frozen": bool(getattr(sys, "frozen", False)),
                    "sample_interval_seconds": 5, "game_summary_interval_seconds": 30,
                    "max_log_files": 4, "max_log_file_mib": 8,
                    "data_policy": "Local technical diagnostics and game save; no upload or environment dump"}
        self.recorder = PerformanceRecorder(self.directory, metadata, **(recorder_options or {}))
        self.closed = False
        self.window = self.writer = None
        self._patches = []
        self._gc_starts = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="industriova-report")
        self._future = self._future_kind = None
        self.last_export = None
        self.status_label = None
        self._tab_name = "Starting"
        self._patch_operations()
        gc.callbacks.append(self._gc_callback)
        self._old_exception_hook = sys.excepthook
        def exception_hook(kind, error, tb):
            self.recorder.event("unhandled_exception", error_type=kind.__name__, message=str(error)[:1000],
                                traceback="".join(traceback.format_exception(kind, error, tb))[-16000:])
            self._old_exception_hook(kind, error, tb)
        self._exception_hook = exception_hook
        sys.excepthook = exception_hook
        app.performance_probe = self

    def _patch(self, owner, attribute, label, event=None):
        original = getattr(owner, attribute, None)
        if original is None:
            return
        @wraps(original)
        def measured(*args, **kwargs):
            if self.closed:
                return original(*args, **kwargs)
            if event is not None:
                try:
                    self.recorder.event(event, command=type(args[1]).__name__ if len(args)>1 else "unknown")
                except Exception:
                    pass
            # A missing slot is the normal new-game path, not a load failure.
            with self.recorder.span(label, expected_errors=(KeyError,) if label == "save_load" else ()):
                result = original(*args, **kwargs)
            if label == "save_request" and result is False:
                self.recorder.event("save_failed", detail="Save request returned False")
            return result
        self._patches.append((owner, attribute, original, measured))
        setattr(owner, attribute, measured)

    def _patch_operations(self):
        from production_zero.core.commands import CommandBus
        from production_zero.core.simulation import SimulationEngine
        from production_zero.persistence import session_writer
        from production_zero.persistence.sqlite_store import SQLiteSaveStore
        from production_zero.ui import main_window
        from production_zero.ui.factory_view import FactoryViewBase
        from production_zero.ui.global_resources import GlobalResourcesOverlay
        self._patch(SimulationEngine, "advance_time", "simulation")
        self._patch(SimulationEngine, "_advance_production", "production")
        self._patch(SimulationEngine, "_apply_freight_market_exports", "freight_market")
        self._patch(SimulationEngine, "_apply_freight_contract_deliveries", "freight_contracts")
        self._patch(SimulationEngine, "_apply_consortium_freight", "freight_consortium")
        self._patch(SimulationEngine, "_complete_outbound_shipments", "freight_arrivals")
        self._patch(FactoryViewBase, "_advance_simulation", "simulation_timer_inclusive")
        self._patch(main_window, "_refresh_active_runtime_view", "visible_ui_runtime")
        self._patch(main_window, "_refresh_entered_view", "navigation_refresh")
        self._patch(main_window.MainWindow, "_save_session", "save_request")
        self._patch(session_writer, "snapshot_game_state", "save_snapshot")
        self._patch(session_writer.SessionWriter, "_write", "save_worker")
        self._patch(SQLiteSaveStore, "load", "save_load")
        self._patch(GlobalResourcesOverlay, "refresh", "resource_overview")
        self._patch(CommandBus, "dispatch", "player_command", "player_command")

    def _gc_callback(self, phase, info):
        if self.closed:
            return
        generation = info.get("generation", -1)
        if phase == "start":
            self._gc_starts[generation] = monotonic()
        else:
            start = self._gc_starts.pop(generation, None)
            if start is not None:
                self.recorder.timing("garbage_collection", monotonic()-start)

    def attach_window(self, window):
        self.window = window
        self.writer = getattr(window, "_save_writer", None)
        tabs = window.findChild(QTabWidget, "mainTabs")
        if tabs is not None:
            def changed(index):
                self._tab_name = tabs.tabText(index)
                self.recorder.event("view_changed", view=self._tab_name)
            tabs.currentChanged.connect(changed)
            changed(tabs.currentIndex())
        from production_zero.ui.dev_tools_view import DevToolsView
        dev = window.findChild(DevToolsView)
        if dev is not None:
            controls = QWidget()
            layout = QVBoxLayout(controls)
            layout.setContentsMargins(0, 0, 0, 0)
            buttons = QHBoxLayout()
            for text, callback in (("SET TEST START", self.set_test_start),
                                   ("MARK STUTTER (F8)", self.mark_stutter),
                                   ("EXPORT TEST REPORT (F9)", self.export_report),
                                   ("OPEN REPORT FOLDER", self.open_folder)):
                button = dev._button(text, callback)
                button.setMinimumHeight(32)
                buttons.addWidget(button)
            layout.addLayout(buttons)
            self.status_label = QLabel("Recording automatically · local only · report also saved on normal exit")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)
            # The extra panel must not squeeze the existing Dev Tools into
            # unreadable controls on a normal laptop-sized window.
            outer = dev.layout()
            content = QWidget()
            panels = QVBoxLayout(content)
            panels.setContentsMargins(0, 0, 0, 0)
            panels.setSpacing(12)
            panels.addWidget(dev._panel("Performance Test", controls))
            while outer.count():
                item = outer.takeAt(0)
                if item.widget() is not None:
                    panels.addWidget(item.widget())
                elif item.layout() is not None:
                    panels.addLayout(item.layout())
                else:
                    panels.addItem(item)
            scroll = QScrollArea(dev)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(content)
            outer.addWidget(scroll)
        for sequence, callback in (("F8", self.mark_stutter), ("F9", self.export_report)):
            shortcut = QShortcut(QKeySequence(sequence), window)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(callback)
        self._last_heartbeat = monotonic()
        self._beat_timer = QTimer(self)
        self._beat_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._beat_timer.setInterval(100)
        self._beat_timer.timeout.connect(self._beat)
        self._beat_timer.start()
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(30_000)
        self._state_timer.timeout.connect(self.capture_state)
        self._state_timer.start()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()
        self.capture_state()
        app = self.app
        app.aboutToQuit.connect(self._stop_timers)

    def _beat(self):
        now = monotonic()
        self.recorder.heartbeat(now-self._last_heartbeat)
        self._last_heartbeat = now

    def capture_state(self):
        if self.window is None or self.closed:
            return
        try:
            with self.recorder.span("diagnostic_state_summary"):
                state = self.window._session_state
                history = state.history.series
                contracts = [c for guild in state.consortium.consortiums.values()
                             for c in (*guild.contracts.values(), *guild.contract_history)]
                from production_zero.ui.factory_view_v2 import FactoryViewV2
                factory = self.window.findChild(FactoryViewV2)
                summary = {
                    "view": self._tab_name, "simulation_seconds": state.market.elapsed_seconds,
                    "cash": state.cash.amount, "company_level": state.company.level,
                    "research_total": state.research.total_earned, "cards_owned": len(state.cards),
                    "production_cards_installed": len(state.installed_card_ids()),
                    "freight_cards_installed": len(state.installed_freight_card_ids()),
                    "factory_buildings": len(state.halls), "resource_buildings": len(state.resource_sites),
                    "energy_buildings": len(state.energy_plants), "freight_buildings": len(state.freight.facilities),
                    "production_status": dict(Counter(p.status for p in state.machine_production.values())),
                    "metric_series": len(history), "metric_points": sum(len(s.values) for s in history.values()),
                    "inventory_history_points": sum(map(len, state.inventory_history.samples.values())),
                    "active_shipments": len(state.freight.outbound_shipments),
                    "completed_delivery_queue": len(state.freight.completed_market_deliveries),
                    "freight_statistic_rows": sum(map(len, state.freight.delivery_statistics.buckets.values())),
                    "consortium_reward_receipts": len(state.consortium.reward_receipts),
                    "consortium_delivery_receipts": sum(len(c.processed_request_ids) for c in contracts),
                    "pending_level_rewards": len(state.company.pending_rewards),
                    "command_history": len(factory._command_bus._history) if factory else None,
                    "save_pending": self.writer.pending_count if self.writer else 0,
                    "save_error": str(self.writer.last_error)[:500] if self.writer and self.writer.last_error else None,
                    "qt_widgets": len(self.app.allWidgets()),
                }
                self.recorder.state(summary)
        except Exception as error:
            self.recorder.event("summary_error", message=str(error)[:1000])

    def _status(self, message):
        if self.status_label is not None:
            self.status_label.setText(message)
        if self.window is not None:
            self.window.statusBar().showMessage(message, 10_000)

    def mark_stutter(self):
        self.capture_state()
        self.recorder.event("user_marked_stutter", view=self._tab_name)
        self._status("Stutter marked. Recording continues; export after your test.")

    def _wait_for_save(self):
        deadline = monotonic()+30
        while self.writer is not None and self.writer.pending_count and monotonic()<deadline:
            sleep(.05)
        return {"save_wait_timed_out": bool(self.writer and self.writer.pending_count),
                "save_error": str(self.writer.last_error)[:1000] if self.writer and self.writer.last_error else None}

    def _create_baseline(self):
        wait = self._wait_for_save()
        result = backup_database(self.save_path, self.directory / "baseline.sqlite")
        atomic_json(self.directory / "baseline-info.json", {**wait, **result, "created_utc": datetime.now(timezone.utc).isoformat()})
        self.recorder.event("baseline_saved", **result)
        return result

    def _create_report(self):
        with self.recorder.span("diagnostic_export"):
            wait = self._wait_for_save()
            with TemporaryDirectory(prefix="report-", dir=self.directory) as temporary:
                target = Path(temporary)
                result = backup_database(self.save_path, target / "company.sqlite")
                if not (self.directory / "baseline.sqlite").exists() and result["included"]:
                    shutil.copyfile(target / "company.sqlite", self.directory / "baseline.sqlite")
                    atomic_json(self.directory / "baseline-info.json", {"automatic_baseline": True, **result})
                self.recorder.copy_logs(target)
                for name in ("baseline.sqlite", "baseline-info.json"):
                    source = self.directory / name
                    if source.is_file():
                        shutil.copyfile(source, target / name)
                atomic_json(target / "export.json", {**wait, **result, "created_utc": datetime.now(timezone.utc).isoformat()})
                (target / "README.txt").write_text(REPORT_README, encoding="utf-8")
                archive = self.directory / "test-report.tmp.zip"
                with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=1) as bundle:
                    for path in sorted(target.iterdir()):
                        bundle.write(path, path.name)
                final = self.directory / "Industriova-Testbericht.zip"
                archive.replace(final)
        self.recorder.event("report_exported", bytes=final.stat().st_size, save_included=result["included"])
        return str(final)

    def _request(self, kind):
        if self._future is not None and not self._future.done():
            self._status("A report or baseline is already being prepared. Recording continues.")
            return
        self._poll()
        self.capture_state()
        self.recorder.event("user_requested_diagnostic_action", action=kind)
        self.window._save_session()
        self._future_kind = kind
        self._future = self._executor.submit(self._create_baseline if kind == "baseline" else self._create_report)
        self._status("Preparing test baseline…" if kind == "baseline" else "Preparing test report in the background…")

    def set_test_start(self):
        self._request("baseline")

    def export_report(self):
        self._request("report")

    def _poll(self):
        if self._future is not None and self._future.done():
            future, kind = self._future, self._future_kind
            self._future = self._future_kind = None
            try:
                result = future.result()
                if kind == "report":
                    self.last_export = Path(result)
                    self._status("Test report ready. Use OPEN REPORT FOLDER to find Industriova-Testbericht.zip.")
                elif result.get("included"):
                    self._status("Test baseline saved. Play normally; press F8 if you notice a stutter.")
                else:
                    self._status("No saved game available for the baseline. Recording continues.")
            except Exception as error:
                self.recorder.event("diagnostic_export_error", message=str(error)[:1000])
                self._status(f"Test report failed: {error}. Recording continues.")
        if self.recorder.last_error:
            self._status(f"Performance recording failed: {self.recorder.last_error}. Gameplay is unaffected.")

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.directory)))

    def _stop_timers(self):
        for name in ("_beat_timer", "_state_timer", "_poll_timer"):
            timer = getattr(self, name, None)
            if timer is not None:
                timer.stop()

    def close(self):
        if self.closed:
            return
        self._stop_timers()
        self.capture_state()
        self._executor.shutdown(wait=True)
        self._poll()
        self.closed = True
        if sys.excepthook is self._exception_hook:
            sys.excepthook = self._old_exception_hook
        if self._gc_callback in gc.callbacks:
            gc.callbacks.remove(self._gc_callback)
        for owner, attribute, original, measured in reversed(self._patches):
            if getattr(owner, attribute, None) is measured:
                setattr(owner, attribute, original)
        self.app.performance_probe = None
        try:
            self.recorder.close()
            # After the Qt loop exits and normal saves drain, make one atomic
            # final report, including the terminal record and closed summary.
            self.last_export = Path(self._create_report())
        except Exception:
            pass


def start_diagnostics(app, save_path, **kwargs):
    if not enabled():
        return None
    try:
        return PerformanceProbe(app, save_path, **kwargs)
    except Exception:
        # A diagnostic setup failure must not prevent playing. The caller shows
        # a visible warning after constructing the normal main window.
        return None
