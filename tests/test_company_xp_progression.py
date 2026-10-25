from __future__ import annotations

from dataclasses import replace
from importlib.resources import files

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.company_xp import (
    EFFICIENCY_THRESHOLDS,
    FIRST_PRODUCTION_XP,
    record_accepted_production_xp,
    sync_company_xp_periods,
)
from production_zero.core.contracts import (
    CONTRACT_COMPANY_XP,
    CONTRACT_KINDS,
    DAILY,
    REGULAR,
    WEEKLY,
    accept_contract,
    generate_contract_offers,
    initialize_contracts,
    receive_contract_delivery,
    refresh_contracts,
)
from production_zero.core.production_values import ProductionValueCalculator
from production_zero.core.progression import (
    PRODUCTION_UNLOCK_BASE_THRESHOLDS,
    initial_production_ids,
    initialize_production_progress,
    progression_families,
    progression_resources,
    record_lifetime_production,
    update_production_unlocks,
)
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.resources import create_resource_inventory
from production_zero.core.state import GameState, MachineProductionState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def fresh_state(level: int = 1) -> GameState:
    resources = create_resource_inventory(
        load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    )
    state = GameState(rng_seed=77, resources=resources)
    state.company.level = level
    initialize_production_progress(state, definitions())
    return state


def produce(state: GameState, outputs: dict[str, float], seconds: float = 0, now: float = 0) -> float:
    defs = definitions()
    record_lifetime_production(state, outputs, defs)
    return record_accepted_production_xp(state, outputs, seconds, defs, now)


def test_production_time_itself_never_awards_xp() -> None:
    state = fresh_state()
    produce(state, {}, seconds=60)
    assert state.company_xp_progress.xp_by_source == {}

    produce(state, {"iron_ore": 12, "copper_ore": 12}, seconds=60)
    assert "continuity" not in state.company_xp_progress.xp_by_source
    assert state.company_xp_progress.xp_by_source["first_production"] == 50


def test_elapsed_days_never_bank_or_award_time_xp() -> None:
    state = fresh_state()
    produce(state, {"iron_ore": 1}, seconds=3_600, now=0)
    assert state.company_xp_progress.xp_by_source == {"first_production": 25}
    before = state.company.current_xp

    sync_company_xp_periods(state, now_utc=4 * 86_400)
    sync_company_xp_periods(state, now_utc=4 * 86_400)
    assert state.company.current_xp == before

    produce(state, {"iron_ore": 1}, seconds=5_400, now=4 * 86_400)
    assert state.company_xp_progress.xp_by_source == {"first_production": 25}


def test_efficiency_thresholds_award_once_and_cap_at_2000() -> None:
    state = fresh_state()
    calculator = ProductionValueCalculator(definitions())
    value = calculator.value_for_resource("iron_ore").value_per_unit
    for threshold in EFFICIENCY_THRESHOLDS:
        current = state.company_xp_progress.efficiency_production_value
        produce(state, {"iron_ore": (threshold - current) / value + 0.001}, now=0)
    assert state.company_xp_progress.xp_by_source["efficiency"] == 2_000
    produce(state, {"iron_ore": 1_000_000}, now=0)
    assert state.company_xp_progress.xp_by_source["efficiency"] == 2_000


def test_first_production_stage_values_and_family_mastery_are_once_only() -> None:
    state = fresh_state(level=25)
    samples = {
        "iron_ore": 25,
        "iron": 40,
        "iron_components": 60,
        "industrial_equipment": 100,
    }
    for resource_id in samples:
        produce(state, {resource_id: 1}, now=0)
        produce(state, {resource_id: 1}, now=0)
    assert state.company_xp_progress.xp_by_source["first_production"] == sum(samples.values())

    family = progression_families()[0]
    outputs = {str(root): 120 for root in family["resources"]}
    produce(state, outputs, now=0)
    produce(state, outputs, now=0)
    assert state.company_xp_progress.xp_by_source["family_mastery"] == 250


def test_mastery_catalog_totals_are_exact() -> None:
    resources = progression_resources()
    first_total = sum(FIRST_PRODUCTION_XP[str(entry["stage"])] for entry in resources.values())
    assert first_total == 24_105
    assert len(progression_families()) * 250 == 4_500
    assert first_total + len(progression_families()) * 250 == 28_605


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_contract_company_xp_scales_with_work_and_category(kind: str) -> None:
    from math import sqrt, log1p
    state = fresh_state(level=25)
    defs = definitions()
    for rid in ("iron_ore", "coal", "copper_ore", "bauxite"):
        state.ensure_resource(rid).amount = 1000
    initialize_contracts(state, defs, now_utc=0)
    assert len(state.contracts.offers[kind]) == 1
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(state, defs, kind)
    accepted = state.contracts.active[kind].offer
    calculator = ProductionValueCalculator(defs)
    work = sum(calculator.value_for_resource(rid).value_per_unit * amount for rid, amount in accepted.requirements.items())
    expected = round(20 * sqrt(max(1., work)) * (1 + log1p(state.company.level) / 4) * {REGULAR: 1., DAILY: 2., WEEKLY: 4.}[kind], 2)
    assert accepted.reward_xp == expected > 0


