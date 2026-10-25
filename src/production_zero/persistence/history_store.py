"""Incremental content-addressed history blocks inside the save transaction."""
from array import array
from hashlib import sha256
from itertools import islice, zip_longest
import json
import struct
import sys

from production_zero.core.history import BLOCK_SIZE, FrozenNumbers


def initialize_history_tables(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS save_history_header '
                       '(slot TEXT PRIMARY KEY, revision TEXT NOT NULL, metadata_json TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS save_history_records '
                       '(slot TEXT NOT NULL, kind TEXT NOT NULL, metric_id TEXT NOT NULL, '
                       'metadata_json TEXT NOT NULL, chunks_json TEXT NOT NULL, '
                       'PRIMARY KEY(slot, kind, metric_id))')
    connection.execute('CREATE TABLE IF NOT EXISTS save_history_blocks '
                       '(slot TEXT NOT NULL, digest TEXT NOT NULL, data BLOB NOT NULL, '
                       'PRIMARY KEY(slot, digest))')


def delete_history(connection, slot):
    for table in ('save_history_header', 'save_history_records', 'save_history_blocks'):
        connection.execute(f'DELETE FROM {table} WHERE slot=?', (slot,))


def _chunks(values):
    from production_zero.persistence.session_writer import HistoryPrefix
    if isinstance(values, HistoryPrefix):
        values = values.values
    if hasattr(values, 'iter_blocks'):
        yield from values.iter_blocks()
    else:
        iterator = iter(values)
        while chunk := tuple(islice(iterator, BLOCK_SIZE)):
            yield chunk


def _little_endian(values):
    if isinstance(values, memoryview) and values.format == 'd' and sys.byteorder == 'little':
        return values.tobytes()
    numbers = array('d', values)
    if sys.byteorder != 'little':
        numbers.byteswap()
    return numbers.tobytes()


def _pack(times, values):
    if len(times) != len(values) or not 0 < len(times) <= BLOCK_SIZE:
        raise ValueError('History block values and timestamps do not match')
    return struct.pack('<I', len(times)) + _little_endian(times) + _little_endian(values)


def _unpack(digest, data):
    if sha256(data).hexdigest() != digest or len(data) < 4:
        raise ValueError('Saved history block is corrupt')
    count, = struct.unpack('<I', data[:4])
    if not 0 < count <= BLOCK_SIZE or len(data) != 4 + count * 16:
        raise ValueError('Saved history block has an invalid length')
    times, values = array('d'), array('d')
    times.frombytes(data[4:4 + count * 8])
    values.frombytes(data[4 + count * 8:])
    if sys.byteorder != 'little':
        times.byteswap()
        values.byteswap()
    return times, values


def _records(snapshot):
    for metric_id, series in snapshot.get('history', {}).items():
        metadata = {key: value for key, value in series.items() if key not in ('values', 'timestamps')}
        pairs = zip_longest(_chunks(series.get('timestamps', ())), _chunks(series['values']))
        yield 'metric', metric_id, metadata, pairs
    for resource_id, points in snapshot.get('inventory_history', {}).get('samples', {}).items():
        def pairs(points=points):
            for start in range(0, len(points), BLOCK_SIZE):
                chunk = points[start:start + BLOCK_SIZE]
                yield tuple(t for t, _ in chunk), tuple(v for _, v in chunk)
        yield 'inventory', resource_id, {}, pairs()


