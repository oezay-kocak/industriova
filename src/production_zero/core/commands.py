from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from production_zero.core.cards import CardInstance
from production_zero.core.contracts import accept_contract, deliver_available_to_contract
from production_zero.core.crafting import craft_rarity_card
from production_zero.core.definitions import CardDefinition, FreightDefinition
from production_zero.core.economy import hall_purchase_price
from production_zero.core.enums import CardKind
from production_zero.core.freight import (
    assign_freight_card,
    build_freight_facility,
    cancel_freight_card_assignment,
    expand_freight_facility,
    freight_facility_build_cost,
    freight_facility_expansion_cost,
    is_freight_card_busy,
    start_outbound_shipments,
    update_freight_reserve,
)
from production_zero.core.market import market_price_for
from production_zero.core.mk_upgrades import upgrade_mk_card
from production_zero.core.packs import grant_pack, open_pack
from production_zero.core.recycling import recycle_cards
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import (
    FactoryHall,
    GameState,
    MAX_FACTORY_LINES,
    MAX_FACTORY_SLOTS_PER_LINE,
    START_FACTORY_SLOTS_PER_LINE,
    next_factory_slot_index,
    factory_slot_unlock_cost,
)
from production_zero.core.storage_upgrades import (
    MAX_INVENTORY_STORAGE_LEVEL,
    apply_inventory_storage_level,
    inventory_storage_upgrade_cost,
)
from production_zero.core.supply import buy_common_supply_card, buy_daily_freight_supply_card, buy_daily_machine_supply_card, buy_daily_uncommon_supply_card


class Command(Protocol):
    def apply(self, state: GameState) -> None:
        """Apply a state transition."""


@dataclass(frozen=True, slots=True)
class AddCard:
    card: CardInstance

    def apply(self, state: GameState) -> None:
        if self.card.card_id in state.cards:
            raise ValueError(f"Card already exists: {self.card.card_id}")
        state.cards[self.card.card_id] = self.card


@dataclass(frozen=True, slots=True)
class BuildHall:
    hall: FactoryHall

    def apply(self, state: GameState) -> None:
        if self.hall.hall_id in state.halls:
            raise ValueError(f"Hall already exists: {self.hall.hall_id}")
        state.halls[self.hall.hall_id] = self.hall


@dataclass(frozen=True, slots=True)
class PurchaseHall:
    slot_count: int = 6

    def apply(self, state: GameState) -> None:
        if self.slot_count <= 0:
            raise ValueError("Hall slot count must be positive.")
        cost = hall_purchase_price(len(state.halls))
        state.cash.spend(cost)
        next_number = len(state.halls) + 1
        hall_id = f"hall-{next_number}"
        while hall_id in state.halls:
            next_number += 1
            hall_id = f"hall-{next_number}"
        state.halls[hall_id] = FactoryHall(
            hall_id=hall_id,
            name=f"Hall {next_number}",
            slot_count=self.slot_count,
        )
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class RenameHall:
    hall_id: str
    name: str

    def apply(self, state: GameState) -> None:
        cleaned = self.name.strip()
        if not cleaned:
            raise ValueError("Hall name cannot be empty.")
        state.halls[self.hall_id].name = cleaned


@dataclass(frozen=True, slots=True)
class AddCash:
    amount: float

    def apply(self, state: GameState) -> None:
        state.cash.add(self.amount)


@dataclass(frozen=True, slots=True)
class SetCash:
    amount: float

    def apply(self, state: GameState) -> None:
        if self.amount < 0:
            raise ValueError("Cash cannot be negative.")
        state.cash.amount = self.amount
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class SpendCash:
    amount: float

    def apply(self, state: GameState) -> None:
        state.cash.spend(self.amount)


@dataclass(frozen=True, slots=True)
class AddIndustrialScrap:
    amount: int

    def apply(self, state: GameState) -> None:
        state.scrap.add(self.amount)
        state.history.append("industrial_scrap", state.scrap.amount)


@dataclass(frozen=True, slots=True)
class SetResourceCapacity:
    resource_id: str
    capacity: float

    def apply(self, state: GameState) -> None:
        if self.capacity < 0:
            raise ValueError("Resource capacity cannot be negative.")
        stock = state.ensure_resource(self.resource_id)
        stock.capacity = self.capacity
        stock.amount = min(stock.amount, stock.capacity)


