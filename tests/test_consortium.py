from __future__ import annotations
from consortium_freight_fixture import freight_contribute, freight_receive

from pathlib import Path

import pytest
from tests.contract_capacity_fixture import remote_stock

from production_zero.core.consortium import (
    ACTIVE,
    APPLICATION,
    BOARD_MEMBER,
    CHAIRMAN,
    COMPLETED,
    CONSORTIUM_DAILY,
    CONSORTIUM_WEEKLY,
    INVITE_ONLY,
    MEMBER,
    OPEN,
    ConsortiumMember,
    ConsortiumService,
    member_capacity_for_level,
)
from production_zero.core.state import GameState
from production_zero.core.progression import production_options
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore, deserialize_game_state, serialize_game_state


DEFINITIONS = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def service(*, company_level: int = 20, now: float = 1_000.0) -> tuple[GameState, ConsortiumService]:
    state = GameState(rng_seed=77)
    state.company.level = company_level
    for option in production_options(DEFINITIONS):
        state.production_progress.unlocked_production_ids.add(option.production_id)
        state.ensure_resource(option.output_resource).amount = 1
    from tests.contract_capacity_fixture import provide_capacity
    provide_capacity(state, DEFINITIONS)
    return state, ConsortiumService(state, DEFINITIONS, clock=lambda: now)


def start(api: ConsortiumService, consortium, kind: str, actor: str | None = None):
    count = 3 if kind == CONSORTIUM_DAILY else 4
    products = api.contract_candidates(consortium.consortium_id, kind)[:count]
    return api.start_contract(consortium.consortium_id, actor or api.current_company_id, kind, products)


def created(*, policy: str = OPEN, minimum: int = 1) -> tuple[GameState, ConsortiumService, object]:
    state, api = service()
    consortium = api.create("Northstar Industries", policy, minimum)
    return state, api, consortium


def add_member(consortium, company_id: str, role: str = MEMBER, level: int = 20) -> None:
    consortium.members[company_id] = ConsortiumMember(company_id, company_id.upper(), level, role, 1_000.0)


def test_creation_makes_creator_chairman_and_materializes_offers() -> None:
    state, _, consortium = created()
    assert consortium.members[state.consortium.current_company_id].role == CHAIRMAN
    assert consortium.member_capacity == 10
    assert set(consortium.contracts) == {CONSORTIUM_DAILY, CONSORTIUM_WEEKLY}
    assert all(not offer.requirements for offer in consortium.contracts.values())


def test_management_selects_unique_available_products_before_snapshot() -> None:
    state, api, consortium = created()
    daily = api.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)
    weekly = api.contract_candidates(consortium.consortium_id, CONSORTIUM_WEEKLY)
    assert len(daily) >= 3 and len(weekly) >= 4
    with pytest.raises(ValueError, match="Select Contract products"):
        api.start_contract(consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY)
    with pytest.raises(ValueError, match="unique"):
        api.start_contract(consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, (daily[0],) * 3)
    with pytest.raises(ValueError, match="unavailable"):
        api.start_contract(consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, (daily[0], daily[1], "not_a_product"))
    selected = daily[:3]
    preview = api.preview_contract(consortium.consortium_id, CONSORTIUM_DAILY, selected)
    rewards = api.preview_contract_rewards(consortium.consortium_id, CONSORTIUM_DAILY)
    started = api.start_contract(consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, selected)
    assert started.requirements == preview and tuple(started.requirements) == selected
    assert (started.personal_reward, started.consortium_xp_reward) == rewards
    assert started.eligible_member_ids == (api.current_company_id,)
    assert len(weekly[:4]) == 4


def test_remote_member_capabilities_enter_candidate_pool_without_locked_ids() -> None:
    state, api, consortium = created()
    values = api.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)
    special = values[-1]
    for option in production_options(DEFINITIONS):
        if option.output_resource == special:
            state.production_progress.unlocked_production_ids.discard(option.production_id)
    state.ensure_resource(special).amount = 0
    assert special not in api.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)
    add_member(consortium, "remote")
    remote, _ = service()
    remote.consortium.current_company_id = "remote"
    api.update_capacity_snapshot("remote", remote)
    consortium.members["remote"].capable_resource_ids = (special, "invalid_resource")
    candidates = api.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)
    assert special in candidates and "invalid_resource" not in candidates


