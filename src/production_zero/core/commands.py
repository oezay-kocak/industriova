from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4
from typing import Protocol

from production_zero.core.cards import CardInstance
from production_zero.core.contracts import (accept_contract, cancel_contract, deliver_available_to_contract,
    set_contract_priority, set_regular_auto_repeat)
from production_zero.core.consortium import ConsortiumService
from production_zero.core.crafting import craft_rarity_card
from production_zero.core.definitions import CardDefinition, FreightDefinition
from production_zero.core.economy import hall_purchase_price
from production_zero.core.infrastructure_prices import (BOARD_LIMITS, RESOURCE_TYPES, check_quote, production_facility_price,
    unit_line_price, unit_slot_price, resource_retype_price, next_expansion_tier, record_expansion_tier)
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
)
from production_zero.core.market import market_price_for
from production_zero.core.modifiers import market_sale_price
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
from production_zero.core.supply import buy_common_supply_cards, buy_common_supply_card, buy_daily_freight_supply_card, buy_daily_machine_supply_card


class Command(Protocol):
    def apply(self, state: GameState) -> None:
        """Apply a state transition."""


@dataclass(frozen=True, slots=True)
class ReorderBuildings:
    kind: str
    ids: tuple[str, ...]

    def apply(self, state: GameState) -> None:
        from production_zero.core.building_order import reorder_buildings
        reorder_buildings(state, self.kind, self.ids)


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
    slot_count: int = 3
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        if type(self.slot_count) is not int or self.slot_count <= 0:
            raise ValueError("Hall slot count must be positive.")
        cost = check_quote(production_facility_price(state,'factory'),self.expected_cost)
        next_number = len(state.halls) + 1
        hall_id = f"hall-{next_number}"
        while hall_id in state.halls:
            next_number += 1
            hall_id = f"hall-{next_number}"
        prepared = FactoryHall(
            hall_id=hall_id,
            name=f"Hall {next_number}",
            slot_count=BOARD_LIMITS['factory'][2],
            max_lines=MAX_FACTORY_LINES,
            building_investment=cost,
            start_unlocked_lines=1,
            expansion_tier=next_expansion_tier(state, 'factory'),
        )
        state.cash.spend(cost)
        state.halls[hall_id]=prepared
        record_expansion_tier(state, 'factory', None, prepared.expansion_tier)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class PurchaseProductionUnit:
    board_kind: str
    unit_label: str
    unit_id_prefix: str
    max_lines: int
    max_slots_per_line: int
    start_unlocked_lines: int
    start_slots_per_line: int
    specialization: str | None = None
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        units = state.production_units(self.board_kind)
        if self.board_kind == "resources" and self.specialization not in {None, "machine.extractor", "machine.drilling", "machine.agriculture"}:
            raise ValueError("Unknown resource site specialization.")
        maximum,cap,start=BOARD_LIMITS[self.board_kind]
        if (self.max_lines,self.max_slots_per_line,self.start_slots_per_line)!=(maximum,cap,start):
            raise ValueError('Use the existing production area limits and starting slots.')
        cost = check_quote(production_facility_price(state,self.board_kind,self.specialization),self.expected_cost)
        next_number = len(units) + 1
        unit_id = f"{self.unit_id_prefix}-{next_number}"
        while unit_id in units:
            next_number += 1
            unit_id = f"{self.unit_id_prefix}-{next_number}"
        prepared = FactoryHall(
            hall_id=unit_id,
            name=f"{self.unit_label} {next_number}",
            slot_count=self.start_slots_per_line,
            board_kind=self.board_kind,
            building_investment=cost,
            specialization=(self.specialization or "machine.extractor") if self.board_kind == "resources" else None,
            max_lines=self.max_lines,
            max_slots_per_line=self.max_slots_per_line,
            start_unlocked_lines=1,
            start_slots_per_line=self.start_slots_per_line,
            expansion_tier=next_expansion_tier(state, self.board_kind, self.specialization),
        )
        state.cash.spend(cost)
        units[unit_id]=prepared
        record_expansion_tier(state, self.board_kind, self.specialization, prepared.expansion_tier)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class RenameHall:
    hall_id: str
    name: str
    board_kind: str = "legacy"
    specialization: str | None = None
    expected_cost: float | None = None
    expected_specialization: str | None = '__unspecified__'

    def apply(self, state: GameState) -> None:
        cleaned = self.name.strip()
        if not cleaned:
            raise ValueError("Hall name cannot be empty.")
        unit=_units_for_command(state,self.board_kind)[self.hall_id]
        if self.specialization is not None:
            raise ValueError('A building type is fixed at construction. Rename changes only its name.')
        check_quote(0.0,self.expected_cost)
        unit.name=cleaned


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
        if state.warehouse_capacity <= 0:
            state.warehouse_capacity = self.capacity