@dataclass(frozen=True, slots=True)
class AddResource:
    resource_id: str
    amount: float

    def apply(self, state: GameState) -> None:
        state.ensure_resource(self.resource_id).add(self.amount)


@dataclass(frozen=True, slots=True)
class ExpandInventoryStorage:
    resource_definitions: dict[str, ResourceDefinition]

    def apply(self, state: GameState) -> None:
        if state.inventory_storage_level >= MAX_INVENTORY_STORAGE_LEVEL:
            raise ValueError("Inventory storage is already at maximum level.")
        cost = inventory_storage_upgrade_cost(state.inventory_storage_level)
        state.cash.spend(cost)
        state.inventory_storage_level += 1
        apply_inventory_storage_level(state, self.resource_definitions)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class ConsumeResource:
    resource_id: str
    amount: float

    def apply(self, state: GameState) -> None:
        state.ensure_resource(self.resource_id).consume(self.amount)


@dataclass(frozen=True, slots=True)
class SellResource:
    resource_id: str
    amount: float
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        if self.amount < 0:
            raise ValueError("Cannot sell a negative resource amount.")
        price = market_price_for(state.market, self.resource_id)
        if price <= 0:
            raise ValueError(f"Resource cannot be sold: {self.resource_id}")
        stock = state.ensure_resource(self.resource_id)
        if self.amount > stock.amount:
            raise ValueError("Cannot consume more resources than available.")
        shipments = start_outbound_shipments(
            state.freight,
            state.cards,
            self.definitions,
            destination_kind="market",
            resource_id=self.resource_id,
            quantity=self.amount,
            market_price=price,
        )
        shipped = sum(shipment.quantity for shipment in shipments)
        stock.consume(shipped)
        state.history.append(f"resource.{self.resource_id}", stock.amount)


@dataclass(frozen=True, slots=True)
class ConfigureAutoSell:
    resource_id: str
    enabled: bool
    threshold_percent: float

    def apply(self, state: GameState) -> None:
        if self.threshold_percent < 0 or self.threshold_percent > 100:
            raise ValueError("Auto-sell threshold must be between 0 and 100 percent.")
        if market_price_for(state.market, self.resource_id) <= 0:
            raise ValueError(f"Resource cannot be auto-sold: {self.resource_id}")
        setting = state.ensure_auto_sell_setting(self.resource_id)
        setting.enabled = self.enabled
        setting.threshold_percent = self.threshold_percent


@dataclass(frozen=True, slots=True)
class AcceptContract:
    kind: str
    contract_id: str

    def apply(self, state: GameState) -> None:
        accept_contract(state, self.kind, self.contract_id)


@dataclass(frozen=True, slots=True)
class DeliverAvailableToContract:
    kind: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        deliver_available_to_contract(state, self.kind, self.definitions)


@dataclass(frozen=True, slots=True)
class BuyCommonSupplyCard:
    definition_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        buy_common_supply_card(state, self.definitions, self.definition_id)


@dataclass(frozen=True, slots=True)
class BuyDailyUncommonSupplyCard:
    offer_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        buy_daily_uncommon_supply_card(state, self.definitions, self.offer_id)


@dataclass(frozen=True, slots=True)
class BuyDailyFreightSupplyCard:
    offer_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        buy_daily_freight_supply_card(state, self.definitions, self.offer_id)


@dataclass(frozen=True, slots=True)
class BuyDailyMachineSupplyCard:
    offer_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        buy_daily_machine_supply_card(state, self.definitions, self.offer_id)


@dataclass(frozen=True, slots=True)
class GrantPack:
    pack_type: str
    source: str = "dev"

    def apply(self, state: GameState) -> None:
        grant_pack(state, self.pack_type, self.source)


@dataclass(frozen=True, slots=True)
class OpenPack:
    pack_id: str
    definitions: dict[str, CardDefinition]
    category_id: str = "general"

    def apply(self, state: GameState) -> None:
        open_pack(state, self.definitions, self.pack_id, self.category_id)


@dataclass(frozen=True, slots=True)
class RecycleCards:
    card_ids: tuple[str, ...]

    def apply(self, state: GameState) -> None:
        recycle_cards(state, self.card_ids)