def test_every_regular_completion_grants_quoted_xp_and_cash_without_packs() -> None:
    state = fresh_state()
    defs = definitions()
    for rid in ("iron_ore", "coal", "copper_ore"):
        state.ensure_resource(rid).amount = 1000
    total_cash = expected_xp = 0.0
    for index in range(6):
        refresh_contracts(state, defs, now_utc=0)
        from tests.contract_acceptance_fixture import accept_fixture
        accept_fixture(state, defs, REGULAR)
        active = state.contracts.active[REGULAR]
        assert active.offer.contract_id.startswith(f"regular-{index}-0-")
        expected_xp += active.offer.reward_xp
        total_cash += active.offer.reward_cash
        for rid, amount in active.offer.requirements.items():
            receive_contract_delivery(state, active.offer.contract_id, rid, amount, defs)
        assert state.cash.amount == pytest.approx(total_cash)
        assert state.packs.unopened == []
    assert state.company_xp_progress.regular_full_xp_completions == 6
    assert state.company_xp_progress.xp_by_source["regular_contracts"] == pytest.approx(expected_xp)
    assert state.contracts.offers[REGULAR][0].reward_xp > 0


def test_utc_rollovers_closed_game_reload_and_backward_clock_are_safe() -> None:
    state = fresh_state()
    defs = definitions()
    initialize_contracts(state, defs, now_utc=0)
    first_daily = state.contracts.daily_period_index
    first_week = state.contracts.weekly_period_index
    payload = serialize_game_state(state)
    loaded = deserialize_game_state(payload)

    refresh_contracts(loaded, defs, now_utc=86_400)
    assert loaded.contracts.daily_period_index == first_daily + 1
    refresh_contracts(loaded, defs, now_utc=8 * 86_400)
    assert loaded.contracts.weekly_period_index > first_week
    high_water = loaded.company_xp_progress.utc_high_water_timestamp
    refresh_contracts(loaded, defs, now_utc=0)
    assert loaded.company_xp_progress.utc_high_water_timestamp == high_water
    assert loaded.contracts.daily_period_index == 8


def test_curve_b_start_counts_thresholds_and_full_graph_reachability() -> None:
    state = fresh_state()
    defs = definitions()
    resources = progression_resources()
    assert len(resources) == 353
    assert len(initial_production_ids()) == 49
    assert len([entry for entry in resources.values() if entry["stage"] == "extractor"]) == 49
    assert len(progression_families()) == 18
    levels = {str(family["id"]): int(family["company_level"]) for family in progression_families()}
    assert set(levels.values()) == {1}
    assert PRODUCTION_UNLOCK_BASE_THRESHOLDS == {
        MachineType.PROCESSOR: 100.0,
        MachineType.FABRICATOR: 100.0,
        MachineType.ASSEMBLER: 100.0,
    }

    state.company.level = 1
    state.production_progress.lifetime_produced.update({resource_id: 10_000 for resource_id in resources})
    update_production_unlocks(state, defs, emit_pending=False)
    assert len(state.production_progress.unlocked_production_ids) == 353


def test_inventory_and_freight_stock_do_not_bypass_unlocks() -> None:
    state = fresh_state()
    defs = definitions()
    state.ensure_resource("iron_ore").amount = 10_000
    update_production_unlocks(state, defs)
    assert "recipe.processor.iron" not in state.production_progress.unlocked_production_ids


def test_progression_and_company_xp_fields_persist_and_migration_is_idempotent() -> None:
    state = fresh_state(level=25)
    produce(state, {"iron_ore": 120}, seconds=60, now=10 * 86_400)
    state.cards["legacy"] = create_card_instance(
        "legacy", "machine.processor", CardKind.MACHINE, Rarity.COMMON
    )
    state.machine_production["legacy"] = MachineProductionState("legacy", "steel", "recipe.processor.steel")
    once = deserialize_game_state(serialize_game_state(state))
    twice = deserialize_game_state(serialize_game_state(once))
    assert serialize_game_state(once)["production_progress"] == serialize_game_state(twice)["production_progress"]
    assert serialize_game_state(once)["company_xp_progress"] == serialize_game_state(twice)["company_xp_progress"]
    assert "recipe.processor.steel" in twice.production_progress.unlocked_production_ids