@dataclass(frozen=True, slots=True)
class AddResource:
    resource_id: str
    amount: float

    def apply(self, state: GameState) -> None:
        state.store_resource(self.resource_id, self.amount)


@dataclass(frozen=True, slots=True)
class ExpandInventoryStorage:
    resource_definitions: dict[str, ResourceDefinition]
    expected_level: int | None = None
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        if self.expected_level is not None and self.expected_level != state.inventory_storage_level:
            raise ValueError('Storage changed. Review the expansion quote again.')
        cost = inventory_storage_upgrade_cost(state.inventory_storage_level)
        check_quote(cost, self.expected_cost)
        from production_zero.core.storage_upgrades import next_storage_capacity
        next_storage_capacity(state, self.resource_definitions)
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
        price = market_sale_price(state, self.resource_id)
        if price <= 0:
            raise ValueError(f"Resource cannot be sold: {self.resource_id}")
        stock = state.ensure_resource(self.resource_id)
        if self.amount > stock.amount:
            raise ValueError("Cannot consume more resources than available.")
        shipments = start_outbound_shipments(
            state.freight,
            state.cards,
            self.definitions,
            research=state.research,
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
    definitions: dict[str, CardDefinition] | None = None
    selected_resource_id: str | None = None
    selected_resource_ids: tuple[str, ...] | None = None
    expected_reward: tuple[float, float] | None = None
    auto_repeat: bool = False

    def apply(self, state: GameState) -> None:
        accept_contract(
            state,
            self.kind,
            self.contract_id,
            self.definitions,
            self.selected_resource_id,
            self.selected_resource_ids,
            expected_reward=self.expected_reward,
            auto_repeat=self.auto_repeat,
        )


@dataclass(frozen=True, slots=True)
class SetContractPriority:
    kind: str
    priority: int

    def apply(self, state):
        set_contract_priority(state, self.kind, self.priority)


@dataclass(frozen=True, slots=True)
class SetRegularContractAutoRepeat:
    enabled: bool
    expected_contract_id: str | None = None

    def apply(self, state):
        set_regular_auto_repeat(state, self.enabled, expected_contract_id=self.expected_contract_id)


@dataclass(frozen=True, slots=True)
class CancelContract:
    kind: str
    definitions: dict[str, CardDefinition] | None = None

    def apply(self, state: GameState) -> None:
        cancel_contract(state, self.kind, self.definitions)


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
    quantity: int = 1
    expected_unit_price: float | None = None
    operation_id: str = field(default_factory=lambda: uuid4().hex)

    def apply(self, state: GameState) -> None:
        buy_common_supply_cards(state, self.definitions, self.definition_id, self.quantity,
                                expected_unit_price=self.expected_unit_price, operation_id=self.operation_id)




@dataclass(frozen=True, slots=True)
class BuyDailyFreightSupplyCard:
    offer_id: str
    definitions: dict[str, CardDefinition]
    expected_unit_price: float | None = None
    operation_id: str = field(default_factory=lambda: uuid4().hex)

    def apply(self, state: GameState) -> None:
        buy_daily_freight_supply_card(state, self.definitions, self.offer_id,
                                     expected_unit_price=self.expected_unit_price, operation_id=self.operation_id)


@dataclass(frozen=True, slots=True)
class BuyDailyMachineSupplyCard:
    offer_id: str
    definitions: dict[str, CardDefinition]
    expected_unit_price: float | None = None
    operation_id: str = field(default_factory=lambda: uuid4().hex)

    def apply(self, state: GameState) -> None:
        buy_daily_machine_supply_card(state, self.definitions, self.offer_id,
                                     expected_unit_price=self.expected_unit_price, operation_id=self.operation_id)


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
class SelectMachineProduction:
    card_id: str
    production_id: str
    target_resource_id: str

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.cards:
            raise ValueError(f"Unknown card: {self.card_id}")
        card = state.cards[self.card_id]
        if card.definition_id in {"machine.extractor", "machine.drilling", "machine.agriculture"}:
            from production_zero.data.definitions import primary_machine_type_for_resource
            expected_definition_id = {
                "extractor": "machine.extractor",
                "drilling": "machine.drilling",
                "agriculture": "machine.agriculture",
            }[primary_machine_type_for_resource(self.target_resource_id).value]
            valid_ids = {f"resource.{self.target_resource_id}", f"recipe.extract.{self.target_resource_id}"}
            if card.definition_id != expected_definition_id or self.production_id not in valid_ids:
                raise ValueError(f"Production target is incompatible with {card.definition_id}: {self.target_resource_id}")
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
    board_kind: str = "legacy"
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        hall = _units_for_command(state, self.board_kind)[self.hall_id]
        line = next((line for line in hall.production_lines if line.line_id == self.line_id), None)
        if line is None:
            raise ValueError(f"Unknown production line: {self.line_id}")
        if line.unlocked:
            raise ValueError(f"Production line is already unlocked: {self.line_id}")
        if line.slot_indexes:
            raise ValueError('Locked production line contains stale slot references.')
        number=hall.production_lines.index(line)+1
        if number>hall.max_lines:raise ValueError('Invalid production line.')
        cost=check_quote(unit_line_price(hall,number,self.board_kind),self.expected_cost)
        used={index for existing in hall.production_lines for index in existing.slot_indexes}
        prepared=[i for i in range(hall.max_lines*hall.max_slots_per_line) if i not in used][:hall.start_slots_per_line]
        if len(prepared)!=hall.start_slots_per_line:raise ValueError('Not enough structural slots for this line.')
        state.cash.spend(cost)
        hall.building_investment += cost
        line.unlocked = True
        line.unlock_cost=cost
        line.slot_indexes = prepared
        hall.slot_count = sum(len(existing.slot_indexes) for existing in hall.production_lines if existing.unlocked)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class UnlockProductionSlot:
    hall_id: str
    line_id: str
    board_kind: str = "legacy"
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        hall = _units_for_command(state, self.board_kind)[self.hall_id]
        line = next((line for line in hall.production_lines if line.line_id == self.line_id), None)
        if line is None:
            raise ValueError(f"Unknown production line: {self.line_id}")
        if not line.unlocked:
            raise ValueError(f"Production line is locked: {self.line_id}")
        line_number = hall.production_lines.index(line) + 1
        if line_number < 1 or line_number > hall.max_lines:
            raise ValueError(f"Invalid production line: {self.line_id}")
        if len(line.slot_indexes) >= hall.max_slots_per_line:
            raise ValueError(f"Production line already has maximum slots: {self.line_id}")
        next_slot_number = len(line.slot_indexes) + 1
        cost = check_quote(unit_slot_price(hall,line_number,next_slot_number,self.board_kind),self.expected_cost)
        prepared=next_factory_slot_index(hall)
        state.cash.spend(cost)
        hall.building_investment += cost
        line.slot_indexes.append(prepared)
        hall.slot_count = sum(len(existing.slot_indexes) for existing in hall.production_lines if existing.unlocked)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class InstallCardInHall:
    hall_id: str
    slot_index: int
    card_id: str
    board_kind: str | None = None

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.cards:
            raise ValueError(f"Unknown card: {self.card_id}")
        card = state.cards[self.card_id]
        board_kind = _resolved_install_board_kind(state, self.board_kind, self.hall_id)
        if not _card_allowed_on_board(card, board_kind):
            raise ValueError(f"Card cannot be installed in a hall slot: {self.card_id}")
        hall = _units_for_command(state, board_kind)[self.hall_id]
        if type(self.slot_index) is not int or self.slot_index < 0 or self.slot_index >= len(hall.slots):
            raise IndexError(f"Invalid slot index: {self.slot_index}")
        if self.slot_index not in hall.unlocked_slot_indexes():
            raise ValueError(f"Slot is locked: {self.slot_index}")
        if hall.slots[self.slot_index].card_id is not None:
            raise ValueError(f"Slot already occupied: {self.slot_index}")
        if self.card_id in state.installed_card_ids() or self.card_id in state.installed_freight_card_ids():
            raise ValueError("Machine is already installed.")
        if is_freight_card_busy(state.freight, self.card_id):
            raise ValueError("Card has a reserved freight shipment.")
        if board_kind == "resources":
            from production_zero.core.machine_operations import site_accepts
            if not site_accepts(state, hall, card.definition_id):
                raise ValueError("Machine does not match the resource site type.")
            hall.specialization = card.definition_id
        hall.slots[self.slot_index].card_id = self.card_id


@dataclass(frozen=True, slots=True)
class InstallInventoryCards:
    """Validate the complete group using the existing installation commands."""
    commands: tuple

    def apply(self, state: GameState) -> None:
        from copy import deepcopy
        if not self.commands or any(not isinstance(c, (InstallCardInHall, InstallFreightCard)) for c in self.commands):
            raise ValueError('Select available cards and compatible slots.')
        prepared = deepcopy(state)
        for command in self.commands:
            command.apply(prepared)
        # CommandBus is synchronous; no state can change between validation/commit.
        for command in self.commands:
            command.apply(state)


@dataclass(frozen=True, slots=True)
class RemoveCardFromHall:
    hall_id: str
    slot_index: int
    board_kind: str = "legacy"

    def apply(self, state: GameState) -> None:
        hall = _units_for_command(state, self.board_kind)[self.hall_id]
        if self.slot_index < 0 or self.slot_index >= len(hall.slots):
            raise IndexError(f"Invalid slot index: {self.slot_index}")
        if hall.slots[self.slot_index].card_id is None:
            raise ValueError(f"Slot is already empty: {self.slot_index}")
        card_id = hall.slots[self.slot_index].card_id
        ReturnMachinesToInventory((card_id,)).apply(state)


def _card_allowed_on_board(card: CardInstance, board_kind: str) -> bool:
    if board_kind == "legacy":
        return card.card_kind in {CardKind.MACHINE, CardKind.ENERGY}
    if board_kind == "energy":
        return card.card_kind is CardKind.ENERGY
    if card.card_kind is not CardKind.MACHINE:
        return False
    definition_id = card.definition_id.lower()
    if board_kind == "resources":
        return definition_id in {"machine.extractor", "machine.drilling", "machine.agriculture", "machine.mining_drill"}
    if board_kind == "factory":
        return definition_id in {"machine.processor", "machine.fabricator", "machine.assembler", "machine.furnace", "machine.blast_furnace"}
    return False


def _units_for_command(state: GameState, board_kind: str) -> dict[str, FactoryHall]:
    return state.halls if board_kind == "legacy" else state.production_units(board_kind)


def _resolved_install_board_kind(state: GameState, board_kind: str | None, unit_id: str) -> str:
    """Resolve old calls safely; split states always enforce the owning board."""
    if board_kind not in {None, "legacy"}:
        return board_kind
    if state.resource_sites or state.energy_plants:
        if unit_id in state.halls:
            return "factory"
        if unit_id in state.resource_sites:
            return "resources"
        if unit_id in state.energy_plants:
            return "energy"
    return "legacy"


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
        if type(self.slot_index) is not int or self.slot_index < 0 or self.slot_index >= len(facility.slots):
            raise IndexError(f"Invalid freight slot index: {self.slot_index}")
        if self.slot_index not in facility.unlocked_slot_indexes():
            raise ValueError('The freight slot has not been purchased.')
        if facility.slots[self.slot_index].card_id is not None:
            raise ValueError(f"Freight slot already occupied: {self.slot_index}")
        if self.card_id in state.installed_card_ids() or self.card_id in state.installed_freight_card_ids():
            raise ValueError(f"Card is already installed: {self.card_id}")
        if is_freight_card_busy(state.freight, self.card_id):
            raise ValueError("Vehicle has a reserved freight shipment.")
        assignment = state.freight.assignments.get(self.card_id)
        if assignment is not None:
            from production_zero.core.freight import OUTBOUND_FREIGHT_DESTINATIONS
            if assignment.resource_id not in state.resources or assignment.destination_kind not in OUTBOUND_FREIGHT_DESTINATIONS:
                raise ValueError("Retained freight route is no longer available.")
        facility.slots[self.slot_index].card_id = self.card_id


@dataclass(frozen=True, slots=True)
class BuildFreightFacility:
    facility_type: str
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        cost = check_quote(freight_facility_build_cost(state.freight, self.facility_type),self.expected_cost)
        from production_zero.core.freight import prepare_freight_facility
        facility = prepare_freight_facility(state.freight, self.facility_type)
        facility.expansion_tier = next_expansion_tier(state, 'freight', self.facility_type)
        facility.building_investment = cost
        state.cash.spend(cost)
        state.freight.facilities[facility.facility_id]=facility
        record_expansion_tier(state, 'freight', self.facility_type, facility.expansion_tier)
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class ExpandFreightFacility:
    facility_id: str
    slot_index: int | None = None
    expected_cost: float | None = None

    def apply(self, state: GameState) -> None:
        if self.facility_id not in state.freight.facilities:
            raise ValueError(f"Unknown freight facility: {self.facility_id}")
        facility = state.freight.facilities[self.facility_id]
        from production_zero.core.freight import validate_freight_expansion
        target=validate_freight_expansion(facility,self.slot_index)
        cost = check_quote(freight_facility_expansion_cost(facility,slot_index=target),self.expected_cost)
        state.cash.spend(cost)
        expand_freight_facility(facility,target)
        facility.building_investment += cost
        state.history.append("cash", state.cash.amount)


@dataclass(frozen=True, slots=True)
class AssignFreightCard:
    card_id: str
    resource_id: str
    destination_kind: str

    def apply(self, state: GameState) -> None:
        if self.card_id not in state.installed_freight_card_ids():
            raise ValueError(f"Freight card is not installed: {self.card_id}")
        assign_freight_card(
            state.freight,
            self.card_id,
            self.resource_id,
            self.destination_kind,
        )


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
        ReturnMachinesToInventory((card_id,)).apply(state)


@dataclass(frozen=True, slots=True)
class PurchaseResearch:
    node_id: str

    def apply(self, state: GameState) -> None:
        from production_zero.core.research import purchase_research
        purchase_research(state, self.node_id)


@dataclass(frozen=True, slots=True)
class PurchaseSpecialization:
    slot_id: str
    product_id: str

    def apply(self, state: GameState) -> None:
        from production_zero.core.research import purchase_specialization
        purchase_specialization(state, self.slot_id, self.product_id)


@dataclass(frozen=True, slots=True)
class RespecResearch:
    def apply(self, state: GameState) -> None:
        from production_zero.core.research import respec_research
        respec_research(state)


@dataclass(frozen=True, slots=True)
class CreateConsortium:
    name: str
    join_policy: str
    minimum_company_level: int = 1
    definitions: dict[str, CardDefinition] | None = None

    def apply(self, state: GameState) -> None:
        ConsortiumService(state, self.definitions).create(self.name, self.join_policy, self.minimum_company_level)


@dataclass(frozen=True, slots=True)
class JoinConsortium:
    consortium_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).join(self.consortium_id)


