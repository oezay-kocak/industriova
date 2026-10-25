"""Atomic state/history commits, incremental blocks and bounded save requests."""
from concurrent.futures import ThreadPoolExecutor
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Event
import weakref

import pytest

from production_zero.core.history import MetricSeries
from production_zero.core.inventory_history import InventoryHistory
from production_zero.core.state import GameState
from production_zero.persistence.session_writer import SessionWriter, snapshot_game_state, encode_snapshot
from production_zero.persistence.sqlite_store import SQLiteSaveStore, serialize_game_state, deserialize_game_state


def state_at(value=1, count=600):
    state = GameState(rng_seed=42)
    state.cash.amount = value
    state.history.elapsed_seconds = count * 10
    state.history.series['resource.iron_ore'] = MetricSeries(
        'resource.iron_ore', values=[value + n for n in range(count)],
        timestamps=[n * 10 for n in range(count)])
    state.inventory_history.advance(300, {'iron_ore': value})
    return state


@pytest.fixture
def store(tmp_path):
    result = SQLiteSaveStore(tmp_path / 'split.sqlite')
    result.initialize()
    return result


def canonical(snapshot):
    return serialize_game_state(deserialize_game_state(json.loads(encode_snapshot(snapshot))))


def rows(store, query, args=()):
    with sqlite3.connect(store._path) as db:
        return db.execute(query, args).fetchall()


def audit_changes(store):
    with sqlite3.connect(store._path) as db:
        db.execute('CREATE TABLE changes_log(table_name TEXT, operation TEXT)')
        for table in ('save_history_records', 'save_history_blocks'):
            for operation in ('INSERT', 'UPDATE', 'DELETE'):
                db.execute(f'CREATE TRIGGER log_{table}_{operation} AFTER {operation} ON {table} '
                           f"BEGIN INSERT INTO changes_log VALUES ('{table}','{operation}'); END")


def test_split_round_trip_reconstructs_the_same_full_state(store):
    state = state_at()
    state.history.observe_rate('rate.production.iron_ore', 2, .25)
    snapshot = snapshot_game_state(state)
    store.save_snapshot('company', snapshot)
    root = json.loads(rows(store, 'SELECT state_json FROM saves')[0][0])
    assert not {'history', 'inventory_history', 'history_elapsed_seconds'} & root.keys()
    assert rows(store, 'SELECT revision FROM save_history_header')[0][0] == root['_history_revision']
    assert {row[0] for row in rows(store, 'SELECT DISTINCT kind FROM save_history_records')} == {'metric', 'inventory'}
    assert serialize_game_state(store.load('company')) == canonical(snapshot)
    # Reopen through a new store instance; no process-local cache is required.
    reopened = SQLiteSaveStore(store._path)
    reopened.initialize()
    assert serialize_game_state(reopened.load('company')) == canonical(snapshot)


def test_unchanged_histories_do_not_write_records_or_blocks(store):
    state = state_at()
    store.save('company', state)
    audit_changes(store)
    state.cash.amount = 99
    store.save('company', state)
    assert rows(store, 'SELECT * FROM changes_log') == []
    assert store.load('company').cash.amount == 99


def test_partial_bucket_replaces_only_one_block_and_collects_the_old_tail(store):
    state = state_at(count=600)
    series = state.history.series['resource.iron_ore']
    series.observe(700, 6000)
    store.save('company', state)
    before = set(row[0] for row in rows(store, 'SELECT digest FROM save_history_blocks'))
    audit_changes(store)
    series.observe(701, 6000)
    store.save('company', state)
    after = set(row[0] for row in rows(store, 'SELECT digest FROM save_history_blocks'))
    assert len(after - before) == len(before - after) == 1
    assert rows(store, 'SELECT COUNT(*) FROM changes_log WHERE table_name="save_history_records"') == [(1,)]
    assert store.load('company').history.latest_value_for('resource.iron_ore') == 701


