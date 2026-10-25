"""Bounded observations of global storage, measured in active simulation time."""
from dataclasses import dataclass, field

SAMPLE_INTERVAL_SECONDS = 300.0
RETENTION_SECONDS = 72 * 3600.0
MAX_SAMPLES = 865  # Inclusive endpoints of a 72-hour window at five minutes.


@dataclass(slots=True)
class InventoryHistory:
    elapsed_seconds: float = 0.0
    last_sample_at: float | None = None
    samples: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    def advance(self, elapsed_seconds: float, amounts: dict[str, float]) -> None:
        if elapsed_seconds <= 0:
            return
        self.elapsed_seconds += elapsed_seconds
        if self.last_sample_at is not None and self.elapsed_seconds - self.last_sample_at < SAMPLE_INTERVAL_SECONDS:
            return
        now = self.elapsed_seconds
        cutoff = now - RETENTION_SECONDS
        # A long advance records only the observed endpoint. Never fabricate
        # intervening inventory states or retroactively populate an old save.
        for resource_id in self.samples.keys() | amounts.keys():
            retained = [(t, value) for t, value in self.samples.get(resource_id, ()) if t >= cutoff]
            retained.append((now, max(0.0, amounts.get(resource_id, 0.0))))
            self.samples[resource_id] = retained[-MAX_SAMPLES:]
        self.last_sample_at = now

    def values_for(self, resource_id: str) -> tuple[tuple[float, float], ...]:
        cutoff = self.elapsed_seconds - RETENTION_SECONDS
        return tuple((t, value) for t, value in self.samples.get(resource_id, ()) if t >= cutoff)

    @classmethod
    def from_payload(cls, payload):
        elapsed = float(payload.get("elapsed_seconds", 0.0))
        last = payload.get("last_sample_at")
        samples = {rid: [(float(t), float(value)) for t, value in points
                         if elapsed - RETENTION_SECONDS <= float(t) <= elapsed][-MAX_SAMPLES:]
                   for rid, points in payload.get("samples", {}).items()}
        return cls(elapsed, float(last) if last is not None else None, samples)
