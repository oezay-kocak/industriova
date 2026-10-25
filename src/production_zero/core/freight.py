from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from production_zero.core.freight_statistics import FreightDeliveryStatistics

from production_zero.core.modifiers import research_multiplier
from production_zero.core.production_pause import freight_slot_paused
from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.cards import CardInstance
from production_zero.core.definitions import CardDefinition, FreightDefinition


DEFAULT_FREIGHT_SLOT_COUNT = 3
FREIGHT_LINE_CAPACITY = 8
FREIGHT_FACILITY_START_SLOTS: dict[str, int] = {
    "garage_depot": 3,
    "rail_station": 2,
    "harbor": 2,
    "airport": 2,
}
FREIGHT_FACILITY_EXPANSION_SLOTS: dict[str, tuple[int, int, int]] = {
    "garage_depot": (2, 2, 1),
    "rail_station": (2, 2, 2),
    "harbor": (1, 1, 1),
    "airport": (1, 1, 1),
}
MAX_FREIGHT_FACILITY_EXPANSIONS = 3
OUTBOUND_FREIGHT_DESTINATIONS = {"market", "contract", "consortium"}
FREIGHT_FACILITY_TYPES: dict[str, str] = {
    "garage_depot": "Garage",
    "rail_station": "Rail Depot",
    "harbor": "Seaport",
    "airport": "Air Terminal",
}
# Compatibility name; all quotes share the central P7 schedule.
from production_zero.core.infrastructure_prices import FREIGHT_BUILD_BASES
FREIGHT_FACILITY_BUILD_BASE_COSTS = FREIGHT_BUILD_BASES


@dataclass(slots=True)
class FreightSlot:
    index: int
    card_id: str | None = None


@dataclass(slots=True)
class FreightFacility:
    facility_id: str
    name: str
    facility_type: str = "garage_depot"
    slot_count: int = DEFAULT_FREIGHT_SLOT_COUNT
    expansion_level: int = 0
    slots: list[FreightSlot] = field(default_factory=list)
    building_investment: float = 0.0
    paused: bool = False
    paused_lines: set[int] = field(default_factory=set)
    line_capacity: int = 0
    purchased_slot_indexes: set[int] | None = None
    expansion_tier: int = 1

    def __post_init__(self) -> None:
        from math import isfinite
        if not isfinite(self.building_investment) or self.building_investment < 0:
            raise ValueError("Invalid freight building investment.")
        if type(self.expansion_tier) is not int or self.expansion_tier < 1:
            raise ValueError("Invalid freight expansion tier.")
        if self.facility_type not in FREIGHT_FACILITY_TYPES and self.facility_id in FREIGHT_FACILITY_TYPES:
            self.facility_type = self.facility_id
        if not self.line_capacity:
            self.line_capacity = FREIGHT_LINE_CAPACITY
        if type(self.line_capacity) is not int or self.line_capacity < 1:
            raise ValueError("Invalid freight line capacity.")
        if not self.slots:
            self.slots = [FreightSlot(index=index) for index in range(self.slot_count)]
        if self.purchased_slot_indexes is not None and any(type(i) is not int or i<0 or i>=len(self.slots) for i in self.purchased_slot_indexes):
            raise ValueError('Invalid purchased freight slots.')
        if self.purchased_slot_indexes is not None and any(slot.card_id and slot.index not in self.purchased_slot_indexes for slot in self.slots):
            raise ValueError('A vehicle occupies an unpurchased freight slot.')
        if self.purchased_slot_indexes is not None and len(self.purchased_slot_indexes)==len(self.slots):
            self.purchased_slot_indexes=None

    def unlocked_slot_indexes(self) -> set[int] | range:
        return range(len(self.slots)) if self.purchased_slot_indexes is None else self.purchased_slot_indexes