def test_join_policies_minimum_level_and_capacity() -> None:
    _, api, consortium = created(policy=OPEN, minimum=10)
    with pytest.raises(PermissionError, match="Minimum"):
        api.join(consortium.consortium_id, "low", "Low Co", 9)
    api.join(consortium.consortium_id, "open", "Open Co", 10)
    consortium.join_policy = APPLICATION
    api.apply(consortium.consortium_id, "applicant", "Applicant", 10)
    api.process_application(consortium.consortium_id, api.current_company_id, "applicant", True)
    consortium.join_policy = INVITE_ONLY
    with pytest.raises(PermissionError, match="invitation"):
        api.join(consortium.consortium_id, "invitee", "Invitee", 10)
    api.invite(consortium.consortium_id, api.current_company_id, "invitee", "Invitee", 10)
    api.join(consortium.consortium_id, "invitee", "Invitee", 10)
    while len(consortium.members) < consortium.member_capacity:
        index = len(consortium.members)
        add_member(consortium, f"member-{index}")
    with pytest.raises(ValueError, match="full"):
        api.join(consortium.consortium_id, "overflow", "Overflow", 20)


def test_invite_identity_is_resolved_from_known_network_not_entered_level() -> None:
    _, api, consortium = created(policy=APPLICATION, minimum=10)
    api.apply(consortium.consortium_id, "external.steel", "Steel Works", 12)
    by_name = api.resolve_company("steel works")
    by_id = api.resolve_company("EXTERNAL.STEEL")
    assert by_name == by_id and by_id.company_level == 12
    assert api.invitation_eligibility(consortium.consortium_id, by_id) == (True, "ELIGIBLE FOR INVITATION")
    assert api.resolve_company("invented company") is None
    with pytest.raises(ValueError, match="not found"):
        api.invite_resolved(consortium.consortium_id, api.current_company_id, "invented company")
    api.invite_resolved(consortium.consortium_id, api.current_company_id, "steel works")
    assert consortium.invitations["external.steel"].company_level == 12


def test_role_permissions_board_can_manage_but_cannot_remove_or_disband() -> None:
    _, api, consortium = created(policy=APPLICATION)
    add_member(consortium, "board", BOARD_MEMBER)
    add_member(consortium, "member")
    api.invite(consortium.consortium_id, "board", "candidate", "Candidate", 20)
    start(api, consortium, CONSORTIUM_DAILY, "board")
    with pytest.raises(PermissionError, match="Chairman"):
        api.remove(consortium.consortium_id, "board", "member")
    with pytest.raises(PermissionError, match="Chairman"):
        api.disband(consortium.consortium_id, "board")
    with pytest.raises(PermissionError, match="management"):
        api.invite(consortium.consortium_id, "member", "other", "Other", 20)


def test_contract_snapshot_contribution_and_exactly_once_rewards() -> None:
    state, api, consortium = created()
    add_member(consortium, "partner")
    contract = start(api, consortium, CONSORTIUM_DAILY)
    requirements = dict(contract.requirements)
    reward = contract.personal_reward
    eligible = contract.eligible_member_ids
    assert contract.status == ACTIVE and contract.member_count_at_start == 2
    api.join(consortium.consortium_id, "late", "Late Joiner", 20)
    assert contract.requirements == requirements and contract.personal_reward == reward and contract.eligible_member_ids == eligible
    for resource_id, amount in contract.requirements.items():
        state.ensure_resource(resource_id).amount = amount
        state.ensure_resource(resource_id).capacity = amount
        freight_contribute(api,
            consortium.consortium_id,
            api.current_company_id,
            CONSORTIUM_DAILY,
            resource_id,
            amount,
            request_id=f"request-{resource_id}",
        )
    assert contract.status == COMPLETED
    assert api.current_company_id in contract.reward_delivered_member_ids
    assert "partner" not in contract.reward_delivered_member_ids
    assert "late" not in contract.reward_delivered_member_ids
    cash = state.cash.amount
    xp = consortium.consortium_xp
    assert api.complete_contract(consortium.consortium_id, CONSORTIUM_DAILY) == (api.current_company_id,)
    assert state.cash.amount == cash and consortium.consortium_xp == xp


