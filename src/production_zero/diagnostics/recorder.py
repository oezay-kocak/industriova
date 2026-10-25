"""Bounded background performance recording; never retains live game objects."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import ctypes
import json
import math
import os
from pathlib import Path
from queue import Empty, Full, Queue
import shutil
import sys
import traceback
from threading import Event, Lock, RLock, Thread, get_ident
from time import monotonic, process_time


MIB = 1024 * 1024
MAX_METRICS = 64
MAX_TIMING_SAMPLES = 256


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def atomic_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def process_memory():
    """Windows working set/private bytes; page faults include soft faults."""
    if os.name != "nt":
        return {"memory_available": False}

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("page_faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
                "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile", "private")]

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load_percent", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total_physical", "available_physical", "total_pagefile", "available_pagefile",
                "total_virtual", "available_virtual", "available_extended_virtual")]

    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    data = Counters()
    data.cb = ctypes.sizeof(data)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(kernel.GetCurrentProcess()), ctypes.byref(data), data.cb):
        raise ctypes.WinError()
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return {
        "memory_available": True, "rss_bytes": data.working_set, "private_bytes": data.private,
        "peak_rss_bytes": data.peak_working_set, "page_faults_total": data.page_faults,
        "system_ram_total_bytes": status.total_physical,
        "system_ram_available_bytes": status.available_physical,
        "system_ram_load_percent": status.load_percent,
    }


class RotatingLog:
    """A fixed set of JSONL files; only the recorder thread writes them."""
    def __init__(self, directory, *, max_bytes=8 * MIB, backups=3):
        self.directory = Path(directory)
        self.max_bytes = max_bytes
        self.backups = backups
        self.path = self.directory / "performance.jsonl"
        self._stream = self.path.open("a", encoding="utf-8", newline="\n")
        self._size = self.path.stat().st_size

    def write(self, record):
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        size = len(line.encode("utf-8"))
        if self._size and self._size + size > self.max_bytes:
            self._stream.close()
            for n in range(self.backups, 0, -1):
                target = self.directory / f"performance.{n}.jsonl"
                source = self.path if n == 1 else self.directory / f"performance.{n-1}.jsonl"
                if target.exists():
                    target.unlink()
                if source.exists():
                    source.replace(target)
            self._stream = self.path.open("w", encoding="utf-8", newline="\n")
            self._size = 0
        self._stream.write(line)
        self._size += size

    def flush(self):
        self._stream.flush()

    def close(self):
        self._stream.close()


class PerformanceRecorder:
    """Fixed queues/samples, periodic process data, and bounded lifetime totals."""
    def __init__(self, directory, metadata, *, interval=5.0, queue_limit=256,
                 max_log_bytes=8 * MIB, backups=3, memory_sampler=process_memory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.started = monotonic()
        self.metadata = {"format": "industriova-performance-v1", "started_utc": utc_now(), **metadata}
        atomic_json(self.directory / "session.json", self.metadata)
        self._sink = RotatingLog(self.directory, max_bytes=max_log_bytes, backups=backups)
        self._io_lock = Lock()
        # A GC callback may record a pause while a metrics dictionary allocates.
        # Allow that same-thread callback to enter without freezing the game.
        self._lock = RLock()
        self._queue = Queue(maxsize=queue_limit)
        self._stop = Event()
        self._closed = False
        self._interval = interval
        self._memory_sampler = memory_sampler
        self._window = {}
        self._lifetime = {}
        self._active = {}
        self._state = {}
        self._state_at = self.started
        self._heartbeat_at = self.started
        self._observed_thread_id = get_ident()
        self._samples = self._dropped = self._slow_dropped = self._slow_in_window = 0
        self._peaks = {}
        self.last_error = None
        self._cpu_at, self._cpu = self.started, process_time()
        self._thread = Thread(target=self._run, name="industriova-performance", daemon=True)
        self._thread.start()
        self.event("session_started", metadata=self.metadata)

    def event(self, kind, **fields):
        if self._closed:
            return
        record = {"kind": kind, "utc": utc_now(), "elapsed_s": round(monotonic() - self.started, 4), **fields}
        try:
            self._queue.put_nowait(record)
        except Full:
            with self._lock:
                self._dropped += 1

    def state(self, summary):
        # Caller supplies a detached, small summary from the UI thread.
        with self._lock:
            self._state = summary
            self._state_at = monotonic()

    def heartbeat(self, duration):
        with self._lock:
            self._heartbeat_at = monotonic()
        self.timing("ui_heartbeat_gap", duration)

    def timing(self, name, seconds):
        if self._closed or not math.isfinite(seconds) or seconds < 0:
            return
        milliseconds = seconds * 1000
        slow = False
        with self._lock:
            if name not in self._lifetime and len(self._lifetime) >= MAX_METRICS - 1:
                name = "other"
            lifetime = self._lifetime.setdefault(name, {"count": 0, "total_ms": 0., "max_ms": 0., "max_at_s": 0.})
            lifetime["count"] += 1
            lifetime["total_ms"] += milliseconds
            if milliseconds > lifetime["max_ms"]:
                lifetime["max_ms"] = milliseconds
                lifetime["max_at_s"] = monotonic() - self.started
            window = self._window.setdefault(name, {"count": 0, "total_ms": 0., "max_ms": 0.,
                                                   "recent": deque(maxlen=MAX_TIMING_SAMPLES)})
            window["count"] += 1
            window["total_ms"] += milliseconds
            window["max_ms"] = max(window["max_ms"], milliseconds)
            window["recent"].append(milliseconds)
            # A heartbeat intentionally lasts 100 ms; only missed beats are slow.
            threshold = 200 if name == "ui_heartbeat_gap" else 100
            if milliseconds >= threshold:
                if self._slow_in_window < 20:
                    self._slow_in_window += 1
                    slow = True
                else:
                    self._slow_dropped += 1
        if slow:
            self.event("slow_operation", operation=name, duration_ms=round(milliseconds, 3))
        return slow

    @contextmanager
    def span(self, name, *, expected_errors=()):
        start = monotonic()
        token = (get_ident(), name)
        with self._lock:
            previous = self._active.get(token)
            if len(self._active) < 64 or token in self._active:
                self._active[token] = start
        try:
            yield
        except Exception as error:
            if not isinstance(error, expected_errors):
                self.event("operation_error", operation=name, error_type=type(error).__name__, message=str(error)[:1000])
            raise
        finally:
            elapsed = monotonic() - start
            with self._lock:
                if previous is None:
                    self._active.pop(token, None)
                else:
                    self._active[token] = previous
            self.timing(name, elapsed)

    def _sample(self):
        now, cpu = monotonic(), process_time()
        one_core = 100 * (cpu - self._cpu) / max(1e-6, now - self._cpu_at)
        self._cpu_at, self._cpu = now, cpu
        try:
            memory = self._memory_sampler()
        except Exception as error:
            memory = {"memory_available": False, "memory_error": str(error)[:256]}
        with self._lock:
            window, self._window = self._window, {}
            self._slow_in_window = 0
            state = self._state
            state_age = now - self._state_at
            heartbeat_age = now - self._heartbeat_at
            active = [{"operation": name, "thread_id": thread, "elapsed_ms": round((now-start)*1000, 3)}
                      for (thread, name), start in self._active.items()]
            self._samples += 1
            for key in ("rss_bytes", "private_bytes", "system_ram_load_percent"):
                if key in memory:
                    self._peaks[key] = max(self._peaks.get(key, 0), memory[key])
        timings = {}
        for name, values in window.items():
            ordered = sorted(values.pop("recent"))
            timings[name] = {
                **{k: round(v, 3) if isinstance(v, float) else v for k, v in values.items()},
                "mean_ms": round(values["total_ms"] / values["count"], 3),
                "recent_sample_count": len(ordered),
                "recent_p95_ms": round(ordered[max(0, math.ceil(len(ordered)*.95)-1)], 3),
            }
        blocked_stack = None
        if heartbeat_age >= .5:
            # Capture code locations, never locals or retained game objects.
            frame = sys._current_frames().get(self._observed_thread_id)
            try:
                if frame is not None:
                    blocked_stack = "".join(traceback.format_stack(frame, limit=24))[-12000:]
            finally:
                del frame
        return {"kind": "sample", "utc": utc_now(), "elapsed_s": round(now-self.started, 4),
                "cpu_one_core_percent": round(one_core, 3),
                "cpu_machine_percent": round(one_core / max(1, os.cpu_count() or 1), 3),
                **memory, "ui_heartbeat_age_ms": round(heartbeat_age*1000, 3),
                "game_summary_age_ms": round(state_age*1000, 3), "active_operations": active,
                "blocked_ui_stack": blocked_stack, "game": state, "timings": timings}

    def _write(self, record):
        with self._io_lock:
            if self._sink is not None:
                try:
                    self._sink.write(record)
                except Exception as error:
                    self.last_error = f"{type(error).__name__}: {error}"[:1000]
                    try:
                        self._sink.close()
                    except Exception:
                        pass
                    self._sink = None

    def _run(self):
        next_sample = monotonic() + self._interval
        try:
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    record = self._queue.get(timeout=.1)
                except Empty:
                    record = None
                if record is not None:
                    self._write(record)
                    self._queue.task_done()
                if monotonic() >= next_sample:
                    self._write(self._sample())
                    with self._io_lock:
                        if self._sink is not None:
                            self._sink.flush()
                    next_sample = monotonic() + self._interval
            self._write(self._sample())
        except Exception as error:
            self.last_error = f"{type(error).__name__}: {error}"[:1000]
        finally:
            with self._io_lock:
                if self._sink is not None:
                    self._sink.close()
                    self._sink = None

    def summary(self):
        with self._lock:
            return {"format": "industriova-performance-v1", "elapsed_s": monotonic()-self.started,
                    "samples": self._samples, "peak_samples": dict(self._peaks),
                    "dropped_records": self._dropped, "suppressed_slow_records": self._slow_dropped,
                    "logger_error": self.last_error, "closed": self._closed,
                    "timings": {name: dict(values) for name, values in list(self._lifetime.items())},
                    "last_game_summary": dict(self._state)}

    def copy_logs(self, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        with self._io_lock:
            if self._sink is not None:
                self._sink.flush()
            for path in self.directory.glob("performance*.jsonl"):
                shutil.copyfile(path, destination / path.name)
        shutil.copyfile(self.directory / "session.json", destination / "session.json")
        atomic_json(destination / "summary.json", self.summary())

    def close(self):
        if self._closed:
            return
        self.event("session_ended")
        self._closed = True
        self._stop.set()
        self._thread.join(timeout=3)
        atomic_json(self.directory / "summary.json", self.summary())