@dataclass(frozen=True, slots=True)
class ApplyToConsortium:
    consortium_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).apply(self.consortium_id)


@dataclass(frozen=True, slots=True)
class InviteToConsortium:
    consortium_id: str
    actor_id: str
    company_id: str
    company_name: str
    company_level: int

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).invite(
            self.consortium_id, self.actor_id, self.company_id, self.company_name, self.company_level
        )


@dataclass(frozen=True, slots=True)
class ProcessConsortiumApplication:
    consortium_id: str
    actor_id: str
    company_id: str
    accept: bool

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).process_application(self.consortium_id, self.actor_id, self.company_id, self.accept)


@dataclass(frozen=True, slots=True)
class LeaveConsortium:
    consortium_id: str
    company_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).leave(self.consortium_id, self.company_id)


@dataclass(frozen=True, slots=True)
class RemoveConsortiumMember:
    consortium_id: str
    actor_id: str
    company_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).remove(self.consortium_id, self.actor_id, self.company_id)


@dataclass(frozen=True, slots=True)
class SetConsortiumRole:
    consortium_id: str
    actor_id: str
    company_id: str
    role: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).set_role(self.consortium_id, self.actor_id, self.company_id, self.role)


@dataclass(frozen=True, slots=True)
class TransferConsortiumLeadership:
    consortium_id: str
    actor_id: str
    company_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).transfer_leadership(self.consortium_id, self.actor_id, self.company_id)


