"""Ordered atomic SQLite commits from detached state and frozen history blocks."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
import json
from io import StringIO
from time import sleep, perf_counter
from threading import Condition


@dataclass(frozen=True)
class HistoryPrefix:
    """A stable block view, detached from subsequent tail edits and eviction."""
    values: object
    length: int


def _detach_snapshot(value):
    """Detach serialized containers once; primitive/enum leaves are immutable.

    The serializer has already converted dataclasses. Never retain its live
    dictionary/list aliases. Unknown leaf types keep the conservative deepcopy.
    """
    kind = type(value)
    if kind is dict:
        return {key: _detach_snapshot(item) for key, item in value.items()}
    if kind is list:
        return [_detach_snapshot(item) for item in value]
    if kind is tuple:
        return tuple(_detach_snapshot(item) for item in value)
    if value is None or kind in (str, int, float, bool):
        return value
    return deepcopy(value)


def snapshot_game_state(state):
    from production_zero.persistence.sqlite_store import serialize_game_state
    payload = serialize_game_state(state, include_histories=False)
    history = state.history.to_payload(frozen=True)
    # Some serializer fields reference live dictionaries. Detach all non-history
    # data; historical numbers share immutable blocks and copy only their tails.
    payload = _detach_snapshot(payload)
    for series in history.values():
        for key in ("values", "timestamps"):
            values = series[key]
            series[key] = HistoryPrefix(values, len(values))
    payload["history"] = history
    payload['history_elapsed_seconds'] = state.history.elapsed_seconds
    inventory = state.inventory_history
    # Each point is an immutable (time, quantity) tuple. Copy list references,
    # never recursively rebuild every tuple and then detach it a second time.
    payload['inventory_history'] = {
        'elapsed_seconds': inventory.elapsed_seconds, 'last_sample_at': inventory.last_sample_at,
        'samples': {rid: tuple(points) for rid, points in inventory.samples.items()},
    }
    return payload


def encode_snapshot(payload):
    """Encode ordinary fields in C and stream immutable history prefixes.

    A bounded history chunk limits each GIL hold. Yielding between chunks keeps
    Qt responsive while avoiding the old recursive per-dictionary-key encoder.
    """
    if isinstance(payload, str):
        return payload
    if "history" not in payload:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)
    ordinary = {key: value for key, value in payload.items() if key != "history"}
    output = StringIO()
    output.write(json.dumps(ordinary, separators=(",", ":"), sort_keys=True)[:-1])
    history = payload.get("history", {})
    output.write((',"history":{' if ordinary else '"history":{'))
    last_yield = perf_counter()
    for index, (metric_id, series) in enumerate(sorted(history.items())):
        if index:
            output.write(",")
        metadata = {key: value for key, value in series.items() if key not in ("values", "timestamps")}
        output.write(json.dumps(metric_id) + ":" + json.dumps(metadata, separators=(",", ":"), sort_keys=True)[:-1])
        for key in ("values", "timestamps"):
            if key not in series:
                continue
            values = series[key]
            length = values.length if isinstance(values, HistoryPrefix) else len(values)
            source = values.values if isinstance(values, HistoryPrefix) else values
            output.write(',"' + key + '":[')
            for start in range(0, length, 2048):
                if start:
                    output.write(",")
                output.write(json.dumps(source[start:min(start + 2048, length)], separators=(",", ":"))[1:-1])
                if perf_counter() - last_yield >= .004:
                    sleep(.001)
                    last_yield = perf_counter()
            output.write("]")
        output.write("}")
    output.write("}}")
    return output.getvalue()


class SessionWriter:
    def __init__(self, store):
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pz-save")
        self._condition = Condition()
        self._next = None
        self._active = self._running = self._closed = False
        self.last_error = None

    def submit(self, payload):
        """Keep one running save plus the newest complete waiting snapshot."""
        with self._condition:
            if self._closed:
                raise RuntimeError('Save writer is closed')
            self._next = payload
            if not self._running:
                self._running = True
                try:
                    self._executor.submit(self._drain)
                except Exception:
                    self._running = False
                    self._next = None
                    raise

    @property
    def pending_count(self):
        with self._condition:
            return int(self._active) + int(self._next is not None)

    def _drain(self):
        while True:
            with self._condition:
                if self._next is None:
                    self._running = False
                    self._condition.notify_all()
                    return
                payload, self._next = self._next, None
                self._active = True
            error = None
            try:
                self._write(payload)
            except Exception as exc:
                error = exc
                # Do not retain a traceback holding a discarded large snapshot.
                error.__traceback__ = None
                error.__context__ = error.__cause__ = None
            finally:
                payload = None
            with self._condition:
                self._active = False
                self.last_error = error
                self._condition.notify_all()

    def _write(self, payload):
        if hasattr(self.store, 'save_snapshot'):
            self.store.save_snapshot('company', payload)
        else:
            # Small developer/test stores can still accept an ordinary JSON save.
            self.store.save_payload("company", encode_snapshot(payload))

    def poll(self, *, wait=False):
        with self._condition:
            while wait and self._running:
                self._condition.wait()
            return self.last_error

    def shutdown(self):
        with self._condition:
            self._closed = True
        self._executor.shutdown(wait=True)
