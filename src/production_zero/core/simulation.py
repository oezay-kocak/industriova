from __future__ import annotations

from copy import copy
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Callable

from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.cards import CardInstance
from production_zero.core.contracts import receive_contract_delivery, refresh_contracts
from production_zero.core.company_xp import award_market_sale_xp, record_accepted_production_xp, utc_timestamp
from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.freight import MarketDeliveryResolution, advance_outbound_shipments, start_outbound_shipment_for_card, _FreightDispatchIndex
from production_zero.core.market import advance_market_time
from production_zero.core.modifiers import market_sale_price, research_multiplier
from production_zero.core.research import sync_research_clock
from production_zero.core.progression import record_lifetime_production
from production_zero.core.state import GameState
from production_zero.core.production_pause import production_slot_paused
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
    def __init__(
        self,
        definitions: dict[str, CardDefinition],
        utc_now: Callable[[], datetime | float] | None = None,
    ) -> None:
        self._definitions = definitions
        self._utc_now = utc_now

    def preview_tick(self, state: GameState) -> ProductionTotals:
        """Preview the next production second without changing the live state."""
        # The production pass only mutates these two collections. Keep clocks,
        # histories, logistics and progression outside the preview entirely.
        projected = copy(state)
        projected.resources = {rid: replace(stock) for rid, stock in state.resources.items()}
        projected.machine_production = {cid: replace(machine) for cid, machine in state.machine_production.items()}
        totals, _events = self._advance_production(projected, 1.0)
        return ProductionTotals(gross_power=totals.gross_power, used_power=totals.used_power, outputs={})

    def advance_time(self, state: GameState, elapsed_seconds: float) -> ProductionTotals:
        from math import isfinite
        if not isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("Elapsed time cannot be negative.")
        # Keep the same causal order as online play: downstream machines may
        # use an upstream batch on the next second, never retroactively at the
        # start of a large catchup interval. Production and sale rewards follow
        # the same causal completion order at dt=1/2/3/6/60/etc.
        if elapsed_seconds <= 1:
            return self._advance_step(state, elapsed_seconds)
        end_utc = utc_timestamp(self._utc_now() if self._utc_now is not None else None)
        remaining = elapsed_seconds
        outputs, inputs, sold = {}, {}, {}
        while remaining > 1e-9:
            step = min(1., remaining)
            remaining -= step
            totals = self._advance_step(state, step, end_utc - remaining)
            for target, values in ((outputs, totals.outputs), (inputs, totals.inputs), (sold, totals.auto_sold)):
                for rid, amount in (values or {}).items():
                    target[rid] = target.get(rid, 0.) + amount
        return ProductionTotals(totals.gross_power, totals.used_power, outputs, inputs, sold, totals.blocked_cards)

    def _advance_production(
        self, state: GameState, elapsed_seconds: float,
    ) -> tuple[ProductionTotals, dict[int, dict[str, float]]]:
        """Advance production stocks and machine states, without other game effects."""
        gross_power = 0.0
        available_power = 0.0
        used_power = 0.0
        outputs: dict[str, float] = {}
        inputs: dict[str, float] = {}
        blocked_cards: list[str] = []
        # Record accepted completion events for progression, milestones and
        # production telemetry. Multiple machines share each event bucket.
        from math import ceil
        event_start = state.market.elapsed_seconds
        production_events: dict[int, dict[str, float]] = {}
        for hall in state.all_production_units():
            for slot in hall.slots:
                if slot.card_id is None:
                    continue
                card = state.cards[slot.card_id]
                if card.paused or production_slot_paused(hall, slot.index):
                    production_state = state.machine_production.get(card.card_id)
                    if production_state is not None:
                        production_state.status = "paused"
                    continue
                definition = self._definitions[card.definition_id]
                if not isinstance(definition, EnergyDefinition):
                    continue
                consumed = self._consume_energy_fuel_if_available(state, definition, elapsed_seconds * card.mk_multiplier)
                if consumed is None:
                    continue
                power_output = definition.base_power_output * card.output_multiplier * research_multiplier(state.research, "energy_output")
                gross_power += power_output
                available_power += power_output
                for resource_id, amount in consumed.items():
                    inputs[resource_id] = inputs.get(resource_id, 0.0) + amount

        # The production pass is synchronous: only this pass changes stocks.
        # Keep a tick-local balance instead of summing every stored product for
        # each preflight and cycle. The public GameState balance remains derived
        # from real stocks, and the local balance is discarded after this pass.
        production_storage_used = state.used_storage
        production_storage_capacity = state.storage_capacity
        def can_store_output(amount, *, released_amount=0.):
            return amount <= max(0., production_storage_capacity - production_storage_used + released_amount) + 1e-9

        for hall in state.all_production_units():
            for slot in hall.slots:
                if slot.card_id is None:
                    continue
                card = state.cards[slot.card_id]
                if card.paused or production_slot_paused(hall, slot.index):
                    production_state = state.machine_production.get(card.card_id)
                    if production_state is not None:
                        production_state.status = "paused"
                    continue
                definition = self._definitions[card.definition_id]
                if not isinstance(definition, MachineDefinition):
                    continue

                machine_state = state.ensure_machine_production(
                    card.card_id,
                    "",
                    None,
                )
                if machine_state.selected_production_id is None:
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
                produced_per_cycle = production.output_amount_for(definition) * card.output_multiplier
                released_per_cycle = sum(production.input_resources.values()) * card.mk_multiplier
                if not can_store_output(produced_per_cycle, released_amount=released_per_cycle):
                    machine_state.status = "storage_full"
                    blocked_cards.append(card.card_id)
                    continue

                if not self._has_required_inputs(state, production, card.mk_multiplier):
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
                speed = research_multiplier(state.research, "production_speed")
                progress_before = machine_state.progress_seconds
                machine_state.progress_seconds += elapsed_seconds * speed
                cycle_seconds = max(0.001, production.cycle_seconds_for(definition))
                completed_cycles = int((machine_state.progress_seconds + 1e-9) // cycle_seconds)
                if completed_cycles <= 0:
                    continue

                accepted_cycles = 0
                for _ in range(completed_cycles):
                    if not can_store_output(produced_per_cycle, released_amount=released_per_cycle):
                        machine_state.status = "storage_full"
                        blocked_cards.append(card.card_id)
                        break
                    if not self._has_required_inputs(state, production, card.mk_multiplier):
                        machine_state.status = "missing_input"
                        blocked_cards.append(card.card_id)
                        break

                    self._consume_inputs(state, production, card.mk_multiplier)
                    production_storage_used -= released_per_cycle
                    for resource_id, amount in production.input_resources.items():
                        inputs[resource_id] = inputs.get(resource_id, 0.0) + amount * card.mk_multiplier
                    machine_state.progress_seconds -= cycle_seconds
                    if -1e-9 < machine_state.progress_seconds < 0:
                        machine_state.progress_seconds = 0.0
                    produced = produced_per_cycle
                    accepted = min(produced, max(0., production_storage_capacity - production_storage_used))
                    storage.amount += accepted
                    production_storage_used += accepted
                    if accepted < produced - 1e-9:
                        raise RuntimeError("Production storage transaction was not atomic.")
                    outputs[machine_state.target_resource_id] = outputs.get(machine_state.target_resource_id, 0.0) + accepted
                    if accepted > 0:
                        accepted_cycles += 1
                        offset = max(0.0, (accepted_cycles * cycle_seconds - progress_before) / speed)
                        bucket = ceil(event_start + min(elapsed_seconds, offset) - 1e-9) - 1
                        event = production_events.setdefault(bucket, {})
                        event[machine_state.target_resource_id] = event.get(machine_state.target_resource_id, 0.0) + accepted
                    if not can_store_output(produced_per_cycle, released_amount=released_per_cycle):
                        machine_state.status = "storage_full"
                        blocked_cards.append(card.card_id)
                        break

        return ProductionTotals(gross_power, used_power, outputs, inputs, blocked_cards=tuple(blocked_cards)), production_events

    def _advance_step(self, state: GameState, elapsed_seconds: float, step_utc=None) -> ProductionTotals:
        totals, production_events = self._advance_production(state, elapsed_seconds)
        state.history.elapsed_seconds += elapsed_seconds
        gross_power, used_power = totals.gross_power, totals.used_power
        outputs, inputs = totals.outputs, totals.inputs
        blocked_cards = totals.blocked_cards
        auto_sold: dict[str, float] = {}
        shipments_to_advance = set(state.freight.outbound_shipments)
        delivery_clock = state.freight.delivery_statistics.seconds
        completion_times = {sid: delivery_clock + max(0.0, shipment.remaining_seconds)
                            for sid, shipment in state.freight.outbound_shipments.items()}

        state.energy.consumed = used_power
        state.energy.generated = gross_power
        previous_market_tick = state.market.market_tick
        advance_market_time(state.market, elapsed_seconds, state.rng_seed)
        if state.market.market_tick != previous_market_tick:
            for resource_id, resource_state in state.market.resources.items():
                state.history.append(f"market.price.{resource_id}", resource_state.current_price)
        now_utc = step_utc if step_utc is not None else self._utc_now() if self._utc_now is not None else None
        # Apply XP in completion order, including UTC day boundaries during
        # catchup. Empty time and rejected batches never produce XP events.
        now_timestamp = utc_timestamp(now_utc)
        if not production_events:
            # Unlock eligibility can also change through commands/imported
            # history; preserve the existing empty-tick progression refresh.
            record_lifetime_production(state, {}, self._definitions)
        for bucket, produced in sorted(production_events.items()):
            progress = state.company_xp_progress
            productive_seconds = 1.0 if bucket > progress.last_productive_bucket else 0.0
            progress.last_productive_bucket = max(progress.last_productive_bucket, bucket)
            progress.productive_event_seconds += productive_seconds
            event_timestamp = now_timestamp - (state.market.elapsed_seconds - (bucket + 1))
            record_lifetime_production(state, produced, self._definitions)
            record_accepted_production_xp(state, produced, productive_seconds, self._definitions, event_timestamp)
        sync_research_clock(state, now_timestamp)
        refresh_contracts(state, self._definitions, now_utc=now_utc)
        refresh_supply(state, self._definitions)
        state.freight.delivery_statistics.advance(elapsed_seconds)
        self._complete_outbound_shipments(state, advance_outbound_shipments(state.freight, elapsed_seconds, shipments_to_advance), completion_times, now_utc)
        dispatch_index = _FreightDispatchIndex(state.freight)
        self._apply_freight_market_exports(state, auto_sold, _dispatch_index=dispatch_index)
        self._apply_freight_contract_deliveries(state, _dispatch_index=dispatch_index)
        self._apply_consortium_freight(state, now_utc, _dispatch_index=dispatch_index)
        state.tick += 1
        state.inventory_history.advance(elapsed_seconds, {rid: stock.amount for rid, stock in state.resources.items()})
        state.history.observe("cash", state.cash.amount)
        state.history.observe("energy.generated", state.energy.generated)
        state.history.observe("energy.consumed", state.energy.consumed)
        for resource_id, stock in state.resources.items():
            state.history.observe(f"resource.{resource_id}", stock.amount)
            state.history.observe_rate(f"rate.production.{resource_id}", outputs.get(resource_id, 0.0), elapsed_seconds)
            state.history.observe_rate(f"rate.consumption.{resource_id}", inputs.get(resource_id, 0.0), elapsed_seconds)
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

    def _has_required_inputs(self, state: GameState, production: ProductionOptionDefinition, factor: float = 1.) -> bool:
        return all(
            state.ensure_resource(resource_id).amount >= amount * factor
            for resource_id, amount in production.input_resources.items()
        )

    def _consume_inputs(self, state: GameState, production: ProductionOptionDefinition, factor: float = 1.) -> None:
        for resource_id, amount in production.input_resources.items():
            state.ensure_resource(resource_id).consume(amount * factor)

    def _energy_fuel_required(self, definition: EnergyDefinition, elapsed_seconds: float) -> dict[str, float]:
        if not definition.requires_fuel or definition.fuel_resource_id is None:
            return {}
        return {
            definition.fuel_resource_id: definition.fuel_consumption_per_cycle * max(0.0, elapsed_seconds) / ECONOMIC_CYCLE_SECONDS
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

    def _apply_freight_market_exports(self, state: GameState, auto_sold: dict[str, float], *, _dispatch_index=None) -> None:
        index = _dispatch_index if _dispatch_index is not None else _FreightDispatchIndex(state.freight)
        prices = {}
        for card_id in self._available_assigned_freight_cards(state, "market", _dispatch_index=index):
            assignment = state.freight.assignments[card_id]
            resource_id = assignment.resource_id
            if resource_id not in prices:
                prices[resource_id] = market_sale_price(state, resource_id)
            price = prices[resource_id]
            if price <= 0:
                continue
            stock = state.ensure_resource(resource_id)
            excess = max(0.0, stock.amount)
            if excess <= 0:
                continue
            shipment = start_outbound_shipment_for_card(
                state.freight,
                state.cards,
                self._definitions,
                research=state.research,
                card_id=card_id,
                destination_kind="market",
                resource_id=resource_id,
                quantity=excess,
                market_price=price,
                _dispatch_index=index,
            )
            if shipment is None:
                continue
            stock.consume(shipment.quantity)
            auto_sold[resource_id] = auto_sold.get(resource_id, 0.0) + shipment.quantity

    def _apply_freight_contract_deliveries(self, state: GameState, *, _dispatch_index=None) -> None:
        from production_zero.core.contract_allocation import dispatch_contract_freight
        dispatch_contract_freight(state, self._definitions, _dispatch_index=_dispatch_index)

    def _available_assigned_freight_cards(self, state: GameState, destination_kind: str, *, _dispatch_index=None) -> tuple[str, ...]:
        index = _dispatch_index if _dispatch_index is not None else _FreightDispatchIndex(state.freight)
        cards: list[str] = []
        for cid in index.ordered_card_ids:
            if cid in index.busy or state.cards[cid].paused:
                continue
            assignment = state.freight.assignments.get(cid)
            if assignment is not None and assignment.destination_kind == destination_kind:
                cards.append(cid)
        return tuple(cards)

    def _pending_contract_shipments(self, state: GameState) -> dict[tuple[str, str], float]:
        from production_zero.core.contract_allocation import pending_contract_deliveries
        return pending_contract_deliveries(state)

    def _apply_consortium_freight(self, state, now_utc=None, *, _dispatch_index=None):
        membership = state.consortium.membership()
        if membership is None:
            return
        consortium, member = membership
        index = _dispatch_index if _dispatch_index is not None else _FreightDispatchIndex(state.freight)
        pending = {}
        for shipment in state.freight.outbound_shipments.values():
            if shipment.destination_kind == "consortium" and shipment.target_id:
                key = (shipment.target_id, shipment.resource_id)
                pending[key] = pending.get(key, 0.) + shipment.quantity
        for cid in self._available_assigned_freight_cards(state, "consortium", _dispatch_index=index):
            assignment = state.freight.assignments[cid]
            stock = state.ensure_resource(assignment.resource_id)
            for kind, contract in consortium.contracts.items():
                target = f"{consortium.consortium_id}|{kind}|{contract.contract_id}"
                now = utc_timestamp(now_utc)
                if contract.status != "active" or contract.expires_at <= now or assignment.resource_id not in contract.requirements:
                    continue
                needed = contract.remaining(assignment.resource_id) - pending.get((target, assignment.resource_id), 0.)
                if needed <= 0 or stock.amount <= 0:
                    continue
                shipment = start_outbound_shipment_for_card(state.freight, state.cards, self._definitions, card_id=cid, destination_kind="consortium", resource_id=assignment.resource_id, quantity=min(stock.amount, needed), target_id=target, research=state.research, _dispatch_index=index)
                if shipment is not None:
                    stock.consume(shipment.quantity)
                    pending[(target, assignment.resource_id)] = pending.get((target, assignment.resource_id), 0.) + shipment.quantity
                break

    def _complete_outbound_shipments(self, state: GameState, shipments, completion_times=None, now_utc=None) -> None:
        if now_utc is None and self._utc_now is not None:
            now_utc = self._utc_now()
        for shipment in sorted(shipments, key=lambda s: (completion_times.get(s.shipment_id, 0.) if completion_times else 0., s.shipment_id)):
            if shipment.economic_processed or shipment.active or shipment.remaining_seconds > 0:
                continue
            sell = contract = consortium = 0.0
            if shipment.destination_kind == "market":
                delivered_to_contracts = (
                    0.0
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
                if market_quantity > 0:
                    earnings = market_quantity * shipment.market_price
                    state.cash.add(earnings)
                    state.statistics.record_earnings(earnings)
                    state.history.append("cash", state.cash.amount)
                    award_market_sale_xp(state, earnings, self._definitions)
                sell, contract = market_quantity, delivered_to_contracts
            elif shipment.destination_kind == "contract" and shipment.resource_id:
                from production_zero.core.freight import contract_shipment_allocations
                allocation = contract_shipment_allocations(shipment)
                if not allocation:
                    self._sell_unneeded_reserved_goods(state, shipment, shipment.quantity)
                # JSON key sorting must not change reward/renewal ordering when
                # several targets finish on the same physical arrival.
                for target, quantity in sorted(allocation.items()):
                    cancelled_price = shipment.cancelled_contract_prices.get(target)
                    valid = next((active for active in state.contracts.active.values()
                        if active.status == 'active' and active.offer.contract_id == target), None) if cancelled_price is None else None
                    delivered = min(quantity, valid.remaining_amount(shipment.resource_id)) if valid else 0.
                    if delivered > 0:
                        receive_contract_delivery(state, target, shipment.resource_id, delivered, self._definitions, now_utc=now_utc)
                    self._sell_unneeded_reserved_goods(state, shipment, quantity - delivered, price=cancelled_price)
                    contract += delivered
                contract = min(shipment.quantity, contract)
                sell = max(0., shipment.quantity - contract)
            elif shipment.destination_kind == "consortium" and shipment.target_id and shipment.resource_id:
                from production_zero.core.consortium import ConsortiumService
                from production_zero.core.freight_settlement import _economic_arrival, _FreightAlreadySettled
                delivered = 0.
                try:
                    consortium_id, kind, contract_id = shipment.target_id.split("|", 2)
                    service = ConsortiumService(state, self._definitions, clock=lambda: utc_timestamp(now_utc))
                    with _economic_arrival(state, shipment) as grant:
                        delivered = service._accept_freight_arrival(grant)
                except _FreightAlreadySettled:
                    shipment.economic_processed = True
                    continue
                except (ValueError, KeyError, PermissionError):
                    pass  # Missing/expired membership converts reserved cargo into a sale.
                self._sell_unneeded_reserved_goods(state, shipment, shipment.quantity - delivered)
                consortium, sell = delivered, shipment.quantity - delivered
            # This transition and removal from outbound_shipments belong to the same
            # synchronous engine call. The session writer sees a detached full snapshot.
            state.freight.delivery_statistics.record(
                shipment.freight_card_id, shipment.source_facility_id,
                sell=sell, contract=contract, consortium=consortium,
                resource_id=shipment.resource_id,
                at_seconds=completion_times.get(shipment.shipment_id) if completion_times is not None else None,
            )
            shipment.economic_processed = True

    def _sell_unneeded_reserved_goods(self, state, shipment, amount, *, price=None):
        if amount <= 0:
            return
        earnings = amount * (market_sale_price(state, shipment.resource_id) if price is None else price)
        state.cash.add(earnings)
        state.statistics.record_earnings(earnings)
        state.history.append("cash", state.cash.amount)
        award_market_sale_xp(state, earnings, self._definitions)
