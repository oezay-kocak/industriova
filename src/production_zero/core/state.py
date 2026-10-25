from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from production_zero.core.cards import CardInstance, CardStack, CardStackKey
from production_zero.core.company import CompanyProfile
from production_zero.core.company_xp import CompanyXpProgress
from production_zero.core.communications import CompanyCommunications
from production_zero.core.consortium import ConsortiumNetwork
from production_zero.core.research import ResearchState
from production_zero.core.modifiers import research_multiplier
from production_zero.core.contracts import ContractBook
from production_zero.core.economy import CashWallet, EnergyState
from production_zero.core.freight import FreightState
from production_zero.core.history import MetricHistory
from production_zero.core.inventory_history import InventoryHistory
from production_zero.core.market import MarketState, create_market_state
from production_zero.core.packs import PackInventory
from production_zero.core.progression import ProductionProgress
from production_zero.core.recycling import IndustrialScrapWallet
from production_zero.core.resources import ResourceStock
from production_zero.core.statistics import AccountStatistics
from production_zero.core.supply import SupplyBook


MAX_FACTORY_LINES = 5
MAX_FACTORY_SLOTS_PER_LINE = 10
START_UNLOCKED_FACTORY_LINES = 2
START_FACTORY_SLOTS_PER_LINE = 3


@dataclass(slots=True)
class HallSlot:
    index: int
    card_id: str | None = None


@dataclass(slots=True)
class ProductionLine:
    line_id: str
    name: str
    slot_indexes: list[int]
    unlocked: bool = True
    unlock_cost: float = 0.0
    paused: bool = False


@dataclass(slots=True)
class MachineProductionState:
    card_id: str
    target_resource_id: str
    selected_production_id: str | None = None
    progress_seconds: float = 0.0
    status: str = "idle"

    @property
    def is_storage_full(self) -> bool:
        return self.status == "storage_full"

    @property
    def is_no_power(self) -> bool:
        return self.status == "no_power"

    @property
    def is_missing_input(self) -> bool:
        return self.status == "missing_input"

    @property
    def is_unconfigured(self) -> bool:
        return self.status == "unconfigured"


@dataclass(slots=True)
class AutoSellSetting:
    enabled: bool = False
    threshold_percent: float = 100.0

    @property
    def threshold_ratio(self) -> float:
        return min(1.0, max(0.0, self.threshold_percent / 100.0))


@dataclass(slots=True)
class FactoryHall:
    hall_id: str
    name: str
    slot_count: int
    specialization: str | None = None
    slots: list[HallSlot] = field(default_factory=list)
    production_lines: list[ProductionLine] = field(default_factory=list)
    board_kind: str = "factory"
    max_lines: int = 6
    max_slots_per_line: int = MAX_FACTORY_SLOTS_PER_LINE
    start_unlocked_lines: int = START_UNLOCKED_FACTORY_LINES
    start_slots_per_line: int = START_FACTORY_SLOTS_PER_LINE
    building_investment: float = 0.0
    paused: bool = False
    expansion_tier: int = 1

    def __post_init__(self) -> None:
        from math import isfinite
        if not isfinite(self.building_investment) or self.building_investment < 0:
            raise ValueError("Invalid building investment.")
        if type(self.expansion_tier) is not int or self.expansion_tier < 1:
            raise ValueError("Invalid building expansion tier.")
        structural_count = self.max_lines * self.max_slots_per_line
        if not self.slots:
            self.slots = [HallSlot(index=i) for i in range(structural_count)]
        elif len(self.slots) < structural_count:
            existing = {slot.index: slot for slot in self.slots}
            self.slots = [
                existing.get(index, HallSlot(index=index))
                for index in range(structural_count)
            ]
        if not self.production_lines:
            self.production_lines = _default_production_lines(
                self.hall_id,
                max_lines=self.max_lines,
                start_unlocked_lines=self.start_unlocked_lines,
                start_slots_per_line=self.start_slots_per_line,
                board_kind=self.board_kind,
            )
        self.slot_count = sum(len(line.slot_indexes) for line in self.production_lines if line.unlocked)

    def unlocked_slot_indexes(self) -> set[int]:
        return {
            slot_index
            for line in self.production_lines
            if line.unlocked
            for slot_index in line.slot_indexes
        }


