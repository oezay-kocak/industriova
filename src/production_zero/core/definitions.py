from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.enums import CardKind, EnergyType, FreightFamily, MachineType


@dataclass(frozen=True, slots=True)
class ProductionOptionDefinition:
    """Selectable production target or recipe for one machine family."""

    production_id: str
    name: str
    input_resources: Mapping[str, float]
    output_resource: str
    stage: MachineType
    icon_key: str
    accent_key: str
    output_amount: float | None = None
    cycle_seconds: float | None = None
    power_draw: float | None = None
    aliases: tuple[str, ...] = ()

    def output_amount_for(self, definition: MachineDefinition) -> float:
        return self.output_amount if self.output_amount is not None else definition.base_output_per_tick

    def cycle_seconds_for(self, definition: MachineDefinition) -> float:
        return self.cycle_seconds if self.cycle_seconds is not None else definition.cycle_seconds

    def power_draw_for(self, definition: MachineDefinition) -> float:
        return self.power_draw if self.power_draw is not None else definition.base_power_draw


@dataclass(frozen=True, slots=True)
class MachineDefinition:
    """Static machine blueprint loaded from game data."""

    definition_id: str
    name: str
    machine_type: MachineType
    base_output_per_tick: float
    base_power_draw: float
    cycle_seconds: float
    input_resources: Mapping[str, float]
    output_resource: str
    production_options: tuple[ProductionOptionDefinition, ...] = ()
    stage: MachineType | None = None
    icon_key: str = ""
    accent_key: str = ""
    alias_default_productions: Mapping[str, str] = field(default_factory=dict)

    @property
    def card_kind(self) -> CardKind:
        return CardKind.MACHINE

    @property
    def default_production_id(self) -> str:
        if self.production_options:
            return self.production_options[0].production_id
        return f"resource.{self.output_resource}"

    def default_production_id_for_card_definition(self, card_definition_id: str) -> str:
        return self.alias_default_productions.get(card_definition_id, self.default_production_id)

    def production_option(self, production_id: str | None = None) -> ProductionOptionDefinition:
        selected_id = production_id or self.default_production_id
        for option in self.available_production_options:
            if option.production_id == selected_id or selected_id in option.aliases:
                return option
        return self.available_production_options[0]

    @property
    def available_production_options(self) -> tuple[ProductionOptionDefinition, ...]:
        if self.production_options:
            return self.production_options
        return (
            ProductionOptionDefinition(
                production_id=f"resource.{self.output_resource}",
                name=self.output_resource.replace("_", " ").title(),
                input_resources=self.input_resources,
                output_resource=self.output_resource,
                stage=self.machine_type,
                icon_key=self.icon_key or self.output_resource,
                accent_key=self.accent_key or self.output_resource,
            ),
        )

    def is_compatible_with(self, production: ProductionOptionDefinition) -> bool:
        return production.stage is self.machine_type


@dataclass(frozen=True, slots=True)
class EnergyDefinition:
    """Static energy producer blueprint loaded from game data."""

    definition_id: str
    name: str
    energy_type: EnergyType
    base_power_output: float
    input_resources: Mapping[str, float]
    fuel_resource_id: str | None = None
    fuel_consumption_per_minute: float = 0.0
    supply_price_cash: float | None = None

    @property
    def card_kind(self) -> CardKind:
        return CardKind.ENERGY

    @property
    def fuel_consumption_per_cycle(self) -> float:
        return self.fuel_consumption_per_minute * ECONOMIC_CYCLE_SECONDS / 60.0

    @property
    def requires_fuel(self) -> bool:
        return self.fuel_resource_id is not None and self.fuel_consumption_per_minute > 0




@dataclass(frozen=True, slots=True)
class FreightDefinition:
    """Static freight blueprint loaded from game data."""

    definition_id: str
    name: str
    family: FreightFamily
    facility_id: str
    facility_name: str
    base_capacity: float
    base_transport_time_seconds: float
    supply_price_cash: float | None = None

    @property
    def card_kind(self) -> CardKind:
        return CardKind.FREIGHT


CardDefinition = MachineDefinition | EnergyDefinition | FreightDefinition