@dataclass(frozen=True, slots=True)
class CraftRarityCard:
    material_card_ids: tuple[str, ...]
    target_definition_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        craft_rarity_card(state, self.definitions, self.material_card_ids, self.target_definition_id)


@dataclass(frozen=True, slots=True)
class UpgradeCardMk:
    card_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        upgrade_mk_card(state, self.definitions, self.card_id)


@dataclass(frozen=True, slots=True)
class SelectMachineProduction:
    card_id: str
    production_id: str
    target_resource_id: str

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.cards:
            raise ValueError(f"Unknown card: {self.card_id}")
        machine_state = state.ensure_machine_production(
            self.card_id,
            self.target_resource_id,
            self.production_id,
        )
        if (
            machine_state.selected_production_id != self.production_id
            or machine_state.target_resource_id != self.target_resource_id
        ):
            machine_state.progress_seconds = 0.0
        machine_state.selected_production_id = self.production_id
        machine_state.target_resource_id = self.target_resource_id


@dataclass(frozen=True, slots=True)
class RecordMetric:
    metric_id: str
    value: float

    def apply(self, state: GameState) -> None:
        state.history.append(self.metric_id, self.value)


@dataclass(frozen=True, slots=True)
class UnlockProductionLine:
    hall_id: str
    line_id: str

    def apply(self, state: GameState) -> None:
        hall = state.halls[self.hall_id]
        line = next((line for line in hall.production_lines if line.line_id == self.line_id), None)
        if line is None:
            raise ValueError(f"Unknown production line: {self.line_id}")
        if line.unlocked:
            raise ValueError(f"Production line is already unlocked: {self.line_id}")
        state.cash.spend(line.unlock_cost)
        line.unlocked = True
        line.slot_indexes = []
        for _ in range(START_FACTORY_SLOTS_PER_LINE):
            line.slot_indexes.append(next_factory_slot_index(hall))
        hall.slot_count = sum(len(existing.slot_indexes) for existing in hall.production_lines if existing.unlocked)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class UnlockProductionSlot:
    hall_id: str
    line_id: str

    def apply(self, state: GameState) -> None:
        hall = state.halls[self.hall_id]
        line = next((line for line in hall.production_lines if line.line_id == self.line_id), None)
        if line is None:
            raise ValueError(f"Unknown production line: {self.line_id}")
        if not line.unlocked:
            raise ValueError(f"Production line is locked: {self.line_id}")
        line_number = hall.production_lines.index(line) + 1
        if line_number < 1 or line_number > MAX_FACTORY_LINES:
            raise ValueError(f"Invalid production line: {self.line_id}")
        if len(line.slot_indexes) >= MAX_FACTORY_SLOTS_PER_LINE:
            raise ValueError(f"Production line already has maximum slots: {self.line_id}")
        next_slot_number = len(line.slot_indexes) + 1
        state.cash.spend(factory_slot_unlock_cost(line_number, next_slot_number))
        line.slot_indexes.append(next_factory_slot_index(hall))
        hall.slot_count = sum(len(existing.slot_indexes) for existing in hall.production_lines if existing.unlocked)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class InstallCardInHall:
    hall_id: str
    slot_index: int
    card_id: str

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.cards:
            raise ValueError(f"Unknown card: {self.card_id}")
        if state.cards[self.card_id].card_kind not in {CardKind.MACHINE, CardKind.ENERGY}:
            raise ValueError(f"Card cannot be installed in a hall slot: {self.card_id}")
        hall = state.halls[self.hall_id]
        if self.slot_index < 0 or self.slot_index >= len(hall.slots):
            raise IndexError(f"Invalid slot index: {self.slot_index}")
        if self.slot_index not in hall.unlocked_slot_indexes():
            raise ValueError(f"Slot is locked: {self.slot_index}")
        if hall.slots[self.slot_index].card_id is not None:
            raise ValueError(f"Slot already occupied: {self.slot_index}")
        hall.slots[self.slot_index].card_id = self.card_id


@dataclass(frozen=True, slots=True)
class RemoveCardFromHall:
    hall_id: str
    slot_index: int

    def apply(self, state: GameState) -> None:
        hall = state.halls[self.hall_id]
        if self.slot_index < 0 or self.slot_index >= len(hall.slots):
            raise IndexError(f"Invalid slot index: {self.slot_index}")
        if hall.slots[self.slot_index].card_id is None:
            raise ValueError(f"Slot is already empty: {self.slot_index}")
        card_id = hall.slots[self.slot_index].card_id
        hall.slots[self.slot_index].card_id = None
        state.machine_production.pop(card_id, None)


