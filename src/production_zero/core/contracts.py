from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from production_zero.core.company import TITLE_MILESTONES, award_company_xp, xp_reward_for_contract_kind
from production_zero.core.definitions import CardDefinition
from production_zero.core.freight import start_outbound_shipments
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack, grant_packs

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
class ContractBook:
    offers: dict[str, list[ContractOffer]] = field(default_factory=dict)
    active: dict[str, ActiveContract] = field(default_factory=dict)
    daily_period_index: int = -1
    weekly_period_index: int = -1
    regular_generation: int = 0
    last_status: dict[str, str] = field(default_factory=dict)


def initialize_contracts(state: GameState) -> None:
    refresh_contracts(state)
    _ensure_regular_offers(state)


def refresh_contracts(state: GameState) -> None:
    elapsed = state.market.elapsed_seconds
    daily_period = int(elapsed // DAY_SECONDS)
    weekly_period = int(elapsed // WEEK_SECONDS)

    if state.contracts.daily_period_index != daily_period:
        _expire_active_contract(state, DAILY)
        state.contracts.daily_period_index = daily_period
        state.contracts.offers[DAILY] = generate_contract_offers(
            state.rng_seed,
            DAILY,
            daily_period,
            expires_at=(daily_period + 1) * DAY_SECONDS,
        )

    if state.contracts.weekly_period_index != weekly_period:
        _expire_active_contract(state, WEEKLY)
        state.contracts.weekly_period_index = weekly_period
        state.contracts.offers[WEEKLY] = generate_contract_offers(
            state.rng_seed,
            WEEKLY,
            weekly_period,
            expires_at=(weekly_period + 1) * WEEK_SECONDS,
        )

    _ensure_regular_offers(state)


def accept_contract(state: GameState, kind: str, contract_id: str) -> None:
    refresh_contracts(state)
    if kind not in CONTRACT_KINDS:
        raise ValueError(f"Unknown contract kind: {kind}")
    if kind in state.contracts.active:
        raise ValueError(f"Contract already active for kind: {kind}")
    offer = _find_offer(state, kind, contract_id)
    state.contracts.active[kind] = ActiveContract(offer=offer)
    state.contracts.last_status[kind] = "Active"


def deliver_available_to_contract(
    state: GameState,
    kind: str,
    definitions: dict[str, CardDefinition],
) -> dict[str, float]:
    refresh_contracts(state)
    if kind not in state.contracts.active:
        raise ValueError(f"No active contract for kind: {kind}")
    active = state.contracts.active[kind]
    if active.status != "active":
        return {}

    delivered_now: dict[str, float] = {}
    for resource_id, required in active.offer.requirements.items():
        remaining = max(0.0, required - active.delivered.get(resource_id, 0.0))
        if remaining <= 0:
            continue
        stock = state.ensure_resource(resource_id)
        amount = min(stock.amount, remaining)
        if amount <= 0:
            continue
        try:
            shipments = start_outbound_shipments(
                state.freight,
                state.cards,
                definitions,
                destination_kind="contract",
                target_id=active.offer.contract_id,
                resource_id=resource_id,
                quantity=amount,
            )
        except ValueError:
            continue
        shipped = sum(shipment.quantity for shipment in shipments)
        stock.consume(shipped)
        delivered_now[resource_id] = shipped
        state.history.append(f"resource.{resource_id}", stock.amount)

    return delivered_now


def receive_contract_delivery(
    state: GameState,
    contract_id: str,
    resource_id: str,
    amount: float,
) -> None:
    for kind, active in tuple(state.contracts.active.items()):
        if active.offer.contract_id != contract_id or active.status != "active":
            continue
        remaining = active.remaining_amount(resource_id)
        if remaining <= 0:
            return
        delivered = min(amount, remaining)
        active.delivered[resource_id] = active.delivered.get(resource_id, 0.0) + delivered
        if active.is_complete:
            _complete_contract(state, kind)
        return


def route_market_delivery_to_contracts(
    state: GameState,
    resource_id: str,
    amount: float,
) -> float:
    if amount <= 0:
        return 0.0
    remaining_amount = amount
    delivered_total = 0.0
    for kind in CONTRACT_KINDS:
        active = state.contracts.active.get(kind)
        if active is None or active.status != "active" or resource_id not in active.offer.requirements:
            continue
        needed = active.remaining_amount(resource_id)
        if needed <= 0:
            continue
        delivered = min(remaining_amount, needed)
        active.delivered[resource_id] = active.delivered.get(resource_id, 0.0) + delivered
        delivered_total += delivered
        remaining_amount -= delivered
        if active.is_complete:
            _complete_contract(state, kind)
        if remaining_amount <= 0:
            break
    return delivered_total


def seconds_until_contract_reset(state: GameState, kind: str) -> float | None:
    elapsed = state.market.elapsed_seconds
    if kind == DAILY:
        return max(0.0, (int(elapsed // DAY_SECONDS) + 1) * DAY_SECONDS - elapsed)
    if kind == WEEKLY:
        return max(0.0, (int(elapsed // WEEK_SECONDS) + 1) * WEEK_SECONDS - elapsed)
    return None


def generate_contract_offers(
    seed: int,
    kind: str,
    period_index: int,
    expires_at: float | None = None,
) -> list[ContractOffer]:
    rng = random.Random(f"{seed}:contracts:{kind}:{period_index}")
    offers: list[ContractOffer] = []
    used_resource_sets: set[tuple[str, ...]] = set()
    for offer_index in range(3):
        requirements = _generate_unique_requirements(rng, kind, used_resource_sets)
        value = sum(BASE_MARKET_PRICES[resource_id] * amount for resource_id, amount in requirements.items())
        reward_cash = round(value * _reward_multiplier(kind) / 5.0) * 5.0
        offers.append(
            ContractOffer(
                contract_id=f"{kind}-{period_index}-{offer_index}",
                kind=kind,
                name=f"{CONTRACT_KIND_LABELS[kind]} #{offer_index + 1}",
                requirements=requirements,
                reward_cash=reward_cash,
                reward_xp=xp_reward_for_contract_kind(kind),
                period_index=period_index,
                expires_at=expires_at,
            )
        )
    return offers


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


def _ensure_regular_offers(state: GameState) -> None:
    if state.contracts.offers.get(REGULAR):
        return
    state.contracts.offers[REGULAR] = generate_contract_offers(
        state.rng_seed,
        REGULAR,
        state.contracts.regular_generation,
    )


def _find_offer(state: GameState, kind: str, contract_id: str) -> ContractOffer:
    for offer in state.contracts.offers.get(kind, []):
        if offer.contract_id == contract_id:
            return offer
    raise ValueError(f"Unknown contract offer: {contract_id}")


def _complete_contract(state: GameState, kind: str) -> None:
    active = state.contracts.active[kind]
    active.status = "completed"
    state.cash.add(active.offer.reward_cash)
    state.statistics.record_earnings(active.offer.reward_cash)
    gained_levels = award_company_xp(state.company, active.offer.reward_xp)
    if kind == DAILY:
        grant_pack(state, DAILY_MINI_PACK, f"contract:{active.offer.contract_id}")
    elif kind == WEEKLY:
        grant_pack(state, FULL_PACK, f"contract:{active.offer.contract_id}")
    _grant_title_milestone_packs(state, gained_levels)
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
        )


def _grant_title_milestone_packs(state: GameState, gained_levels: tuple[int, ...]) -> None:
    if not gained_levels:
        return
    milestones = {level for level, _ in TITLE_MILESTONES if level > 1}
    for level in gained_levels:
        if level in milestones:
            grant_packs(state, FULL_PACK, 3, f"title-level:{level}")


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