@dataclass(slots=True)
class OutboundFreightShipment:
    shipment_id: str
    destination_kind: str
    target_id: str | None = None
    resource_id: str | None = None
    quantity: float = 0.0
    freight_card_id: str | None = None
    freight_definition_id: str | None = None
    freight_type: str | None = None
    transport_capacity: float = 0.0
    transport_time_seconds: float = 0.0
    remaining_seconds: float = 0.0
    market_price: float = 0.0
    active: bool = True
    source_facility_id: str | None = None
    economic_processed: bool = False
    contract_allocations: dict[str, float] = field(default_factory=dict)
    cancelled_contract_prices: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
            raise ValueError(f"Unsupported outbound freight destination: {self.destination_kind}")
        from math import fsum, isclose, isfinite
        if self.contract_allocations:
            if (self.destination_kind != 'contract'
                or any(not isinstance(k, str) or not k or not isfinite(v) or v <= 0 for k, v in self.contract_allocations.items())
                or not isclose(fsum(self.contract_allocations.values()), self.quantity, rel_tol=1e-12, abs_tol=1e-9)):
                raise ValueError('Invalid reserved Contract cargo allocation.')
        if any(k not in self.contract_allocations or not isfinite(v) or v < 0 for k, v in self.cancelled_contract_prices.items()):
            raise ValueError('Invalid cancelled Contract sale quote.')


def contract_shipment_allocations(shipment):
    if shipment.destination_kind != 'contract':
        return {}
    return shipment.contract_allocations or ({shipment.target_id: shipment.quantity} if shipment.target_id else {})


@dataclass(frozen=True, slots=True)
class MarketDeliveryResolution:
    delivery_id: int
    shipment_id: str
    resource_id: str
    delivered_amount: float
    contract_amount: float
    market_amount: float
    market_price: float
    market_earnings: float

    def __post_init__(self) -> None:
        allocated = self.contract_amount + self.market_amount
        if allocated - self.delivered_amount > 0.000001:
            raise ValueError("Market delivery allocation exceeds delivered amount.")


@dataclass(slots=True)
class FreightAssignment:
    resource_id: str
    destination_kind: str

    def __post_init__(self) -> None:
        if self.destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
            raise ValueError(f"Unsupported outbound freight destination: {self.destination_kind}")


@dataclass(slots=True)
class FreightState:
    facilities: dict[str, FreightFacility] = field(default_factory=dict)
    outbound_shipments: dict[str, OutboundFreightShipment] = field(default_factory=dict)
    assignments: dict[str, FreightAssignment] = field(default_factory=dict)
    completed_market_deliveries: deque[MarketDeliveryResolution] = field(default_factory=lambda: deque(maxlen=512))
    next_shipment_sequence: int = 0
    next_market_delivery_sequence: int = 0
    delivery_statistics: FreightDeliveryStatistics = field(default_factory=FreightDeliveryStatistics)

    def __post_init__(self) -> None:
        ensure_initial_freight_facility(self)


@dataclass(frozen=True, slots=True)
class FreightCardStats:
    capacity: float
    transport_time_seconds: float

    @property
    def capacity_per_cycle(self) -> float:
        """Full-load sustainable capacity; actual dispatch is simulation-tick quantized."""
        return self.capacity * ECONOMIC_CYCLE_SECONDS / self.transport_time_seconds


def ensure_initial_freight_facility(freight: FreightState) -> None:
    if freight.facilities:
        return
    freight.facilities["garage-1"] = FreightFacility(
        facility_id="garage-1",
        facility_type="garage_depot",
        name="Garage 1",
    )


def freight_facility_build_cost(freight: FreightState, facility_type: str) -> float:
    if facility_type not in FREIGHT_FACILITY_TYPES:
        raise ValueError(f"Unknown freight facility type: {facility_type}")
    existing_same_type = sum(1 for facility in freight.facilities.values() if facility.facility_type == facility_type)
    from production_zero.core.infrastructure_prices import FREIGHT_BUILD_BASES, check_quote
    return check_quote(FREIGHT_BUILD_BASES[facility_type] * (1 + existing_same_type) ** 2)


