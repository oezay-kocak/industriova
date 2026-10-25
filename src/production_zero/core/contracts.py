from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime
from math import pow, sqrt, log1p
from typing import TYPE_CHECKING

from production_zero.core.company import xp_reward_for_contract_kind
from production_zero.core.company_xp import (
    award_contract_company_xp,
    sync_company_xp_periods,
    utc_period_ids,
    utc_timestamp,
)
from production_zero.core.definitions import CardDefinition, MachineDefinition
from production_zero.core.freight import start_outbound_shipments
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack
from production_zero.core.production_values import ProductionValueCalculator, contract_required_amount, eligible_contract_products, production_value_for_resource

if TYPE_CHECKING:
    from production_zero.core.state import GameState


REGULAR = "regular"
DAILY = "daily"
WEEKLY = "weekly"
CONTRACT_KINDS = (REGULAR, DAILY, WEEKLY)
CONTRACT_KIND_LABELS = {
    REGULAR: "Regular Contract",
    DAILY: "Daily Contract",
    WEEKLY: "Weekly Contract",
}
DAY_SECONDS = 24 * 60 * 60
WEEK_SECONDS = 7 * DAY_SECONDS
CONTRACT_RESOURCES = ("iron_ore", "coal", "copper_ore", "iron", "copper", "steel")
CONTRACT_PRODUCTION_VALUE_BUDGETS = {
    REGULAR: (5.0, 10.0, 15.0),
    DAILY: (20.0, 30.0, 45.0),
    WEEKLY: (80.0, 120.0, 180.0),
}
CONTRACT_TARGET_MINUTES = {
    REGULAR: (6.0, 10.0, 16.0),
    DAILY: (25.0, 45.0, 75.0),
    WEEKLY: (90.0, 160.0, 260.0),
}
CONTRACT_FORWARD_PROGRESS_MULTIPLIER = {
    REGULAR: 1.0,
    DAILY: 1.25,
    WEEKLY: 1.65,
}
CONTRACT_CAPACITY_EXPONENT = 0.88
MIN_CONTRACT_CAPACITY_PV_PER_MINUTE = 0.75
MAX_CONTRACT_BUDGET_TO_CURRENT_CAPACITY = {
    REGULAR: 22.0,
    DAILY: 110.0,
    WEEKLY: 520.0,
}
CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE = {
    REGULAR: 150.0,
    DAILY: 180.0,
    WEEKLY: 220.0,
}
CONTRACT_COMPANY_XP = {
    REGULAR: (100.0, 150.0, 225.0),
    DAILY: (600.0, 900.0, 1_350.0),
    WEEKLY: (3_000.0, 4_500.0, 6_750.0),
}
CONTRACT_DIFFICULTIES = ("easy", "medium", "hard")
CONTRACT_REQUIREMENT_COUNTS = {REGULAR: 2, DAILY: 3, WEEKLY: 4}


@dataclass(frozen=True, slots=True)
class ContractOffer:
    contract_id: str
    kind: str
    name: str
    requirements: dict[str, float]
    reward_cash: float
    reward_xp: float
    period_index: int
    expires_at: float | None = None
    production_value_budget: float | None = None
    selected_resource_id: str | None = None
    difficulty: str = "medium"
    balance_version: int = 0
    capacity_rates: dict[str, float] = field(default_factory=dict)
    unit_prices: dict[str, float] = field(default_factory=dict)
    unit_cash: dict[str, float] = field(default_factory=dict)
    target_minutes: float = 0.
    quoted_level: int = 0
    reward_rp: int | None = None
    capacity_signature: str = ""


@dataclass(slots=True)
class ActiveContract:
    offer: ContractOffer
    delivered: dict[str, float] = field(default_factory=dict)
    status: str = "active"

    def delivered_amount(self, resource_id: str) -> float:
        return self.delivered.get(resource_id, 0.0)

    def remaining_amount(self, resource_id: str) -> float:
        required = self.offer.requirements.get(resource_id, 0.0)
        return max(0.0, required - self.delivered_amount(resource_id))

    @property
    def is_complete(self) -> bool:
        return all(
            self.delivered_amount(resource_id) >= required
            for resource_id, required in self.offer.requirements.items()
        )