def test_saturated_head_and_tail_change_without_rewriting_the_middle(store):
    state = state_at(count=1025)
    series = state.history.series['resource.iron_ore']
    series.max_points = series.values.max_points = series.timestamps.max_points = 1025
    store.save('company', state)
    before = set(row[0] for row in rows(store, 'SELECT digest FROM save_history_blocks WHERE slot="company"'))
    series.append(9999)
    state.history.elapsed_seconds = series.timestamps[-1]
    store.save('company', state)
    after = set(row[0] for row in rows(store, 'SELECT digest FROM save_history_blocks WHERE slot="company"'))
    assert len(after - before) == len(before - after) == 2
    assert len(before & after) >= 3
    assert tuple(store.load('company').history.series['resource.iron_ore'].values) == tuple(series.values)


def test_reopened_saturated_history_keeps_block_boundaries_and_writes_nothing(store):
    state = state_at(count=1025)
    series = state.history.series['resource.iron_ore']
    series.max_points = series.values.max_points = series.timestamps.max_points = 1025
    for n in range(17):
        series.append(n)
    state.history.elapsed_seconds = series.timestamps[-1]
    store.save('company', state)
    loaded = store.load('company')
    audit_changes(store)
    store.save('company', loaded)
    assert rows(store, 'SELECT * FROM changes_log') == []
    assert tuple(loaded.history.series['resource.iron_ore'].values) == tuple(series.values)
    restored = loaded.history.series['resource.iron_ore']
    for n in range(300):
        restored.append(n)
        series.append(n)
    assert restored.snapshot() == series.snapshot()
    assert tuple(restored.timestamps) == tuple(series.timestamps)


def test_deduplicated_metric_blocks_do_not_share_writable_live_arrays(store):
    state = state_at(count=600)
    original = state.history.series['resource.iron_ore']
    state.history.series['resource.coal'] = MetricSeries('resource.coal', values=original.values, timestamps=original.timestamps)
    store.save('company', state)
    loaded = store.load('company')
    coal = loaded.history.values_for('resource.coal')
    loaded.history.series['resource.iron_ore'].observe(99999, loaded.history.elapsed_seconds)
    assert loaded.history.values_for('resource.coal') == coal


def test_new_game_removes_all_previous_history_without_affecting_other_slots(store):
    store.save('company', state_at(1))
    store.save('backup', state_at(2))
    expected_backup = serialize_game_state(store.load('backup'))
    fresh = GameState(rng_seed=99)
    store.save('company', fresh)
    assert rows(store, 'SELECT COUNT(*) FROM save_history_records WHERE slot="company"') == [(0,)]
    assert rows(store, 'SELECT COUNT(*) FROM save_history_blocks WHERE slot="company"') == [(0,)]
    assert not store.load('company').history.series
    assert not store.load('company').inventory_history.samples
    assert serialize_game_state(store.load('backup')) == expected_backup


def test_identical_inventory_blocks_are_shared_within_a_slot(store):
    state = GameState(rng_seed=1)
    state.inventory_history.advance(300, {f'resource-{n}': 0 for n in range(353)})
    store.save('company', state)
    assert rows(store, 'SELECT COUNT(*) FROM save_history_records') == [(353,)]
    assert rows(store, 'SELECT COUNT(*) FROM save_history_blocks') == [(1,)]
    assert store.load('company').inventory_history == state.inventory_history


def test_sql_failure_rolls_back_state_header_records_and_blocks(store):
    store.save('company', state_at(1))
    old_root = rows(store, 'SELECT state_json FROM saves')
    old_blocks = rows(store, 'SELECT digest,data FROM save_history_blocks ORDER BY digest')
    with sqlite3.connect(store._path) as db:
        db.execute("CREATE TRIGGER reject_blocks BEFORE INSERT ON save_history_blocks BEGIN SELECT RAISE(ABORT,'test full disk'); END")
    with pytest.raises(sqlite3.IntegrityError, match='test full disk'):
        store.save('company', state_at(2))
    assert rows(store, 'SELECT state_json FROM saves') == old_root
    assert rows(store, 'SELECT digest,data FROM save_history_blocks ORDER BY digest') == old_blocks
    assert store.load('company').cash.amount == 1
    assert rows(store, 'PRAGMA integrity_check') == [('ok',)]


