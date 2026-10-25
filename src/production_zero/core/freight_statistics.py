"""Bounded delivery aggregates, using simulation seconds rather than wall time.

One-second buckets: displayed window is (floor(now)-60, floor(now)],
retention is (floor(now)-600, floor(now)]. No shipment identifiers are kept.
The rolling indexes are derived, transient data; snapshots contain only buckets.
"""
from dataclasses import dataclass, field
from math import floor, isfinite

WINDOW_SECONDS = 60
RETENTION_SECONDS = 600


@dataclass(frozen=True, slots=True)
class DeliveryRate:
    sell: float = 0.0
    contract: float = 0.0
    consortium: float = 0.0
    observing_seconds: float = 0.0
    event: float = 0.0

    @property
    def total(self):
        return self.sell + self.contract + self.consortium + self.event

    @property
    def measuring(self):
        return self.observing_seconds < WINDOW_SECONDS


@dataclass(slots=True)
class FreightDeliveryStatistics:
    seconds: float = 0.0
    buckets: dict = field(default_factory=dict)
    _vehicles: dict = field(default_factory=dict, repr=False)
    _facilities: dict = field(default_factory=dict, repr=False)
    resource_buckets: dict = field(default_factory=dict)

    def advance(self, elapsed_seconds):
        if not isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("Invalid delivery statistics elapsed time")
        previous = floor(self.seconds)
        future = self.seconds + elapsed_seconds
        if not isfinite(future):
            raise ValueError("Invalid delivery statistics clock")
        current = floor(future)
        self.seconds = future
        if current == previous:
            return
        if current - previous >= WINDOW_SECONDS:
            self._vehicles.clear()
            self._facilities.clear()
            for epoch, entries in self.buckets.items():
                if current - WINDOW_SECONDS < epoch <= current:
                    for (cid, fid), amounts in entries.items():
                        self._index(cid, fid, amounts)
        else:
            for epoch in range(previous - WINDOW_SECONDS + 1, current - WINDOW_SECONDS + 1):
                for (cid, fid), amounts in self.buckets.get(epoch, {}).items():
                    self._index(cid, fid, amounts, -1)
        # Only occupied seconds are held. A large jump never loops through elapsed time.
        for epoch in tuple(self.buckets):
            if epoch <= current - RETENTION_SECONDS:
                del self.buckets[epoch]
        for epoch in tuple(self.resource_buckets):
            if epoch <= current - RETENTION_SECONDS:
                del self.resource_buckets[epoch]

    @staticmethod
    def _add(index, key, amounts, sign, entry_delta):
        if key is None:
            return
        row = index.setdefault(key, [0.0, 0.0, 0.0, 0])
        for i, amount in enumerate(amounts):
            row[i] += sign * amount
        row[3] += entry_delta
        if row[3] == 0:
            del index[key]

    def _index(self, cid, fid, amounts, sign=1, entry_delta=None):
        entry_delta = sign if entry_delta is None else entry_delta
        self._add(self._vehicles, cid, amounts, sign, entry_delta)
        self._add(self._facilities, fid, amounts, sign, entry_delta)

    def record(self, card_id, facility_id, *, sell=0.0, contract=0.0, consortium=0.0, at_seconds=None, resource_id=None):
        if resource_id is not None and not isinstance(resource_id, str):
            raise ValueError('Invalid resource delivery owner')
        amounts = (sell, contract, consortium)
        if any(not isfinite(n) or n < 0 for n in amounts):
            raise ValueError("Invalid completed delivery allocation")
        when = self.seconds if at_seconds is None else at_seconds
        if not isfinite(when) or when < 0 or when > self.seconds:
            raise ValueError("Invalid completed delivery timestamp")
        if not any(amounts):
            return
        epoch = floor(when)
        current = floor(self.seconds)
        if epoch <= current - RETENTION_SECONDS:
            return
        entries = self.buckets.setdefault(epoch, {})
        new_entry = (card_id, facility_id) not in entries
        row = entries.setdefault((card_id, facility_id), [0.0, 0.0, 0.0])
        for i, amount in enumerate(amounts):
            row[i] += amount
        if epoch > current - WINDOW_SECONDS:
            self._index(card_id, facility_id, amounts, entry_delta=int(new_entry))
        if resource_id:
            self.record_resource(resource_id, sell=sell, contract=contract, consortium=consortium, at_seconds=when)

    def record_resource(self, resource_id, *, sell=0.0, contract=0.0, consortium=0.0, event=0.0, at_seconds=None):
        """Completed quantities only. The event channel is reserved for future event freight."""
        amounts = (sell, contract, consortium, event)
        when = self.seconds if at_seconds is None else at_seconds
        if not isinstance(resource_id, str) or not resource_id or any(not isfinite(n) or n < 0 for n in amounts):
            raise ValueError('Invalid resource delivery allocation')
        if not isfinite(when) or when < 0 or when > self.seconds:
            raise ValueError('Invalid resource delivery timestamp')
        if not any(amounts) or floor(when) <= floor(self.seconds) - RETENTION_SECONDS:
            return
        row = self.resource_buckets.setdefault(floor(when), {}).setdefault(resource_id, [0.0] * 4)
        for i, amount in enumerate(amounts):
            row[i] += amount

    def resource_rate(self, resource_id):
        totals = [0.0] * 4
        current = floor(self.seconds)
        for epoch, entries in self.resource_buckets.items():
            if current - WINDOW_SECONDS < epoch <= current:
                for i, amount in enumerate(entries.get(resource_id, ())):
                    totals[i] += amount
        duration = min(WINDOW_SECONDS, self.seconds)
        factor = 60.0 / duration if duration > 0 else 0.0
        return DeliveryRate(*(n * factor for n in totals[:3]), duration, totals[3] * factor)

    def rate(self, *, card_id=None, facility_id=None):
        if (card_id is None) == (facility_id is None):
            raise ValueError("Choose exactly one delivery statistics owner")
        values = self._vehicles.get(card_id, ()) if card_id is not None else self._facilities.get(facility_id, ())
        duration = min(WINDOW_SECONDS, self.seconds)
        factor = 60.0 / duration if duration > 0 else 0.0
        return DeliveryRate(*(max(0.0, n) * factor for n in (values[:3] or (0.0, 0.0, 0.0))), duration)

    def retained_facility_ids(self):
        return {fid for entries in self.buckets.values() for _cid, fid in entries if fid is not None}

    def snapshot(self):
        return {"seconds": self.seconds, "buckets": [
            [epoch, [[cid, fid, *amounts] for (cid, fid), amounts in entries.items()]]
            for epoch, entries in sorted(self.buckets.items())
        ], "resource_buckets": [[epoch, [[rid, *amounts] for rid, amounts in sorted(entries.items())]]
                                for epoch, entries in sorted(self.resource_buckets.items())]}

    @classmethod
    def from_snapshot(cls, payload):
        result = cls()
        result.advance(float(payload.get("seconds", 0.0)))
        for epoch, entries in payload.get("buckets", []):
            if type(epoch) is not int:
                raise ValueError("Invalid delivery statistics bucket")
            for cid, fid, sell, contract, consortium in entries:
                if cid is not None and not isinstance(cid, str) or fid is not None and not isinstance(fid, str):
                    raise ValueError("Invalid delivery statistics owner")
                result.record(cid, fid, sell=float(sell), contract=float(contract), consortium=float(consortium), at_seconds=epoch)
        for epoch, entries in payload.get('resource_buckets', []):
            if type(epoch) is not int:
                raise ValueError('Invalid resource delivery bucket')
            for rid, sell, contract, consortium, event in entries:
                result.record_resource(rid, sell=float(sell), contract=float(contract), consortium=float(consortium),
                                       event=float(event), at_seconds=epoch)
        return result