@dataclass(slots=True)
class RegularContractAutomation:
    enabled: bool = False
    resource_ids: tuple[str, ...] = ()
    pause_reason: str = ""

    def __post_init__(self):
        if type(self.enabled) is not bool or not isinstance(self.pause_reason, str):
            raise ValueError("Invalid Regular Contract automation settings.")
        self.resource_ids = tuple(self.resource_ids)
        if any(not isinstance(rid, str) or not rid for rid in self.resource_ids):
            raise ValueError("Invalid Regular Contract products.")
        if self.enabled and (len(self.resource_ids) != CONTRACT_REQUIREMENT_COUNTS[REGULAR] or len(set(self.resource_ids)) != len(self.resource_ids)):
            raise ValueError("Auto repeat needs two distinct Regular Contract products.")


@dataclass(slots=True)
class ContractBook:
    offers: dict[str, list[ContractOffer]] = field(default_factory=dict)
    active: dict[str, ActiveContract] = field(default_factory=dict)
    daily_period_index: int = -1
    weekly_period_index: int = -1
    regular_generation: int = 0
    last_status: dict[str, str] = field(default_factory=dict)
    _capacity_signature: str = field(default="", repr=False, compare=False)
    _capacity_plan: object = field(default=None, repr=False, compare=False)
    _capacity_inputs: tuple | None = field(default=None, repr=False, compare=False)
    _capacity_estimate_key: tuple | None = field(default=None, repr=False, compare=False)
    _capacity_estimate: object = field(default=None, repr=False, compare=False)
    _value_calculator: object = field(default=None, repr=False, compare=False)
    _value_definitions_signature: tuple = field(default=(), repr=False, compare=False)
    priorities: dict[str, int] = field(default_factory=lambda: dict.fromkeys(CONTRACT_KINDS, 0))
    regular_auto: RegularContractAutomation = field(default_factory=RegularContractAutomation)

    def __post_init__(self):
        if any(kind not in CONTRACT_KINDS or type(priority) is not int or priority not in (0, 1, 2)
               for kind, priority in self.priorities.items()):
            raise ValueError("Invalid Contract priorities.")


def set_contract_priority(state, kind, priority):
    if kind not in CONTRACT_KINDS or type(priority) is not int or priority not in (0, 1, 2):
        raise ValueError("Choose Even, Priority 1 or Priority 2 for a Contract.")
    state.contracts.priorities[kind] = priority


def set_regular_auto_repeat(state, enabled, *, expected_contract_id=None):
    if type(enabled) is not bool:
        raise ValueError("Choose whether Regular Contract auto repeat is enabled.")
    active = state.contracts.active.get(REGULAR)
    if expected_contract_id is not None and (active is None or active.offer.contract_id != expected_contract_id):
        raise ValueError("Regular Contract changed. Review its current auto-repeat setting.")
    if enabled:
        if active is None or active.status != 'active':
            raise ValueError("Accept a Regular Contract before enabling auto repeat.")
        prepared = RegularContractAutomation(True, tuple(active.offer.requirements))
    else:
        prepared = RegularContractAutomation(False, state.contracts.regular_auto.resource_ids)
    state.contracts.regular_auto = prepared


@dataclass(frozen=True, slots=True)
class ContractCapacityEstimate:
    active_pv_per_minute: float
    fallback_pv_per_minute: float
    effective_pv_per_minute: float
    scaled_pv_per_minute: float
    installed_machine_count: int
    configured_machine_count: int
    unlocked_production_count: int


def initialize_contracts(
    state: GameState,
    definitions: dict[str, CardDefinition] | None = None,
    *,
    now_utc: datetime | float | None = None,
) -> None:
    refresh_contracts(state, definitions, now_utc=now_utc)
    _ensure_regular_offers(state, definitions)


def contract_value_calculator(state, definitions):
    """Cache only immutable catalog work, never stocks, eligibility or rewards."""
    signature = tuple((key,id(value)) for key,value in definitions.items())
    book = state.contracts
    if book._value_calculator is None or book._value_definitions_signature != signature:
        book._value_calculator = ProductionValueCalculator(definitions)
        book._value_definitions_signature = signature
    return book._value_calculator


def contract_work_xp_quote(state, definitions, kind, requirements, *, level=None):
    """Retain the release's work/category/level quote at manual acceptance."""
    calculator = contract_value_calculator(state, definitions)
    work = sum((calculator.value_for_resource(rid).value_per_unit if calculator.value_for_resource(rid) else 1.) * amount for rid, amount in requirements.items())
    return round(20 * sqrt(max(1., work)) * (1 + log1p(state.company.level if level is None else level) / 4) * {REGULAR: 1., DAILY: 2., WEEKLY: 4.}[kind], 2)


