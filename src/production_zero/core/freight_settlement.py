"""Internal one-use authority for the synchronous economic arrival boundary.

No grant is persisted or exposed through Commands, UI, or network requests.
Python modules are trusted application code, not a hostile-code sandbox.
"""
from contextlib import contextmanager

_arrivals = {}

class _FreightAlreadySettled(Exception):
    """A retained accepted receipt also forbids another Sell fallback."""

@contextmanager
def _economic_arrival(state, shipment):
    if shipment.active or shipment.remaining_seconds > 0 or shipment.economic_processed:
        raise PermissionError("Freight has not reached its economic completion.")
    grant = object()
    _arrivals[grant] = (state, shipment)
    try:
        yield grant
    finally:
        _arrivals.pop(grant, None)

def _claim_arrival(grant, state):
    try:
        arrival = _arrivals.get(grant)
    except TypeError:
        arrival = None
    if arrival is None or arrival[0] is not state:
        raise PermissionError("Only the central Freight completion may deliver goods.")
    del _arrivals[grant]
    return arrival[1]