def write_history(connection, slot, revision, snapshot):
    existing = {digest for digest, in connection.execute('SELECT digest FROM save_history_blocks WHERE slot=?', (slot,))}
    previous = {(kind, metric): (metadata, chunks) for kind, metric, metadata, chunks in connection.execute(
        'SELECT kind, metric_id, metadata_json, chunks_json FROM save_history_records WHERE slot=?', (slot,))}
    new_blocks, live, desired, changed = {}, set(), set(), []
    for kind, metric_id, metadata, pairs in _records(snapshot):
        references = []
        for times, values in pairs:
            if times is None or values is None:
                raise ValueError('History values and timestamps have different blocks')
            data = _pack(times, values)
            digest = sha256(data).hexdigest()
            references.append(digest)
            live.add(digest)
            if digest not in existing and digest not in new_blocks:
                new_blocks[digest] = data
        metadata_json = json.dumps(metadata, separators=(',', ':'), sort_keys=True)
        chunks_json = json.dumps(references, separators=(',', ':'))
        desired.add((kind, metric_id))
        if previous.get((kind, metric_id)) != (metadata_json, chunks_json):
            changed.append((slot, kind, metric_id, metadata_json, chunks_json))
    connection.executemany('INSERT INTO save_history_blocks(slot,digest,data) VALUES (?,?,?)',
                           ((slot, digest, data) for digest, data in new_blocks.items()))
    connection.executemany('INSERT INTO save_history_records VALUES (?,?,?,?,?) '
                           'ON CONFLICT(slot,kind,metric_id) DO UPDATE SET '
                           'metadata_json=excluded.metadata_json,chunks_json=excluded.chunks_json', changed)
    connection.executemany('DELETE FROM save_history_records WHERE slot=? AND kind=? AND metric_id=?',
                           ((slot, kind, metric) for kind, metric in previous.keys() - desired))
    connection.executemany('DELETE FROM save_history_blocks WHERE slot=? AND digest=?',
                           ((slot, digest) for digest in existing - live))
    inventory = snapshot.get('inventory_history', {})
    header = {'history_elapsed_seconds': snapshot.get('history_elapsed_seconds', 0.0),
              'inventory_history': {key: value for key, value in inventory.items() if key != 'samples'},
              'record_count': len(desired), 'block_count': len(live)}
    connection.execute('INSERT INTO save_history_header VALUES (?,?,?) ON CONFLICT(slot) DO UPDATE SET '
                       'revision=excluded.revision,metadata_json=excluded.metadata_json',
                       (slot, revision, json.dumps(header, separators=(',', ':'), sort_keys=True)))


def read_history(connection, slot, payload):
    if payload.pop('_history_storage') != 1:
        raise ValueError('Save uses an unsupported history storage format')
    revision = payload.pop('_history_revision', None)
    if not isinstance(revision, str) or not revision:
        raise ValueError('Saved state is missing its history revision')
    header = connection.execute('SELECT revision,metadata_json FROM save_history_header WHERE slot=?', (slot,)).fetchone()
    if header is None or header[0] != revision:
        raise ValueError('Saved state and history do not belong to the same snapshot')
    metadata = json.loads(header[1])
    records = connection.execute(
        'SELECT kind,metric_id,metadata_json,chunks_json FROM save_history_records WHERE slot=?', (slot,)).fetchall()
    blocks = {digest: data for digest, data in connection.execute('SELECT digest,data FROM save_history_blocks WHERE slot=?', (slot,))}
    if not isinstance(metadata, dict) or len(records) != metadata.pop('record_count', None) or len(blocks) != metadata.pop('block_count', None):
        raise ValueError('Saved history is incomplete')
    payload.update(metadata)
    payload['history'] = {}
    inventory = payload.setdefault('inventory_history', {})
    inventory['samples'] = {}
    decoded = {}
    for kind, metric_id, metadata, references in records:
        time_blocks, value_blocks = [], []
        for digest in json.loads(references):
            if digest not in blocks:
                raise ValueError('Saved history references a missing block')
            if digest not in decoded:
                decoded[digest] = _unpack(digest, blocks[digest])
            block_times, block_values = decoded[digest]
            time_blocks.append(block_times)
            value_blocks.append(block_values)
        length = sum(map(len, time_blocks))
        times = FrozenNumbers(tuple(time_blocks), 0, length)
        values = FrozenNumbers(tuple(value_blocks), 0, length)
        if kind == 'metric':
            series = json.loads(metadata)
            if not isinstance(series, dict) or not {'metric_id', 'max_points'} <= series.keys():
                raise ValueError('Saved history series has invalid metadata')
            payload['history'][metric_id] = {**series, 'timestamps': times, 'values': values}
        elif kind == 'inventory':
            inventory['samples'][metric_id] = tuple(zip(times, values))
        else:
            raise ValueError('Saved history has an unknown record type')