@dataclass(frozen=True, slots=True)
class UpdateConsortiumSettings:
    consortium_id: str
    actor_id: str
    join_policy: str
    minimum_company_level: int

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).update_settings(
            self.consortium_id, self.actor_id, self.join_policy, self.minimum_company_level
        )


@dataclass(frozen=True, slots=True)
class StartConsortiumContract:
    consortium_id: str
    actor_id: str
    kind: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        ConsortiumService(state, self.definitions).start_contract(self.consortium_id, self.actor_id, self.kind)


@dataclass(frozen=True, slots=True)
class ContributeToConsortiumContract:
    consortium_id: str
    company_id: str
    kind: str
    resource_id: str
    amount: float
    request_id: str | None = None

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).contribute(
            self.consortium_id,
            self.company_id,
            self.kind,
            self.resource_id,
            self.amount,
            request_id=self.request_id,
        )


@dataclass(frozen=True, slots=True)
class CompleteConsortiumContract:
    consortium_id: str
    kind: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).complete_contract(self.consortium_id, self.kind)


@dataclass(frozen=True, slots=True)
class DeliverConsortiumRewards:
    consortium_id: str
    kind: str

    def apply(self, state: GameState) -> None:
        # Completion is the sole idempotent reward boundary; a retry is safe.
        ConsortiumService(state).complete_contract(self.consortium_id, self.kind)