def contract_reward_quote(state, offer, definitions, requirements):
    """The single UI/acceptance quote; accepted offers are never requoted."""
    from production_zero.core.modifiers import contract_cash_quote
    from production_zero.core.contract_capacity import CASH_BONUS
    from math import isfinite
    if any(not isfinite(amount) or amount <= 0 for amount in requirements.values()):
        raise ValueError("Contract quantities must be finite and positive.")
    if offer.balance_version:
        cash = sum(offer.unit_cash[rid] * amount for rid, amount in requirements.items())
        xp = contract_work_xp_quote(state, definitions, offer.kind, requirements, level=offer.quoted_level)
    else:
        cash = contract_cash_quote(state, requirements) * (1 + CASH_BONUS[offer.kind])
        xp = contract_work_xp_quote(state, definitions, offer.kind, requirements) if not offer.requirements and definitions else offer.reward_xp
    return round(cash, 2), xp


def _capacity_plan(state, definitions):
    from production_zero.core.contract_capacity import capacity_inputs, capacity_signature, reachable_capacity
    book = state.contracts
    inputs = capacity_inputs(state)
    if (inputs == book._capacity_inputs and book._capacity_plan is not None
        and book._capacity_signature == book._capacity_plan.signature):
        return book._capacity_plan
    signature = capacity_signature(state, inputs)
    if signature != book._capacity_signature or book._capacity_plan is None:
        book._capacity_plan = reachable_capacity(state, definitions, signature)
        book._capacity_signature = signature
    book._capacity_inputs = inputs
    return book._capacity_plan


def _refresh_capacity_offers(state, definitions):
    if not definitions:
        return
    plan = _capacity_plan(state, definitions)
    for kind, offers in tuple(state.contracts.offers.items()):
        if kind in state.contracts.active:
            continue
        if offers and offers[0].balance_version and not offers[0].requirements and offers[0].capacity_signature != plan.signature:
            old = offers[0]
            state.contracts.offers[kind] = generate_contract_offers(state.rng_seed, kind, old.period_index, old.expires_at, state=state, definitions=definitions)


def refresh_contracts(
    state: GameState,
    definitions: dict[str, CardDefinition] | None = None,
    *,
    now_utc: datetime | float | None = None,
) -> None:
    previous_day = state.company_xp_progress.utc_day_index
    daily_period, weekly_period = sync_company_xp_periods(state, now_utc)
    if previous_day >= 0 and daily_period != previous_day and REGULAR not in state.contracts.active:
        state.contracts.offers.pop(REGULAR, None)

    if state.contracts.daily_period_index != daily_period or (DAILY not in state.contracts.offers and DAILY not in state.contracts.active):
        _expire_active_contract(state, DAILY)
        state.contracts.daily_period_index = daily_period
        state.contracts.offers[DAILY] = generate_contract_offers(
            state.rng_seed,
            DAILY,
            daily_period,
            expires_at=(daily_period + 1) * DAY_SECONDS,
            state=state,
            definitions=definitions,
        )

    if state.contracts.weekly_period_index != weekly_period or (WEEKLY not in state.contracts.offers and WEEKLY not in state.contracts.active):
        _expire_active_contract(state, WEEKLY)
        state.contracts.weekly_period_index = weekly_period
        state.contracts.offers[WEEKLY] = generate_contract_offers(
            state.rng_seed,
            WEEKLY,
            weekly_period,
            expires_at=(weekly_period + 1) * WEEK_SECONDS + 4 * DAY_SECONDS,
            state=state,
            definitions=definitions,
        )

    _ensure_regular_offers(state, definitions)
    _refresh_capacity_offers(state, definitions)
    _try_regular_auto_repeat(state, definitions)


