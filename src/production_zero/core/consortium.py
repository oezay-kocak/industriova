from __future__ import annotations

import re
import time
import json
from dataclasses import asdict, dataclass, field
from math import pow, isfinite
from typing import TYPE_CHECKING, Callable

from production_zero.core.company_xp import award_contract_company_xp
from production_zero.core.contracts import contract_capacity_estimate
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack
from production_zero.core.production_values import ProductionValueCalculator, contract_required_amount, eligible_contract_products

if TYPE_CHECKING:
    from production_zero.core.definitions import CardDefinition
    from production_zero.core.state import GameState


OPEN = "open"
APPLICATION = "application"
INVITE_ONLY = "invite_only"
JOIN_POLICIES = (OPEN, APPLICATION, INVITE_ONLY)

CHAIRMAN = "chairman"
BOARD_MEMBER = "board_member"
MEMBER = "member"
ROLES = (CHAIRMAN, BOARD_MEMBER, MEMBER)

AVAILABLE = "available"
ACTIVE = "active"
COMPLETED = "completed"
EXPIRED = "expired"
CONTRACT_STATUSES = (AVAILABLE, ACTIVE, COMPLETED, EXPIRED)
CONSORTIUM_DAILY = "daily"
CONSORTIUM_WEEKLY = "weekly"
CONSORTIUM_CONTRACT_KINDS = (CONSORTIUM_DAILY, CONSORTIUM_WEEKLY)

MEMBER_CAPACITY_MILESTONES: tuple[tuple[int, int], ...] = (
    (1, 10),
    (5, 15),
    (10, 20),
    (15, 25),
    (20, 30),
    (30, 40),
    (40, 50),
)
MAX_CONSORTIUM_MEMBERS = 50
CONSORTIUM_XP_BASE = 1_000.0
CONSORTIUM_XP_GROWTH = 250.0
MEMBER_SCALE_EXPONENT = 0.72
ACTIVITY_LIMIT = 100
CONTRACT_PRODUCT_SLOTS = {CONSORTIUM_DAILY: 3, CONSORTIUM_WEEKLY: 4}


def _scoped_receipt(kind, company_id, request_id):
    return kind+":"+json.dumps([str(company_id),str(request_id)],separators=(",",":"))


def consortium_xp_for_next_level(level: int) -> float:
    if level < 1:
        raise ValueError("Consortium level must be positive.")
    return CONSORTIUM_XP_BASE + (level - 1) * CONSORTIUM_XP_GROWTH


def consortium_xp_floor(level: int) -> float:
    return sum(consortium_xp_for_next_level(value) for value in range(1, max(1, level)))


def consortium_level_for_xp(total_xp: float) -> int:
    remaining = max(0.0, total_xp)
    level = 1
    while remaining >= consortium_xp_for_next_level(level):
        remaining -= consortium_xp_for_next_level(level)
        level += 1
    return level


def member_capacity_for_level(level: int) -> int:
    capacity = 10
    for required_level, unlocked_capacity in MEMBER_CAPACITY_MILESTONES:
        if level >= required_level:
            capacity = unlocked_capacity
    return min(MAX_CONSORTIUM_MEMBERS, capacity)


@dataclass(slots=True)
class ConsortiumMember:
    company_id: str
    company_name: str
    company_level: int
    role: str = MEMBER
    joined_at: float = 0.0
    lifetime_contribution: float = 0.0
    capable_resource_ids: tuple[str, ...] = ()
    capacity_rates: dict[str, float] = field(default_factory=dict)
    capacity_signature: str = ""
    sale_prices: dict[str, float] = field(default_factory=dict)
    capacity_observed_at: float | None = None


@dataclass(slots=True)
class ConsortiumApplication:
    company_id: str
    company_name: str
    company_level: int
    created_at: float


@dataclass(slots=True)
class ConsortiumInvitation:
    company_id: str
    company_name: str
    company_level: int
    invited_by: str
    created_at: float


@dataclass(frozen=True, slots=True)
class CompanyIdentity:
    company_id: str
    company_name: str
    company_level: int


@dataclass(frozen=True, slots=True)
class ConsortiumPersonalReward:
    cash: float = 0.0
    company_xp: float = 0.0
    packs: int = 0
    research_points: int = 0


@dataclass(slots=True)
class ConsortiumContract:
    contract_id: str
    kind: str
    status: str
    created_at: float
    expires_at: float
    requirements: dict[str, float]
    personal_reward: ConsortiumPersonalReward
    consortium_xp_reward: float
    started_at: float | None = None
    completed_at: float | None = None
    eligible_member_ids: tuple[str, ...] = ()
    member_count_at_start: int = 0
    scaling_inputs: dict[str, float] = field(default_factory=dict)
    delivered: dict[str, float] = field(default_factory=dict)
    contributions: dict[str, dict[str, float]] = field(default_factory=dict)
    forfeited_member_ids: set[str] = field(default_factory=set)
    reward_delivered_member_ids: set[str] = field(default_factory=set)
    consortium_xp_delivered: bool = False
    processed_request_ids: set[str] = field(default_factory=set)
    balance_version: int = 0
    capacity_rates: dict[str, float] = field(default_factory=dict)
    unit_prices: dict[str, float] = field(default_factory=dict)
    capacity_signature: str = ""
    quoted_level: int = 1
    member_unit_prices: dict[str, dict[str, float]] = field(default_factory=dict)
    rp_minimum_shares: dict[str, float] = field(default_factory=dict)

    def remaining(self, resource_id: str) -> float:
        return max(0.0, self.requirements.get(resource_id, 0.0) - self.delivered.get(resource_id, 0.0))

    @property
    def is_fulfilled(self) -> bool:
        return bool(self.requirements) and all(self.remaining(resource_id) <= 1e-9 for resource_id in self.requirements)

    def member_contribution(self, company_id: str) -> float:
        return sum(self.contributions.get(company_id, {}).values())


@dataclass(slots=True)
class ConsortiumActivity:
    activity_id: str
    event_type: str
    label: str
    created_at: float


