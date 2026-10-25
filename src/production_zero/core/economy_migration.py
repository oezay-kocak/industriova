"""Lossless, idempotent N0 -> N1/C2 transition, separate from board schemas."""
ECONOMY_VERSION = 2


def migrate_economy(state):
    if state.economy_version > ECONOMY_VERSION:
        raise ValueError('Save uses a newer economic model.')
    if state.economy_version == ECONOMY_VERSION:
        return
    from production_zero.core.market import BASE_MARKET_PRICES
    # Market state is a display snapshot, never an accepted freight quote.
    for rid, resource in state.market.resources.items():
        if rid in BASE_MARKET_PRICES:
            resource.current_price = resource.anchor_price = BASE_MARKET_PRICES[rid]
            resource.momentum = resource.last_change = 0.
    # Inputs are debited only when a batch completes in this engine. Retaining
    # elapsed progress therefore converts an unfinished batch to N1 atomically:
    # no refund, pre-consumption, duplicated output, or inventory replacement.
    # Active contract/consortium snapshots and outbound freight stay untouched.
    state.contracts.offers.clear()
    state.contracts._capacity_signature = ''
    state.contracts._capacity_plan = None
    state.contracts._value_calculator = None
    state.contracts._value_definitions_signature = ()
    for consortium in state.consortium.consortiums.values():
        # Available drafts may be regenerated. Accepted commitments contain
        # their own frozen member prices/rewards and must never be rewritten.
        consortium.contracts = {kind: contract for kind, contract in consortium.contracts.items() if contract.status != 'available'}
        for member in consortium.members.values():
            member.capacity_signature = ''
            member.capacity_observed_at = 0.
            member.sale_prices.clear()
    state.economy_version = ECONOMY_VERSION
