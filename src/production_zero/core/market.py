from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


MARKET_TICK_SECONDS = 5 * 60
MARKET_EVENT_SECONDS = 3 * 24 * 60 * 60

_RESOURCE_DEFINITIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "resource_definitions.json"


def _load_resource_market_field(field_name: str, fallback: float) -> dict[str, float]:
    raw = json.loads(_RESOURCE_DEFINITIONS_PATH.read_text(encoding="utf-8"))
    return {
        item["id"]: float(item.get(field_name, fallback))
        for item in raw["resources"]
    }


from production_zero.core.fixed_prices import build_fixed_prices

LEGACY_BASE_MARKET_PRICES: dict[str, float] = _load_resource_market_field("base_market_price", 1.0)
BASE_MARKET_PRICES: dict[str, float] = build_fixed_prices(LEGACY_BASE_MARKET_PRICES)
BASE_VOLATILITY: dict[str, float] = _load_resource_market_field("volatility", 0.008)
RESOURCE_RANDOM_OFFSETS: dict[str, int] = {
    resource_id: int.from_bytes(hashlib.sha256(resource_id.encode("utf-8")).digest()[:4], "big") % 1_000_000
    for resource_id in BASE_MARKET_PRICES
}


@dataclass(slots=True)
class ResourceMarketState:
    resource_id: str
    current_price: float
    anchor_price: float
    volatility: float
    momentum: float = 0.0
    trend_age: int = 0
    last_change: float = 0.0


@dataclass(frozen=True, slots=True)
class MarketEventDefinition:
    event_id: str
    name: str
    affected_resources: tuple[str, ...]
    bias_by_resource: Mapping[str, float]
    volatility_multiplier: float = 1.0
    momentum_multiplier: float = 1.0
    anchor_shift_by_resource: Mapping[str, float] = field(default_factory=dict)

    def bias_for(self, resource_id: str) -> float:
        return self.bias_by_resource.get(resource_id, 0.0)

    def anchor_shift_for(self, resource_id: str) -> float:
        return self.anchor_shift_by_resource.get(resource_id, 0.0)


@dataclass(slots=True)
class MarketState:
    elapsed_seconds: float = 0.0
    next_market_tick_seconds: float = MARKET_TICK_SECONDS
    market_tick: int = 0
    active_event_id: str = "industrial_boom"
    event_started_at: float = 0.0
    resources: dict[str, ResourceMarketState] = field(default_factory=dict)

    def ensure_resource(self, resource_id: str) -> ResourceMarketState:
        if resource_id not in self.resources:
            anchor = BASE_MARKET_PRICES[resource_id]
            self.resources[resource_id] = ResourceMarketState(
                resource_id=resource_id,
                current_price=anchor,
                anchor_price=anchor,
                volatility=BASE_VOLATILITY[resource_id],
            )
        return self.resources[resource_id]


def _bias(resources: tuple[str, ...], value: float) -> dict[str, float]:
    return {resource_id: value for resource_id in resources if resource_id in BASE_MARKET_PRICES}


def _shift(resources: tuple[str, ...], value: float) -> dict[str, float]:
    return {resource_id: value for resource_id in resources if resource_id in BASE_MARKET_PRICES}


