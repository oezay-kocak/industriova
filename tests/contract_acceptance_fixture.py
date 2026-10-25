"""Explicit acceptance for tests about deliveries/rewards, not automatic startup."""
from production_zero.core.contracts import CONTRACT_REQUIREMENT_COUNTS, accept_contract, refresh_contracts
from production_zero.core.production_values import eligible_contract_products

def accept_fixture(state, definitions, kind):
    from tests.contract_capacity_fixture import provide_capacity
    provide_capacity(state, definitions)
    refresh_contracts(state, definitions)
    offer = state.contracts.offers[kind][0]
    products = eligible_contract_products(state, definitions, offer.production_value_budget or 1)
    products = tuple(p for p in products if not offer.balance_version or p.resource_id in offer.capacity_rates)
    selected = tuple(p.resource_id for p in products[:CONTRACT_REQUIREMENT_COUNTS[kind]])
    accept_contract(state, kind, offer.contract_id, definitions, selected_resource_ids=selected)
    return state.contracts.active[kind]
