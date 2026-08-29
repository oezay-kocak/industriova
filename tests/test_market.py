from __future__ import annotations

from functools import lru_cache

from production_zero.core.market import (
    BASE_MARKET_PRICES,
    MARKET_EVENT_SECONDS,
    MARKET_TICK_SECONDS,
    active_market_event,
    advance_market_time,
    create_market_state,
    market_price_for,
)

MARKET_SAMPLE_RESOURCES = (
    "iron_ore",
    "coal",
    "steel",
    "wheat",
    "timber",
    "lithium",
    "semiconductor_components",
    "ai_server",
    "biofuel",
    "satellite",
)


def _deviation_from_fundamental(resource_id: str, price: float) -> float:
    return price / BASE_MARKET_PRICES[resource_id] - 1.0


@lru_cache(maxsize=None)
def _long_market_stats(seed: int) -> tuple[float, float, float, float, float, float]:
    ticks_90_days = (90 * 24 * 60 * 60) // MARKET_TICK_SECONDS
    ticks_1_year = (365 * 24 * 60 * 60) // MARKET_TICK_SECONDS
    market = create_market_state(MARKET_SAMPLE_RESOURCES)
    highest_deviation = 0.0
    lowest_deviation = 0.0
    maximum_anchor_deviation = 0.0
    day_90_average = 0.0

    for tick in range(1, ticks_1_year + 1):
        advance_market_time(market, MARKET_TICK_SECONDS, seed=seed, resource_ids=MARKET_SAMPLE_RESOURCES)
        for resource_id, resource in market.resources.items():
            price_deviation = _deviation_from_fundamental(resource_id, resource.current_price)
            highest_deviation = max(highest_deviation, price_deviation)
            lowest_deviation = min(lowest_deviation, price_deviation)
            maximum_anchor_deviation = max(
                maximum_anchor_deviation,
                abs(_deviation_from_fundamental(resource_id, resource.anchor_price)),
            )
        if tick == ticks_90_days:
            day_90_deviations = [
                _deviation_from_fundamental(resource_id, resource.current_price)
                for resource_id, resource in market.resources.items()
            ]
            day_90_average = sum(day_90_deviations) / len(day_90_deviations)

    year_deviations = [
        _deviation_from_fundamental(resource_id, resource.current_price)
        for resource_id, resource in market.resources.items()
    ]
    year_average = sum(year_deviations) / len(year_deviations)
    maximum_final_deviation = max(abs(value) for value in year_deviations)
    return (
        day_90_average,
        year_average,
        maximum_final_deviation,
        maximum_anchor_deviation,
        highest_deviation,
        lowest_deviation,
    )


def test_market_price_changes_only_on_five_minute_ticks() -> None:
    market = create_market_state()
    starting_price = market_price_for(market, "iron_ore")

    advance_market_time(market, MARKET_TICK_SECONDS - 1, seed=123)

    assert market.market_tick == 0
    assert market_price_for(market, "iron_ore") == starting_price

    advance_market_time(market, 1, seed=123)

    assert market.market_tick == 1
    assert market_price_for(market, "iron_ore") != starting_price


def test_market_state_initializes_all_defined_industrial_resources() -> None:
    market = create_market_state()

    assert set(market.resources) == set(BASE_MARKET_PRICES)
    assert len(market.resources) > 300
    assert market_price_for(market, "ai_server") == BASE_MARKET_PRICES["ai_server"]


def test_market_movement_is_deterministic_for_seed_and_elapsed_time() -> None:
    first = create_market_state()
    second = create_market_state()

    advance_market_time(first, MARKET_TICK_SECONDS * 4, seed=777)
    advance_market_time(second, MARKET_TICK_SECONDS * 4, seed=777)

    assert {
        resource_id: round(resource.current_price, 6)
        for resource_id, resource in first.resources.items()
    } == {
        resource_id: round(resource.current_price, 6)
        for resource_id, resource in second.resources.items()
    }


