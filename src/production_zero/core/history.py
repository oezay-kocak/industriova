"""Bounded, timestamped telemetry; it never participates in game calculations."""
from __future__ import annotations

from array import array
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import islice
from math import ceil


SAMPLE_INTERVAL_SECONDS = 10.0
RETENTION_SECONDS = 24 * 3600.0
DEFAULT_HISTORY_MAX_POINTS = int(RETENTION_SECONDS / SAMPLE_INTERVAL_SECONDS) + 1
BLOCK_SIZE = 256
TIME_RANGE_SECONDS: dict[str, float | None] = {
    "10M": 600, "1H": 3_600, "6H": 21_600, "24H": RETENTION_SECONDS, "ALL": None,
}
# Kept as the chart's range catalogue. Selection uses timestamps, not counts.
TIME_RANGE_SAMPLES = TIME_RANGE_SECONDS


class FrozenNumbers(Sequence):
    """Completed blocks are shared; only the writable tail is copied on capture."""
    def __init__(self, blocks, head, length):
        self._blocks, self._head, self._length = blocks, head, length

    def __len__(self):
        return self._length

    def __iter__(self):
        for index, block in enumerate(self._blocks):
            yield from islice(block, self._head if index == 0 else 0, None)

    def iter_blocks(self):
        """Read-only logical blocks for persistence, without expanding floats."""
        for index, block in enumerate(self._blocks):
            yield memoryview(block)[self._head if index == 0 else 0:].toreadonly()

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step < 0:
                return tuple(self)[index]
            return tuple(islice(self, start, stop, step))
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        index += self._head
        for block in self._blocks:
            if index < len(block):
                return block[index]
            index -= len(block)
        raise IndexError(index)


class NumericBuffer(Sequence):
    """Compact doubles with constant-cost append/eviction, including at capacity."""
    def __init__(self, values=(), max_points=DEFAULT_HISTORY_MAX_POINTS):
        self.max_points = max_points
        self._blocks = deque()
        self._head = self._length = 0
        if isinstance(values, FrozenNumbers) and len(values) <= max_points:
            # Preserve persisted block boundaries across a restart, while giving
            # the live series its own writable arrays (no cross-series aliases).
            for block in values.iter_blocks():
                numbers = array('d')
                numbers.frombytes(block.tobytes())
                self._blocks.append(numbers)
            self._length = len(values)
            return
        for value in values:
            self.append(value)

    def __len__(self):
        return self._length

    def __iter__(self):
        for index, block in enumerate(self._blocks):
            yield from islice(block, self._head if index == 0 else 0, None)

    def __reversed__(self):
        for index in range(len(self._blocks) - 1, -1, -1):
            block = self._blocks[index]
            for offset in range(len(block) - 1, self._head - 1 if index == 0 else -1, -1):
                yield block[offset]

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step < 0:
                return tuple(self)[index]
            if stop == len(self) and step == 1:
                return tuple(reversed(tuple(islice(reversed(self), stop - start))))
            return tuple(islice(self, start, stop, step))
        if index == -1 and self._length:
            return self._blocks[-1][-1]
        if index == 0 and self._length:
            return self._blocks[0][self._head]
        return FrozenNumbers(self._blocks, self._head, self._length)[index]

    def __eq__(self, other):
        return isinstance(other, Sequence) and tuple(self) == tuple(other)

    def append(self, value):
        if not self.max_points:
            return
        if not self._blocks or len(self._blocks[-1]) == BLOCK_SIZE:
            self._blocks.append(array('d'))
        self._blocks[-1].append(float(value))
        self._length += 1
        if self._length > self.max_points:
            self.popleft()

    def replace_last(self, value):
        self._blocks[-1][-1] = float(value)

    def popleft(self):
        self._head += 1
        self._length -= 1
        if self._head == len(self._blocks[0]):
            self._blocks.popleft()
            self._head = 0

    def freeze(self):
        blocks = tuple(self._blocks)
        if blocks:
            blocks = blocks[:-1] + (array('d', blocks[-1]),)
        return FrozenNumbers(blocks, self._head, self._length)