@dataclass(slots=True)
class Consortium:
    consortium_id: str
    name: str
    level: int = 1
    consortium_xp: float = 0.0
    member_capacity: int = 10
    join_policy: str = OPEN
    minimum_company_level: int = 1
    created_at: float = 0.0
    members: dict[str, ConsortiumMember] = field(default_factory=dict)
    applications: dict[str, ConsortiumApplication] = field(default_factory=dict)
    invitations: dict[str, ConsortiumInvitation] = field(default_factory=dict)
    contracts: dict[str, ConsortiumContract] = field(default_factory=dict)
    contract_history: list[ConsortiumContract] = field(default_factory=list)
    activity: list[ConsortiumActivity] = field(default_factory=list)
    next_contract_sequence: int = 1
    next_activity_sequence: int = 1

    def chairman(self) -> ConsortiumMember:
        return next(member for member in self.members.values() if member.role == CHAIRMAN)


@dataclass(slots=True)
class ConsortiumNetwork:
    current_company_id: str = "company.local"
    current_company_name: str = "ZERO INDUSTRIES"
    consortiums: dict[str, Consortium] = field(default_factory=dict)
    next_consortium_sequence: int = 1
    reward_receipts: dict[str, dict[str, ConsortiumPersonalReward]] = field(default_factory=dict)

    def membership(self, company_id: str | None = None) -> tuple[Consortium, ConsortiumMember] | None:
        target = company_id or self.current_company_id
        for consortium in self.consortiums.values():
            member = consortium.members.get(target)
            if member is not None:
                return consortium, member
        return None