def test_contribution_storage_validation_and_retry_idempotency() -> None:
    state, api, consortium = created()
    contract = start(api, consortium, CONSORTIUM_DAILY)
    resource_id = next(iter(contract.requirements))
    state.ensure_resource(resource_id).amount = 5
    with pytest.raises(ValueError, match="positive"):
        freight_contribute(api,consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, resource_id, 0)
    with pytest.raises(ValueError, match="Insufficient"):
        freight_contribute(api,consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, resource_id, 6)
    freight_contribute(api,consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, resource_id, 2, request_id="same")
    assert freight_contribute(api,consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, resource_id, 2, request_id="same") == 0
    assert state.resources[resource_id].amount == 3


@pytest.mark.parametrize("action", ["leave", "kick"])
def test_leave_kick_and_rejoin_never_restore_active_eligibility(action: str) -> None:
    _, api, consortium = created()
    add_member(consortium, "worker")
    contract = start(api, consortium, CONSORTIUM_DAILY)
    resource_id = next(iter(contract.requirements))
    freight_contribute(api,consortium.consortium_id, "worker", CONSORTIUM_DAILY, resource_id, 1, company_state=remote_stock("worker",resource_id,1))
    if action == "leave":
        api.leave(consortium.consortium_id, "worker")
    else:
        api.remove(consortium.consortium_id, api.current_company_id, "worker")
    api.join(consortium.consortium_id, "worker", "WORKER", 20)
    eligibility = api.reward_eligibility(consortium.consortium_id, CONSORTIUM_DAILY, "worker")
    assert eligibility == {
        "eligible_at_start": False,
        "contributed": True,
        "current_member": True,
        "reward_eligible": False,
    }


def test_full_reward_for_each_eligible_contributor_and_zero_contribution_rejected() -> None:
    _, api, consortium = created()
    add_member(consortium, "worker")
    add_member(consortium, "idle")
    contract = start(api, consortium, CONSORTIUM_DAILY)
    first = next(iter(contract.requirements))
    freight_contribute(api,consortium.consortium_id, "worker", CONSORTIUM_DAILY, first, 1, company_state=remote_stock("worker",first,1))
    for resource_id, required in contract.requirements.items():
        remaining = contract.remaining(resource_id)
        if remaining:
            api.state.ensure_resource(resource_id).amount = remaining
            api.state.ensure_resource(resource_id).capacity = remaining
            freight_contribute(api,consortium.consortium_id, api.current_company_id, CONSORTIUM_DAILY, resource_id, remaining)
    assert contract.reward_delivered_member_ids == {api.current_company_id, "worker"}
    receipts = api.network.reward_receipts[contract.contract_id]
    assert receipts[api.current_company_id] == api.personal_reward_quote(contract,api.current_company_id)
    assert receipts["worker"] == api.personal_reward_quote(contract,"worker")
    assert receipts["worker"].cash < receipts[api.current_company_id].cash
    assert sum(r.cash for r in receipts.values()) <= contract.personal_reward.cash
    assert "idle" not in receipts


def test_progression_capacity_milestones_through_maximum() -> None:
    _, api, consortium = created()
    for level, expected in ((1, 10), (5, 15), (10, 20), (15, 25), (20, 30), (30, 40), (40, 50), (99, 50)):
        assert member_capacity_for_level(level) == expected
    api._award_consortium_xp(consortium, 1_000_000)
    assert consortium.level >= 40 and consortium.member_capacity == 50


def test_persistence_roundtrip_and_old_save_defaults_to_no_consortium(tmp_path) -> None:
    state, api, consortium = created()
    add_member(consortium, "partner", BOARD_MEMBER)
    start(api, consortium, CONSORTIUM_WEEKLY)
    store = SQLiteSaveStore(tmp_path / "consortium.sqlite")
    store.initialize()
    store.save("company", state)
    loaded = store.load("company")
    membership = loaded.consortium.membership()
    assert membership is not None
    assert membership[0].members["partner"].role == BOARD_MEMBER
    assert membership[0].contracts[CONSORTIUM_WEEKLY].eligible_member_ids == (api.current_company_id, "partner")

    payload = serialize_game_state(GameState(rng_seed=2))
    payload.pop("consortium")
    legacy = deserialize_game_state(payload)
    assert legacy.consortium.membership() is None and legacy.consortium.consortiums == {}