def test_encoding_failure_rolls_back_root_written_before_history(store):
    store.save('company', state_at(1))
    old = serialize_game_state(store.load('company'))
    malformed = snapshot_game_state(state_at(2))
    malformed['history']['resource.iron_ore']['timestamps'] = []
    with pytest.raises(ValueError, match='different blocks'):
        store.save_snapshot('company', malformed)
    assert serialize_game_state(store.load('company')) == old


@pytest.mark.parametrize('damage', ['header', 'revision', 'missing_revision', 'missing_record', 'missing_block', 'digest', 'length', 'format', 'kind', 'metadata'])
def test_corrupt_or_mixed_history_is_rejected_instead_of_silently_reset(store, damage):
    store.save('company', state_at())
    with sqlite3.connect(store._path) as db:
        if damage == 'header':
            db.execute('DELETE FROM save_history_header')
        elif damage == 'revision':
            db.execute('UPDATE save_history_header SET revision="wrong"')
        elif damage == 'missing_block':
            db.execute('DELETE FROM save_history_blocks')
        elif damage == 'missing_record':
            db.execute('DELETE FROM save_history_records')
        elif damage == 'missing_revision':
            root = json.loads(db.execute('SELECT state_json FROM saves').fetchone()[0])
            root.pop('_history_revision')
            db.execute('UPDATE saves SET state_json=?', (json.dumps(root),))
        elif damage == 'digest':
            db.execute('UPDATE save_history_blocks SET data=?', (b'corrupt',))
        elif damage == 'length':
            digest, = db.execute('SELECT digest FROM save_history_blocks LIMIT 1').fetchone()
            data = b'\x01\x00\x00\x00'
            replacement = sha256(data).hexdigest()
            db.execute('UPDATE save_history_blocks SET digest=?, data=? WHERE digest=?', (replacement, data, digest))
            for kind, metric, references in db.execute('SELECT kind,metric_id,chunks_json FROM save_history_records').fetchall():
                db.execute('UPDATE save_history_records SET chunks_json=? WHERE kind=? AND metric_id=?',
                           (references.replace(digest, replacement), kind, metric))
        elif damage == 'format':
            root = json.loads(db.execute('SELECT state_json FROM saves').fetchone()[0])
            root['_history_storage'] = 999
            db.execute('UPDATE saves SET state_json=?', (json.dumps(root),))
        elif damage == 'kind':
            db.execute('UPDATE save_history_records SET kind="future"')
        elif damage == 'metadata':
            db.execute('UPDATE save_history_records SET metadata_json="{}" WHERE kind="metric"')
    with pytest.raises(ValueError):
        store.load('company')


