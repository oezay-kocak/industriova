"""Retention, time-based sampling, and save isolation at/after saturation."""
from array import array
from concurrent.futures import ThreadPoolExecutor
import json
from math import ceil

import pytest

from production_zero.core.history import (
    BLOCK_SIZE, DEFAULT_HISTORY_MAX_POINTS, RETENTION_SECONDS,
    SAMPLE_INTERVAL_SECONDS, MetricHistory, MetricSeries, NumericBuffer,
)
from production_zero.core.state import GameState
from production_zero.persistence.session_writer import encode_snapshot, snapshot_game_state
from production_zero.persistence.sqlite_store import (
    SQLiteSaveStore, deserialize_game_state, serialize_game_state,
)


@pytest.mark.parametrize('limit', [0, 1, 3, 255, 256, 257, DEFAULT_HISTORY_MAX_POINTS])
def test_numeric_buffer_rollover_and_slicing_match_bounded_reference(limit):
    buffer = NumericBuffer(max_points=limit)
    expected = []
    for value in range(limit + 800):
        buffer.append(value)
        expected = (expected + [float(value)])[-limit:] if limit else []
    assert tuple(buffer) == tuple(expected)
    assert list(reversed(buffer)) == expected[::-1]
    for selection in (slice(None), slice(-32, None), slice(1, 50, 3), slice(None, None, -1)):
        assert buffer[selection] == tuple(expected[selection])
    for index in range(-len(buffer), len(buffer)):
        assert buffer[index] == expected[index]
    with pytest.raises(IndexError):
        _ = buffer[len(buffer)]
    assert len(buffer._blocks) <= ceil(limit / BLOCK_SIZE) + 1
    assert all(isinstance(block, array) and block.typecode == 'd' for block in buffer._blocks)


@pytest.mark.parametrize('limit', [-10, 0, 1, 3, 257, 1_000_000])
def test_series_constructor_enforces_hard_cap_and_aligned_timestamps(limit):
    series = MetricSeries('test', max_points=limit, values=range(20_000), timestamps=range(20_000))
    expected_size = max(0, min(limit, DEFAULT_HISTORY_MAX_POINTS))
    assert len(series.values) == len(series.timestamps) == expected_size
    assert series.max_points == expected_size
    if expected_size:
        assert series.values[-1] == series.timestamps[-1] == 19_999
    series.append(20_000, 20_000)
    assert len(series.values) == expected_size


@pytest.mark.parametrize('size', [0, 1, 255, 256, 257, 512, 513, 8641])
def test_frozen_blocks_survive_tail_replacement_append_and_eviction(size):
    buffer = NumericBuffer(range(size), max_points=max(1, size))
    frozen = buffer.freeze()
    expected = tuple(buffer)
    if buffer:
        buffer.replace_last(-1)
    for value in range(size + 700):
        buffer.append(value * 2)
    assert tuple(frozen) == expected
    assert frozen[-4:] == expected[-4:]


@pytest.mark.parametrize('step', [.25, .5, 1.0, .3, .7])
def test_sampling_uses_play_time_instead_of_timer_count(step):
    history = MetricHistory()
    for index in range(ceil(600 / step)):
        duration = min(step, 600 - history.elapsed_seconds)
        history.elapsed_seconds = min(600, (index + 1) * step)
        history.observe('resource.test', history.elapsed_seconds)
        history.observe_rate('rate.production.test', 2 * duration, duration)
    assert len(history.values_for('resource.test')) == 60
    assert history.values_for('resource.test')[-1] == 600
    assert history.values_for('rate.production.test') == pytest.approx((120,) * 60)
    # Stock observations use actual endpoints, never invented intermediate stocks.
    for timestamp, boundary in zip(history.series['resource.test'].timestamps, range(10, 601, 10)):
        assert boundary - step - 1e-8 <= timestamp <= boundary + 1e-8
    assert tuple(history.series['rate.production.test'].timestamps) == pytest.approx(tuple(range(10, 601, 10)))


def test_zero_catalogue_does_not_allocate_and_activated_series_records_return_to_zero():
    history = MetricHistory()
    for second in range(1, 61):
        history.elapsed_seconds = second
        for rid in range(353):
            history.observe(f'resource.{rid}', 0)
            history.observe_rate(f'rate.production.{rid}', 0, 1)
            history.observe_rate(f'rate.consumption.{rid}', 0, 1)
    assert not history.series
    history.elapsed_seconds = 61
    history.observe('resource.0', 10)
    history.observe_rate('rate.production.0', 1, 1)
    for second in range(62, 81):
        history.elapsed_seconds = second
        history.observe('resource.0', 0)
        history.observe_rate('rate.production.0', 0, 1)
    assert history.values_for('resource.0') == (0, 0)
    assert history.values_for('rate.production.0') == pytest.approx((6, 0))


