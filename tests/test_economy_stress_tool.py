from __future__ import annotations

from production_zero.core.state import GameState
from production_zero.tools.economy_stress_test import _install_stress_contract_freight_fleet, format_summary, run_stress_test, summarize


def test_stress_contract_freight_fleet_expands_harbor_and_rail_slots_validly() -> None:
    state = GameState(rng_seed=76)

    _install_stress_contract_freight_fleet(state)

    harbor_facilities = [
        facility
        for facility in state.freight.facilities.values()
        if facility.facility_type == "harbor"
    ]
    rail_facilities = [
        facility
        for facility in state.freight.facilities.values()
        if facility.facility_type == "rail_station"
    ]
    assert sum(1 for facility in harbor_facilities for slot in facility.slots if slot.card_id is not None) == 3
    assert sum(1 for facility in rail_facilities for slot in facility.slots if slot.card_id is not None) == 3
    assert sum(len(facility.slots) for facility in harbor_facilities) >= 3
    assert sum(len(facility.slots) for facility in rail_facilities) >= 3
    assert all(card_id in state.freight.assignments for card_id in state.installed_freight_card_ids())


def test_economy_stress_tool_is_deterministic_for_same_seed() -> None:
    first = summarize(run_stress_test(players=12, days=14, seeds=(77,)))
    second = summarize(run_stress_test(players=12, days=14, seeds=(77,)))

    assert first == second


def test_economy_stress_tool_is_deterministic_across_process_counts() -> None:
    serial = summarize(run_stress_test(players=120, days=7, seeds=(78,), processes=1))
    parallel = summarize(run_stress_test(players=120, days=7, seeds=(78,), processes=2))

    assert serial == parallel


def test_economy_stress_tool_reports_card_scrap_and_supply_metrics() -> None:
    summary = summarize(run_stress_test(players=16, days=21, seeds=(88, 99)))

    assert summary["players_per_seed"] == 16
    assert summary["days"] == 21
    assert sum(summary["profiles"].values()) == 32
    assert sum(profile["players"] for profile in summary["by_profile"].values()) == 32
    assert set(summary["created_cards_by_rarity"]) == {"common", "uncommon", "rare", "epic", "legendary"}
    assert sum(summary["created_cards_by_rarity"].values()) > 0
    assert "scrap_generated" in summary
    assert "scrap_consumed" in summary
    assert "scrap_surplus" in summary
    assert "crafting_consumed_by_rarity" in summary
    assert "remaining_cards_by_rarity" in summary
    assert "legendarys_per_player" in summary
    assert "cards_per_player" in summary
    assert "per_player_year" in summary
    assert summary["net_supply_growth"] == sum(summary["remaining_cards_by_rarity"].values())

    rendered = format_summary(summary)
    assert "Industriova Economy Stress Test" in rendered
    assert "Net supply growth" in rendered


def test_economy_stress_tool_models_freight_card_economy() -> None:
    summary = summarize(run_stress_test(players=24, days=28, seeds=(89,)))
    freight = summary["freight"]

    assert freight["created_total"] > 0
    assert freight["remaining_total"] >= 0
    assert set(freight["created_by_rarity"]) == {"common", "uncommon", "rare", "epic", "legendary"}
    assert freight["daily_freight_rotation_total"] > 0
    assert freight["daily_freight_rotation_by_rarity"]["uncommon"] == freight["daily_freight_rotation_total"]
    assert set(freight["created_by_family"]) <= {"truck", "train", "ship", "aircraft"}
    assert freight["created_by_family"]
    assert "cards_per_player" in freight
    assert "legendary_players_at_least_1" in freight
    assert "rare_per_player_year" in freight


def test_economy_stress_tool_reports_freight_by_profile_and_seed() -> None:
    summary = summarize(run_stress_test(players=24, days=28, seeds=(90, 91)))

    assert all("freight" in profile for profile in summary["by_profile"].values())
    assert all("freight" in seed_summary for seed_summary in summary["per_seed"])
    assert sum(profile["freight"]["daily_freight_rotation_total"] for profile in summary["by_profile"].values()) == summary["freight"]["daily_freight_rotation_total"]