def test_market_events_rotate_every_three_days() -> None:
    market = create_market_state(MARKET_SAMPLE_RESOURCES)

    assert active_market_event(market).event_id == "industrial_boom"

    advance_market_time(market, MARKET_EVENT_SECONDS, seed=123, resource_ids=MARKET_SAMPLE_RESOURCES)

    assert active_market_event(market).event_id == "energy_crisis"
    assert market.event_started_at == MARKET_EVENT_SECONDS


def test_long_market_simulation_stays_mostly_near_fundamental_without_price_caps() -> None:
    market = create_market_state(MARKET_SAMPLE_RESOURCES)
    deviations: list[float] = []
    total_ticks = (30 * 24 * 60 * 60) // MARKET_TICK_SECONDS

    for _ in range(total_ticks):
        advance_market_time(market, MARKET_TICK_SECONDS, seed=2024, resource_ids=MARKET_SAMPLE_RESOURCES)
        deviations.extend(
            abs(_deviation_from_fundamental(resource_id, resource.current_price))
            for resource_id, resource in market.resources.items()
        )

    ordered_deviations = sorted(deviations)
    p95 = ordered_deviations[int(len(ordered_deviations) * 0.95)]
    p99 = ordered_deviations[int(len(ordered_deviations) * 0.99)]

    assert p95 < 0.25
    assert p99 < 0.35
    assert max(deviations) < 0.45


def test_market_has_no_systematic_long_term_positive_drift_across_seeds() -> None:
    seeds = (1, 2, 2024)
    final_90_day_averages: list[float] = []
    final_1_year_averages: list[float] = []
    maximum_final_deviation = 0.0
    maximum_anchor_deviation = 0.0

    for seed in seeds:
        day_90_average, year_average, final_deviation, anchor_deviation, _, _ = _long_market_stats(seed)
        final_90_day_averages.append(day_90_average)
        final_1_year_averages.append(year_average)
        maximum_final_deviation = max(maximum_final_deviation, final_deviation)
        maximum_anchor_deviation = max(maximum_anchor_deviation, anchor_deviation)

    assert max(final_90_day_averages) < 0.08
    assert max(final_1_year_averages) < 0.08
    assert maximum_final_deviation < 0.25
    assert maximum_anchor_deviation < 0.03


def test_market_forms_bull_and_bear_phases_around_fundamental_prices() -> None:
    seeds = (1, 2, 2024)
    highest_deviation = 0.0
    lowest_deviation = 0.0

    for seed in seeds:
        _, _, _, _, seed_highest_deviation, seed_lowest_deviation = _long_market_stats(seed)
        highest_deviation = max(highest_deviation, seed_highest_deviation)
        lowest_deviation = min(lowest_deviation, seed_lowest_deviation)

    assert highest_deviation > 0.20
    assert lowest_deviation < -0.20


def test_extreme_price_deviations_create_long_term_return_moves() -> None:
    scenarios = (
        ("overpriced", 1.80, 0.90),
        ("underpriced", 0.55, -0.90),
    )
    total_ticks = (30 * 24 * 60 * 60) // MARKET_TICK_SECONDS

    for _, price_multiplier, momentum in scenarios:
        market = create_market_state(("steel",))
        resource = market.ensure_resource("steel")
        fundamental_price = BASE_MARKET_PRICES["steel"]
        resource.current_price = fundamental_price * price_multiplier
        resource.anchor_price = fundamental_price
        resource.momentum = momentum
        resource.trend_age = 80
        starting_deviation = abs(_deviation_from_fundamental("steel", resource.current_price))

        for _ in range(total_ticks):
            advance_market_time(market, MARKET_TICK_SECONDS, seed=42, resource_ids=("steel",))

        ending_deviation = abs(_deviation_from_fundamental("steel", resource.current_price))
        anchor_deviation = abs(_deviation_from_fundamental("steel", resource.anchor_price))

        assert ending_deviation < starting_deviation * 0.35
        assert anchor_deviation < 0.03