@dataclass(slots=True)
class MetricSeries:
    metric_id: str
    max_points: int = DEFAULT_HISTORY_MAX_POINTS
    values: NumericBuffer | Sequence[float] = field(default_factory=tuple)
    timestamps: NumericBuffer | Sequence[float] = field(default_factory=tuple)
    bucket_id: int | None = None
    bucket_total: float = 0.0
    bucket_weight: float = 0.0

    def __post_init__(self):
        self.max_points = max(0, min(int(self.max_points), DEFAULT_HISTORY_MAX_POINTS))
        values = (self.values if len(self.values) <= self.max_points else self.values[-self.max_points:]) if self.max_points else ()
        times = (self.timestamps if len(self.timestamps) <= self.max_points else self.timestamps[-self.max_points:]) if self.max_points else ()
        if not times:
            times = (index * SAMPLE_INTERVAL_SECONDS for index in range(len(values)))
        self.values = NumericBuffer(values, self.max_points)
        self.timestamps = NumericBuffer(times, self.max_points)
        if len(self.values) != len(self.timestamps):
            raise ValueError("History values and timestamps must have equal lengths")

    def _trim(self, now):
        cutoff = now - RETENTION_SECONDS
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
            self.values.popleft()

    def append(self, value: float, at_seconds: float | None = None) -> None:
        """Explicit events keep their observed time, subject to the same bounds."""
        if at_seconds is None:
            at_seconds = self.timestamps[-1] + SAMPLE_INTERVAL_SECONDS if self.timestamps else 0.0
        self.values.append(value)
        self.timestamps.append(at_seconds)
        self.bucket_id = None
        self.bucket_total = self.bucket_weight = 0.0
        self._trim(at_seconds)

    def observe(self, value, at_seconds, *, weight=None):
        if not self.max_points:
            return
        bucket = max(0, ceil(at_seconds / SAMPLE_INTERVAL_SECONDS - 1e-10) - 1)
        if bucket != self.bucket_id or not self.values:
            self.values.append(value)
            self.timestamps.append(at_seconds)
            self.bucket_id = bucket
            self.bucket_total = self.bucket_weight = 0.0
        if weight is not None:
            self.bucket_total += value * weight
            self.bucket_weight += weight
            value = self.bucket_total / self.bucket_weight if self.bucket_weight else value
        self.values.replace_last(value)
        self.timestamps.replace_last(at_seconds)
        self._trim(at_seconds)

    def snapshot(self) -> tuple[float, ...]:
        return tuple(self.values)


@dataclass(slots=True)
class MetricHistory:
    series: dict[str, MetricSeries] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def append(self, metric_id: str, value: float, max_points: int = DEFAULT_HISTORY_MAX_POINTS) -> None:
        if metric_id not in self.series:
            self.series[metric_id] = MetricSeries(metric_id=metric_id, max_points=max_points)
        self.series[metric_id].append(value, self.elapsed_seconds)

    def observe(self, metric_id, value):
        if metric_id not in self.series:
            if value == 0:
                return
            self.series[metric_id] = MetricSeries(metric_id)
        self.series[metric_id].observe(value, self.elapsed_seconds)

    def observe_rate(self, metric_id, amount, elapsed_seconds):
        if elapsed_seconds <= 0:
            return
        if metric_id not in self.series:
            if amount == 0:
                return
            self.series[metric_id] = MetricSeries(metric_id)
            start = self.elapsed_seconds - elapsed_seconds
            leading = start % SAMPLE_INTERVAL_SECONDS
            if leading > 1e-10:
                # Earlier observations in this bucket were implicit zeroes.
                self.series[metric_id].observe(0.0, start, weight=leading)
        series = self.series[metric_id]
        rate = amount * 60.0 / elapsed_seconds
        start = self.elapsed_seconds - elapsed_seconds
        while start < self.elapsed_seconds - 1e-10:
            boundary = (int(start / SAMPLE_INTERVAL_SECONDS + 1e-10) + 1) * SAMPLE_INTERVAL_SECONDS
            end = min(boundary, self.elapsed_seconds)
            series.observe(rate, end, weight=end - start)
            start = end

    def values_for(self, metric_id: str) -> tuple[float, ...]:
        series = self.series.get(metric_id)
        return series.snapshot() if series is not None else ()

    def recent_values_for(self, metric_id, count):
        series = self.series.get(metric_id)
        return series.values[-count:] if series is not None and count > 0 else ()

    def latest_value_for(self, metric_id, default=0.0):
        series = self.series.get(metric_id)
        return series.values[-1] if series is not None and series.values else default

    def points_for_range(self, metric_id, range_id):
        series = self.series.get(metric_id)
        if series is None:
            return ()
        duration = TIME_RANGE_SECONDS.get(range_id) or RETENTION_SECONDS
        cutoff = self.elapsed_seconds - duration
        points = []
        for timestamp, value in zip(reversed(series.timestamps), reversed(series.values)):
            if timestamp < cutoff:
                break
            points.append((timestamp, value))
        return tuple(reversed(points))

    def values_for_range(self, metric_id: str, range_id: str) -> tuple[float, ...]:
        return tuple(value for _, value in self.points_for_range(metric_id, range_id))

    def to_payload(self, *, frozen=False):
        result = {}
        for metric_id, series in self.series.items():
            result[metric_id] = {
                'metric_id': series.metric_id, 'max_points': series.max_points,
                'values': series.values.freeze() if frozen else list(series.values),
                'timestamps': series.timestamps.freeze() if frozen else list(series.timestamps),
                'bucket_id': series.bucket_id, 'bucket_total': series.bucket_total,
                'bucket_weight': series.bucket_weight,
            }
        return result