@dataclass(frozen=True, slots=True)
class DisbandConsortium:
    consortium_id: str
    actor_id: str

    def apply(self, state: GameState) -> None:
        ConsortiumService(state).disband(self.consortium_id, self.actor_id)


@dataclass(frozen=True, slots=True)
class UpgradeMachines:
    card_ids: tuple[str, ...]
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        from production_zero.core.mk_upgrades import upgrade_cards
        upgrade_cards(state, self.definitions, self.card_ids)


@dataclass(frozen=True, slots=True)
class ReturnMachinesToInventory:
    card_ids: tuple[str, ...]

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import return_machines_to_inventory
        return_machines_to_inventory(state, self.card_ids)


@dataclass(frozen=True, slots=True)
class ResetInventoryFreightRoutes:
    """Clear only routes belonging to available idle vehicles, atomically."""
    card_ids: tuple[str, ...]

    def apply(self, state: GameState) -> None:
        ids = self.card_ids
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("Select distinct available vehicles.")
        if any(cid not in state.cards or state.cards[cid].card_kind is not CardKind.FREIGHT for cid in ids):
            raise ValueError("Select owned existing freight cards.")
        installed = state.installed_card_ids() | state.installed_freight_card_ids()
        if installed.intersection(ids):
            raise ValueError("Return vehicles to Inventory before resetting their stored routes.")
        if any(is_freight_card_busy(state.freight, cid) for cid in ids):
            raise ValueError("A vehicle with a reserved shipment cannot have its route reset.")
        for cid in ids:
            state.freight.assignments.pop(cid, None)


