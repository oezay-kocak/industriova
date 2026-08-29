from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from production_zero.core.cards import CardInstance
from production_zero.core.company import CompanyProfile, LevelUpRewardDefinition, xp_reward_for_contract_kind
from production_zero.core.contracts import ActiveContract, ContractBook, ContractOffer
from production_zero.core.economy import CashWallet, EnergyState
from production_zero.core.freight import FreightAssignment, FreightFacility, FreightSlot, FreightState, OutboundFreightShipment
from production_zero.core.enums import CardKind, Rarity, TradeState
from production_zero.core.history import MetricHistory, MetricSeries
from production_zero.core.market import MarketState, ResourceMarketState, create_market_state
from production_zero.core.packs import PackInstance, PackInventory
from production_zero.core.recycling import IndustrialScrapWallet
from production_zero.core.resources import ResourceStock
from production_zero.core.state import AutoSellSetting, FactoryHall, GameState, HallSlot, MachineProductionState, ProductionLine
from production_zero.core.statistics import AccountStatistics
from production_zero.core.supply import SupplyBook, SupplyOffer


class SQLiteSaveStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def initialize(self) -> None:
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS saves (
                    slot TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL
                )
                """
            )

    def save(self, slot: str, state: GameState) -> None:
        payload = json.dumps(_state_to_dict(state), sort_keys=True)
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO saves (slot, state_json) VALUES (?, ?)",
                (slot, payload),
            )

    def load(self, slot: str) -> GameState:
        with sqlite3.connect(self._path) as connection:
            row = connection.execute("SELECT state_json FROM saves WHERE slot = ?", (slot,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown save slot: {slot}")
        return _state_from_dict(json.loads(row[0]))


def _state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "rng_seed": state.rng_seed,
        "tick": state.tick,
        "cash": asdict(state.cash),
        "statistics": asdict(state.statistics),
        "inventory_storage_level": state.inventory_storage_level,
        "scrap": asdict(state.scrap),
        "company": {
            "level": state.company.level,
            "current_xp": state.company.current_xp,
            "selected_title": state.company.selected_title,
            "achievement_titles": state.company.achievement_titles,
            "pending_rewards": [asdict(reward) for reward in state.company.pending_rewards],
        },
        "resources": {resource_id: asdict(stock) for resource_id, stock in state.resources.items()},
        "energy": asdict(state.energy),
        "market": {
            "elapsed_seconds": state.market.elapsed_seconds,
            "next_market_tick_seconds": state.market.next_market_tick_seconds,
            "market_tick": state.market.market_tick,
            "active_event_id": state.market.active_event_id,
            "event_started_at": state.market.event_started_at,
            "resources": {
                resource_id: asdict(resource_state)
                for resource_id, resource_state in state.market.resources.items()
            },
        },
        "history": {
            metric_id: {
                "metric_id": series.metric_id,
                "max_points": series.max_points,
                "values": series.values,
            }
            for metric_id, series in state.history.series.items()
        },
        "cards": {card_id: asdict(card) for card_id, card in state.cards.items()},
        "machine_production": {
            card_id: asdict(machine_state)
            for card_id, machine_state in state.machine_production.items()
        },
        "auto_sell": {
            resource_id: asdict(setting)
            for resource_id, setting in state.auto_sell.items()
        },
        "contracts": {
            "offers": {
                kind: [asdict(offer) for offer in offers]
                for kind, offers in state.contracts.offers.items()
            },
            "active": {
                kind: {
                    "offer": asdict(active.offer),
                    "delivered": active.delivered,
                    "status": active.status,
                }
                for kind, active in state.contracts.active.items()
            },
            "daily_period_index": state.contracts.daily_period_index,
            "weekly_period_index": state.contracts.weekly_period_index,
            "regular_generation": state.contracts.regular_generation,
            "last_status": state.contracts.last_status,
        },
        "supply": {
            "daily_period_index": state.supply.daily_period_index,
            "daily_offers": [asdict(offer) for offer in state.supply.daily_offers],
            "daily_purchased_period_index": state.supply.daily_purchased_period_index,
            "daily_purchased_offer_id": state.supply.daily_purchased_offer_id,
            "freight_daily_period_index": state.supply.freight_daily_period_index,
            "freight_daily_offers": [asdict(offer) for offer in state.supply.freight_daily_offers],
            "freight_daily_purchased_period_index": state.supply.freight_daily_purchased_period_index,
            "freight_daily_purchased_offer_id": state.supply.freight_daily_purchased_offer_id,
            "machine_daily_period_index": state.supply.machine_daily_period_index,
            "machine_daily_offers": [asdict(offer) for offer in state.supply.machine_daily_offers],
            "machine_daily_purchased_period_index": state.supply.machine_daily_purchased_period_index,
            "machine_daily_purchased_offer_id": state.supply.machine_daily_purchased_offer_id,
        },
        "packs": {
            "unopened": [asdict(pack) for pack in state.packs.unopened],
            "opened_count": state.packs.opened_count,
            "last_opened_cards": [asdict(card) for card in state.packs.last_opened_cards],
        },
        "freight": {
            "facilities": {
                facility_id: {
                    "facility_id": facility.facility_id,
                    "name": facility.name,
                    "facility_type": facility.facility_type,
                    "slot_count": facility.slot_count,
                    "expansion_level": facility.expansion_level,
                    "slots": [asdict(slot) for slot in facility.slots],
                }
                for facility_id, facility in state.freight.facilities.items()
            },
            "outbound_shipments": {
                shipment_id: asdict(shipment)
                for shipment_id, shipment in state.freight.outbound_shipments.items()
            },
            "assignments": {
                card_id: asdict(assignment)
                for card_id, assignment in state.freight.assignments.items()
            },
            "next_shipment_sequence": state.freight.next_shipment_sequence,
        },
        "halls": {
            hall_id: {
                "hall_id": hall.hall_id,
                "name": hall.name,
                "slot_count": hall.slot_count,
                "specialization": hall.specialization,
                "slots": [asdict(slot) for slot in hall.slots],
                "production_lines": [asdict(line) for line in hall.production_lines],
            }
            for hall_id, hall in state.halls.items()
        },
    }


def _state_from_dict(payload: dict[str, object]) -> GameState:
    cards = {
        card_id: CardInstance(
            card_id=card_data["card_id"],
            definition_id=card_data["definition_id"],
            card_kind=CardKind(card_data["card_kind"]),
            rarity=Rarity(card_data["rarity"]),
            output_bonus_percent=float(card_data["output_bonus_percent"]),
            power_bonus_percent=float(card_data["power_bonus_percent"]),
            trade_state=TradeState(card_data["trade_state"]),
            collectible_token_id=card_data["collectible_token_id"],
        )
        for card_id, card_data in payload["cards"].items()
    }
    halls = {
        hall_id: FactoryHall(
            hall_id=hall_data["hall_id"],
            name=hall_data["name"],
            slot_count=int(hall_data["slot_count"]),
            specialization=hall_data["specialization"],
            slots=[HallSlot(index=int(slot["index"]), card_id=slot["card_id"]) for slot in hall_data["slots"]],
            production_lines=[
                ProductionLine(
                    line_id=line["line_id"],
                    name=line["name"],
                    slot_indexes=[int(index) for index in line["slot_indexes"]],
                    unlocked=bool(line["unlocked"]),
                    unlock_cost=float(line.get("unlock_cost", 0.0)),
                )
                for line in hall_data.get("production_lines", [])
            ],
        )
        for hall_id, hall_data in payload["halls"].items()
    }
    resources = {}
    for resource_id, stock_data in payload.get("resources", {}).items():
        if isinstance(stock_data, dict):
            resources[resource_id] = ResourceStock(
                amount=float(stock_data["amount"]),
                capacity=float(stock_data["capacity"]),
            )
        else:
            resources[resource_id] = ResourceStock(amount=float(stock_data), capacity=float(stock_data))
    history = MetricHistory(
        series={
            metric_id: MetricSeries(
                metric_id=series_data["metric_id"],
                max_points=int(series_data["max_points"]),
                values=[float(value) for value in series_data["values"]],
            )
            for metric_id, series_data in payload.get("history", {}).items()
        }
    )
    cash_payload = payload.get("cash", {"amount": payload.get("money", 0.0)})
    scrap_payload = payload.get("scrap", {"amount": 0})
    statistics_payload = payload.get("statistics", {"total_earnings": 0.0})
    energy_payload = payload.get("energy", {"generated": 0.0, "consumed": 0.0})
    market_payload = payload.get("market")
    market = create_market_state()
    if isinstance(market_payload, dict):
        market = MarketState(
            elapsed_seconds=float(market_payload.get("elapsed_seconds", 0.0)),
            next_market_tick_seconds=float(market_payload.get("next_market_tick_seconds", 300.0)),
            market_tick=int(market_payload.get("market_tick", 0)),
            active_event_id=str(market_payload.get("active_event_id", "industrial_boom")),
            event_started_at=float(market_payload.get("event_started_at", 0.0)),
            resources={
                resource_id: ResourceMarketState(
                    resource_id=resource_data["resource_id"],
                    current_price=float(resource_data["current_price"]),
                    anchor_price=float(resource_data["anchor_price"]),
                    volatility=float(resource_data["volatility"]),
                    momentum=float(resource_data.get("momentum", 0.0)),
                    trend_age=int(resource_data.get("trend_age", 0)),
                    last_change=float(resource_data.get("last_change", 0.0)),
                )
                for resource_id, resource_data in market_payload.get("resources", {}).items()
            },
        )
    contracts_payload = payload.get("contracts", {})
    contracts = ContractBook()
    if isinstance(contracts_payload, dict):
        contracts = ContractBook(
            offers={
                kind: [
                    ContractOffer(
                        contract_id=offer_data["contract_id"],
                        kind=offer_data["kind"],
                        name=offer_data["name"],
                        requirements={
                            resource_id: float(amount)
                            for resource_id, amount in offer_data["requirements"].items()
                        },
                        reward_cash=float(offer_data["reward_cash"]),
                        reward_xp=float(offer_data.get("reward_xp", xp_reward_for_contract_kind(offer_data["kind"]))),
                        period_index=int(offer_data["period_index"]),
                        expires_at=(
                            None
                            if offer_data.get("expires_at") is None
                            else float(offer_data["expires_at"])
                        ),
                    )
                    for offer_data in offers
                ]
                for kind, offers in contracts_payload.get("offers", {}).items()
            },
            active={
                kind: ActiveContract(
                    offer=ContractOffer(
                        contract_id=active_data["offer"]["contract_id"],
                        kind=active_data["offer"]["kind"],
                        name=active_data["offer"]["name"],
                        requirements={
                            resource_id: float(amount)
                            for resource_id, amount in active_data["offer"]["requirements"].items()
                        },
                        reward_cash=float(active_data["offer"]["reward_cash"]),
                        reward_xp=float(
                            active_data["offer"].get(
                                "reward_xp",
                                xp_reward_for_contract_kind(active_data["offer"]["kind"]),
                            )
                        ),
                        period_index=int(active_data["offer"]["period_index"]),
                        expires_at=(
                            None
                            if active_data["offer"].get("expires_at") is None
                            else float(active_data["offer"]["expires_at"])
                        ),
                    ),
                    delivered={
                        resource_id: float(amount)
                        for resource_id, amount in active_data.get("delivered", {}).items()
                    },
                    status=active_data.get("status", "active"),
                )
                for kind, active_data in contracts_payload.get("active", {}).items()
            },
            daily_period_index=int(contracts_payload.get("daily_period_index", -1)),
            weekly_period_index=int(contracts_payload.get("weekly_period_index", -1)),
            regular_generation=int(contracts_payload.get("regular_generation", 0)),
            last_status={
                kind: str(status)
                for kind, status in contracts_payload.get("last_status", {}).items()
            },
        )
    company_payload = payload.get("company", {})
    company = CompanyProfile()
    if isinstance(company_payload, dict):
        company = CompanyProfile(
            level=int(company_payload.get("level", 1)),
            current_xp=float(company_payload.get("current_xp", 0.0)),
            selected_title=company_payload.get("selected_title"),
            achievement_titles=[
                str(title)
                for title in company_payload.get("achievement_titles", [])
            ],
            pending_rewards=[
                LevelUpRewardDefinition(
                    level=int(reward_data["level"]),
                    cash=float(reward_data.get("cash", 0.0)),
                    packs=int(reward_data.get("packs", 0)),
                    cosmetic_id=reward_data.get("cosmetic_id"),
                    unlock_ids=tuple(reward_data.get("unlock_ids", ())),
                )
                for reward_data in company_payload.get("pending_rewards", [])
            ],
        )
    supply_payload = payload.get("supply", {})
    supply = SupplyBook()
    if isinstance(supply_payload, dict):
        supply = SupplyBook(
            daily_period_index=int(supply_payload.get("daily_period_index", -1)),
            daily_offers=[
                SupplyOffer(
                    offer_id=offer_data["offer_id"],
                    definition_id=offer_data["definition_id"],
                    card_kind=CardKind(offer_data["card_kind"]),
                    rarity=Rarity(offer_data["rarity"]),
                    bonus_tenths=int(offer_data["bonus_tenths"]),
                    price_cash=float(offer_data["price_cash"]),
                    period_index=(
                        None
                        if offer_data.get("period_index") is None
                        else int(offer_data["period_index"])
                    ),
                )
                for offer_data in supply_payload.get("daily_offers", [])
            ],
            daily_purchased_period_index=(
                None
                if supply_payload.get("daily_purchased_period_index") is None
                else int(supply_payload["daily_purchased_period_index"])
            ),
            daily_purchased_offer_id=supply_payload.get("daily_purchased_offer_id"),
            freight_daily_period_index=int(supply_payload.get("freight_daily_period_index", -1)),
            freight_daily_offers=[
                SupplyOffer(
                    offer_id=offer_data["offer_id"],
                    definition_id=offer_data["definition_id"],
                    card_kind=CardKind(offer_data["card_kind"]),
                    rarity=Rarity(offer_data["rarity"]),
                    bonus_tenths=int(offer_data["bonus_tenths"]),
                    price_cash=float(offer_data["price_cash"]),
                    period_index=(
                        None
                        if offer_data.get("period_index") is None
                        else int(offer_data["period_index"])
                    ),
                )
                for offer_data in supply_payload.get("freight_daily_offers", [])
            ],
            freight_daily_purchased_period_index=(
                None
                if supply_payload.get("freight_daily_purchased_period_index") is None
                else int(supply_payload["freight_daily_purchased_period_index"])
            ),
            freight_daily_purchased_offer_id=supply_payload.get("freight_daily_purchased_offer_id"),
            machine_daily_period_index=int(supply_payload.get("machine_daily_period_index", -1)),
            machine_daily_offers=[
                SupplyOffer(
                    offer_id=offer_data["offer_id"],
                    definition_id=offer_data["definition_id"],
                    card_kind=CardKind(offer_data["card_kind"]),
                    rarity=Rarity(offer_data["rarity"]),
                    bonus_tenths=int(offer_data["bonus_tenths"]),
                    price_cash=float(offer_data["price_cash"]),
                    period_index=(
                        None
                        if offer_data.get("period_index") is None
                        else int(offer_data["period_index"])
                    ),
                )
                for offer_data in supply_payload.get("machine_daily_offers", [])
            ],
            machine_daily_purchased_period_index=(
                None
                if supply_payload.get("machine_daily_purchased_period_index") is None
                else int(supply_payload["machine_daily_purchased_period_index"])
            ),
            machine_daily_purchased_offer_id=supply_payload.get("machine_daily_purchased_offer_id"),
        )
    packs_payload = payload.get("packs", {})
    packs = PackInventory()
    if isinstance(packs_payload, dict):
        packs = PackInventory(
            unopened=[
                PackInstance(
                    pack_id=pack_data["pack_id"],
                    pack_type=pack_data["pack_type"],
                    source=pack_data.get("source", "system"),
                )
                for pack_data in packs_payload.get("unopened", [])
            ],
            opened_count=int(packs_payload.get("opened_count", 0)),
            last_opened_cards=[
                CardInstance(
                    card_id=card_data["card_id"],
                    definition_id=card_data["definition_id"],
                    card_kind=CardKind(card_data["card_kind"]),
                    rarity=Rarity(card_data["rarity"]),
                    output_bonus_percent=float(card_data["output_bonus_percent"]),
                    power_bonus_percent=float(card_data["power_bonus_percent"]),
                    trade_state=TradeState(card_data["trade_state"]),
                    collectible_token_id=card_data["collectible_token_id"],
                )
                for card_data in packs_payload.get("last_opened_cards", [])
            ],
        )
    freight_payload = payload.get("freight", {})
    freight = FreightState()
    if isinstance(freight_payload, dict):
        facilities_payload = freight_payload.get("facilities", {})
        if isinstance(facilities_payload, dict) and facilities_payload:
            freight = FreightState(
                facilities={
                    facility_id: FreightFacility(
                    facility_id=facility_data["facility_id"],
                    name=facility_data["name"],
                    facility_type=facility_data.get("facility_type", facility_data["facility_id"]),
                    slot_count=int(facility_data.get("slot_count", len(facility_data.get("slots", [])))),
                    expansion_level=int(facility_data.get("expansion_level", 0)),
                    slots=[
                            FreightSlot(index=int(slot["index"]), card_id=slot["card_id"])
                            for slot in facility_data.get("slots", [])
                        ],
                    )
                    for facility_id, facility_data in facilities_payload.items()
                },
                outbound_shipments={
                    shipment_id: OutboundFreightShipment(
                        shipment_id=shipment_data["shipment_id"],
                        destination_kind=shipment_data["destination_kind"],
                        target_id=shipment_data.get("target_id"),
                        resource_id=shipment_data.get("resource_id"),
                        quantity=float(shipment_data.get("quantity", shipment_data.get("prepared_amount", 0.0))),
                        freight_card_id=shipment_data.get("freight_card_id"),
                        freight_definition_id=shipment_data.get("freight_definition_id"),
                        freight_type=shipment_data.get("freight_type"),
                        transport_capacity=float(shipment_data.get("transport_capacity", 0.0)),
                        transport_time_seconds=float(shipment_data.get("transport_time_seconds", 0.0)),
                        remaining_seconds=float(shipment_data.get("remaining_seconds", 0.0)),
                        market_price=float(shipment_data.get("market_price", 0.0)),
                        active=bool(shipment_data.get("active", True)),
                    )
                    for shipment_id, shipment_data in freight_payload.get("outbound_shipments", {}).items()
                },
                assignments={
                    card_id: FreightAssignment(
                        resource_id=assignment_data["resource_id"],
                        destination_kind=assignment_data["destination_kind"],
                        reserve_percent=float(assignment_data.get("reserve_percent", 100.0)),
                    )
                    for card_id, assignment_data in freight_payload.get("assignments", {}).items()
                },
                next_shipment_sequence=int(freight_payload.get("next_shipment_sequence", 0)),
            )
    return GameState(
        rng_seed=int(payload["rng_seed"]),
        tick=int(payload["tick"]),
        cash=CashWallet(amount=float(cash_payload["amount"])),
        statistics=AccountStatistics(total_earnings=float(statistics_payload.get("total_earnings", 0.0))),
        scrap=IndustrialScrapWallet(amount=int(scrap_payload.get("amount", 0))),
        company=company,
        resources=resources,
        energy=EnergyState(
            generated=float(energy_payload["generated"]),
            consumed=float(energy_payload["consumed"]),
        ),
        market=market,
        history=history,
        cards=cards,
        halls=halls,
        machine_production={
            card_id: MachineProductionState(
                card_id=machine_state["card_id"],
                target_resource_id=machine_state["target_resource_id"],
                selected_production_id=machine_state.get("selected_production_id"),
                progress_seconds=float(machine_state["progress_seconds"]),
                status=machine_state["status"],
            )
            for card_id, machine_state in payload.get("machine_production", {}).items()
        },
        auto_sell={
            resource_id: AutoSellSetting(
                enabled=bool(setting_data.get("enabled", False)),
                threshold_percent=float(setting_data.get("threshold_percent", 100.0)),
            )
            for resource_id, setting_data in payload.get("auto_sell", {}).items()
        },
        contracts=contracts,
        supply=supply,
        packs=packs,
        freight=freight,
        inventory_storage_level=int(payload.get("inventory_storage_level", 0)),
    )
