from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from production_zero.core.company import award_company_xp
from production_zero.core.enums import MachineType
from production_zero.core.production_values import ProductionValueCalculator
from production_zero.core.progression import (
    newly_mastered_families,
    progression_resources,
    update_production_unlocks,
)

if TYPE_CHECKING:
    from production_zero.core.definitions import CardDefinition
    from production_zero.core.state import GameState


COMPANY_XP_SCHEMA_VERSION = 2
MARKET_SALE_XP_PER_DOLLAR = 0.1
EFFICIENCY_THRESHOLDS = (25.0, 100.0, 300.0, 750.0)
EFFICIENCY_XP_PER_THRESHOLD = 500.0
FIRST_PRODUCTION_XP = {
    MachineType.EXTRACTOR.value: 25.0,
    MachineType.PROCESSOR.value: 40.0,
    MachineType.FABRICATOR.value: 60.0,
    MachineType.ASSEMBLER.value: 100.0,
}
FAMILY_MASTERY_XP = 250.0


@dataclass(slots=True)
class CompanyXpProgress:
    schema_version: int = COMPANY_XP_SCHEMA_VERSION
    utc_day_index: int = -1
    utc_week_index: int = -1
    utc_high_water_timestamp: float = 0.0
    efficiency_production_value: float = 0.0
    efficiency_milestones: set[int] = field(default_factory=set)
    regular_full_xp_completions: int = 0
    xp_by_source: dict[str, float] = field(default_factory=dict)
    # Production telemetry follows the union of one-second completion buckets.
    # Time itself grants no XP. Persist the watermark across ticks/save/load.
    last_productive_bucket: int = -1
    productive_event_seconds: float = 0.0


def utc_timestamp(now_utc: datetime | float | None = None) -> float:
    if now_utc is None:
        return datetime.now(timezone.utc).timestamp()
    if isinstance(now_utc, (int, float)):
        return float(now_utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc).timestamp()


def utc_period_ids(now_utc: datetime | float | None = None) -> tuple[int, int, float]:
    timestamp = utc_timestamp(now_utc)
    day_index = int(timestamp // 86_400)
    # Fixed Monday-to-Sunday UTC weeks; 1970-01-05 was the first Monday after epoch.
    week_index = (day_index - 4) // 7
    return day_index, week_index, timestamp


def sync_company_xp_periods(
    state: "GameState", now_utc: datetime | float | None = None
) -> tuple[int, int]:
    progress = state.company_xp_progress
    requested = utc_timestamp(now_utc)
    effective = max(requested, progress.utc_high_water_timestamp)
    day_index, week_index, _ = utc_period_ids(effective)
    if progress.utc_day_index < 0:
        progress.utc_day_index = day_index
        progress.utc_week_index = week_index
    elif day_index > progress.utc_day_index:
        progress.utc_day_index = day_index
        progress.efficiency_production_value = 0.0
        progress.efficiency_milestones.clear()
        progress.regular_full_xp_completions = 0
    if week_index > progress.utc_week_index:
        progress.utc_week_index = week_index
    progress.utc_high_water_timestamp = max(progress.utc_high_water_timestamp, effective)
    return progress.utc_day_index, progress.utc_week_index


def record_accepted_production_xp(
    state: "GameState",
    produced: dict[str, float],
    elapsed_seconds: float,
    definitions: dict[str, "CardDefinition"],
    now_utc: datetime | float | None = None,
) -> float:
    sync_company_xp_periods(state, now_utc)
    accepted = {resource_id: amount for resource_id, amount in produced.items() if amount > 0}
    if not accepted:
        return 0.0

    total_awarded = 0.0
    progress = state.company_xp_progress
    calculator = ProductionValueCalculator(definitions)
    produced_value = sum(
        amount * value.value_per_unit
        for resource_id, amount in accepted.items()
        if (value := calculator.value_for_resource(resource_id)) is not None
    )
    progress.efficiency_production_value += produced_value
    for milestone_index, threshold in enumerate(EFFICIENCY_THRESHOLDS):
        if (
            milestone_index not in progress.efficiency_milestones
            and progress.efficiency_production_value >= threshold
        ):
            progress.efficiency_milestones.add(milestone_index)
            total_awarded += _award(state, EFFICIENCY_XP_PER_THRESHOLD, "efficiency", definitions)

    resources = progression_resources()
    for resource_id in accepted:
        if resource_id in progress_first_produced(state) or resource_id not in resources:
            continue
        state.production_progress.first_produced_resource_ids.add(resource_id)
        stage = str(resources[resource_id]["stage"])
        total_awarded += _award(state, FIRST_PRODUCTION_XP[stage], "first_production", definitions)

    for family_id in newly_mastered_families(state):
        state.production_progress.mastered_family_ids.add(family_id)
        total_awarded += _award(state, FAMILY_MASTERY_XP, "family_mastery", definitions)
    return total_awarded


def award_market_sale_xp(
    state: "GameState",
    earnings: float,
    definitions: dict[str, "CardDefinition"],
) -> float:
    """Called only when Freight actually settles a resource sale.

    Preserve fractional XP: no per-delivery minimum, rounding bonus or daily cap.
    Contract cash, ownership sales and refunds never use this award path.
    """
    from math import isfinite
    if not isfinite(earnings) or earnings < 0:
        raise ValueError("Market sale earnings must be finite and nonnegative.")
    return _award(state, earnings * MARKET_SALE_XP_PER_DOLLAR, "market_sales", definitions)


def award_contract_company_xp(
    state: "GameState",
    amount: float,
    definitions: dict[str, "CardDefinition"] | None,
    *,
    source: str,
) -> float:
    return _award(state, amount, source, definitions)


def progress_first_produced(state: "GameState") -> set[str]:
    return state.production_progress.first_produced_resource_ids


def _award(
    state: "GameState",
    amount: float,
    source: str,
    definitions: dict[str, "CardDefinition"] | None,
) -> float:
    if amount <= 0:
        return 0.0
    gained_levels = award_company_xp(state.company, amount)
    if gained_levels:
        from production_zero.core.research import grant_research_points
        grant_research_points(state, len(gained_levels), "Company level up")
    state.company_xp_progress.xp_by_source[source] = (
        state.company_xp_progress.xp_by_source.get(source, 0.0) + amount
    )
    if definitions is not None and gained_levels:
        update_production_unlocks(state, definitions)
    state.history.append("company.level", state.company.level)
    state.history.append("company.xp", state.company.current_xp)
    return amount