@dataclass(frozen=True, slots=True)
class SellMachines:
    card_ids: tuple[str, ...]
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import sell_machines
        sell_machines(state, self.definitions, self.card_ids)


@dataclass(frozen=True, slots=True)
class PauseMachines:
    card_ids: tuple[str, ...]
    paused: bool

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import pause_machines
        if type(self.paused) is not bool:
            raise ValueError("Pause state must be a boolean.")
        pause_machines(state, self.card_ids, self.paused)


@dataclass(frozen=True, slots=True)
class MoveMachines:
    card_ids: tuple[str, ...]
    board_kind: str
    target_unit_id: str
    target_indexes: tuple[int, ...]

    expected_origins: tuple | None = None

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import move_machines
        move_machines(state, self.card_ids, self.board_kind, self.target_unit_id, self.target_indexes, expected_origins=self.expected_origins)


@dataclass(frozen=True, slots=True)
class MoveFreightVehicle:
    card_id: str
    facility_id: str
    slot_index: int
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        from production_zero.core.freight import move_freight_vehicle
        move_freight_vehicle(state, self.definitions, self.card_id, self.facility_id, self.slot_index)


@dataclass(frozen=True, slots=True)
class ConfigureMachines:
    card_ids: tuple[str, ...]
    production_id: str
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import configure_machines
        configure_machines(state, self.definitions, self.card_ids, self.production_id)