def accept_contract(
    state: GameState,
    kind: str,
    contract_id: str,
    definitions: dict[str, CardDefinition] | None = None,
    selected_resource_id: str | None = None,
    selected_resource_ids: tuple[str, ...] | None = None,
    *,
    expected_reward: tuple[float, float] | None = None,
    auto_repeat: bool = False,
    now_utc: datetime | float | None = None,
) -> None:
    if type(auto_repeat) is not bool or (auto_repeat and kind != REGULAR):
        raise ValueError("Auto repeat is available only for Regular Contracts.")
    if kind not in CONTRACT_KINDS:
        raise ValueError(f"Unknown contract kind: {kind}")
    refresh_contracts(state, definitions, now_utc=now_utc)
    if kind in state.contracts.active:
        if state.contracts.active[kind].offer.contract_id == contract_id:
            return  # Idempotent acceptance of the same persisted contract.
        raise ValueError(f"Contract already active for kind: {kind}")
    offer = _prepare_accepted_offer(state, _find_offer(state, kind, contract_id), definitions,
                                    selected_resource_id, selected_resource_ids, expected_reward)
    auto = RegularContractAutomation(auto_repeat, tuple(offer.requirements)) if kind == REGULAR else None
    state.contracts.active[kind] = ActiveContract(offer=offer)
    state.contracts.last_status[kind] = "Active"
    if auto is not None:
        state.contracts.regular_auto = auto


def _prepare_accepted_offer(state, offer, definitions, selected_resource_id=None, selected_resource_ids=None, expected_reward=None):
    kind = offer.kind
    if not offer.requirements and offer.production_value_budget is not None:
        if definitions is None:
            raise ValueError("Flexible contracts require card definitions.")
        if offer.balance_version and selected_resource_ids is None:
            raise ValueError("Select every Contract product explicitly.")
        if selected_resource_ids is not None:
            requirements = contract_requirements_for_products(state, offer, definitions, selected_resource_ids)
            offer = replace(
                offer,
                requirements=requirements,
                selected_resource_id=selected_resource_ids[0],
            )
        else:
            if selected_resource_id is None:
                raise ValueError("Flexible contracts require selected products.")
            offer = _offer_with_selected_product(state, offer, definitions, selected_resource_id)
        offer = replace(offer, reward_xp=contract_work_xp_quote(state, definitions, kind, offer.requirements))
    # The persisted offer is the acceptance snapshot, including for fixed-product offers.
    from production_zero.core.modifiers import contract_cash_quote

    cash, xp = contract_reward_quote(state, offer, definitions, offer.requirements)
    if expected_reward is not None and (cash,xp) != tuple(expected_reward):
        raise ValueError("Contract reward changed; review the current preview.")
    offer = replace(offer, reward_cash=cash, reward_xp=xp)
    return offer


def _try_regular_auto_repeat(state, definitions):
    auto = state.contracts.regular_auto
    if not auto.enabled or REGULAR in state.contracts.active:
        return
    try:
        if definitions is None:
            raise ValueError("Production definitions are unavailable. Auto repeat is paused.")
        offers = state.contracts.offers.get(REGULAR, ())
        if not offers:
            raise ValueError("No Regular Contract offer is available.")
        offer = _prepare_accepted_offer(state, offers[0], definitions, selected_resource_ids=auto.resource_ids)
    except ValueError as error:
        reason = str(error)
        if auto.pause_reason != reason:
            state.communications.add_activity('contract', 'Regular auto paused: ' + reason)
        auto.pause_reason = reason
        return
    auto.pause_reason = ''
    state.contracts.active[REGULAR] = ActiveContract(offer)


def cancel_contract(state: GameState, kind: str, definitions: dict[str, CardDefinition] | None = None) -> None:
    refresh_contracts(state, definitions)
    active = state.contracts.active.get(kind)
    if active is None or active.status != "active":
        raise ValueError(f"No cancellable contract for kind: {kind}")
    if kind == REGULAR:
        set_regular_auto_repeat(state, False)
    # Goods already in transit continue to market instead of a cancelled target.
    for shipment in state.freight.outbound_shipments.values():
        from production_zero.core.freight import contract_shipment_allocations
        allocations = contract_shipment_allocations(shipment)
        if shipment.active and active.offer.contract_id in allocations:
            if len(allocations) > 1:
                from production_zero.core.modifiers import market_sale_price
                shipment.cancelled_contract_prices[active.offer.contract_id] = market_sale_price(state, shipment.resource_id)
                continue
            shipment.destination_kind = "market"
            shipment.target_id = None
            shipment.contract_allocations = {}
            shipment.cancelled_contract_prices = {}
            if shipment.resource_id is not None:
                from production_zero.core.modifiers import market_sale_price
                shipment.market_price = market_sale_price(state, shipment.resource_id)
    del state.contracts.active[kind]
    state.contracts.last_status[kind] = f"Cancelled: {active.offer.name}"