@dataclass(frozen=True, slots=True)
class InstallFreightCard:
    facility_id: str
    slot_index: int
    card_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.cards:
            raise ValueError(f"Unknown card: {self.card_id}")
        card = state.cards[self.card_id]
        definition = self.definitions.get(card.definition_id)
        if card.card_kind is not CardKind.FREIGHT or not isinstance(definition, FreightDefinition):
            raise ValueError(f"Card cannot be installed in a freight facility: {self.card_id}")
        if self.facility_id not in state.freight.facilities:
            raise ValueError(f"Unknown freight facility: {self.facility_id}")
        facility = state.freight.facilities[self.facility_id]
        if definition.facility_id != facility.facility_type:
            raise ValueError(f"Freight card requires facility: {definition.facility_id}")
        if self.slot_index < 0 or self.slot_index >= len(facility.slots):
            raise IndexError(f"Invalid freight slot index: {self.slot_index}")
        if facility.slots[self.slot_index].card_id is not None:
            raise ValueError(f"Freight slot already occupied: {self.slot_index}")
        if self.card_id in state.installed_card_ids() or self.card_id in state.installed_freight_card_ids():
            raise ValueError(f"Card is already installed: {self.card_id}")
        facility.slots[self.slot_index].card_id = self.card_id


@dataclass(frozen=True, slots=True)
class BuildFreightFacility:
    facility_type: str

    def apply(self, state: GameState) -> None:
        cost = freight_facility_build_cost(state.freight, self.facility_type)
        state.cash.spend(cost)
        build_freight_facility(state.freight, self.facility_type)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class ExpandFreightFacility:
    facility_id: str

    def apply(self, state: GameState) -> None:
        if self.facility_id not in state.freight.facilities:
            raise ValueError(f"Unknown freight facility: {self.facility_id}")
        facility = state.freight.facilities[self.facility_id]
        cost = freight_facility_expansion_cost(facility)
        state.cash.spend(cost)
        expand_freight_facility(facility)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class AssignFreightCard:
    card_id: str
    resource_id: str
    destination_kind: str
    reserve_percent: float = 100.0

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.installed_freight_card_ids():
            raise ValueError(f"Freight card is not installed: {self.card_id}")
        assign_freight_card(
            state.freight,
            self.card_id,
            self.resource_id,
            self.destination_kind,
            self.reserve_percent,
        )


@dataclass(frozen=True, slots=True)
class UpdateFreightReserve:
    card_id: str
    reserve_percent: float

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.installed_freight_card_ids():
            raise ValueError(f"Freight card is not installed: {self.card_id}")
        update_freight_reserve(state.freight, self.card_id, self.reserve_percent)


@dataclass(frozen=True, slots=True)
class CancelFreightCardAssignment:
    card_id: str

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.installed_freight_card_ids():
            raise ValueError(f"Freight card is not installed: {self.card_id}")
        cancel_freight_card_assignment(state.freight, self.card_id)


@dataclass(frozen=True, slots=True)
class RemoveFreightCard:
    facility_id: str
    slot_index: int

    def apply(self, state: GameState) -> None:
        facility = state.freight.facilities[self.facility_id]
        if self.slot_index < 0 or self.slot_index >= len(facility.slots):
            raise IndexError(f"Invalid freight slot index: {self.slot_index}")
        if facility.slots[self.slot_index].card_id is None:
            raise ValueError(f"Freight slot is already empty: {self.slot_index}")
        card_id = facility.slots[self.slot_index].card_id
        if is_freight_card_busy(state.freight, card_id):
            raise ValueError(f"Freight card is currently transporting a shipment: {card_id}")
        facility.slots[self.slot_index].card_id = None
        state.freight.assignments.pop(card_id, None)


class CommandBus:
    def __init__(self, state: GameState) -> None:
        self._state = state
        self._history: list[Command] = []

    @property
    def history(self) -> tuple[Command, ...]:
        return tuple(self._history)

    def dispatch(self, command: Command) -> None:
        command.apply(self._state)
        self._history.append(command)
