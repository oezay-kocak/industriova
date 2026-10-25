import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from threading import Event, get_ident
from time import perf_counter

from production_zero.core.history import DEFAULT_HISTORY_MAX_POINTS, MetricSeries
from production_zero.core.state import GameState
from production_zero.persistence.session_writer import SessionWriter, encode_snapshot, snapshot_game_state
from production_zero.persistence.sqlite_store import serialize_game_state


def test_snapshot_preserves_click_state_during_append_trim_and_other_mutations():
    state = GameState(rng_seed=42)
    series = MetricSeries("cash", max_points=3, values=[1., 2.])
    state.history.series["cash"] = series
    state.production_progress.lifetime_produced["iron_ore"] = 20
    expected = json.loads(json.dumps(serialize_game_state(state)))
    snapshot = snapshot_game_state(state)
    series.append(3)
    series.append(4)  # Eviction and mutable-tail updates cannot change the snapshot.
    state.cash.amount += 100
    state.production_progress.lifetime_produced["iron_ore"] = 99
    state.company.achievement_titles.append("Later")
    assert json.loads(encode_snapshot(snapshot)) == expected
    assert series.values == [2., 3., 4.]


def test_history_caps_imported_values_and_snapshot_shares_only_completed_blocks():
    state = GameState(rng_seed=42)
    values = [1.] * 1_000_000
    series = MetricSeries("cash", values=values)
    state.history.series["cash"] = series
    snapshot = snapshot_game_state(state)
    prefix = snapshot["history"]["cash"]["values"]
    assert prefix.length == DEFAULT_HISTORY_MAX_POINTS
    assert prefix.values._blocks[0] is series.values._blocks[0]
    assert prefix.values._blocks[-1] is not series.values._blocks[-1]
    series.append(2)
    assert prefix.values[-1] == 1.0


def test_slow_encoder_and_commit_never_block_submit_or_completion_poll(monkeypatch):
    from production_zero.persistence import session_writer
    entered, release = Event(), Event()
    main_thread = get_ident()
    commits = []
    original = session_writer.encode_snapshot
    def slow_encode(payload):
        assert get_ident() != main_thread
        entered.set()
        assert release.wait(5)
        return original(payload)
    class Store:
        def save_payload(self, slot, payload):
            commits.append(json.loads(payload))
    monkeypatch.setattr(session_writer, "encode_snapshot", slow_encode)
    writer = SessionWriter(Store())
    try:
        start = perf_counter()
        writer.submit({"purchase": 1})
        assert writer.poll() is None
        assert perf_counter() - start < .1
        assert entered.wait(1) and not commits
        writer.submit({"purchase": 2})
        release.set()
        assert writer.poll(wait=True) is None
        assert commits == [{"purchase": 1}, {"purchase": 2}]
    finally:
        release.set()
        writer.shutdown()


def test_heartbeat_detects_a_stall_after_the_initiating_callback(tmp_path):
    from time import sleep
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from production_zero.ui.research_trace import ResearchTrace
    app = QApplication.instance() or QApplication([])
    trace = ResearchTrace(app, tmp_path / "trace.jsonl")
    loop = QEventLoop()
    try:
        trace.begin("post-handler-stall-test")
        QTimer.singleShot(40, lambda: sleep(.12))
        QTimer.singleShot(350, loop.quit)
        loop.exec()
        trace.finish()
        assert trace.completed[-1]["max_heartbeat_gap_ms"] >= 110
    finally:
        trace.close()
    records = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
