from __future__ import annotations

from dataclasses import dataclass, field

from production_zero.core.cards import CardInstance
from production_zero.core.definitions import CardDefinition, FreightDefinition


DEFAULT_FREIGHT_SLOT_COUNT = 3
FREIGHT_FACILITY_START_SLOTS: dict[str, int] = {
    "garage_depot": 3,
    "rail_station": 2,
    "harbor": 2,
    "airport": 2,
}
FREIGHT_FACILITY_EXPANSION_SLOTS: dict[str, tuple[int, int, int]] = {
    "garage_depot": (2, 2, 2),
    "rail_station": (2, 2, 2),
    "harbor": (1, 1, 1),
    "airport": (1, 1, 1),
}
MAX_FREIGHT_FACILITY_EXPANSIONS = 3
OUTBOUND_FREIGHT_DESTINATIONS = {"market", "contract"}
FREIGHT_FACILITY_TYPES: dict[str, str] = {
    "garage_depot": "Garage",
    "rail_station": "Rail Station",
    "harbor": "Harbor",
    "airport": "Airport",
}
FREIGHT_FACILITY_BUILD_BASE_COSTS: dict[str, float] = {
    "garage_depot": 500.0,
    "rail_station": 1_500.0,
    "harbor": 2_500.0,
    "airport": 3_500.0,
}
FREIGHT_FACILITY_BUILD_COST_STEP = 500.0
FREIGHT_FACILITY_EXPANSION_BASE_COST = 300.0
FREIGHT_FACILITY_EXPANSION_COST_STEP = 200.0


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

    def __post_init__(self) -> None:
        if self.facility_type not in FREIGHT_FACILITY_TYPES and self.facility_id in FREIGHT_FACILITY_TYPES:
            self.facility_type = self.facility_id
        if not self.slots:
            self.slots = [FreightSlot(index=index) for index in range(self.slot_count)]


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

    def __post_init__(self) -> None:
        if self.destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
            raise ValueError(f"Unsupported outbound freight destination: {self.destination_kind}")


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
    reserve_percent: float = 100.0

    def __post_init__(self) -> None:
        if self.destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
            raise ValueError(f"Unsupported outbound freight destination: {self.destination_kind}")
        self.reserve_percent = min(100.0, max(0.0, self.reserve_percent))


@dataclass(slots=True)
class FreightState:
    facilities: dict[str, FreightFacility] = field(default_factory=dict)
    outbound_shipments: dict[str, OutboundFreightShipment] = field(default_factory=dict)
    assignments: dict[str, FreightAssignment] = field(default_factory=dict)
    completed_market_deliveries: list[MarketDeliveryResolution] = field(default_factory=list)
    next_shipment_sequence: int = 0
    next_market_delivery_sequence: int = 0

    def __post_init__(self) -> None:
        ensure_initial_freight_facility(self)


@dataclass(frozen=True, slots=True)
class FreightCardStats:
    capacity: float
    transport_time_seconds: float


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
    return FREIGHT_FACILITY_BUILD_BASE_COSTS[facility_type] + existing_same_type * FREIGHT_FACILITY_BUILD_COST_STEP


def freight_facility_expansion_cost(facility: FreightFacility) -> float:
    unlocked_extra_slots = _freight_facility_unlocked_extra_slots(facility)
    if unlocked_extra_slots >= _freight_facility_unlockable_slot_count(facility.facility_type):
        raise ValueError(f"Freight facility already has maximum expansions: {facility.facility_id}")
    return FREIGHT_FACILITY_EXPANSION_BASE_COST + unlocked_extra_slots * FREIGHT_FACILITY_EXPANSION_COST_STEP


def _freight_facility_unlockable_slot_count(facility_type: str) -> int:
    return sum(FREIGHT_FACILITY_EXPANSION_SLOTS.get(facility_type, (1, 1, 1)))


def _freight_facility_unlocked_extra_slots(facility: FreightFacility) -> int:
    start_slots = FREIGHT_FACILITY_START_SLOTS.get(facility.facility_type, DEFAULT_FREIGHT_SLOT_COUNT)
    return max(0, len(facility.slots) - start_slots)


def next_freight_facility_id(freight: FreightState, facility_type: str) -> str:
    base = FREIGHT_FACILITY_TYPES[facility_type].lower().replace(" ", "_")
    next_number = sum(1 for facility in freight.facilities.values() if facility.facility_type == facility_type) + 1
    facility_id = f"{base}-{next_number}"
    while facility_id in freight.facilities:
        next_number += 1
        facility_id = f"{base}-{next_number}"
    return facility_id


def build_freight_facility(freight: FreightState, facility_type: str) -> FreightFacility:
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
    freight.facilities[facility_id] = facility
    return facility