class ConsortiumService:
    """Authoritative local implementation of the future server command boundary."""

    def __init__(
        self,
        state: GameState,
        definitions: dict[str, CardDefinition] | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.state = state
        self.definitions = definitions or {}
        self.clock = clock
        self._preview_requirements = {}
        self._network_token = None

    @property
    def network(self):
        # MainWindow keeps the shared GameState object but replaces subsystems
        # on Load/New Game. Never hold the previous network or its draft quotes.
        network = self.state.consortium
        token = (id(network), network.current_company_id)
        if token != self._network_token:
            self._preview_requirements.clear()
            self._network_token = token
        return network

    @property
    def current_company_id(self) -> str:
        return self.network.current_company_id

    def create(self, name: str, join_policy: str = OPEN, minimum_company_level: int = 1) -> Consortium:
        if self.network.membership() is not None:
            raise ValueError("Company already belongs to a Consortium.")
        normalized = " ".join(name.split()).strip()
        if not 3 <= len(normalized) <= 40 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 '&.-]*", normalized):
            raise ValueError("Consortium name must be 3–40 valid characters.")
        if any(item.name.casefold() == normalized.casefold() for item in self.network.consortiums.values()):
            raise ValueError("Consortium name is already in use.")
        self._validate_settings(join_policy, minimum_company_level)
        now = self.clock()
        consortium_id = f"consortium-{self.network.next_consortium_sequence}"
        self.network.next_consortium_sequence += 1
        consortium = Consortium(
            consortium_id=consortium_id,
            name=normalized,
            join_policy=join_policy,
            minimum_company_level=minimum_company_level,
            created_at=now,
        )
        consortium.members[self.current_company_id] = ConsortiumMember(
            self.current_company_id,
            self.network.current_company_name,
            self.state.company.level,
            CHAIRMAN,
            now,
        )
        self.network.consortiums[consortium_id] = consortium
        self._activity(consortium, "created", f"{normalized} ESTABLISHED")
        if self.definitions:
            self._ensure_offers(consortium)
        return consortium

    def join(self, consortium_id: str, company_id: str | None = None, company_name: str | None = None, company_level: int | None = None) -> None:
        consortium = self._consortium(consortium_id)
        cid, name, level = self._identity(company_id, company_name, company_level)
        if self.network.membership(cid) is not None:
            raise ValueError("Company already belongs to a Consortium.")
        self._validate_join(consortium, level)
        if consortium.join_policy == APPLICATION:
            raise PermissionError("This Consortium requires an application.")
        if consortium.join_policy == INVITE_ONLY and cid not in consortium.invitations:
            raise PermissionError("This Consortium requires an invitation.")
        self._add_member(consortium, cid, name, level)

    def apply(self, consortium_id: str, company_id: str | None = None, company_name: str | None = None, company_level: int | None = None) -> None:
        consortium = self._consortium(consortium_id)
        cid, name, level = self._identity(company_id, company_name, company_level)
        if consortium.join_policy != APPLICATION:
            raise ValueError("Consortium does not accept applications.")
        if self.network.membership(cid) is not None:
            raise ValueError("Company already belongs to a Consortium.")
        self._validate_join(consortium, level)
        if cid in consortium.applications:
            return
        consortium.applications[cid] = ConsortiumApplication(cid, name, level, self.clock())

    def invite(self, consortium_id: str, actor_id: str, company_id: str, company_name: str, company_level: int) -> None:
        consortium = self._consortium(consortium_id)
        self._require_management(consortium, actor_id)
        if self.network.membership(company_id) is not None:
            raise ValueError("Company already belongs to a Consortium.")
        self._validate_join(consortium, company_level)
        consortium.invitations[company_id] = ConsortiumInvitation(
            company_id, company_name, company_level, actor_id, self.clock()
        )

    def resolve_company(self, query: str) -> CompanyIdentity | None:
        """Resolve only identities already known to the local Consortium network."""
        text = query.strip().casefold()
        if not text:
            return None
        known = {self.current_company_id: CompanyIdentity(
            self.current_company_id, self.network.current_company_name, self.state.company.level
        )}
        for consortium in self.network.consortiums.values():
            for record in (*consortium.members.values(), *consortium.applications.values(), *consortium.invitations.values()):
                known.setdefault(record.company_id, CompanyIdentity(record.company_id, record.company_name, record.company_level))
        matches = [identity for identity in known.values() if text in (identity.company_id.casefold(), identity.company_name.casefold())]
        return matches[0] if len(matches) == 1 else None

    def invite_resolved(self, consortium_id: str, actor_id: str, query: str) -> CompanyIdentity:
        identity = self.resolve_company(query)
        if identity is None:
            raise ValueError("Company not found in the local identity directory.")
        self.invite(consortium_id, actor_id, identity.company_id, identity.company_name, identity.company_level)
        return identity

    def invitation_eligibility(self, consortium_id: str, identity: CompanyIdentity) -> tuple[bool, str]:
        consortium = self._consortium(consortium_id)
        if self.network.membership(identity.company_id) is not None:
            return False, "ALREADY IN A CONSORTIUM"
        try:
            self._validate_join(consortium, identity.company_level)
        except (ValueError, PermissionError) as error:
            return False, str(error).upper()
        return True, "ELIGIBLE FOR INVITATION"

    def process_application(self, consortium_id: str, actor_id: str, company_id: str, accept: bool) -> None:
        consortium = self._consortium(consortium_id)
        self._require_management(consortium, actor_id)
        application = consortium.applications.pop(company_id, None)
        if application is None:
            raise KeyError("Unknown Consortium application.")
        if accept:
            self._validate_join(consortium, application.company_level)
            self._add_member(consortium, application.company_id, application.company_name, application.company_level)

    def leave(self, consortium_id: str, company_id: str) -> None:
        consortium = self._consortium(consortium_id)
        member = self._member(consortium, company_id)
        if member.role == CHAIRMAN:
            raise PermissionError("Chairman must transfer leadership or disband before leaving.")
        self._forfeit_active_contracts(consortium, company_id)
        del consortium.members[company_id]
        self._activity(consortium, "member_left", f"{member.company_name} LEFT")

    def remove(self, consortium_id: str, actor_id: str, company_id: str) -> None:
        consortium = self._consortium(consortium_id)
        self._require_chairman(consortium, actor_id)
        member = self._member(consortium, company_id)
        if member.role == CHAIRMAN:
            raise ValueError("Chairman cannot be removed.")
        self._forfeit_active_contracts(consortium, company_id)
        del consortium.members[company_id]
        self._activity(consortium, "member_removed", f"{member.company_name} REMOVED")

    def set_role(self, consortium_id: str, actor_id: str, company_id: str, role: str) -> None:
        consortium = self._consortium(consortium_id)
        self._require_chairman(consortium, actor_id)
        if role not in (BOARD_MEMBER, MEMBER):
            raise ValueError("Only Board Member and Member role changes are supported.")
        member = self._member(consortium, company_id)
        if member.role == CHAIRMAN:
            raise ValueError("Use leadership transfer for the Chairman.")
        member.role = role
        self._activity(consortium, "role_changed", f"{member.company_name} · {role.replace('_', ' ').upper()}")

    def transfer_leadership(self, consortium_id: str, actor_id: str, company_id: str) -> None:
        consortium = self._consortium(consortium_id)
        current = self._require_chairman(consortium, actor_id)
        successor = self._member(consortium, company_id)
        if successor.company_id == current.company_id:
            return
        current.role = BOARD_MEMBER
        successor.role = CHAIRMAN
        self._activity(consortium, "role_changed", f"{successor.company_name} APPOINTED CHAIRMAN")

    def update_settings(self, consortium_id: str, actor_id: str, join_policy: str, minimum_company_level: int) -> None:
        consortium = self._consortium(consortium_id)
        self._require_chairman(consortium, actor_id)
        self._validate_settings(join_policy, minimum_company_level)
        consortium.join_policy = join_policy
        consortium.minimum_company_level = minimum_company_level

    def disband(self, consortium_id: str, actor_id: str) -> None:
        consortium = self._consortium(consortium_id)
        self._require_chairman(consortium, actor_id)
        for contract in consortium.contracts.values():
            if contract.status == ACTIVE:
                contract.status = EXPIRED
                contract.forfeited_member_ids.update(contract.eligible_member_ids)
        del self.network.consortiums[consortium_id]

    def update_capacity_snapshot(self, company_id, company_state):
        """Trusted local/server boundary: derive capability from a real company.

        An identity or declared product list is never evidence of throughput.
        Remote adapters must authenticate the company before calling this method.
        """
        if company_state.consortium.current_company_id != company_id:
            raise PermissionError("Capacity snapshot belongs to another company.")
        membership = self.network.membership(company_id)
        if membership is None:
            raise PermissionError("Company is not a Consortium member.")
        from production_zero.core.contracts import _capacity_plan
        plan = _capacity_plan(company_state, self.definitions)
        member = membership[1]
        previous_signature = member.capacity_signature
        # Permanent paid equipment; pauses, current stock and routes are excluded.
        # Prefix invalidates P8 remote production-only evidence without new fields.
        signature = "freight-only-v1:" + plan.signature
        member.capacity_rates = dict(plan.rates)
        member.capacity_signature = signature
        member.capable_resource_ids = tuple(sorted(member.capacity_rates))
        member.capacity_observed_at = self.clock()
        from production_zero.core.modifiers import market_sale_price
        from production_zero.core.progression import production_options
        products = tuple(option.output_resource for option in production_options(self.definitions))
        if previous_signature != signature or len(member.sale_prices)!=len(products):
            # A stock donor keeps its real Research value even when it cannot
            # currently manufacture the product itself.
            member.sale_prices = {rid:market_sale_price(company_state,rid) for rid in products}

    def _group_capacity(self, consortium):
        from production_zero.core.contract_capacity import combined_rates
        self.update_capacity_snapshot(self.current_company_id, self.state)
        # Preserve unknown remote identities for roles, never invent their output.
        rates = combined_rates(self._fresh_rates(m) for m in consortium.members.values())
        signature = "|".join(f"{cid}:{m.capacity_signature}:{self._snapshot_fresh(m)}" for cid,m in sorted(consortium.members.items()))
        return rates, signature

    def _fresh_rates(self, member):
        # A short pause keeps recoverable capability. A remote company which
        # has not supplied real state for a day is unknown, never extrapolated.
        return member.capacity_rates if self._snapshot_fresh(member) and member.capacity_signature.startswith("freight-only-v1:") else {}

    def _snapshot_fresh(self, member):
        return member.capacity_observed_at is not None and max(0.,self.clock()-member.capacity_observed_at)<=86400

    def rp_minimum_shares(self, consortium, contract, requirements):
        total = sum(contract.unit_prices[rid]*qty for rid,qty in requirements.items())
        expected = {cid:sum(contract.unit_prices[rid]*qty*self._fresh_rates(member).get(rid,0.)/contract.capacity_rates[rid] for rid,qty in requirements.items())/total for cid,member in consortium.members.items()}
        smallest = min((share for share in expected.values() if share>0),default=1.)
        return {cid:.5*(share if share>0 else smallest) for cid,share in expected.items()}

    def contract_candidates(self, consortium_id: str, kind: str) -> tuple[str, ...]:
        consortium = self._consortium(consortium_id)
        if kind not in CONSORTIUM_CONTRACT_KINDS:
            raise ValueError("Unknown Consortium Contract kind.")
        self._ensure_offers(consortium, rotate_completed=False)
        contract = consortium.contracts[kind]
        if contract.balance_version:
            return tuple(sorted(contract.capacity_rates, key=lambda rid: (rid.replace("_"," "),rid)))
        values = ProductionValueCalculator(self.definitions).values()
        budget = consortium.contracts[kind].scaling_inputs["production_value_budget"] / CONTRACT_PRODUCT_SLOTS[kind]
        local = {option.resource_id for option in eligible_contract_products(self.state, self.definitions, budget)}
        remote = {resource_id for member in consortium.members.values() if member.company_id != self.current_company_id for resource_id in member.capable_resource_ids}
        return tuple(sorted((local | remote) & values.keys(), key=lambda resource_id: (values[resource_id].name, resource_id)))

    def preview_contract(self, consortium_id: str, kind: str, selected_resource_ids: tuple[str, ...]) -> dict[str, float]:
        consortium = self._consortium(consortium_id)
        if kind not in CONSORTIUM_CONTRACT_KINDS:
            raise ValueError("Unknown Consortium Contract kind.")
        if len(selected_resource_ids) != CONTRACT_PRODUCT_SLOTS[kind] or len(set(selected_resource_ids)) != len(selected_resource_ids):
            raise ValueError("Select a unique product for every Contract slot.")
        candidates = set(self.contract_candidates(consortium_id, kind))
        if any(resource_id not in candidates for resource_id in selected_resource_ids):
            raise ValueError("Selected product is unavailable to the Consortium.")
        contract = consortium.contracts[kind]
        if contract.balance_version:
            from production_zero.core.contract_capacity import requirements_for_rates
            result = requirements_for_rates(contract.capacity_rates, contract.unit_prices, selected_resource_ids, 120. if kind==CONSORTIUM_DAILY else 480.)
            self._preview_requirements[contract.contract_id] = result
            return result
        scale = pow(max(1, len(consortium.members)), MEMBER_SCALE_EXPONENT)
        values = ProductionValueCalculator(self.definitions).values()
        per_product = contract.scaling_inputs["production_value_budget"] / CONTRACT_PRODUCT_SLOTS[kind]
        return {resource_id: max(1.0, round(contract_required_amount(per_product, values[resource_id].value_per_unit) * scale)) for resource_id in selected_resource_ids}

    def preview_contract_rewards(self, consortium_id: str, kind: str, selected_resource_ids=None) -> tuple[ConsortiumPersonalReward, float]:
        consortium = self._consortium(consortium_id)
        contract = self._contract(consortium, kind)
        if contract.balance_version:
            if contract.status != AVAILABLE:
                return contract.personal_reward, contract.consortium_xp_reward
            requirements = self.preview_contract(consortium_id,kind,selected_resource_ids) if selected_resource_ids is not None else self._preview_requirements.get(contract.contract_id,{})
            return self._balanced_rewards(contract, requirements)
        scale = pow(max(1, len(consortium.members)), MEMBER_SCALE_EXPONENT)
        reward_scale = 1.0 + (scale - 1.0) * 0.35
        reward = ConsortiumPersonalReward(
            cash=round(contract.personal_reward.cash * reward_scale / 5.0) * 5.0,
            company_xp=round(contract.personal_reward.company_xp * reward_scale / 5.0) * 5.0,
            packs=contract.personal_reward.packs,
            research_points=contract.personal_reward.research_points,
        )
        xp = round(contract.consortium_xp_reward * (0.75 + 0.25 * scale) / 5.0) * 5.0
        return reward, xp

    def start_contract(self, consortium_id: str, actor_id: str, kind: str, selected_resource_ids: tuple[str, ...] | None = None, *, expected_contract_id: str | None = None) -> ConsortiumContract:
        consortium = self._consortium(consortium_id)
        self._require_management(consortium, actor_id)
        self.expire_contracts(consortium_id)
        if kind not in CONSORTIUM_CONTRACT_KINDS:
            raise ValueError("Unknown Consortium Contract kind.")
        self._ensure_offers(consortium)
        contract = consortium.contracts[kind]
        if expected_contract_id is not None and contract.contract_id != expected_contract_id:
            raise ValueError("Consortium offer changed; review the new quote.")
        if contract.status != AVAILABLE:
            raise ValueError("Consortium Contract is not available.")
        if selected_resource_ids is None:
            raise ValueError("Select Contract products before starting.")
        requirements = self.preview_contract(consortium_id, kind, selected_resource_ids)
        quoted_reward, quoted_xp = self.preview_contract_rewards(consortium_id, kind)
        now = self.clock()
        snapshot = tuple(consortium.members)
        contract.status = ACTIVE
        contract.started_at = now
        contract.eligible_member_ids = snapshot
        contract.member_count_at_start = len(snapshot)
        # The preview becomes the immutable product/quantity snapshot at START.
        scale = pow(max(1, len(snapshot)), MEMBER_SCALE_EXPONENT)
        contract.requirements = requirements
        if contract.balance_version:
            contract.member_unit_prices = {cid:{rid:prices[rid] for rid in requirements if rid in prices} for cid,prices in contract.member_unit_prices.items()}
            contract.rp_minimum_shares = self.rp_minimum_shares(consortium,contract,requirements)
        reward_scale = 1.0 + (scale - 1.0) * 0.35
        contract.personal_reward, contract.consortium_xp_reward = quoted_reward, quoted_xp
        contract.scaling_inputs["member_scale"] = scale
        contract.scaling_inputs["reward_scale"] = reward_scale
        contract.scaling_inputs["member_count_at_start"] = float(len(snapshot))
        self._activity(consortium, "contract_started", f"{kind.upper()} CONTRACT STARTED")
        return contract

    def contribute(
        self,
        consortium_id: str,
        company_id: str,
        kind: str,
        resource_id: str,
        amount: float,
        *,
        request_id: str | None = None,
        company_state: GameState | None = None,
        expected_contract_id: str | None = None,
    ) -> float:
        # Retain a rejecting compatibility endpoint for old Commands/adapters.
        # Reject before touching membership, expiry, storage, history or receipts.
        raise PermissionError("DELIVER VIA FREIGHT: direct Consortium contributions are disabled.")

    def receive_freight_delivery(self, consortium_id, kind, contract_id, resource_id, amount, delivery_id):
        raise PermissionError("Only the central Freight completion may deliver goods.")

    def _accept_freight_arrival(self, grant):
        from production_zero.core.freight_settlement import _claim_arrival
        shipment = _claim_arrival(grant, self.state)
        consortium_id, kind, contract_id = shipment.target_id.split("|", 2)
        resource_id, amount, delivery_id = shipment.resource_id, shipment.quantity, shipment.shipment_id
        consortium = self._consortium(consortium_id)
        receipt = _scoped_receipt("freight",self.current_company_id,delivery_id)
        legacy_receipt = f"freight:{delivery_id}"
        # A retry can arrive after completion, rotation or membership loss.
        # Check retained receipts before target/status checks: zero accepted
        # quantity alone would otherwise turn a replay into a second sale.
        retained = (*consortium.contracts.values(), *consortium.contract_history)
        for settled in retained:
            if settled.contract_id == contract_id and (
                receipt in settled.processed_request_ids or
                not settled.balance_version and legacy_receipt in settled.processed_request_ids
            ):
                from production_zero.core.freight_settlement import _FreightAlreadySettled
                raise _FreightAlreadySettled()
        self._member(consortium, self.current_company_id)
        contract = self._contract(consortium, kind)
        self._expire_one(consortium, contract)
        if contract.contract_id != contract_id or contract.status != ACTIVE:
            return 0.
        from math import isfinite
        if not isfinite(amount) or amount <= 0 or resource_id not in contract.requirements:
            raise ValueError("Invalid reserved freight delivery")
        delivered = min(amount, contract.remaining(resource_id))
        if delivered <= 0:
            return 0.
        contract.delivered[resource_id] = contract.delivered.get(resource_id, 0.) + delivered
        contributions = contract.contributions.setdefault(self.current_company_id, {})
        contributions[resource_id] = contributions.get(resource_id, 0.) + delivered
        consortium.members[self.current_company_id].lifetime_contribution += delivered
        contract.processed_request_ids.add(receipt)
        self._contribution_activity(consortium, self.current_company_id, kind, delivered)
        if contract.is_fulfilled:
            self.complete_contract(consortium_id, kind)
        return delivered

    def complete_contract(self, consortium_id: str, kind: str) -> tuple[str, ...]:
        consortium = self._consortium(consortium_id)
        contract = self._contract(consortium, kind)
        if contract.status == COMPLETED:
            return tuple(sorted(contract.reward_delivered_member_ids))
        self._expire_one(consortium, contract)
        if contract.status != ACTIVE or not contract.is_fulfilled:
            raise ValueError("Consortium Contract is not complete.")
        contract.status = COMPLETED
        contract.completed_at = self.clock()
        recipients: list[str] = []
        for company_id in contract.eligible_member_ids:
            if company_id in contract.forfeited_member_ids:
                continue
            if company_id not in consortium.members:
                continue
            if contract.member_contribution(company_id) <= 0:
                continue
            self._deliver_reward(consortium, contract, company_id)
            recipients.append(company_id)
        if not contract.consortium_xp_delivered:
            self._award_consortium_xp(consortium, contract.consortium_xp_reward)
            contract.consortium_xp_delivered = True
        self._activity(consortium, "contract_completed", f"{kind.upper()} CONTRACT COMPLETE")
        return tuple(recipients)

    def expire_contracts(self, consortium_id: str) -> None:
        consortium = self._consortium(consortium_id)
        for contract in consortium.contracts.values():
            self._expire_one(consortium, contract)

    def reward_eligibility(self, consortium_id: str, kind: str, company_id: str | None = None) -> dict[str, bool]:
        consortium = self._consortium(consortium_id)
        contract = self._contract(consortium, kind)
        cid = company_id or self.current_company_id
        at_start = cid in contract.eligible_member_ids and cid not in contract.forfeited_member_ids
        contributed = contract.member_contribution(cid) > 0
        current = cid in consortium.members
        return {
            "eligible_at_start": at_start,
            "contributed": contributed,
            "current_member": current,
            "reward_eligible": at_start and contributed and current,
        }

    def _ensure_offers(self, consortium: Consortium, *, rotate_completed=True) -> None:
        rates, signature = self._group_capacity(consortium)
        for kind in CONSORTIUM_CONTRACT_KINDS:
            current = consortium.contracts.get(kind)
            changed = current is not None and current.status==AVAILABLE and (not current.balance_version or current.capacity_signature != signature)
            if current is None or (rotate_completed and current.status in (COMPLETED, EXPIRED)) or changed:
                if current is not None:
                    self._preview_requirements.pop(current.contract_id, None)
                if current is not None and current.status != AVAILABLE:
                    consortium.contract_history.append(current)
                    consortium.contract_history[:] = consortium.contract_history[-40:]
                consortium.contracts[kind] = self._generate_contract(consortium, kind)

    def renew_contract_offer(self, consortium_id, actor_id, kind):
        """Expose the existing rotation without accepting or replacing an active goal."""
        consortium = self._consortium(consortium_id)
        self._require_management(consortium, actor_id)
        contract = self._contract(consortium, kind)
        self._expire_one(consortium, contract)
        if contract.status == ACTIVE:
            raise ValueError("An active Consortium Contract cannot be replaced.")
        self._ensure_offers(consortium)
        return consortium.contracts[kind]

    def _generate_contract(self, consortium: Consortium, kind: str) -> ConsortiumContract:
        now = self.clock()
        sequence = consortium.next_contract_sequence
        consortium.next_contract_sequence += 1
        duration = 24 * 60 * 60 if kind == CONSORTIUM_DAILY else 7 * 24 * 60 * 60
        from production_zero.core.market import market_price_for
        from production_zero.core.contract_capacity import BALANCE_VERSION
        rates, signature = self._group_capacity(consortium)
        if not self.definitions:
            raise ValueError("No valid production definitions for Consortium Contracts.")
        budget = max(1., max(rates.values(),default=0.))
        capacity_value = max(rates.values(),default=0.)
        reward = ConsortiumPersonalReward()
        from hashlib import sha256
        suffix = sha256(f"{self.state.rng_seed}:{signature}:{now}".encode()).hexdigest()[:12]
        seen = {c.contract_id for c in (*consortium.contracts.values(), *consortium.contract_history)}
        seen.update(self.network.reward_receipts)
        seen.update(ship.target_id.split("|",2)[-1] for ship in self.state.freight.outbound_shipments.values() if ship.target_id)
        contract_id = f"{consortium.consortium_id}-{kind}-{sequence}-{suffix}"
        while contract_id in seen:
            sequence = consortium.next_contract_sequence
            consortium.next_contract_sequence += 1
            contract_id = f"{consortium.consortium_id}-{kind}-{sequence}-{suffix}"
        return ConsortiumContract(
            contract_id=contract_id,
            kind=kind,
            status=AVAILABLE,
            created_at=now,
            expires_at=now + duration,
            requirements={},
            personal_reward=reward,
            consortium_xp_reward=0.,
            balance_version=BALANCE_VERSION, capacity_rates=rates,
            unit_prices={rid:market_price_for(self.state.market,rid) for rid in rates},
            capacity_signature=signature, quoted_level=self.state.company.level,
            member_unit_prices={cid:{rid:m.sale_prices[rid] for rid in rates if rid in m.sale_prices} if self._snapshot_fresh(m) else {} for cid,m in consortium.members.items()},
            scaling_inputs={"production_value_budget": budget, "capacity_pv_per_minute": capacity_value},
        )

    def _balanced_rewards(self, contract, requirements):
        from production_zero.core.contracts import contract_work_xp_quote
        from production_zero.core.production_values import ProductionValueCalculator
        if not requirements:
            return ConsortiumPersonalReward(), 0.
        ceiling = {rid:max([contract.unit_prices[rid], *(prices.get(rid,contract.unit_prices[rid]) for prices in contract.member_unit_prices.values())]) for rid in requirements}
        value = sum(ceiling[rid]*qty for rid,qty in requirements.items())
        from production_zero.core.contracts import contract_value_calculator
        work = contract_value_calculator(self.state,self.definitions)
        pv = sum(work.value_for_resource(rid).value_per_unit*qty for rid,qty in requirements.items())
        reward = ConsortiumPersonalReward(
            cash=round(value*(1.15 if contract.kind==CONSORTIUM_DAILY else 1.25),2),
            company_xp=contract_work_xp_quote(self.state,self.definitions,contract.kind,requirements,level=contract.quoted_level),
            research_points=0 if contract.kind==CONSORTIUM_DAILY else 1)
        return reward, round((400. if contract.kind==CONSORTIUM_DAILY else 1750.)+pv,2)

    def personal_reward_quote(self, contract, company_id):
        """Frozen pool times fixed-price contribution share; no redistribution.

        Forfeited/late contributions remain in the denominator. They cannot
        increase a remaining member's payment. Old accepted contracts retain the
        original full-reward-per-contributor rule (balance_version == 0).
        """
        if not contract.balance_version:
            return contract.personal_reward
        total = sum(contract.unit_prices[rid]*qty for rid,qty in contract.requirements.items())
        contribution = sum(contract.unit_prices.get(rid,0.)*qty for rid,qty in contract.contributions.get(company_id,{}).items())
        share = min(1., max(0., contribution/total)) if total>0 else 0.
        ceiling = {rid:max([contract.unit_prices[rid], *(prices.get(rid,contract.unit_prices[rid]) for prices in contract.member_unit_prices.values())]) for rid in contract.requirements}
        cash_total = sum(ceiling[rid]*qty for rid,qty in contract.requirements.items())
        prices = contract.member_unit_prices.get(company_id,{})
        cash_contribution = sum(prices.get(rid,contract.unit_prices.get(rid,0.))*qty for rid,qty in contract.contributions.get(company_id,{}).items())
        cash_share = min(1.,max(0.,cash_contribution/cash_total)) if cash_total>0 else 0.
        pool = contract.personal_reward
        return ConsortiumPersonalReward(
            cash=int((pool.cash*100+1e-7)*cash_share)/100,
            company_xp=int(pool.company_xp*100*share)/100,
            research_points=pool.research_points if share+1e-12>=contract.rp_minimum_shares.get(company_id,1/max(1,contract.member_count_at_start)) else 0)

    def _deliver_reward(self, consortium: Consortium, contract: ConsortiumContract, company_id: str) -> None:
        if company_id in contract.reward_delivered_member_ids:
            return
        contract.reward_delivered_member_ids.add(company_id)
        reward = self.personal_reward_quote(contract, company_id)
        self.network.reward_receipts.setdefault(contract.contract_id, {})[company_id] = reward
        if company_id != self.current_company_id:
            return
        self.state.cash.add(reward.cash)
        self.state.statistics.record_earnings(reward.cash)
        self.state.history.append("cash", self.state.cash.amount)
        award_contract_company_xp(
            self.state,
            reward.company_xp,
            self.definitions,
            source=f"consortium_{contract.kind}",
        )

        if reward.research_points:
            from production_zero.core.research import grant_research_points

            grant_research_points(self.state, reward.research_points, "Consortium Contract")

    def _award_consortium_xp(self, consortium: Consortium, amount: float) -> None:
        old_level = consortium.level
        old_capacity = consortium.member_capacity
        consortium.consortium_xp += max(0.0, amount)
        consortium.level = consortium_level_for_xp(consortium.consortium_xp)
        consortium.member_capacity = member_capacity_for_level(consortium.level)
        if consortium.level > old_level:
            self._activity(consortium, "level_up", f"CONSORTIUM LEVEL {consortium.level}")
        if consortium.member_capacity > old_capacity:
            self._activity(
                consortium,
                "capacity_milestone",
                f"MEMBER CAPACITY {old_capacity} → {consortium.member_capacity}",
            )

    def _expire_one(self, consortium: Consortium, contract: ConsortiumContract) -> None:
        if contract.status in (AVAILABLE, ACTIVE) and self.clock() >= contract.expires_at:
            contract.status = EXPIRED
            self._activity(consortium, "contract_expired", f"{contract.kind.upper()} CONTRACT EXPIRED")

    def _add_member(self, consortium: Consortium, company_id: str, name: str, level: int) -> None:
        existing = self.network.membership(company_id)
        if existing is not None:
            if existing[0].consortium_id == consortium.consortium_id:
                return
            raise ValueError("Company already belongs to a Consortium.")
        self._validate_join(consortium, level)
        consortium.members[company_id] = ConsortiumMember(company_id, name, level, MEMBER, self.clock())
        consortium.applications.pop(company_id, None)
        consortium.invitations.pop(company_id, None)
        self._activity(consortium, "member_joined", f"{name} JOINED")

    def _forfeit_active_contracts(self, consortium: Consortium, company_id: str) -> None:
        for contract in consortium.contracts.values():
            if contract.status == ACTIVE:
                contract.forfeited_member_ids.add(company_id)

    def _contribution_activity(self, consortium: Consortium, company_id: str, kind: str, amount: float) -> None:
        member = consortium.members[company_id]
        event_type = f"contribution:{kind}:{company_id}"
        if consortium.activity and consortium.activity[-1].event_type == event_type:
            consortium.activity[-1].label = f"{member.company_name} CONTRIBUTED · {kind.upper()}"
            consortium.activity[-1].created_at = self.clock()
            return
        self._activity(consortium, event_type, f"{member.company_name} CONTRIBUTED {amount:,.0f}")

    def _activity(self, consortium: Consortium, event_type: str, label: str) -> None:
        consortium.activity.append(
            ConsortiumActivity(
                f"{consortium.consortium_id}-activity-{consortium.next_activity_sequence}",
                event_type,
                label,
                self.clock(),
            )
        )
        consortium.next_activity_sequence += 1
        consortium.activity[:] = consortium.activity[-ACTIVITY_LIMIT:]
        self.state.communications.add_activity("consortium", label)

    def _identity(self, company_id: str | None, company_name: str | None, company_level: int | None) -> tuple[str, str, int]:
        cid = company_id or self.current_company_id
        name = company_name or (self.network.current_company_name if cid == self.current_company_id else cid)
        level = company_level if company_level is not None else (self.state.company.level if cid == self.current_company_id else 1)
        return cid, name, int(level)

    @staticmethod
    def _validate_settings(join_policy: str, minimum_company_level: int) -> None:
        if join_policy not in JOIN_POLICIES:
            raise ValueError("Unknown Consortium join policy.")
        if type(minimum_company_level) is not int or minimum_company_level < 1:
            raise ValueError("Minimum company level must be a positive integer.")

    @staticmethod
    def _validate_join(consortium: Consortium, company_level: int) -> None:
        if company_level < consortium.minimum_company_level:
            raise PermissionError("Minimum company level not met.")
        if len(consortium.members) >= consortium.member_capacity:
            raise ValueError("Consortium is full.")

    def _consortium(self, consortium_id: str) -> Consortium:
        try:
            return self.network.consortiums[consortium_id]
        except KeyError as error:
            raise KeyError("Unknown Consortium.") from error

    @staticmethod
    def _member(consortium: Consortium, company_id: str) -> ConsortiumMember:
        try:
            return consortium.members[company_id]
        except KeyError as error:
            raise PermissionError("Company is not a Consortium member.") from error

    def _require_management(self, consortium: Consortium, company_id: str) -> ConsortiumMember:
        member = self._member(consortium, company_id)
        if member.role not in (CHAIRMAN, BOARD_MEMBER):
            raise PermissionError("Consortium management permission required.")
        return member

    def _require_chairman(self, consortium: Consortium, company_id: str) -> ConsortiumMember:
        member = self._member(consortium, company_id)
        if member.role != CHAIRMAN:
            raise PermissionError("Chairman permission required.")
        return member

    @staticmethod
    def _contract(consortium: Consortium, kind: str) -> ConsortiumContract:
        try:
            return consortium.contracts[kind]
        except KeyError as error:
            raise KeyError("Unknown Consortium Contract.") from error


def consortium_to_dict(network: ConsortiumNetwork) -> dict[str, object]:
    return {
        "current_company_id": network.current_company_id,
        "current_company_name": network.current_company_name,
        "next_consortium_sequence": network.next_consortium_sequence,
        "reward_receipts": {
            contract_id: {company_id: asdict(reward) for company_id, reward in receipts.items()}
            for contract_id, receipts in network.reward_receipts.items()
        },
        "consortiums": {
            consortium_id: {
                "consortium_id": consortium.consortium_id,
                "name": consortium.name,
                "level": consortium.level,
                "consortium_xp": consortium.consortium_xp,
                "member_capacity": consortium.member_capacity,
                "join_policy": consortium.join_policy,
                "minimum_company_level": consortium.minimum_company_level,
                "created_at": consortium.created_at,
                "members": {key: asdict(value) for key, value in consortium.members.items()},
                "applications": {key: asdict(value) for key, value in consortium.applications.items()},
                "invitations": {key: asdict(value) for key, value in consortium.invitations.items()},
                "contracts": {
                    key: {
                        **asdict(value),
                        "forfeited_member_ids": sorted(value.forfeited_member_ids),
                        "reward_delivered_member_ids": sorted(value.reward_delivered_member_ids),
                        "processed_request_ids": sorted(value.processed_request_ids),
                    }
                    for key, value in consortium.contracts.items()
                },
                "contract_history": [
                    {
                        **asdict(value),
                        "forfeited_member_ids": sorted(value.forfeited_member_ids),
                        "reward_delivered_member_ids": sorted(value.reward_delivered_member_ids),
                        "processed_request_ids": sorted(value.processed_request_ids),
                    }
                    for value in consortium.contract_history
                ],
                "activity": [asdict(value) for value in consortium.activity],
                "next_contract_sequence": consortium.next_contract_sequence,
                "next_activity_sequence": consortium.next_activity_sequence,
            }
            for consortium_id, consortium in network.consortiums.items()
        },
    }


def consortium_from_dict(payload: object) -> ConsortiumNetwork:
    if not isinstance(payload, dict):
        return ConsortiumNetwork()
    network = ConsortiumNetwork(
        current_company_id=str(payload.get("current_company_id", "company.local")),
        current_company_name=str(payload.get("current_company_name", "ZERO INDUSTRIES")),
        next_consortium_sequence=int(payload.get("next_consortium_sequence", 1)),
    )
    for contract_id, receipts in payload.get("reward_receipts", {}).items():
        network.reward_receipts[str(contract_id)] = {
            str(company_id): ConsortiumPersonalReward(**reward)
            for company_id, reward in receipts.items()
        }
    for consortium_id, data in payload.get("consortiums", {}).items():
        consortium = Consortium(
            consortium_id=str(data.get("consortium_id", consortium_id)),
            name=str(data["name"]),
            level=int(data.get("level", 1)),
            consortium_xp=float(data.get("consortium_xp", 0.0)),
            member_capacity=int(data.get("member_capacity", 10)),
            join_policy=str(data.get("join_policy", OPEN)),
            minimum_company_level=int(data.get("minimum_company_level", 1)),
            created_at=float(data.get("created_at", 0.0)),
            members={key: ConsortiumMember(**value) for key, value in data.get("members", {}).items()},
            applications={key: ConsortiumApplication(**value) for key, value in data.get("applications", {}).items()},
            invitations={key: ConsortiumInvitation(**value) for key, value in data.get("invitations", {}).items()},
            activity=[ConsortiumActivity(**value) for value in data.get("activity", [])],
            next_contract_sequence=int(data.get("next_contract_sequence", 1)),
            next_activity_sequence=int(data.get("next_activity_sequence", 1)),
        )
        for kind, value in data.get("contracts", {}).items():
            reward = value.get("personal_reward", {})
            consortium.contracts[kind] = ConsortiumContract(
                contract_id=str(value["contract_id"]),
                kind=str(value["kind"]),
                status=str(value["status"]),
                created_at=float(value["created_at"]),
                expires_at=float(value["expires_at"]),
                requirements={key: float(amount) for key, amount in value.get("requirements", {}).items()},
                personal_reward=ConsortiumPersonalReward(**reward),
                consortium_xp_reward=float(value.get("consortium_xp_reward", 0.0)),
                started_at=None if value.get("started_at") is None else float(value["started_at"]),
                completed_at=None if value.get("completed_at") is None else float(value["completed_at"]),
                eligible_member_ids=tuple(value.get("eligible_member_ids", ())),
                member_count_at_start=int(value.get("member_count_at_start", 0)),
                scaling_inputs={key: float(amount) for key, amount in value.get("scaling_inputs", {}).items()},
                delivered={key: float(amount) for key, amount in value.get("delivered", {}).items()},
                contributions={
                    company_id: {resource_id: float(amount) for resource_id, amount in values.items()}
                    for company_id, values in value.get("contributions", {}).items()
                },
                forfeited_member_ids=set(value.get("forfeited_member_ids", ())),
                reward_delivered_member_ids=set(value.get("reward_delivered_member_ids", ())),
                consortium_xp_delivered=bool(value.get("consortium_xp_delivered", False)),
                processed_request_ids=set(value.get("processed_request_ids", ())),
                balance_version=int(value.get("balance_version",0)),
                capacity_rates=dict(value.get("capacity_rates",{})),
                unit_prices=dict(value.get("unit_prices",{})),
                capacity_signature=str(value.get("capacity_signature","")),
                quoted_level=int(value.get("quoted_level",1)),
                member_unit_prices={cid:dict(prices) for cid,prices in value.get("member_unit_prices",{}).items()},
                rp_minimum_shares=dict(value.get("rp_minimum_shares",{})),
            )
        for value in data.get("contract_history", []):
            reward = value.get("personal_reward", {})
            consortium.contract_history.append(
                ConsortiumContract(
                    contract_id=str(value["contract_id"]),
                    kind=str(value["kind"]),
                    status=str(value["status"]),
                    created_at=float(value["created_at"]),
                    expires_at=float(value["expires_at"]),
                    requirements={key: float(amount) for key, amount in value.get("requirements", {}).items()},
                    personal_reward=ConsortiumPersonalReward(**reward),
                    consortium_xp_reward=float(value.get("consortium_xp_reward", 0.0)),
                    started_at=None if value.get("started_at") is None else float(value["started_at"]),
                    completed_at=None if value.get("completed_at") is None else float(value["completed_at"]),
                    eligible_member_ids=tuple(value.get("eligible_member_ids", ())),
                    member_count_at_start=int(value.get("member_count_at_start", 0)),
                    scaling_inputs={key: float(amount) for key, amount in value.get("scaling_inputs", {}).items()},
                    delivered={key: float(amount) for key, amount in value.get("delivered", {}).items()},
                    contributions={
                        company_id: {resource_id: float(amount) for resource_id, amount in values.items()}
                        for company_id, values in value.get("contributions", {}).items()
                    },
                    forfeited_member_ids=set(value.get("forfeited_member_ids", ())),
                    reward_delivered_member_ids=set(value.get("reward_delivered_member_ids", ())),
                    consortium_xp_delivered=bool(value.get("consortium_xp_delivered", False)),
                    processed_request_ids=set(value.get("processed_request_ids", ())),
                balance_version=int(value.get("balance_version",0)),
                capacity_rates=dict(value.get("capacity_rates",{})),
                unit_prices=dict(value.get("unit_prices",{})),
                capacity_signature=str(value.get("capacity_signature","")),
                quoted_level=int(value.get("quoted_level",1)),
                member_unit_prices={cid:dict(prices) for cid,prices in value.get("member_unit_prices",{}).items()},
                rp_minimum_shares=dict(value.get("rp_minimum_shares",{})),
                )
            )
        network.consortiums[str(consortium_id)] = consortium
    return network
