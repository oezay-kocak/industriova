from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_HISTORY_MAX_POINTS = 86_400
TIME_RANGE_SAMPLES: dict[str, int | None] = {
    "10M": 600,
    "1H": 3_600,
    "6H": 21_600,
    "24H": 86_400,
    "ALL": None,
}


@dataclass(slots=True)
class MetricSeries:
    metric_id: str
    max_points: int = DEFAULT_HISTORY_MAX_POINTS
    values: list[float] = field(default_factory=list)

    def append(self, value: float) -> None:
        self.values.append(float(value))
        if len(self.values) > self.max_points:
            del self.values[: len(self.values) - self.max_points]

    def snapshot(self) -> tuple[float, ...]:
        return tuple(self.values)


@dataclass(slots=True)
class MetricHistory:
    series: dict[str, MetricSeries] = field(default_factory=dict)

    def append(self, metric_id: str, value: float, max_points: int = DEFAULT_HISTORY_MAX_POINTS) -> None:
        if metric_id not in self.series:
            self.series[metric_id] = MetricSeries(metric_id=metric_id, max_points=max_points)
        self.series[metric_id].append(value)

    def values_for(self, metric_id: str) -> tuple[float, ...]:
        series = self.series.get(metric_id)
        if series is None:
            return ()
        return series.snapshot()

    def values_for_range(self, metric_id: str, range_id: str) -> tuple[float, ...]:
        values = self.values_for(metric_id)
        sample_count = TIME_RANGE_SAMPLES.get(range_id)
        if sample_count is None:
            return values
        return values[-sample_count:]
