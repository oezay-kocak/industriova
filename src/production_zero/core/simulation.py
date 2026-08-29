from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.cards import CardInstance
from production_zero.core.contracts import CONTRACT_KINDS, receive_contract_delivery, refresh_contracts, route_market_delivery_to_contracts
from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.freight import MarketDeliveryResolution, advance_outbound_shipments, start_outbound_shipment_for_card
from production_zero.core.market import advance_market_time, market_price_for
from production_zero.core.state import GameState
from production_zero.core.supply import refresh_supply


@dataclass(frozen=True, slots=True)
class ProductionTotals:
    gross_power: float
    used_power: float
    outputs: dict[str, float]
    inputs: dict[str, float] | None = None
    auto_sold: dict[str, float] | None = None
    blocked_cards: tuple[str, ...] = ()


class SimulationEngine:
    def __init__(self, definitions: dict[str, CardDefinition]) -> None:
        self._definitions = definitions

    def preview_tick(self, state: GameState) -> ProductionTotals:
        gross_power = 0.0
        used_power = 0.0
        outputs: dict[str, float] = {}

        for hall in state.halls.values():
            for slot in hall.slots:
                if slot.card_id is None:
                    continue
                card = state.cards[slot.card_id]
                definition = self._definitions[card.definition_id]

                if isinstance(definition, EnergyDefinition):
                    if self._energy_fuel_available(state, definition, 0.0):
                        gross_power += definition.base_power_output * card.output_multiplier
                elif isinstance(definition, MachineDefinition):
                    machine_state = state.machine_production.get(card.card_id)
                    production = definition.production_option(
                        machine_state.selected_production_id
                        if machine_state is not None and machine_state.selected_production_id is not None
                        else definition.default_production_id_for_card_definition(card.definition_id)
                    )
                    used_power += production.power_draw_for(definition) * card.power_multiplier

        return ProductionTotals(gross_power=gross_power, used_power=used_power, outputs=outputs)

    def advance_time(self, state: GameState, elapsed_seconds: float) -> ProductionTotals:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed time cannot be negative.")
        self.preview_tick(state)
        gross_power = 0.0
        available_power = 0.0
        used_power = 0.0
        outputs: dict[str, float] = {}
        inputs: dict[str, float] = {}
        auto_sold: dict[str, float] = {}
        blocked_cards: list[str] = []
        shipments_to_advance = set(state.freight.outbound_shipments)

        for hall in state.halls.values():
            for slot in hall.slots:
                if slot.card_id is None:
                    continue
                card = state.cards[slot.card_id]
                definition = self._definitions[card.definition_id]
                if not isinstance(definition, EnergyDefinition):
                    continue
                consumed = self._consume_energy_fuel_if_available(state, definition, elapsed_seconds)
                if consumed is None:
                    continue
                power_output = definition.base_power_output * card.output_multiplier
                gross_power += power_output
                available_power += power_output
                for resource_id, amount in consumed.items():
                    inputs[resource_id] = inputs.get(resource_id, 0.0) + amount

        for hall in state.halls.values():
            for slot in hall.slots:
                if slot.card_id is None:
                    continue
                card = state.cards[slot.card_id]
                definition = self._definitions[card.definition_id]
                if not isinstance(definition, MachineDefinition):
                    continue

                machine_state = state.ensure_machine_production(
                    card.card_id,
                    "",
                    None,
                )
                if machine_state.selected_production_id is None:
                    power_profile = definition.production_option(
                        definition.default_production_id_for_card_definition(card.definition_id)
                    )
                    required_power = power_profile.power_draw_for(definition) * card.power_multiplier
                    if required_power <= available_power:
                        available_power -= required_power
                        used_power += required_power
                    machine_state.target_resource_id = ""
                    machine_state.status = "unconfigured"
                    machine_state.progress_seconds = 0.0
                    continue
                production = self._selected_production(definition, machine_state.selected_production_id)
                if not definition.is_compatible_with(production):
                    machine_state.status = "missing_input"
                    blocked_cards.append(card.card_id)
                    continue
                machine_state.selected_production_id = production.production_id
                machine_state.target_resource_id = production.output_resource
                storage = state.ensure_resource(machine_state.target_resource_id)
                if storage.free_capacity <= 0:
                    machine_state.status = "storage_full"
                    blocked_cards.append(card.card_id)
                    continue

                if not self._has_required_inputs(state, production):
                    machine_state.status = "missing_input"
                    blocked_cards.append(card.card_id)
                    continue

                required_power = production.power_draw_for(definition) * card.power_multiplier
                if required_power > available_power:
                    machine_state.status = "no_power"
                    blocked_cards.append(card.card_id)
                    continue

                available_power -= required_power
                used_power += required_power
                machine_state.status = "running"
                machine_state.progress_seconds += elapsed_seconds
                cycle_seconds = max(0.001, production.cycle_seconds_for(definition))
                completed_cycles = int(machine_state.progress_seconds // cycle_seconds)
                if completed_cycles <= 0:
                    continue

                for _ in range(completed_cycles):
                    if storage.free_capacity <= 0:
                        machine_state.status = "storage_full"
                        blocked_cards.append(card.card_id)
                        break
                    if not self._has_required_inputs(state, production):
                        machine_state.status = "missing_input"
                        blocked_cards.append(card.card_id)
                        break

                    self._consume_inputs(state, production)
                    for resource_id, amount in production.input_resources.items():
                        inputs[resource_id] = inputs.get(resource_id, 0.0) + amount
                    machine_state.progress_seconds -= cycle_seconds
                    produced = production.output_amount_for(definition) * card.output_multiplier
                    accepted = storage.add(produced)
                    outputs[machine_state.target_resource_id] = outputs.get(machine_state.target_resource_id, 0.0) + accepted
                    if storage.free_capacity <= 0:
                        machine_state.status = "storage_full"
                        blocked_cards.append(card.card_id)
                        break

        state.energy.consumed = used_power
        state.energy.generated = gross_power
        previous_market_tick = state.market.market_tick
        advance_market_time(state.market, elapsed_seconds, state.rng_seed)
        if state.market.market_tick != previous_market_tick:
            for resource_id, resource_state in state.market.resources.items():
                state.history.append(f"market.price.{resource_id}", resource_state.current_price)
        refresh_contracts(state)
        refresh_supply(state, self._definitions)
        self._complete_outbound_shipments(state, advance_outbound_shipments(state.freight, elapsed_seconds, shipments_to_advance))
        self._apply_freight_market_exports(state, auto_sold)
        self._apply_freight_contract_deliveries(state)
        state.tick += 1
        state.history.append("cash", state.cash.amount)
        state.history.append("energy.generated", state.energy.generated)
        state.history.append("energy.consumed", state.energy.consumed)
        for resource_id, stock in state.resources.items():
            state.history.append(f"resource.{resource_id}", stock.amount)
            state.history.append(f"rate.production.{resource_id}", self._per_minute(outputs.get(resource_id, 0.0), elapsed_seconds))
            state.history.append(f"rate.consumption.{resource_id}", self._per_minute(inputs.get(resource_id, 0.0), elapsed_seconds))
        return ProductionTotals(
            gross_power=gross_power,
            used_power=used_power,
            outputs=outputs,
            inputs=inputs,
            auto_sold=auto_sold,
            blocked_cards=tuple(blocked_cards),
        )

    def tick(self, state: GameState) -> ProductionTotals:
        return self.advance_time(state, 1.0)

    def _selected_production(
        self,
        definition: MachineDefinition,
        production_id: str | None,
    ) -> ProductionOptionDefinition:
        return definition.production_option(production_id)

    def _has_required_inputs(self, state: GameState, production: ProductionOptionDefinition) -> bool:
        return all(
            state.ensure_resource(resource_id).amount >= amount
            for resource_id, amount in production.input_resources.items()
        )

    def _consume_inputs(self, state: GameState, production: ProductionOptionDefinition) -> None:
        for resource_id, amount in production.input_resources.items():
            state.ensure_resource(resource_id).consume(amount)

    def _energy_fuel_required(self, definition: EnergyDefinition, elapsed_seconds: float) -> dict[str, float]:
        if not definition.requires_fuel or definition.fuel_resource_id is None:
            return {}
        return {
            definition.fuel_resource_id: definition.fuel_consumption_per_minute * max(0.0, elapsed_seconds) / 60.0
        }

    def _energy_fuel_available(self, state: GameState, definition: EnergyDefinition, elapsed_seconds: float) -> bool:
        required = self._energy_fuel_required(definition, elapsed_seconds)
        if not required:
            return True
        if elapsed_seconds <= 0:
            return all(state.ensure_resource(resource_id).amount > 0 for resource_id in required)
        return all(state.ensure_resource(resource_id).amount >= amount for resource_id, amount in required.items())

    def _consume_energy_fuel_if_available(
        self,
        state: GameState,
        definition: EnergyDefinition,
        elapsed_seconds: float,
    ) -> dict[str, float] | None:
        required = self._energy_fuel_required(definition, elapsed_seconds)
        if not required:
            return {}
        if not self._energy_fuel_available(state, definition, elapsed_seconds):
            return None
        for resource_id, amount in required.items():
            state.ensure_resource(resource_id).consume(amount)
        return required

    def _per_minute(self, amount: float, elapsed_seconds: float) -> float:
        if elapsed_seconds <= 0:
            return 0.0
        return amount / elapsed_seconds * 60.0

    def _apply_freight_market_exports(self, state: GameState, auto_sold: dict[str, float]) -> None:
        for card_id in self._available_assigned_freight_cards(state, "market"):
            assignment = state.freight.assignments[card_id]
            resource_id = assignment.resource_id
            price = market_price_for(state.market, resource_id)
            if price <= 0:
                continue
            stock = state.ensure_resource(resource_id)
            reserve = stock.capacity * assignment.reserve_percent / 100.0
            excess = max(0.0, stock.amount - reserve)
            if excess <= 0:
                continue
            shipment = start_outbound_shipment_for_card(
                state.freight,
                state.cards,
                self._definitions,
                card_id=card_id,
                destination_kind="market",
                resource_id=resource_id,
                quantity=excess,
                market_price=price,
            )
            if shipment is None:
                continue
            stock.consume(shipment.quantity)
            auto_sold[resource_id] = auto_sold.get(resource_id, 0.0) + shipment.quantity

    def _apply_freight_contract_deliveries(self, state: GameState) -> None:
        pending = self._pending_contract_shipments(state)
        for card_id in self._available_assigned_freight_cards(state, "contract"):
            assignment = state.freight.assignments[card_id]
            stock = state.ensure_resource(assignment.resource_id)
            if stock.amount <= 0:
                continue
            target_id, remaining = self._first_contract_need(state, assignment.resource_id, pending)
            if target_id is None or remaining <= 0:
                continue
            shipment = start_outbound_shipment_for_card(
                state.freight,
                state.cards,
                self._definitions,
                card_id=card_id,
                destination_kind="contract",
                target_id=target_id,
                resource_id=assignment.resource_id,
                quantity=min(stock.amount, remaining),
            )
            if shipment is None:
                continue
            stock.consume(shipment.quantity)
            pending[(target_id, assignment.resource_id)] = pending.get((target_id, assignment.resource_id), 0.0) + shipment.quantity
            state.history.append(f"resource.{assignment.resource_id}", stock.amount)

    def _available_assigned_freight_cards(self, state: GameState, destination_kind: str) -> tuple[str, ...]:
        busy = {
            shipment.freight_card_id
            for shipment in state.freight.outbound_shipments.values()
            if shipment.active and shipment.freight_card_id is not None
        }
        cards: list[str] = []
        for facility_id in sorted(state.freight.facilities):
            facility = state.freight.facilities[facility_id]
            for slot in sorted(facility.slots, key=lambda item: item.index):
                if slot.card_id is None or slot.card_id in busy:
                    continue
                assignment = state.freight.assignments.get(slot.card_id)
                if assignment is not None and assignment.destination_kind == destination_kind:
                    cards.append(slot.card_id)
        return tuple(cards)

    def _pending_contract_shipments(self, state: GameState) -> dict[tuple[str, str], float]:
        pending: dict[tuple[str, str], float] = {}
        for shipment in state.freight.outbound_shipments.values():
            if shipment.active and shipment.destination_kind == "contract" and shipment.target_id and shipment.resource_id:
                key = (shipment.target_id, shipment.resource_id)
                pending[key] = pending.get(key, 0.0) + shipment.quantity
        return pending

    def _first_contract_need(
        self,
        state: GameState,
        resource_id: str,
        pending: dict[tuple[str, str], float],
    ) -> tuple[str | None, float]:
        for kind in CONTRACT_KINDS:
            active = state.contracts.active.get(kind)
            if active is None or active.status != "active" or resource_id not in active.offer.requirements:
                continue
            remaining = active.remaining_amount(resource_id) - pending.get((active.offer.contract_id, resource_id), 0.0)
            if remaining > 0:
                return active.offer.contract_id, remaining
        return None, 0.0

    def _complete_outbound_shipments(self, state: GameState, shipments) -> None:
        for shipment in shipments:
            if shipment.destination_kind == "market":
                delivered_to_contracts = (
                    route_market_delivery_to_contracts(state, shipment.resource_id, shipment.quantity)
                    if shipment.resource_id is not None
                    else 0.0
                )
                market_quantity = max(0.0, shipment.quantity - delivered_to_contracts)
                state.freight.completed_market_deliveries.append(
                    MarketDeliveryResolution(
                        delivery_id=state.freight.next_market_delivery_sequence,
                        shipment_id=shipment.shipment_id,
                        resource_id=shipment.resource_id or "",
                        delivered_amount=shipment.quantity,
                        contract_amount=delivered_to_contracts,
                        market_amount=market_quantity,
                        market_price=shipment.market_price,
                        market_earnings=market_quantity * shipment.market_price,
                    )
                )
                state.freight.next_market_delivery_sequence += 1
                if market_quantity <= 0:
                    continue
                earnings = market_quantity * shipment.market_price
                state.cash.add(earnings)
                state.statistics.record_earnings(earnings)
                state.history.append("cash", state.cash.amount)
            elif shipment.destination_kind == "contract" and shipment.target_id and shipment.resource_id:
                receive_contract_delivery(state, shipment.target_id, shipment.resource_id, shipment.quantity)
