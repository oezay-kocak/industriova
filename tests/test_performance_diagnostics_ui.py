"""Diagnostic exports reconstruct real saves and never change the economy."""
from copy import deepcopy
from importlib.resources import files
import json
import os
from pathlib import Path
import sqlite3
from time import monotonic, sleep
from zipfile import ZipFile

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QEvent,QTimer
from PySide6.QtWidgets import QApplication,QPushButton,QTabWidget,QScrollArea
from production_zero.ui.main_window import MainWindow
from production_zero.ui.performance_diagnostics import PerformanceProbe,backup_database,start_diagnostics
from production_zero.persistence.sqlite_store import SQLiteSaveStore,serialize_game_state


@pytest.fixture
def app():
    a=QApplication.instance() or QApplication([])
    yield a
    for widget in a.topLevelWidgets():widget.close();widget.deleteLater()
    a.sendPostedEvents(None,QEvent.Type.DeferredDelete);a.processEvents()


def complete(probe,app):
    end=monotonic()+10
    while probe._future is not None and not probe._future.done() and monotonic()<end:
        app.processEvents();sleep(.01)
    assert probe._future is None or probe._future.done()
    probe._poll()


def make_window(tmp_path,app):
    store=SQLiteSaveStore(tmp_path/'company.sqlite');store.initialize()
    probe=PerformanceProbe(app,store._path,directory=tmp_path/'diagnostics',recorder_options={'interval':.05})
    window=MainWindow(save_store=store,development_mode=True,charts_enabled=False)
    for timer in window.findChildren(QTimer):timer.stop()
    probe.attach_window(window)
    return window,probe,store


def test_startup_opt_in_and_failed_setup_leave_game_available(tmp_path,app,monkeypatch):
    monkeypatch.delenv('PRODUCTION_ZERO_PERFORMANCE_TEST',raising=False)
    assert start_diagnostics(app,tmp_path/'save.sqlite') is None
    monkeypatch.setenv('PRODUCTION_ZERO_PERFORMANCE_TEST','1')
    existing=tmp_path/'not-a-directory';existing.write_text('existing data')
    assert start_diagnostics(app,tmp_path/'save.sqlite',directory=existing) is None
    assert existing.read_text()=='existing data'


def test_controls_baseline_mark_export_and_clean_exit_report(tmp_path,app):
    window,probe,store=make_window(tmp_path,app)
    try:
        labels={b.text() for b in window.findChildren(QPushButton)}
        assert {'SET TEST START','MARK STUTTER (F8)','EXPORT TEST REPORT (F9)','OPEN REPORT FOLDER'}<=labels
        from production_zero.ui.dev_tools_view import DevToolsView
        dev=window.findChild(DevToolsView)
        window.resize(1180,760);window.show()
        window.findChild(QTabWidget,'mainTabs').setCurrentWidget(dev)
        app.processEvents()
        for button in dev.findChildren(QPushButton):
            if button.text() in ('SET TEST START','SAVE GAME','Create','Grant 25 RP'):
                assert button.parentWidget().isVisible() and button.height()>=24
                assert dev.findChild(QScrollArea).widget().isAncestorOf(button)
        window._session_state.cash.amount=4321
        probe.set_test_start();complete(probe,app)
        assert (probe.directory/'baseline.sqlite').is_file()
        window._session_state.cash.amount=9876
        probe.mark_stutter();probe.export_report();complete(probe,app)
        assert probe.last_export and probe.last_export.is_file()
        with ZipFile(probe.last_export) as z:
            assert {'README.txt','session.json','summary.json','company.sqlite','baseline.sqlite','export.json'}<=set(z.namelist())
            z.extract('company.sqlite',tmp_path/'readback');z.extract('baseline.sqlite',tmp_path/'readback')
        assert SQLiteSaveStore(tmp_path/'readback/company.sqlite').load('company').cash.amount==9876
        assert SQLiteSaveStore(tmp_path/'readback/baseline.sqlite').load('company').cash.amount==4321
        assert window._session_state.cash.amount==9876
    finally:
        window.close();probe.close()
    with ZipFile(probe.last_export) as z:
        assert json.loads(z.read('summary.json'))['closed']
        records=[json.loads(line) for n in z.namelist() if n.endswith('.jsonl') for line in z.read(n).decode().splitlines()]
        assert any(r['kind']=='user_marked_stutter' for r in records)
        assert any(r['kind']=='session_ended' for r in records)


def test_instrumented_simulation_matches_uninstrumented_state(tmp_path,app):
    from test_economy_rebalance_xp import firm,DEFS
    from production_zero.core.simulation import SimulationEngine
    a=firm();b=deepcopy(a)
    engine=SimulationEngine(DEFS,utc_now=lambda:2_000_000_000.)
    engine.advance_time(a,60)
    window,probe,store=make_window(tmp_path,app)
    try:
        engine.advance_time(b,60)
        assert serialize_game_state(a)==serialize_game_state(b)
        assert probe.recorder.summary()['timings']['simulation']['count']>0
    finally:window.close();probe.close()


def test_export_queue_does_not_accumulate_duplicate_requests(tmp_path,app,monkeypatch):
    from threading import Event
    window,probe,store=make_window(tmp_path,app);entered,release=Event(),Event()
    original=probe._create_report
    def blocked():
        entered.set();assert release.wait(5);return original()
    monkeypatch.setattr(probe,'_create_report',blocked)
    try:
        probe.export_report();assert entered.wait(2);first=probe._future
        for _ in range(100):probe.export_report()
        assert probe._future is first
    finally:
        release.set();complete(probe,app);window.close();probe.close()


def test_gc_callback_can_record_while_metrics_lock_is_owned(tmp_path,app):
    import gc
    window,probe,store=make_window(tmp_path,app)
    try:
        with probe.recorder._lock:
            gc.collect()
        assert probe.recorder.summary()['timings']['garbage_collection']['count']>0
    finally:window.close();probe.close()


def test_backup_is_consistent_and_never_modifies_source(tmp_path):
    from production_zero.core.state import GameState
    source=tmp_path/'source.sqlite';store=SQLiteSaveStore(source);store.initialize();s=GameState(42)
    s.cash.amount=100;s.history.append('cash',100);store.save('company',s)
    before=source.read_bytes();result=backup_database(source,tmp_path/'copy.sqlite')
    assert result['included'] and source.read_bytes()==before
    assert serialize_game_state(SQLiteSaveStore(tmp_path/'copy.sqlite').load('company'))==serialize_game_state(store.load('company'))


def test_missing_save_is_reported_without_creating_a_source_database(tmp_path):
    path=tmp_path/'missing.sqlite'
    assert not backup_database(path,tmp_path/'copy.sqlite')['included']
    assert not path.exists()