def test_rate_weighting_includes_implicit_idle_time_and_split_intervals():
    history = MetricHistory(elapsed_seconds=10.25)
    history.observe_rate('rate.production.test', 2, .5)  # 9.75 -> 10.25
    assert history.values_for('rate.production.test') == (6, 240)
    assert tuple(history.series['rate.production.test'].timestamps) == (10, 10.25)
    history.elapsed_seconds = 11
    history.observe_rate('rate.production.test', 0, .75)
    assert history.values_for('rate.production.test') == (6, 60)
    history.observe_rate('rate.production.test', 1000, 0)
    assert history.values_for('rate.production.test') == (6, 60)


@pytest.mark.parametrize('range_id,duration', [('10M', 600), ('1H', 3600), ('6H', 21600), ('24H', 86400), ('ALL', 86400)])
def test_ranges_select_timestamps_and_omit_stale_series(range_id, duration):
    history = MetricHistory(elapsed_seconds=100_000)
    for timestamp in (100_000 - duration - 1, 100_000 - duration, 99_999, 100_000):
        history.series.setdefault('test', MetricSeries('test')).append(timestamp, timestamp)
    points = history.points_for_range('test', range_id)
    assert points == ((100_000 - duration, 100_000 - duration), (99_999, 99_999), (100_000, 100_000))
    history.elapsed_seconds += RETENTION_SECONDS + 1
    assert history.points_for_range('test', range_id) == ()
    assert history.values_for_range('missing', range_id) == ()


def test_72_hours_of_dense_telemetry_plateau_in_points_and_storage():
    history = MetricHistory()
    sizes = []
    for second in range(10, 72 * 3600 + 1, 10):
        history.elapsed_seconds = second
        history.observe('resource.test', second)
        history.observe_rate('rate.production.test', 5, 10)
        if second % (24 * 3600) == 0:
            sizes.append(sum(len(s.values) for s in history.series.values()))
    assert sizes[0] <= sizes[1] == sizes[2] == 2 * DEFAULT_HISTORY_MAX_POINTS
    for series in history.series.values():
        assert series.timestamps[0] >= history.elapsed_seconds - RETENTION_SECONDS
        assert len(series.values._blocks) <= ceil(DEFAULT_HISTORY_MAX_POINTS / BLOCK_SIZE) + 1
        assert sum(block.buffer_info()[1] * block.itemsize for block in series.values._blocks) < 72_000


def test_recent_and_latest_reads_do_not_copy_full_history(monkeypatch):
    history = MetricHistory({'test': MetricSeries('test', values=range(8641))})
    def no_full_iteration(self):
        raise AssertionError('Small chart reads must not iterate all retained points')
    monkeypatch.setattr(NumericBuffer, '__iter__', no_full_iteration)
    assert history.recent_values_for('test', 3) == (8638, 8639, 8640)
    assert history.recent_values_for('test', 0) == ()
    assert history.latest_value_for('test') == 8640
    assert history.latest_value_for('missing') == 0


def test_sqlite_round_trip_preserves_partial_bucket_and_continues_identically(tmp_path):
    state = GameState(rng_seed=42)
    history = state.history
    for second in range(1, 24):
        history.elapsed_seconds = second
        history.observe('resource.test', second)
        history.observe_rate('rate.production.test', second % 4, 1)
    store = SQLiteSaveStore(tmp_path / 'history.sqlite')
    store.initialize()
    store.save('test', state)
    loaded = store.load('test')
    assert serialize_game_state(loaded)['history'] == serialize_game_state(state)['history']
    assert loaded.history.elapsed_seconds == 23
    for h in (history, loaded.history):
        for second in range(24, 43):
            h.elapsed_seconds = second
            h.observe('resource.test', second)
            h.observe_rate('rate.production.test', second % 4, 1)
    assert loaded.history.to_payload() == history.to_payload()


def test_background_snapshot_preserves_both_buffers_during_saturated_updates():
    state = GameState(rng_seed=42)
    for second in range(10, 86401, 10):
        state.history.elapsed_seconds = second
        state.history.observe('resource.test', second)
        state.history.observe_rate('rate.production.test', 2, 10)
    expected = serialize_game_state(state)
    snapshot = snapshot_game_state(state)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(encode_snapshot, snapshot)
        for index in range(1, 3001):
            state.history.elapsed_seconds = 86400 + index * .25
            state.history.observe('resource.test', index)
            state.history.observe_rate('rate.production.test', index % 2, .25)
        encoded = future.result(timeout=10)
    assert json.loads(encoded) == expected
    assert deserialize_game_state(json.loads(encoded)).history.to_payload() == expected['history']


def test_direct_payload_is_detached_from_live_history():
    state = GameState(rng_seed=42)
    state.history.append('cash', 10)
    payload = serialize_game_state(state)
    state.history.append('cash', 99)
    assert payload['history']['cash']['values'] == [10]
    assert payload['history']['cash']['timestamps'] == [0]


def test_chart_ticks_represent_elapsed_seconds_minutes_and_hours():
    from production_zero.ui.charts_view import LineChartWidget
    assert LineChartWidget._time_ticks(0, 600) == ((0., '10.0m'), (.5, '5.0m'), (1., '0s'))
    assert LineChartWidget._time_ticks(0, 7200)[0] == (0., '2.0h')
    assert LineChartWidget._time_ticks(5, 5)[-1] == (1., '0s')