def deliver_available_to_contract(
    state: GameState,
    kind: str,
    definitions: dict[str, CardDefinition],
) -> dict[str, float]:
    refresh_contracts(state, definitions)
    if kind not in state.contracts.active:
        raise ValueError(f"No active contract for kind: {kind}")
    active = state.contracts.active[kind]
    if active.status != "active":
        return {}

    from production_zero.core.contract_allocation import dispatch_contract_freight
    return dispatch_contract_freight(state, definitions, resource_ids=set(active.offer.requirements))


def receive_contract_delivery(
    state: GameState,
    contract_id: str,
    resource_id: str,
    amount: float,
    definitions: dict[str, CardDefinition] | None = None,
    *,
    now_utc: datetime | float | None = None,
) -> None:
    from math import isfinite
    if not isfinite(amount) or amount <= 0:
        raise ValueError("Delivery amount must be finite and positive.")
    for kind, active in tuple(state.contracts.active.items()):
        if active.offer.contract_id != contract_id or active.status != "active":
            continue
        remaining = active.remaining_amount(resource_id)
        if remaining <= 0:
            return
        delivered = min(amount, remaining)
        active.delivered[resource_id] = active.delivered.get(resource_id, 0.0) + delivered
        if active.is_complete:
            _complete_contract(state, kind, definitions, now_utc=now_utc)
        return


def route_market_delivery_to_contracts(
    state: GameState,
    resource_id: str,
    amount: float,
    definitions: dict[str, CardDefinition] | None = None,
) -> float:
    from math import isfinite
    if not isfinite(amount):
        raise ValueError("Delivery amount must be finite.")
    if amount <= 0:
        return 0.0
    from production_zero.core.contract_allocation import allocate_contract_cargo
    from math import fsum
    plan = allocate_contract_cargo(state, resource_id, amount)
    for target, quantity in sorted(plan.items()):
        receive_contract_delivery(state, target, resource_id, quantity, definitions)
    return fsum(plan.values())