def expand_freight_facility(facility: FreightFacility) -> FreightSlot:
    unlocked_extra_slots = _freight_facility_unlocked_extra_slots(facility)
    if unlocked_extra_slots >= _freight_facility_unlockable_slot_count(facility.facility_type):
        raise ValueError(f"Freight facility already has maximum expansions: {facility.facility_id}")
    slot = FreightSlot(index=len(facility.slots))
    facility.slots.append(slot)
    facility.slot_count = len(facility.slots)
    facility.expansion_level = _freight_facility_unlocked_extra_slots(facility)
    return slot


def freight_stats(card: CardInstance, definition: FreightDefinition) -> FreightCardStats:
    return FreightCardStats(
        capacity=definition.base_capacity * card.output_multiplier,
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
) -> tuple[OutboundFreightShipment, ...]:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    if quantity <= 0:
        return ()

    remaining = quantity
    shipments: list[OutboundFreightShipment] = []
    for card_id, definition in _available_freight_cards(freight, cards, definitions, resource_id, destination_kind):
        card = cards[card_id]
        stats = freight_stats(card, definition)
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
) -> OutboundFreightShipment | None:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    if quantity <= 0 or is_freight_card_busy(freight, card_id):
        return None
    assignment = freight.assignments.get(card_id)
    if assignment is None or assignment.resource_id != resource_id or assignment.destination_kind != destination_kind:
        return None
    card = cards.get(card_id)
    definition = definitions.get(card.definition_id) if card is not None else None
    if card is None or not isinstance(definition, FreightDefinition):
        return None
    if not _is_card_installed_in_matching_facility(freight, card_id, definition):
        return None
    stats = freight_stats(card, definition)
    shipped = min(quantity, stats.capacity)
    if shipped <= 0:
        return None
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
    )
    freight.outbound_shipments[shipment_id] = shipment
    return shipment


def advance_outbound_shipments(
    freight: FreightState,
    elapsed_seconds: float,
    shipment_ids: set[str] | None = None,
) -> tuple[OutboundFreightShipment, ...]:
    completed: list[OutboundFreightShipment] = []
    target_ids = shipment_ids if shipment_ids is not None else set(freight.outbound_shipments)
    for shipment_id in tuple(target_ids):
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
    reserve_percent: float = 100.0,
) -> None:
    if destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
        raise ValueError(f"Unsupported outbound freight destination: {destination_kind}")
    if is_freight_card_busy(freight, card_id):
        raise ValueError(f"Freight card is currently transporting a shipment: {card_id}")
    freight.assignments[card_id] = FreightAssignment(
        resource_id=resource_id,
        destination_kind=destination_kind,
        reserve_percent=reserve_percent,
    )


def update_freight_reserve(freight: FreightState, card_id: str, reserve_percent: float) -> None:
    assignment = freight.assignments.get(card_id)
    if assignment is None:
        raise ValueError(f"Freight card has no assignment: {card_id}")
    assignment.reserve_percent = min(100.0, max(0.0, reserve_percent))


def cancel_freight_card_assignment(freight: FreightState, card_id: str) -> tuple[OutboundFreightShipment, ...]:
    canceled: list[OutboundFreightShipment] = []
    for shipment_id, shipment in tuple(freight.outbound_shipments.items()):
        if shipment.active and shipment.freight_card_id == card_id:
            shipment.active = False
            canceled.append(shipment)
            freight.outbound_shipments.pop(shipment_id, None)
    freight.assignments.pop(card_id, None)
    return tuple(canceled)


def _available_freight_cards(
    freight: FreightState,
    cards: dict[str, CardInstance],
    definitions: dict[str, CardDefinition],
    resource_id: str,
    destination_kind: str,
) -> tuple[tuple[str, FreightDefinition], ...]:
    busy = {
        shipment.freight_card_id
        for shipment in freight.outbound_shipments.values()
        if shipment.active and shipment.freight_card_id is not None
    }
    available: list[tuple[str, FreightDefinition]] = []
    for facility_id in sorted(freight.facilities):
        facility = freight.facilities[facility_id]
        for slot in sorted(facility.slots, key=lambda item: item.index):
            if slot.card_id is None or slot.card_id in busy or slot.card_id not in cards:
                continue
            assignment = freight.assignments.get(slot.card_id)
            if assignment is None:
                continue
            if assignment.resource_id != resource_id or assignment.destination_kind != destination_kind:
                continue
            card = cards[slot.card_id]
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
        slot.card_id == card_id and definition.facility_id == facility.facility_type
        for facility in freight.facilities.values()
        for slot in facility.slots
    )