def freight_facility_expansion_cost(facility: FreightFacility, *, preview_offset: int = 0, slot_index: int | None = None) -> float:
    from production_zero.core.infrastructure_prices import FREIGHT_LINE_BASE, FREIGHT_SLOT_BASE, scaled_expansion_price
    purchased=facility.unlocked_slot_indexes()
    if slot_index is None:
        slot_index=next((i for i in range(len(facility.slots)) if i not in purchased),len(facility.slots))+preview_offset
    if type(slot_index) is not int or slot_index<0:
        raise ValueError('Invalid freight expansion target.')
    line,pos=divmod(slot_index,facility.line_capacity)
    if line and pos==0:
        base = max(FREIGHT_LINE_BASE, FREIGHT_SLOT_BASE * facility.line_capacity)
        return scaled_expansion_price(base * line ** 2, facility.expansion_tier)
    start=FREIGHT_FACILITY_START_SLOTS[facility.facility_type] if line==0 else 1
    if pos+1<=start:
        raise ValueError('Starting freight slot is already available.')
    return scaled_expansion_price(FREIGHT_SLOT_BASE*(pos+1-start), facility.expansion_tier)


def plan_freight_moves(state, definitions, card_ids, facility_id, slot_indexes, *, expected_origins=None):
    from production_zero.core.machine_operations import plan_slot_permutation
    return plan_slot_permutation(state, card_ids, 'freight', facility_id, slot_indexes,
                                 definitions=definitions, expected_origins=expected_origins)


def validate_freight_move(state, definitions, card_id, facility_id, slot_index):
    # Preserve the old validation API; the shared planner checks reverse moves.
    plan_freight_moves(state, definitions, (card_id,), facility_id, (slot_index,))
    origin = next(slot for unit in state.freight.facilities.values() for slot in unit.slots if slot.card_id == card_id)
    target = next(slot for slot in state.freight.facilities[facility_id].slots if slot.index == slot_index)
    return origin, target


def move_freight_vehicle(state, definitions, card_id, facility_id, slot_index):
    from production_zero.core.machine_operations import commit_slot_permutation
    commit_slot_permutation(plan_freight_moves(state, definitions, (card_id,), facility_id, (slot_index,)))


def _freight_facility_unlockable_slot_count(facility_type: str) -> int:
    return sum(FREIGHT_FACILITY_EXPANSION_SLOTS.get(facility_type, (1, 1, 1)))


def _freight_facility_unlocked_extra_slots(facility: FreightFacility) -> int:
    start_slots = FREIGHT_FACILITY_START_SLOTS.get(facility.facility_type, DEFAULT_FREIGHT_SLOT_COUNT)
    return max(0, len(facility.unlocked_slot_indexes()) - start_slots)


def next_freight_facility_id(freight: FreightState, facility_type: str) -> str:
    base = {"garage_depot": "garage", "rail_station": "rail_station", "harbor": "harbor", "airport": "airport"}[facility_type]
    next_number = sum(1 for facility in freight.facilities.values() if facility.facility_type == facility_type) + 1
    facility_id = f"{base}-{next_number}"
    retained = freight.delivery_statistics.retained_facility_ids()
    retained.update(s.source_facility_id for s in freight.outbound_shipments.values() if s.source_facility_id)
    while facility_id in freight.facilities or facility_id in retained:
        next_number += 1
        facility_id = f"{base}-{next_number}"
    return facility_id


def prepare_freight_facility(freight: FreightState, facility_type: str) -> FreightFacility:
    if facility_type not in FREIGHT_FACILITY_TYPES:
        raise ValueError(f"Unknown freight facility type: {facility_type}")
    facility_id = next_freight_facility_id(freight, facility_type)
    name = f"{FREIGHT_FACILITY_TYPES[facility_type]} {sum(1 for facility in freight.facilities.values() if facility.facility_type == facility_type) + 1}"
    facility = FreightFacility(
        facility_id=facility_id,
        facility_type=facility_type,
        name=name,
        slot_count=FREIGHT_FACILITY_START_SLOTS[facility_type],
    )
    return facility


def build_freight_facility(freight: FreightState, facility_type: str) -> FreightFacility:
    facility=prepare_freight_facility(freight,facility_type)
    freight.facilities[facility.facility_id]=facility
    return facility