def seconds_until_contract_reset(
    state: GameState, kind: str, now_utc: datetime | float | None = None
) -> float | None:
    sync_company_xp_periods(state, now_utc)
    elapsed = max(utc_timestamp(now_utc), state.company_xp_progress.utc_high_water_timestamp)
    if kind == DAILY:
        return max(0.0, (int(elapsed // DAY_SECONDS) + 1) * DAY_SECONDS - elapsed)
    if kind == WEEKLY:
        _, weekly_period, _ = utc_period_ids(elapsed)
        return max(0.0, (weekly_period + 1) * WEEK_SECONDS + 4 * DAY_SECONDS - elapsed)
    return None


def generate_contract_offers(
    seed: int,
    kind: str,
    period_index: int,
    expires_at: float | None = None,
    *,
    state: GameState | None = None,
    definitions: dict[str, CardDefinition] | None = None,
) -> list[ContractOffer]:
    rng = random.Random(f"{seed}:contracts:{kind}:{period_index}")
    offers: list[ContractOffer] = []
    snapshot = {}
    suffix = ""
    if state is not None and definitions:
        from production_zero.core.contract_capacity import BALANCE_VERSION, TARGET_MINUTES, CASH_BONUS
        from production_zero.core.modifiers import contract_cash_quote
        from production_zero.core.market import market_price_for
        plan = _capacity_plan(state, definitions)
        snapshot = dict(balance_version=BALANCE_VERSION, capacity_rates=dict(plan.rates),
            unit_prices={rid: market_price_for(state.market, rid) for rid in plan.rates},
            unit_cash={rid: contract_cash_quote(state, {rid:1.}) * (1+CASH_BONUS[kind]) for rid in plan.rates},
            target_minutes=TARGET_MINUTES[kind], quoted_level=state.company.level,
            reward_rp={REGULAR:0, DAILY:1, WEEKLY:3}[kind], capacity_signature=plan.signature)
        suffix = "-" + plan.signature
    choices = [("medium", contract_production_value_budgets(kind, state, definitions)[1])]
    for offer_index, (difficulty, budget) in enumerate(choices):
        difficulty_index = CONTRACT_DIFFICULTIES.index(difficulty)
        xp = CONTRACT_COMPANY_XP[kind][difficulty_index]
        reward_cash = round(budget * CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE[kind] / 5.0) * 5.0
        offers.append(
            ContractOffer(
                contract_id=f"{kind}-{period_index}-{offer_index}{suffix}",
                kind=kind,
                name=f"{CONTRACT_KIND_LABELS[kind]} #{offer_index + 1}",
                requirements={},
                reward_cash=reward_cash,
                reward_xp=xp,
                period_index=period_index,
                expires_at=expires_at,
                production_value_budget=budget,
                difficulty=difficulty,
                **snapshot,
            )
        )
    return offers


def contract_company_xp(kind: str, difficulty: str) -> float:
    if kind not in CONTRACT_COMPANY_XP:
        raise ValueError(f"Unknown contract kind: {kind}")
    try:
        difficulty_index = CONTRACT_DIFFICULTIES.index(difficulty)
    except ValueError as error:
        raise ValueError(f"Unknown contract difficulty: {difficulty}") from error
    return CONTRACT_COMPANY_XP[kind][difficulty_index]


def contract_capacity_estimate(
    state: GameState,
    definitions: dict[str, CardDefinition],
) -> ContractCapacityEstimate:
    calculator = contract_value_calculator(state, definitions)
    plan = _capacity_plan(state, definitions)
    installed = state.installed_card_ids()
    # This legacy projection counts installed production, unlike the recoverable
    # plan. Returning a machine to inventory must invalidate it independently.
    key = (plan.signature, id(plan), frozenset(installed), state.contracts._value_definitions_signature)
    if state.contracts._capacity_estimate_key == key:
        return state.contracts._capacity_estimate
    # Public legacy PV projection: count configured NET exports only. The new
    # quantity planner uses per-product frozen rates, never this scalar budget.
    exports = {}
    inputs = {}
    for cid in installed:
        card = state.cards.get(cid)
        definition = definitions.get(card.definition_id) if card else None
        machine = state.machine_production.get(cid)
        if not isinstance(definition, MachineDefinition) or not machine or not machine.selected_production_id:
            continue
        option = definition.production_option(machine.selected_production_id)
        rid = option.output_resource
        if rid not in plan.production_rates:
            continue
        from production_zero.core.modifiers import research_multiplier
        gross = option.output_amount_for(definition)*60/option.cycle_seconds_for(definition)*card.output_multiplier*research_multiplier(state.research,"production_speed")
        exports[rid] = exports.get(rid,0.) + gross
        for inp,qty in option.input_resources.items():
            inputs[inp] = inputs.get(inp,0.) + gross*qty/(option.output_amount_for(definition)*(card.output_multiplier/card.mk_multiplier))
    net = {rid:max(0., min(qty,plan.production_rates[rid])-inputs.get(rid,0.)) for rid,qty in exports.items()}
    freight_scale = min(1.,plan.freight_per_minute/sum(net.values())) if sum(net.values()) else 0.
    active = sum(qty*calculator.value_for_resource(rid).value_per_unit for rid,qty in net.items())*freight_scale
    if not exports:
        active = max((rate*calculator.value_for_resource(rid).value_per_unit for rid,rate in plan.rates.items()),default=0.)
    count = sum(isinstance(definitions.get(c.definition_id), MachineDefinition) for c in state.cards.values())
    effective = max(MIN_CONTRACT_CAPACITY_PV_PER_MINUTE, active)
    estimate = ContractCapacityEstimate(active, 0., effective, effective, count, count, len(state.production_progress.unlocked_production_ids))
    state.contracts._capacity_estimate_key = key
    state.contracts._capacity_estimate = estimate
    return estimate


def contract_production_value_budgets(
    kind: str,
    state: GameState | None = None,
    definitions: dict[str, CardDefinition] | None = None,
) -> tuple[float, float, float]:
    if state is None or definitions is None:
        return CONTRACT_PRODUCTION_VALUE_BUDGETS[kind]
    estimate = contract_capacity_estimate(state, definitions)
    multiplier = CONTRACT_FORWARD_PROGRESS_MULTIPLIER[kind]
    current_capacity_cap = estimate.effective_pv_per_minute * MAX_CONTRACT_BUDGET_TO_CURRENT_CAPACITY[kind]
    budgets = []
    for minutes in CONTRACT_TARGET_MINUTES[kind]:
        budget = estimate.scaled_pv_per_minute * minutes * multiplier
        budget = min(budget, current_capacity_cap)
        budgets.append(_round_contract_budget(budget))
    return (budgets[0], budgets[1], budgets[2])


def _round_contract_budget(raw_budget: float) -> float:
    if raw_budget < 20:
        step = 1.0
    elif raw_budget < 100:
        step = 5.0
    elif raw_budget < 500:
        step = 10.0
    else:
        step = 25.0
    return max(1.0, round(raw_budget / step) * step)


def _offer_with_selected_product(
    state: GameState,
    offer: ContractOffer,
    definitions: dict[str, CardDefinition],
    selected_resource_id: str,
) -> ContractOffer:
    requirements = contract_requirements_for_selection(state, offer, definitions, selected_resource_id)
    return replace(
        offer,
        requirements=requirements,
        selected_resource_id=selected_resource_id,
    )


def contract_requirements_for_selection(
    state: GameState,
    offer: ContractOffer,
    definitions: dict[str, CardDefinition],
    selected_resource_id: str,
) -> dict[str, float]:
    eligible = {
        option.resource_id: option
        for option in eligible_contract_products(state, definitions, offer.production_value_budget or 0.0, calculator=contract_value_calculator(state, definitions))
    }
    if selected_resource_id not in eligible:
        raise ValueError(f"Product is not eligible for this contract: {selected_resource_id}")
    required_count = CONTRACT_REQUIREMENT_COUNTS[offer.kind]
    if len(eligible) < required_count:
        raise ValueError(
            f"{CONTRACT_KIND_LABELS[offer.kind]} requires {required_count} eligible unique products; "
            f"only {len(eligible)} available."
        )
    remaining_ids = sorted(resource_id for resource_id in eligible if resource_id != selected_resource_id and (not offer.balance_version or resource_id in offer.capacity_rates))
    rng = random.Random(f"{state.rng_seed}:contract-products:{offer.contract_id}:{selected_resource_id}")
    rng.shuffle(remaining_ids)
    selected_ids = [selected_resource_id, *remaining_ids[: required_count - 1]]
    if offer.balance_version:
        from production_zero.core.contract_capacity import requirements_for_rates
        return requirements_for_rates(offer.capacity_rates, offer.unit_prices, selected_ids, offer.target_minutes)
    per_product_budget = (offer.production_value_budget or 0.0) / required_count
    requirements: dict[str, float] = {}
    for resource_id in selected_ids:
        value = production_value_for_resource(definitions, resource_id)
        if value is None:
            raise ValueError(f"Product has no production value: {resource_id}")
        requirements[resource_id] = contract_required_amount(per_product_budget, value.value_per_unit)
    return requirements


def contract_requirements_for_products(
    state: GameState,
    offer: ContractOffer,
    definitions: dict[str, CardDefinition],
    selected_resource_ids: tuple[str, ...],
) -> dict[str, float]:
    """Build requirements for an explicit, complete UI selection.

    This is also the authoritative acceptance boundary: callers cannot bypass
    uniqueness, eligibility, or the exact requirement count.
    """
    required_count = CONTRACT_REQUIREMENT_COUNTS[offer.kind]
    if len(selected_resource_ids) != required_count:
        raise ValueError(f"{CONTRACT_KIND_LABELS[offer.kind]} requires exactly {required_count} products.")
    if len(set(selected_resource_ids)) != required_count:
        raise ValueError("Contract products must be unique.")
    eligible = {
        option.resource_id
        for option in eligible_contract_products(state, definitions, offer.production_value_budget or 0.0, calculator=contract_value_calculator(state, definitions))
    }
    unavailable = [resource_id for resource_id in selected_resource_ids if resource_id not in eligible]
    if unavailable:
        raise ValueError(f"Product is not eligible for this contract: {unavailable[0]}")

    if offer.balance_version:
        from production_zero.core.contract_capacity import requirements_for_rates
        return requirements_for_rates(offer.capacity_rates, offer.unit_prices, selected_resource_ids, offer.target_minutes)
    per_product_budget = (offer.production_value_budget or 0.0) / required_count
    requirements: dict[str, float] = {}
    for resource_id in selected_resource_ids:
        value = production_value_for_resource(definitions, resource_id)
        if value is None:
            raise ValueError(f"Product has no production value: {resource_id}")
        requirements[resource_id] = contract_required_amount(per_product_budget, value.value_per_unit)
    return requirements


def _generate_unique_requirements(
    rng: random.Random,
    kind: str,
    used_resource_sets: set[tuple[str, ...]],
) -> dict[str, float]:
    resource_count_by_kind = {
        REGULAR: (1, 2),
        DAILY: (1, 2),
        WEEKLY: (2, 3),
    }
    min_count, max_count = resource_count_by_kind[kind]
    for _ in range(20):
        count = rng.randint(min_count, max_count)
        resources = tuple(sorted(rng.sample(CONTRACT_RESOURCES, count)))
        if resources not in used_resource_sets:
            used_resource_sets.add(resources)
            return {
                resource_id: _contract_amount(rng, kind, resource_id)
                for resource_id in resources
            }
    resource = CONTRACT_RESOURCES[len(used_resource_sets) % len(CONTRACT_RESOURCES)]
    used_resource_sets.add((resource,))
    return {resource: _contract_amount(rng, kind, resource)}


def _contract_amount(rng: random.Random, kind: str, resource_id: str) -> float:
    base_values = {
        REGULAR: (45.0, 110.0),
        DAILY: (130.0, 280.0),
        WEEKLY: (650.0, 1350.0),
    }
    low, high = base_values[kind]
    target_value = rng.uniform(low, high)
    raw_amount = target_value / BASE_MARKET_PRICES[resource_id]
    step = 5.0 if raw_amount >= 25 else 1.0
    return max(step, round(raw_amount / step) * step)


def _reward_multiplier(kind: str) -> float:
    if kind == WEEKLY:
        return 1.75
    if kind == DAILY:
        return 1.35
    return 1.15


def _ensure_regular_offers(state: GameState, definitions: dict[str, CardDefinition] | None = None) -> None:
    if state.contracts.offers.get(REGULAR):
        return
    state.contracts.offers[REGULAR] = generate_contract_offers(
        state.rng_seed,
        REGULAR,
        state.contracts.regular_generation,
        state=state,
        definitions=definitions,
    )


def _find_offer(state: GameState, kind: str, contract_id: str) -> ContractOffer:
    for offer in state.contracts.offers.get(kind, []):
        if offer.contract_id == contract_id:
            return offer
    raise ValueError(f"Unknown contract offer: {contract_id}")


def _complete_contract(state: GameState, kind: str, definitions: dict[str, CardDefinition] | None = None, *, now_utc=None) -> None:
    active = state.contracts.active[kind]
    if active.status != "active":
        return
    active.status = "completed"
    state.cash.add(active.offer.reward_cash)
    state.statistics.record_earnings(active.offer.reward_cash)
    sync_company_xp_periods(state, now_utc)
    reward_xp = active.offer.reward_xp
    if kind == REGULAR:
        state.company_xp_progress.regular_full_xp_completions += 1
    award_contract_company_xp(state, reward_xp, definitions, source=f"{kind}_contracts")
    if kind == DAILY:
        from production_zero.core.research import grant_research_points
        grant_research_points(state, active.offer.reward_rp if active.offer.reward_rp is not None else 1, "Daily completion")
    elif kind == WEEKLY:
        from production_zero.core.research import grant_research_points
        grant_research_points(state, active.offer.reward_rp if active.offer.reward_rp is not None else 3, "Weekly completion")
    state.history.append("cash", state.cash.amount)
    state.history.append("company.level", state.company.level)
    state.history.append("company.xp", state.company.current_xp)
    state.contracts.last_status[kind] = f"Completed: {active.offer.name}"
    if kind == REGULAR:
        state.contracts.active.pop(kind, None)
        state.contracts.regular_generation += 1
        state.contracts.offers[REGULAR] = generate_contract_offers(
            state.rng_seed,
            REGULAR,
            state.contracts.regular_generation,
            state=state,
            definitions=definitions,
        )
        _try_regular_auto_repeat(state, definitions)

def _expire_active_contract(state: GameState, kind: str) -> None:
    active = state.contracts.active.get(kind)
    if active is None:
        return
    if active.status == "active":
        active.status = "expired"
        state.contracts.last_status[kind] = f"Expired: {active.offer.name}"
    else:
        state.contracts.last_status[kind] = f"Completed: {active.offer.name}"
    state.contracts.active.pop(kind, None)