def test_reader_sees_previous_complete_snapshot_while_writer_is_mid_transaction(store, monkeypatch):
    from production_zero.persistence import history_store
    store.save('company', state_at(1))
    entered, release = Event(), Event()
    original = history_store.write_history
    def delayed(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(history_store, 'write_history', delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(store.save, 'company', state_at(2))
        try:
            assert entered.wait(2)
            observed = store.load('company')
            assert observed.cash.amount == observed.inventory_history.values_for('iron_ore')[-1][1] == 1
        finally:
            release.set()
        future.result(timeout=5)
    observed = store.load('company')
    assert observed.cash.amount == observed.inventory_history.values_for('iron_ore')[-1][1] == 2


def test_abrupt_process_exit_before_commit_preserves_previous_save(store, tmp_path):
    store.save('company', state_at(1))
    expected = serialize_game_state(store.load('company'))
    data_path = tmp_path / 'next.json'
    data_path.write_text(encode_snapshot(snapshot_game_state(state_at(2))))
    code = '''
import sys,os,json
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.persistence import history_store
original=history_store.write_history
def crash(*args):
 original(*args)
 os._exit(23)
history_store.write_history=crash
SQLiteSaveStore(sys.argv[1]).save_snapshot('company',json.load(open(sys.argv[2])))
'''
    env = dict(os.environ, PYTHONPATH=str(Path.cwd() / 'src'))
    result = subprocess.run([sys.executable, '-B', '-c', code, str(store._path), str(data_path)], env=env, capture_output=True, timeout=10)
    assert result.returncode == 23, result.stderr
    assert serialize_game_state(store.load('company')) == expected
    assert rows(store, 'PRAGMA integrity_check') == [('ok',)]


def test_snapshot_skips_recursive_inventory_conversion_and_detaches_lists(monkeypatch):
    from production_zero.persistence import sqlite_store
    state = GameState(rng_seed=42)
    state.inventory_history = InventoryHistory(259200, 259200,
        {str(rid): [(float(index * 300), float(index)) for index in range(865)] for rid in range(20)})
    original = sqlite_store.asdict
    def checked(value):
        assert not isinstance(value, InventoryHistory), 'Inventory history must not be recursively copied'
        return original(value)
    monkeypatch.setattr(sqlite_store, 'asdict', checked)
    snapshot = snapshot_game_state(state)
    assert snapshot['inventory_history']['samples']['0'][0] is state.inventory_history.samples['0'][0]
    state.inventory_history.samples['0'][0] = (99, 99)
    state.inventory_history.samples['0'].append((259500, 1))
    assert snapshot['inventory_history']['samples']['0'][0] == (0, 0)
    assert len(snapshot['inventory_history']['samples']['0']) == 865


def test_many_saturated_saves_keep_only_live_blocks(store):
    state = state_at(count=257)
    series = state.history.series['resource.iron_ore']
    series.max_points = series.values.max_points = series.timestamps.max_points = 257
    for index in range(100):
        series.append(index)
        state.history.elapsed_seconds = series.timestamps[-1]
        store.save('company', state)
        assert rows(store, 'SELECT COUNT(*) FROM save_history_blocks')[0][0] <= 3
    assert rows(store, 'SELECT COUNT(*) FROM saves') == [(1,)]
    assert rows(store, 'SELECT COUNT(*) FROM save_history_records') == [(2,)]
    assert store.load('company').history.values_for('resource.iron_ore') == tuple(series.values)


def test_real_sqlite_worker_avoids_monolithic_encoding_and_captures_click_state(store, monkeypatch):
    from production_zero.persistence import session_writer
    def forbidden(*args):
        raise AssertionError('SQLite saves must not encode the whole history as JSON')
    monkeypatch.setattr(session_writer, 'encode_snapshot', forbidden)
    state = state_at(4)
    snapshot = snapshot_game_state(state)
    expected = canonical(snapshot)
    writer = SessionWriter(store)
    try:
        writer.submit(snapshot)
        state.cash.amount = 99
        state.history.series['resource.iron_ore'].append(99)
        state.inventory_history.advance(300, {'iron_ore': 99})
        assert writer.poll(wait=True) is None
        assert serialize_game_state(store.load('company')) == expected
    finally:
        writer.shutdown()


def test_reader_pins_root_and_history_even_when_a_new_commit_is_ready(store, monkeypatch):
    from production_zero.persistence import history_store
    store.save('company', state_at(1))
    root_read, release_reader, write_prepared, write_finished = Event(), Event(), Event(), Event()
    original_read, original_write = history_store.read_history, history_store.write_history
    def delayed_read(*args):
        root_read.set()
        assert release_reader.wait(5)
        return original_read(*args)
    def prepared_write(*args):
        result = original_write(*args)
        write_prepared.set()
        return result
    monkeypatch.setattr(history_store, 'read_history', delayed_read)
    monkeypatch.setattr(history_store, 'write_history', prepared_write)
    def write():
        try:
            store.save('company', state_at(2))
        finally:
            write_finished.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(store.load, 'company')
        try:
            assert root_read.wait(2)
            writer = pool.submit(write)
            assert write_prepared.wait(2)
            # The writer's commit waits for the pinned read transaction.
            assert not write_finished.wait(.1)
        finally:
            release_reader.set()
        previous = reader.result(timeout=5)
        writer.result(timeout=5)
    assert previous.cash.amount == previous.inventory_history.values_for('iron_ore')[-1][1] == 1
    assert store.load('company').cash.amount == 2


def test_explicit_json_import_clears_split_history_atomically(store):
    store.save('company', state_at(1))
    imported = serialize_game_state(state_at(9, 3))
    store.save_payload('company', json.dumps(imported))
    assert rows(store, 'SELECT COUNT(*) FROM save_history_blocks') == [(0,)]
    assert rows(store, 'SELECT COUNT(*) FROM save_history_header') == [(0,)]
    assert store.load('company').cash.amount == 9
    assert store.load('company').history.values_for('resource.iron_ore') == (9, 10, 11)


def test_save_requests_are_bounded_and_discarded_snapshots_are_freed():
    class Payload(dict):
        pass
    entered, release = Event(), Event()
    writes = []
    class Store:
        def save_snapshot(self, slot, payload):
            if payload['tick'] == 0:
                entered.set()
                assert release.wait(5)
            writes.append(payload['tick'])
    writer = SessionWriter(Store())
    references = []
    try:
        for index in range(101):
            payload = Payload(tick=index, data=bytearray(100_000))
            references.append(weakref.ref(payload))
            writer.submit(payload)
            if index == 0:
                assert entered.wait(2)
            assert writer.pending_count <= 2
        del payload
        gc.collect()
        assert sum(ref() is not None for ref in references) == 2
        assert writer.pending_count == 2 and writer.poll() is None
        release.set()
        assert writer.poll(wait=True) is None
        assert writes == [0, 100] and writer.pending_count == 0
    finally:
        release.set()
        writer.shutdown()
    gc.collect()
    assert not any(ref() is not None for ref in references)


def test_failed_snapshot_is_not_retained_by_error_tracebacks():
    class Payload(dict):
        pass
    class Store:
        def save_snapshot(self, slot, payload):
            try:
                raise ValueError('nested write failure')
            except ValueError as cause:
                raise OSError('save failed') from cause
    writer = SessionWriter(Store())
    try:
        payload = Payload(data=bytearray(100_000))
        reference = weakref.ref(payload)
        writer.submit(payload)
        del payload
        error = writer.poll(wait=True)
        gc.collect()
        assert isinstance(error, OSError) and str(error) == 'save failed'
        assert error.__traceback__ is error.__cause__ is error.__context__ is None
        assert reference() is None
    finally:
        writer.shutdown()


@pytest.mark.parametrize('failed', [0, 2])
def test_writer_failure_recovery_and_shutdown_keep_latest_result(failed):
    entered, release = Event(), Event()
    writes = []
    class Store:
        def save_snapshot(self, slot, payload):
            if payload['tick'] == 0:
                entered.set()
                assert release.wait(5)
            if payload['tick'] == failed:
                raise OSError('test failed save')
            writes.append(payload['tick'])
    writer = SessionWriter(Store())
    try:
        writer.submit({'tick': 0})
        assert entered.wait(2)
        writer.submit({'tick': 1})
        writer.submit({'tick': 2})
        release.set()
        error = writer.poll(wait=True)
        assert bool(error) == (failed == 2)
        if error:
            assert error.__traceback__ is None
        writer.submit({'tick': 3})
        writer.shutdown()
        assert writer.poll() is None and writes[-1] == 3
        with pytest.raises(RuntimeError, match='closed'):
            writer.submit({'tick': 4})
    finally:
        release.set()
        writer.shutdown()