def validate_freight_expansion(facility: FreightFacility, slot_index: int | None = None) -> int:
    purchased=facility.unlocked_slot_indexes()
    if slot_index is None:slot_index=next((i for i in range(len(facility.slots)) if i not in purchased),len(facility.slots))
    if type(slot_index) is not int or slot_index<0 or slot_index in purchased:
        raise ValueError('Choose an unpurchased freight slot.')
    line,pos=divmod(slot_index,facility.line_capacity)
    if line and (line-1)*facility.line_capacity not in purchased:
        raise ValueError('Buy the preceding freight line first.')
    if line and pos == 0 and any(i not in purchased for i in range(slot_index)):
        raise ValueError('Complete all slots in the previous freight lines first.')
    if pos and line*facility.line_capacity not in purchased:
        raise ValueError('Buy the freight line before its additional slots.')
    if pos and any(i not in purchased for i in range(line * facility.line_capacity, slot_index)):
        raise ValueError('Unlock the preceding freight slots first.')
    freight_facility_expansion_cost(facility,slot_index=slot_index)
    return slot_index


def freight_expansion_problem(facility, slot_index):
    try:
        validate_freight_expansion(facility, slot_index)
    except ValueError as error:
        return str(error)
    return ''


def expand_freight_facility(facility: FreightFacility, slot_index: int | None = None) -> FreightSlot:
    slot_index=validate_freight_expansion(facility,slot_index)
    purchased=facility.unlocked_slot_indexes()
    # All validation precedes structural changes; skipped positions stay locked.
    facility.slots.extend(FreightSlot(index=i) for i in range(len(facility.slots),slot_index+1))
    slot=facility.slots[slot_index]
    owned=set(purchased)|{slot_index}
    facility.purchased_slot_indexes=owned if len(owned)!=len(facility.slots) else None
    facility.slot_count = len(facility.slots)
    facility.expansion_level = len(owned)-FREIGHT_FACILITY_START_SLOTS[facility.facility_type]
    return slot


def freight_stats(card: CardInstance, definition: FreightDefinition, research=None) -> FreightCardStats:
    return FreightCardStats(
        capacity=definition.base_capacity * card.output_multiplier * research_multiplier(research, "freight_capacity"),
        transport_time_seconds=definition.base_transport_time_seconds * freight_transport_time_multiplier(card),
    )


def freight_transport_time_multiplier(card: CardInstance) -> float:
    return 1.0 + card.output_bonus_percent * 0.5 / 100.0


def total_facility_capacity(
    freight: FreightState,
    facility_id: str,
    cards: dict[str, CardInstance],
    definitions: dict[str, CardDefinition],
) -> float:
    facility = freight.facilities[facility_id]
    total = 0.0
    for slot in facility.slots:
        if slot.card_id is None or slot.card_id not in cards:
            continue
        card = cards[slot.card_id]
        definition = definitions.get(card.definition_id)
        if isinstance(definition, FreightDefinition) and definition.facility_id == facility.facility_type:
            total += freight_stats(card, definition).capacity
    return total


class _FreightDispatchIndex:
    """One synchronous dispatch batch, rebuilt after arrivals on every step.

    Placement, pause and research are stable during this batch. New departures
    update busy immediately. Nothing is retained in the game state or engine.
    """
    def __init__(self, freight):
        self.busy = {s.freight_card_id for s in freight.outbound_shipments.values() if s.active}
        self.placements = tuple((freight.facilities[fid], slot)
                                for fid in sorted(freight.facilities)
                                for slot in sorted(freight.facilities[fid].slots, key=lambda s: s.index))
        self.ordered_card_ids = tuple(slot.card_id for _, slot in self.placements if slot.card_id is not None)
        self.origins, self.installed_types, self.paused = {}, {}, set()
        self._stats = {}
        unlocked = {id(facility): facility.unlocked_slot_indexes() for facility in freight.facilities.values()}
        for facility, slot in self.placements:
            cid = slot.card_id
            if cid is None or cid in self.busy:
                continue
            # Duplicate placement has no unambiguous origin, even in one hall.
            self.origins[cid] = None if cid in self.origins else facility.facility_id
            if freight_slot_paused(facility, slot.index):
                self.paused.add(cid)
            if slot.index in unlocked[id(facility)]:
                self.installed_types.setdefault(cid, set()).add(facility.facility_type)

    def stats(self, card, definition, research):
        if card.card_id not in self._stats:
            self._stats[card.card_id] = freight_stats(card, definition, research)
        return self._stats[card.card_id]


