from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from production_zero.core.cards import CardInstance, CardStack, CardStackKey
from production_zero.core.company import CompanyProfile
from production_zero.core.contracts import ContractBook
from production_zero.core.economy import CashWallet, EnergyState
from production_zero.core.freight import FreightState
from production_zero.core.history import MetricHistory
from production_zero.core.market import MarketState, create_market_state
from production_zero.core.packs import PackInventory
from production_zero.core.recycling import IndustrialScrapWallet
from production_zero.core.resources import ResourceStock
from production_zero.core.statistics import AccountStatistics
from production_zero.core.supply import SupplyBook


MAX_FACTORY_LINES = 6
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

    def __post_init__(self) -> None:
        structural_count = MAX_FACTORY_LINES * MAX_FACTORY_SLOTS_PER_LINE
        if not self.slots:
            self.slots = [HallSlot(index=i) for i in range(structural_count)]
        elif len(self.slots) < structural_count:
            existing = {slot.index: slot for slot in self.slots}
            self.slots = [
                existing.get(index, HallSlot(index=index))
                for index in range(structural_count)
            ]
        if not self.production_lines:
            self.production_lines = _default_production_lines(self.hall_id)
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
    for index in range(MAX_FACTORY_LINES * MAX_FACTORY_SLOTS_PER_LINE):
        if index not in used:
            return index
    raise ValueError("Factory hall already has maximum slots.")


def factory_line_unlock_cost(line_number: int) -> float:
    return 750.0 + max(0, line_number - 3) * 500.0


def factory_slot_unlock_cost(line_number: int, slot_number: int) -> float:
    return 120.0 + (slot_number - START_FACTORY_SLOTS_PER_LINE - 1) * 90.0 + (line_number - 1) * 35.0


def _default_production_lines(hall_id: str) -> list[ProductionLine]:
    lines = []
    next_index = 0
    for line_number in range(1, MAX_FACTORY_LINES + 1):
        unlocked = line_number <= START_UNLOCKED_FACTORY_LINES
        indexes = list(range(next_index, next_index + START_FACTORY_SLOTS_PER_LINE)) if unlocked else []
        if unlocked:
            next_index += START_FACTORY_SLOTS_PER_LINE
        lines.append(
            ProductionLine(
                line_id=f"{hall_id}.line-{line_number}",
                name=f"Line {line_number}",
                slot_indexes=indexes,
                unlocked=unlocked,
                unlock_cost=0.0 if unlocked else factory_line_unlock_cost(line_number),
            )
        )
    return lines


@dataclass(slots=True)
class GameState:
    rng_seed: int
    tick: int = 0
    cash: CashWallet = field(default_factory=CashWallet)
    resources: dict[str, ResourceStock] = field(default_factory=dict)
    energy: EnergyState = field(default_factory=EnergyState)
    market: MarketState = field(default_factory=create_market_state)
    history: MetricHistory = field(default_factory=MetricHistory)
    cards: dict[str, CardInstance] = field(default_factory=dict)
    halls: dict[str, FactoryHall] = field(default_factory=dict)
    machine_production: dict[str, MachineProductionState] = field(default_factory=dict)
    auto_sell: dict[str, AutoSellSetting] = field(default_factory=dict)
    contracts: ContractBook = field(default_factory=ContractBook)
    company: CompanyProfile = field(default_factory=CompanyProfile)
    supply: SupplyBook = field(default_factory=SupplyBook)
    packs: PackInventory = field(default_factory=PackInventory)
    scrap: IndustrialScrapWallet = field(default_factory=IndustrialScrapWallet)
    statistics: AccountStatistics = field(default_factory=AccountStatistics)
    freight: FreightState = field(default_factory=FreightState)
    inventory_storage_level: int = 0

    def resource_snapshot(self) -> Mapping[str, float]:
        return {resource_id: stock.amount for resource_id, stock in self.resources.items()}

    def installed_card_ids(self) -> set[str]:
        return {
            slot.card_id
            for hall in self.halls.values()
            for slot in hall.slots
            if slot.card_id is not None
        }

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