def factory_line_slot_index(line_number: int, slot_number: int) -> int:
    return (line_number - 1) * MAX_FACTORY_SLOTS_PER_LINE + (slot_number - 1)


def next_factory_slot_index(hall: FactoryHall) -> int:
    used = {
        slot_index
        for line in hall.production_lines
        for slot_index in line.slot_indexes
    }
    for index in range(hall.max_lines * hall.max_slots_per_line):
        if index not in used:
            return index
    raise ValueError("Factory hall already has maximum slots.")


def factory_line_unlock_cost(line_number: int, board_kind: str = 'factory') -> float:
    from production_zero.core.infrastructure_prices import line_price
    return line_price(board_kind,line_number)


def factory_slot_unlock_cost(
    line_number: int,
    slot_number: int,
    *,
    start_slots_per_line: int = START_FACTORY_SLOTS_PER_LINE,
    board_kind: str = 'factory',
) -> float:
    """Return the next-slot price relative to the board's starting capacity."""
    from production_zero.core.infrastructure_prices import slot_price
    return slot_price(board_kind,line_number,slot_number,start_slots=start_slots_per_line)


def _default_production_lines(
    hall_id: str,
    *,
    max_lines: int = MAX_FACTORY_LINES,
    start_unlocked_lines: int = START_UNLOCKED_FACTORY_LINES,
    start_slots_per_line: int = START_FACTORY_SLOTS_PER_LINE,
    board_kind: str = 'factory',
) -> list[ProductionLine]:
    lines = []
    next_index = 0
    for line_number in range(1, max_lines + 1):
        unlocked = line_number <= start_unlocked_lines
        indexes = list(range(next_index, next_index + start_slots_per_line)) if unlocked else []
        if unlocked:
            next_index += start_slots_per_line
        lines.append(
            ProductionLine(
                line_id=f"{hall_id}.line-{line_number}",
                name=f"Line {line_number}",
                slot_indexes=indexes,
                unlocked=unlocked,
                unlock_cost=0.0 if unlocked else factory_line_unlock_cost(line_number,board_kind),
            )
        )
    return lines