MARKET_EVENTS: tuple[MarketEventDefinition, ...] = (
    MarketEventDefinition(
        event_id="industrial_boom",
        name="Industrial Boom",
        affected_resources=(
            "iron_ore", "coal", "copper_ore", "bauxite", "iron", "steel", "copper", "aluminum",
            "industrial_equipment", "heavy_machinery", "industrial_robot",
        ),
        bias_by_resource={
            "iron_ore": -0.010,
            "coal": 0.005,
            "copper_ore": 0.010,
            "bauxite": 0.010,
            "iron": 0.020,
            "steel": 0.025,
            "copper": 0.018,
            "aluminum": 0.018,
            "industrial_equipment": 0.020,
            "heavy_machinery": 0.020,
            "industrial_robot": 0.018,
        },
        volatility_multiplier=1.05,
        momentum_multiplier=1.05,
        anchor_shift_by_resource={
            "iron_ore": -0.010,
            "coal": 0.005,
            "copper_ore": 0.008,
            "bauxite": 0.008,
            "iron": 0.018,
            "steel": 0.022,
            "copper": 0.015,
            "aluminum": 0.015,
            "industrial_equipment": 0.015,
            "heavy_machinery": 0.015,
            "industrial_robot": 0.014,
        },
    ),
    MarketEventDefinition(
        event_id="energy_crisis",
        name="Energy Crisis",
        affected_resources=("coal", "natural_gas", "crude_oil", "hydrogen", "industrial_gas", "iron", "copper", "steel", "aluminum"),
        bias_by_resource={
            "coal": 0.035,
            "natural_gas": 0.030,
            "crude_oil": 0.026,
            "hydrogen": 0.020,
            "industrial_gas": 0.020,
            "iron": -0.020,
            "copper": -0.015,
            "steel": -0.030,
            "aluminum": -0.018,
        },
        volatility_multiplier=1.10,
        momentum_multiplier=1.04,
        anchor_shift_by_resource={
            "coal": 0.030,
            "natural_gas": 0.026,
            "crude_oil": 0.022,
            "hydrogen": 0.018,
            "industrial_gas": 0.018,
            "iron": -0.018,
            "copper": -0.012,
            "steel": -0.025,
            "aluminum": -0.015,
        },
    ),
    MarketEventDefinition(
        event_id="construction_wave",
        name="Construction Boom",
        affected_resources=("iron_ore", "copper_ore", "timber", "limestone", "gypsum", "iron", "copper", "steel", "cement", "lumber", "concrete_components", "construction_materials", "reinforced_concrete", "industrial_hall_modules"),
        bias_by_resource=_bias(("iron_ore", "copper_ore", "timber", "limestone", "gypsum", "iron", "copper", "steel", "cement", "lumber", "concrete_components", "construction_materials", "reinforced_concrete", "industrial_hall_modules"), 0.018),
        volatility_multiplier=1.06,
        momentum_multiplier=1.04,
        anchor_shift_by_resource=_shift(("iron_ore", "copper_ore", "timber", "limestone", "gypsum", "iron", "copper", "steel", "cement", "lumber", "concrete_components", "construction_materials", "reinforced_concrete", "industrial_hall_modules"), 0.014),
    ),
    MarketEventDefinition(
        event_id="electronics_expansion",
        name="Semiconductor Surge",
        affected_resources=("quartz", "silica_sand", "copper_ore", "gold_ore", "rare_earth_ore", "silicon", "high_purity_silicon", "copper", "gold", "rare_earth_metals", "semiconductor_components", "semiconductor_die", "processor_components", "microchip", "cpu", "ai_accelerator"),
        bias_by_resource=_bias(("quartz", "silica_sand", "copper_ore", "gold_ore", "rare_earth_ore", "silicon", "high_purity_silicon", "copper", "gold", "rare_earth_metals", "semiconductor_components", "semiconductor_die", "processor_components", "microchip", "cpu", "ai_accelerator"), 0.020),
        volatility_multiplier=1.10,
        momentum_multiplier=1.05,
        anchor_shift_by_resource=_shift(("quartz", "silica_sand", "copper_ore", "gold_ore", "rare_earth_ore", "silicon", "high_purity_silicon", "copper", "gold", "rare_earth_metals", "semiconductor_components", "semiconductor_die", "processor_components", "microchip", "cpu", "ai_accelerator"), 0.016),
    ),
    MarketEventDefinition(
        event_id="food_shortage",
        name="Food Shortage",
        affected_resources=("wheat", "corn", "soybeans", "sugarcane", "potatoes", "fruit", "flour", "corn_meal", "soy_protein", "refined_sugar", "food_ingredients", "packaged_food", "packaged_nutrition"),
        bias_by_resource=_bias(("wheat", "corn", "soybeans", "sugarcane", "potatoes", "fruit", "flour", "corn_meal", "soy_protein", "refined_sugar", "food_ingredients", "packaged_food", "packaged_nutrition"), 0.022),
        volatility_multiplier=1.12,
        momentum_multiplier=1.04,
        anchor_shift_by_resource=_shift(("wheat", "corn", "soybeans", "sugarcane", "potatoes", "fruit", "flour", "corn_meal", "soy_protein", "refined_sugar", "food_ingredients", "packaged_food", "packaged_nutrition"), 0.016),
    ),
    MarketEventDefinition(
        event_id="green_energy_expansion",
        name="Green Energy Expansion",
        affected_resources=("lithium_ore", "nickel_ore", "cobalt_ore", "rare_earth_ore", "copper_ore", "lithium", "nickel", "cobalt", "rare_earth_metals", "battery_materials", "battery_components", "solar_components", "wind_components", "grid_battery", "wind_turbine", "solar_array"),
        bias_by_resource=_bias(("lithium_ore", "nickel_ore", "cobalt_ore", "rare_earth_ore", "copper_ore", "lithium", "nickel", "cobalt", "rare_earth_metals", "battery_materials", "battery_components", "solar_components", "wind_components", "grid_battery", "wind_turbine", "solar_array"), 0.020),
        volatility_multiplier=1.08,
        momentum_multiplier=1.05,
        anchor_shift_by_resource=_shift(("lithium_ore", "nickel_ore", "cobalt_ore", "rare_earth_ore", "copper_ore", "lithium", "nickel", "cobalt", "rare_earth_metals", "battery_materials", "battery_components", "solar_components", "wind_components", "grid_battery", "wind_turbine", "solar_array"), 0.015),
    ),
    MarketEventDefinition(
        event_id="biofuel_mandate",
        name="Biofuel Mandate",
        affected_resources=("corn", "sugarcane", "rapeseed", "soybeans", "starch", "vegetable_oil", "fermentation_feedstock", "ethanol_components", "biodiesel_feedstock", "biofuel", "biodiesel", "bioplastic"),
        bias_by_resource=_bias(("corn", "sugarcane", "rapeseed", "soybeans", "starch", "vegetable_oil", "fermentation_feedstock", "ethanol_components", "biodiesel_feedstock", "biofuel", "biodiesel", "bioplastic"), 0.020),
        volatility_multiplier=1.08,
        momentum_multiplier=1.04,
        anchor_shift_by_resource=_shift(("corn", "sugarcane", "rapeseed", "soybeans", "starch", "vegetable_oil", "fermentation_feedstock", "ethanol_components", "biodiesel_feedstock", "biofuel", "biodiesel", "bioplastic"), 0.014),
    ),
    MarketEventDefinition(
        event_id="aerospace_boom",
        name="Aerospace Boom",
        affected_resources=("titanium_ore", "bauxite", "tungsten_ore", "titanium", "aluminum", "carbon_fiber", "aerospace_components", "avionics_components", "jet_engine", "light_aircraft", "cargo_aircraft", "satellite", "launch_vehicle"),
        bias_by_resource=_bias(("titanium_ore", "bauxite", "tungsten_ore", "titanium", "aluminum", "carbon_fiber", "aerospace_components", "avionics_components", "jet_engine", "light_aircraft", "cargo_aircraft", "satellite", "launch_vehicle"), 0.021),
        volatility_multiplier=1.10,
        momentum_multiplier=1.05,
        anchor_shift_by_resource=_shift(("titanium_ore", "bauxite", "tungsten_ore", "titanium", "aluminum", "carbon_fiber", "aerospace_components", "avionics_components", "jet_engine", "light_aircraft", "cargo_aircraft", "satellite", "launch_vehicle"), 0.016),
    ),
    MarketEventDefinition(
        event_id="infrastructure_program",
        name="Infrastructure Program",
        affected_resources=("iron_ore", "copper_ore", "timber", "steel", "copper", "cement", "lumber", "concrete_components", "structural_components", "railway_track", "electrical_cable", "power_cable", "transformer"),
        bias_by_resource=_bias(("iron_ore", "copper_ore", "timber", "steel", "copper", "cement", "lumber", "concrete_components", "structural_components", "railway_track", "electrical_cable", "power_cable", "transformer"), 0.018),
        volatility_multiplier=1.06,
        momentum_multiplier=1.04,
        anchor_shift_by_resource=_shift(("iron_ore", "copper_ore", "timber", "steel", "copper", "cement", "lumber", "concrete_components", "structural_components", "railway_track", "electrical_cable", "power_cable", "transformer"), 0.014),
    ),
)