def start_outbound_shipments(
    freight: FreightState,
    cards: dict[str, CardInstance],
    definitions: dict[str, CardDefinition],
    *,
    destination_kind: str,
    resource_id: str,
    quantity: float,
    target_id: str | None = None,
    market_price: float = 0.0,
    research=None,
) -> tuple[OutboundFreightShipment, ...]:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    if quantity <= 0:
        return ()

    remaining = quantity
    shipments: list[OutboundFreightShipment] = []
    dispatch_index = _FreightDispatchIndex(freight)
    for card_id, definition in _available_freight_cards(freight, cards, definitions, resource_id, destination_kind, _dispatch_index=dispatch_index):
        card = cards[card_id]
        stats = freight_stats(card, definition, research)
        shipped = min(remaining, stats.capacity)
        if shipped <= 0:
            continue
        shipment_id = f"outbound-{freight.next_shipment_sequence}"
        freight.next_shipment_sequence += 1
        shipment = OutboundFreightShipment(
            shipment_id=shipment_id,
            destination_kind=destination_kind,
            target_id=target_id,
            resource_id=resource_id,
            quantity=shipped,
            freight_card_id=card_id,
            freight_definition_id=definition.definition_id,
            freight_type=definition.family.value,
            transport_capacity=stats.capacity,
            transport_time_seconds=stats.transport_time_seconds,
            remaining_seconds=stats.transport_time_seconds,
            market_price=market_price,
            active=True,
            source_facility_id=dispatch_index.origins.get(card_id),
        )
        freight.outbound_shipments[shipment_id] = shipment
        shipments.append(shipment)
        remaining -= shipped
        if remaining <= 0:
            break

    if not shipments:
        raise ValueError("No outbound freight capacity available.")
    return tuple(shipments)


def start_outbound_shipment_for_card(
    freight: FreightState,
    cards: dict[str, CardInstance],
    definitions: dict[str, CardDefinition],
    *,
    card_id: str,
    destination_kind: str,
    resource_id: str,
    quantity: float,
    target_id: str | None = None,
    market_price: float = 0.0,
    research=None,
    contract_allocations=None,
    _dispatch_index=None,
) -> OutboundFreightShipment | None:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    if quantity <= 0 or (card_id in _dispatch_index.busy if _dispatch_index is not None else is_freight_card_busy(freight, card_id)):
        return None
    assignment = freight.assignments.get(card_id)
    if assignment is None or assignment.resource_id != resource_id or assignment.destination_kind != destination_kind:
        return None
    card = cards.get(card_id)
    definition = definitions.get(card.definition_id) if card is not None else None
    if card is None or card.paused or not isinstance(definition, FreightDefinition):
        return None
    if (card_id in _dispatch_index.paused if _dispatch_index is not None else
        any(freight_slot_paused(facility, slot.index) for facility in freight.facilities.values() for slot in facility.slots if slot.card_id == card_id)):
        return None
    if not (definition.facility_id in _dispatch_index.installed_types.get(card_id, ()) if _dispatch_index is not None else
            _is_card_installed_in_matching_facility(freight, card_id, definition)):
        return None
    stats = _dispatch_index.stats(card, definition, research) if _dispatch_index is not None else freight_stats(card, definition, research)
    shipped = min(quantity, stats.capacity)
    if shipped <= 0:
        return None
    shipment_id = f"outbound-{freight.next_shipment_sequence}"
    shipment = OutboundFreightShipment(
        shipment_id=shipment_id,
        destination_kind=destination_kind,
        target_id=target_id,
        resource_id=resource_id,
        quantity=shipped,
        freight_card_id=card_id,
        freight_definition_id=definition.definition_id,
        freight_type=definition.family.value,
        transport_capacity=stats.capacity,
        transport_time_seconds=stats.transport_time_seconds,
        remaining_seconds=stats.transport_time_seconds,
        market_price=market_price,
        active=True,
        source_facility_id=_dispatch_index.origins.get(card_id) if _dispatch_index is not None else freight_card_facility_id(freight, card_id),
        contract_allocations=dict(contract_allocations or {}),
    )
    freight.next_shipment_sequence += 1
    freight.outbound_shipments[shipment_id] = shipment
    if _dispatch_index is not None:
        _dispatch_index.busy.add(card_id)
    return shipment