@dataclass(slots=True)
class GameState:
    rng_seed: int
    # Session-local command receipts, never ownership or save data. A fresh
    # command has a fresh ID; retrying a committed command cannot buy twice.
    completed_card_operations: set[str] = field(default_factory=set, init=False, repr=False, compare=False)
    tick: int = 0
    economy_version: int = 2
    cash: CashWallet = field(default_factory=CashWallet)
    resources: dict[str, ResourceStock] = field(default_factory=dict)
    energy: EnergyState = field(default_factory=EnergyState)
    market: MarketState = field(default_factory=create_market_state)
    history: MetricHistory = field(default_factory=MetricHistory)
    inventory_history: InventoryHistory = field(default_factory=InventoryHistory)
    cards: dict[str, CardInstance] = field(default_factory=dict)
    halls: dict[str, FactoryHall] = field(default_factory=dict)
    resource_sites: dict[str, FactoryHall] = field(default_factory=dict)
    energy_plants: dict[str, FactoryHall] = field(default_factory=dict)
    machine_production: dict[str, MachineProductionState] = field(default_factory=dict)
    auto_sell: dict[str, AutoSellSetting] = field(default_factory=dict)
    contracts: ContractBook = field(default_factory=ContractBook)
    company: CompanyProfile = field(default_factory=CompanyProfile)
    company_xp_progress: CompanyXpProgress = field(default_factory=CompanyXpProgress)
    communications: CompanyCommunications = field(default_factory=CompanyCommunications)
    consortium: ConsortiumNetwork = field(default_factory=ConsortiumNetwork)
    research: ResearchState = field(default_factory=ResearchState)
    supply: SupplyBook = field(default_factory=SupplyBook)
    packs: PackInventory = field(default_factory=PackInventory)
    production_progress: ProductionProgress = field(default_factory=ProductionProgress)
    scrap: IndustrialScrapWallet = field(default_factory=IndustrialScrapWallet)
    statistics: AccountStatistics = field(default_factory=AccountStatistics)
    freight: FreightState = field(default_factory=FreightState)
    inventory_storage_level: int = 0
    warehouse_capacity: float = 0.0
    infrastructure_tiers: dict[str, int] = field(default_factory=dict)
    building_order: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.warehouse_capacity <= 0 and self.resources:
            self.warehouse_capacity = sum(stock.capacity for stock in self.resources.values())

    @property
    def used_storage(self) -> float:
        """Physical warehouse goods; currencies, cards, energy and slots are excluded."""
        return sum(max(0.0, stock.amount) for stock in self.resources.values())

    @property
    def storage_capacity(self) -> float:
        """Authoritative capacity, with a lazy legacy fallback for old/in-memory states."""
        if self.warehouse_capacity > 0:
            return self.warehouse_capacity * research_multiplier(self.research, "storage_capacity")
        return sum(max(0.0, stock.capacity) for stock in self.resources.values()) * research_multiplier(self.research, "storage_capacity")

    @property
    def available_storage(self) -> float:
        return max(0.0, self.storage_capacity - self.used_storage)

    def can_store(self, amount: float, *, released_amount: float = 0.0) -> bool:
        if amount < 0 or released_amount < 0:
            raise ValueError("Storage amounts cannot be negative.")
        return amount <= max(0., self.storage_capacity - self.used_storage + released_amount) + 1e-9

    def store_resource(self, resource_id: str, amount: float) -> float:
        if amount < 0:
            raise ValueError("Cannot add a negative resource amount.")
        accepted = min(amount, self.available_storage)
        self.ensure_resource(resource_id).amount += accepted
        return accepted

    def resource_snapshot(self) -> Mapping[str, float]:
        return {resource_id: stock.amount for resource_id, stock in self.resources.items()}

    def installed_card_ids(self) -> set[str]:
        return {
            slot.card_id
            for hall in self.all_production_units()
            for slot in hall.slots
            if slot.card_id is not None
        }

    def production_units(self, board_kind: str) -> dict[str, FactoryHall]:
        if board_kind == "factory":
            return self.halls
        if board_kind == "resources":
            return self.resource_sites
        if board_kind == "energy":
            return self.energy_plants
        raise ValueError(f"Unknown production board: {board_kind}")

    def all_production_units(self) -> tuple[FactoryHall, ...]:
        return tuple(self.halls.values()) + tuple(self.resource_sites.values()) + tuple(self.energy_plants.values())

    def installed_freight_card_ids(self) -> set[str]:
        return {
            slot.card_id
            for facility in self.freight.facilities.values()
            for slot in facility.slots
            if slot.card_id is not None
        }

    def inventory_card_stacks(self) -> tuple[CardStack, ...]:
        installed = self.installed_card_ids() | self.installed_freight_card_ids()
        grouped: dict[CardStackKey, list[CardInstance]] = {}
        unstacked: list[CardStack] = []

        for card in self.cards.values():
            if card.card_id in installed:
                continue
            if not card.is_stackable:
                unstacked.append(CardStack(key=None, cards=(card,)))
                continue
            key = CardStackKey.from_card(card)
            grouped.setdefault(key, []).append(card)

        stacks = [
            CardStack(key=key, cards=tuple(sorted(cards, key=lambda card: card.card_id)))
            for key, cards in grouped.items()
        ]
        stacks.extend(unstacked)
        return tuple(stacks)

    def ensure_resource(self, resource_id: str, capacity: float = 0.0) -> ResourceStock:
        if resource_id not in self.resources:
            self.resources[resource_id] = ResourceStock(capacity=capacity)
        return self.resources[resource_id]

    def ensure_auto_sell_setting(self, resource_id: str) -> AutoSellSetting:
        if resource_id not in self.auto_sell:
            self.auto_sell[resource_id] = AutoSellSetting()
        return self.auto_sell[resource_id]

    def ensure_machine_production(
        self,
        card_id: str,
        target_resource_id: str,
        selected_production_id: str | None = None,
    ) -> MachineProductionState:
        if card_id not in self.machine_production:
            self.machine_production[card_id] = MachineProductionState(
                card_id=card_id,
                target_resource_id=target_resource_id,
                selected_production_id=selected_production_id,
            )
        return self.machine_production[card_id]