def create_market_state(resource_ids: Iterable[str] | None = None) -> MarketState:
    market = MarketState()
    for resource_id in resource_ids or BASE_MARKET_PRICES:
        market.ensure_resource(resource_id)
    return market


def market_price_for(market: MarketState, resource_id: str) -> float:
    if resource_id not in BASE_MARKET_PRICES:
        return 0.0
    return BASE_MARKET_PRICES[resource_id]


def active_market_event(market: MarketState) -> MarketEventDefinition:
    return next((event for event in MARKET_EVENTS if event.event_id == market.active_event_id), MARKET_EVENTS[0])


def remaining_event_seconds(market: MarketState) -> float:
    return max(0.0, MARKET_EVENT_SECONDS - (market.elapsed_seconds - market.event_started_at))


def advance_market_time(
    market: MarketState,
    elapsed_seconds: float,
    seed: int,
    resource_ids: Iterable[str] | None = None,
) -> None:
    if elapsed_seconds < 0:
        raise ValueError("Elapsed market time cannot be negative.")
    market.elapsed_seconds += elapsed_seconds
    # The elapsed clock still drives Supply and legacy timing; prices are fixed.


def _refresh_event(market: MarketState) -> None:
    event_index = int(market.elapsed_seconds // MARKET_EVENT_SECONDS) % len(MARKET_EVENTS)
    market.active_event_id = MARKET_EVENTS[event_index].event_id
    market.event_started_at = int(market.elapsed_seconds // MARKET_EVENT_SECONDS) * MARKET_EVENT_SECONDS


def _advance_resource_price(
    resource: ResourceMarketState,
    event: MarketEventDefinition,
    seed: int,
    market_tick: int,
) -> None:
    rng = random.Random(seed * 1_000_003 + market_tick * 9_176 + RESOURCE_RANDOM_OFFSETS[resource.resource_id])
    fundamental_price = BASE_MARKET_PRICES[resource.resource_id]
    affected = resource.resource_id in event.affected_resources
    bias = event.bias_for(resource.resource_id) if affected else 0.0
    volatility_multiplier = event.volatility_multiplier if affected else 1.0
    momentum_multiplier = event.momentum_multiplier if affected else 1.0
    anchor_shift = event.anchor_shift_for(resource.resource_id) if affected else 0.0

    anchor_target = fundamental_price * (1.0 + anchor_shift)
    resource.anchor_price += (anchor_target - resource.anchor_price) * 0.00018

    anchor_distance = (resource.current_price - resource.anchor_price) / max(0.001, resource.anchor_price)
    fundamental_distance = (resource.current_price - fundamental_price) / max(0.001, fundamental_price)
    anchor_distance_abs = abs(anchor_distance)
    fundamental_distance_abs = abs(fundamental_distance)
    mean_reversion = (
        -anchor_distance * (0.12 + anchor_distance_abs * 0.45)
        - fundamental_distance * (0.22 + fundamental_distance_abs * 1.05)
    )
    momentum_pressure = resource.momentum * momentum_multiplier * 0.13
    exhaustion = -_sign(resource.momentum) * min(
        0.36,
        abs(resource.momentum) * (resource.trend_age / 16.0) * (1.0 + fundamental_distance_abs * 2.2),
    )
    p_up = _clamp(0.5 + bias + momentum_pressure + mean_reversion + exhaustion, 0.08, 0.92)

    direction = 1 if rng.random() < p_up else -1
    strength = resource.volatility * volatility_multiplier * (0.35 + rng.random() * 1.10)
    reversion_direction = -_sign(fundamental_distance)
    if reversion_direction and direction == reversion_direction:
        strength *= 1.0 + min(1.00, fundamental_distance_abs * 1.10)
    elif reversion_direction:
        strength /= 1.0 + fundamental_distance_abs * 0.90
    old_price = resource.current_price
    resource.current_price = resource.current_price * (1.0 + direction * strength)
    normalized_strength = min(1.0, strength / max(0.001, resource.volatility))
    new_momentum = resource.momentum * 0.62 + direction * normalized_strength * 0.14
    previous_sign = _sign(resource.momentum)
    resource.momentum = _clamp(new_momentum, -1.0, 1.0)
    resource.trend_age = resource.trend_age + 1 if previous_sign == direction else 1
    resource.last_change = resource.current_price - old_price


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