def advance_outbound_shipments(
    freight: FreightState,
    elapsed_seconds: float,
    shipment_ids: set[str] | None = None,
) -> tuple[OutboundFreightShipment, ...]:
    completed: list[OutboundFreightShipment] = []
    target_ids = shipment_ids if shipment_ids is not None else set(freight.outbound_shipments)
    for shipment_id in sorted(target_ids):
        shipment = freight.outbound_shipments.get(shipment_id)
        if shipment is None or not shipment.active:
            continue
        shipment.remaining_seconds = max(0.0, shipment.remaining_seconds - elapsed_seconds)
        if shipment.remaining_seconds > 0:
            continue
        shipment.active = False
        completed.append(shipment)
        freight.outbound_shipments.pop(shipment_id, None)
    return tuple(completed)


def freight_card_facility_id(freight: FreightState, card_id: str | None) -> str | None:
    """Resolve a legacy origin only when placement is unambiguous."""
    if card_id is None:
        return None
    owners = [facility.facility_id for facility in freight.facilities.values()
              for slot in facility.slots if slot.card_id == card_id]
    return owners[0] if len(owners) == 1 else None


def is_freight_card_busy(freight: FreightState, card_id: str) -> bool:
    return any(
        shipment.active and shipment.freight_card_id == card_id
        for shipment in freight.outbound_shipments.values()
    )


def assign_freight_card(
    freight: FreightState,
    card_id: str,
    resource_id: str,
    destination_kind: str,
) -> None:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    freight.assignments[card_id] = FreightAssignment(
        resource_id=resource_id,
        destination_kind=destination_kind,
    )


def cancel_freight_card_assignment(freight: FreightState, card_id: str) -> tuple[OutboundFreightShipment, ...]:
    # Cargo has already left storage. Clearing the next route must never
    # destroy an in-flight shipment or change its reserved destination.
    freight.assignments.pop(card_id, None)
    return ()


def _available_freight_cards(
    freight: FreightState,
    cards: dict[str, CardInstance],
    definitions: dict[str, CardDefinition],
    resource_id: str,
    destination_kind: str,
    *, _dispatch_index=None,
) -> tuple[tuple[str, FreightDefinition], ...]:
    index = _dispatch_index if _dispatch_index is not None else _FreightDispatchIndex(freight)
    busy = index.busy
    available: list[tuple[str, FreightDefinition]] = []
    for facility, slot in index.placements:
        if slot.index not in facility.unlocked_slot_indexes() or slot.card_id is None or slot.card_id in busy or slot.card_id not in cards:
            continue
        assignment = freight.assignments.get(slot.card_id)
        if assignment is None:
            continue
        if assignment.resource_id != resource_id or assignment.destination_kind != destination_kind:
            continue
        card = cards[slot.card_id]
        if card.paused or freight_slot_paused(facility, slot.index):
            continue
        definition = definitions.get(card.definition_id)
        if isinstance(definition, FreightDefinition) and definition.facility_id == facility.facility_type:
            available.append((slot.card_id, definition))
    return tuple(available)


def _is_card_installed_in_matching_facility(
    freight: FreightState,
    card_id: str,
    definition: FreightDefinition,
) -> bool:
    return any(
        slot.card_id == card_id and slot.index in facility.unlocked_slot_indexes() and definition.facility_id == facility.facility_type
        for facility in freight.facilities.values()
        for slot in facility.slots
    )