@dataclass(frozen=True, slots=True)
class PasteMachineConfigurations:
    card_ids: tuple[str, ...]
    configurations: tuple
    definitions: dict[str, CardDefinition]

    def apply(self, state: GameState) -> None:
        from production_zero.core.machine_operations import paste_configuration
        paste_configuration(state, self.definitions, self.card_ids, self.configurations)


@dataclass(frozen=True, slots=True)
class SellProductionBuilding:
    board_kind: str
    unit_id: str
    definitions: dict | None = None
    include_machines: bool = False

    def apply(self, state: GameState) -> None:
        from production_zero.core.infrastructure import sell_production_building
        sell_production_building(state, self.board_kind, self.unit_id, self.definitions, self.include_machines)


@dataclass(frozen=True, slots=True)
class SellFreightBuilding:
    facility_id: str
    definitions: dict | None = None
    include_machines: bool = False

    def apply(self, state: GameState) -> None:
        from production_zero.core.infrastructure import sell_freight_building
        sell_freight_building(state, self.facility_id, self.definitions, self.include_machines)


@dataclass(frozen=True, slots=True)
class PauseProductionScope:
    board_kind: str
    unit_id: str
    paused: bool
    line_id: str | None = None

    def apply(self, state):
        if type(self.paused) is not bool:
            raise ValueError("Invalid pause state.")
        unit = state.production_units(self.board_kind)[self.unit_id]
        target = unit if self.line_id is None else next((line for line in unit.production_lines if line.line_id == self.line_id and line.unlocked), None)
        if target is None:
            raise ValueError("Select an unlocked line.")
        target.paused = self.paused


@dataclass(frozen=True, slots=True)
class PauseFreightScope:
    facility_id: str
    paused: bool
    line_number: int | None = None

    def apply(self, state):
        from production_zero.core.production_pause import freight_line_number
        unit = state.freight.facilities[self.facility_id]
        if type(self.paused) is not bool:
            raise ValueError("Invalid pause state.")
        if self.line_number is None:
            unit.paused = self.paused
        elif self.line_number in {freight_line_number(unit, slot.index) for slot in unit.slots}:
            if self.paused:
                unit.paused_lines.add(self.line_number)
            else:
                unit.paused_lines.discard(self.line_number)
        else:
            raise ValueError("Select an unlocked freight line.")


@dataclass(frozen=True, slots=True)
class MoveFreightVehicles:
    card_ids: tuple[str, ...]
    facility_id: str
    target_indexes: tuple[int, ...]
    definitions: dict
    expected_origins: tuple | None = None

    def apply(self, state):
        from production_zero.core.freight import plan_freight_moves
        from production_zero.core.machine_operations import commit_slot_permutation
        commit_slot_permutation(plan_freight_moves(state, self.definitions, self.card_ids,
            self.facility_id, self.target_indexes, expected_origins=self.expected_origins))


@dataclass(frozen=True, slots=True)
class AssignFreightVehicles:
    card_ids: tuple[str, ...]
    resource_id: str
    destination_kind: str
    definitions: dict | None = None
    expected_origins: tuple | None = None
    require_target: bool = False

    def apply(self, state):
        from production_zero.core.freight import FreightAssignment
        from production_zero.core.freight_routes import validate_route
        validate_route(state, self.card_ids, self.resource_id, self.destination_kind,
                       definitions=self.definitions, expected_origins=self.expected_origins,
                       require_target=self.require_target)
        replacements = {cid: FreightAssignment(self.resource_id, self.destination_kind) for cid in self.card_ids}
        state.freight.assignments.update(replacements)


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
