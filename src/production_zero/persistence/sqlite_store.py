from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path

from production_zero.core.cards import CardInstance
from production_zero.core.company import CompanyProfile, LevelUpRewardDefinition, xp_reward_for_contract_kind
from production_zero.core.company_xp import CompanyXpProgress
from production_zero.core.research import research_from_dict, research_to_dict
from production_zero.core.communications import CompanyCommunications, CompanyMessage
from production_zero.core.consortium import consortium_from_dict, consortium_to_dict
from production_zero.core.contracts import (ActiveContract, ContractBook, ContractOffer, RegularContractAutomation,
    REGULAR, contract_company_xp)
from production_zero.core.economy import CashWallet, EnergyState
from production_zero.core.freight import FreightAssignment, FreightFacility, FreightSlot, FreightState, OutboundFreightShipment
from production_zero.core.freight_statistics import FreightDeliveryStatistics
from production_zero.core.infrastructure_prices import PRICING_VERSION, infrastructure_tier_snapshot
from production_zero.core.enums import CardKind, Rarity, TradeState
from production_zero.core.history import DEFAULT_HISTORY_MAX_POINTS, MetricHistory, MetricSeries
from production_zero.core.inventory_history import InventoryHistory
from production_zero.core.market import MarketState, ResourceMarketState, create_market_state
from production_zero.core.packs import PackInstance, PackInventory
from production_zero.core.progression import (
    ProductionProgress,
    migrate_production_progress,
)
from production_zero.core.recycling import IndustrialScrapWallet
from production_zero.core.resources import ResourceStock
from production_zero.core.state import AutoSellSetting, FactoryHall, GameState, HallSlot, MachineProductionState, ProductionLine
from production_zero.core.statistics import AccountStatistics
from production_zero.core.supply import SupplyBook, SupplyOffer
from production_zero.data.definitions import normalize_legacy_card_definition_id


STATE_SCHEMA_VERSION = 9
PRODUCTION_BOARD_SCHEMA_VERSION = 3
GAME_RULESET = "contract-priority-auto-v1"


def _validate_ruleset(payload):
    if payload.get("game_ruleset") != GAME_RULESET:
        raise ValueError("This test version requires a new company. Previous test saves are incompatible.")


def legacy_mk_level(data):
    import re
    value = data.get("mk_level")
    if value is None:
        match = re.search(r"\.mk(\d+)$", data.get("definition_id", ""), re.IGNORECASE)
        value = int(match.group(1)) if match else 1
    if type(value) is not int or not 1 <= value <= 99:
        raise ValueError("Invalid saved MK level")
    return value


class SQLiteSaveStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def initialize(self) -> None:
        with closing(sqlite3.connect(self._path)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS saves (
                    slot TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL
                )
                """
            )
            from production_zero.persistence.history_store import initialize_history_tables
            initialize_history_tables(connection)

    def save(self, slot: str, state: GameState) -> None:
        from production_zero.persistence.session_writer import snapshot_game_state
        self.save_snapshot(slot, snapshot_game_state(state))

    def save_snapshot(self, slot: str, snapshot) -> None:
        """Commit state, history references and new blocks in one transaction."""
        from uuid import uuid4
        from production_zero.persistence.history_store import write_history
        revision = uuid4().hex
        ordinary = {key: value for key, value in snapshot.items()
                    if key not in ('history', 'history_elapsed_seconds', 'inventory_history')}
        ordinary['_history_storage'] = 1
        ordinary['_history_revision'] = revision
        encoded = json.dumps(ordinary, separators=(',', ':'), sort_keys=True)
        with closing(sqlite3.connect(self._path)) as connection, connection:
            connection.execute(
                'INSERT INTO saves(slot, state_json) VALUES (?, ?) '
                'ON CONFLICT(slot) DO UPDATE SET state_json=excluded.state_json', (slot, encoded))
            write_history(connection, slot, revision, snapshot)

    def save_payload(self, slot: str, payload: str) -> None:
        """Atomically commit an immutable snapshot; safe on a dedicated writer."""
        with closing(sqlite3.connect(self._path)) as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO saves (slot, state_json) VALUES (?, ?)",
                (slot, payload),
            )
            # Explicit JSON imports are complete replacements, not partial saves.
            from production_zero.persistence.history_store import delete_history
            delete_history(connection, slot)

    def load(self, slot: str) -> GameState:
        with closing(sqlite3.connect(self._path)) as connection, connection:
            # Pin all reads to one SQLite snapshot, even if another writer commits.
            connection.execute('BEGIN')
            row = connection.execute("SELECT state_json FROM saves WHERE slot = ?", (slot,)).fetchone()
            payload = json.loads(row[0]) if row is not None else None
            if payload is not None and '_history_storage' in payload:
                from production_zero.persistence.history_store import read_history
                read_history(connection, slot, payload)
            if payload is not None:
                _validate_ruleset(payload)
            if payload is not None and (int(payload.get("state_schema_version", 1)) < STATE_SCHEMA_VERSION or int(payload.get("economy_version", 1)) < 2 or int(payload.get('infrastructure_pricing_version', 0)) < PRICING_VERSION):
                version=int(payload.get('state_schema_version',1))
                backup_suffix = '.pre-economy-n1-c2.sqlite' if version>=STATE_SCHEMA_VERSION else '.pre-industriova-v9.sqlite' if version>=8 else '.pre-industriova-v8.sqlite' if version>=7 else '.pre-industriova-v7.sqlite' if version>=6 else '.pre-industriova-v5.sqlite'
                if version >= STATE_SCHEMA_VERSION and int(payload.get('economy_version', 1)) >= 2:
                    backup_suffix = '.pre-infrastructure-v2.sqlite'
                backup_path = self._path.with_name(self._path.stem + backup_suffix)
                if not backup_path.exists():
                    from tempfile import NamedTemporaryFile
                    import os
                    with NamedTemporaryFile(dir=self._path.parent, suffix=".sqlite", delete=False) as handle:
                        temporary = Path(handle.name)
                    try:
                        with closing(sqlite3.connect(temporary)) as backup:
                            connection.backup(backup)
                            if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                                raise ValueError("Pre-migration backup failed its integrity check.")
                        os.replace(temporary, backup_path)
                    finally:
                        temporary.unlink(missing_ok=True)
        if row is None:
            raise KeyError(f"Unknown save slot: {slot}")
        return deserialize_game_state(payload)


def serialize_game_state(state: GameState, *, frozen_history=False, include_histories=True) -> dict[str, object]:
    payload = {
        "game_ruleset": GAME_RULESET,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "economy_version": state.economy_version,
        "infrastructure_pricing_version": PRICING_VERSION,
        "infrastructure_tiers": infrastructure_tier_snapshot(state),
        "building_order": {kind: list(ids) for kind, ids in state.building_order.items()},
        "rng_seed": state.rng_seed,
        "tick": state.tick,
        "cash": asdict(state.cash),
        "statistics": asdict(state.statistics),
        "inventory_storage_level": state.inventory_storage_level,
        "warehouse_capacity": state.warehouse_capacity or sum(max(0.0, stock.capacity) for stock in state.resources.values()),
        "research": research_to_dict(state.research),
        "scrap": asdict(state.scrap),
        "company": {
            "level": state.company.level,
            "current_xp": state.company.current_xp,
            "selected_title": state.company.selected_title,
            "achievement_titles": state.company.achievement_titles,
            "pending_rewards": [asdict(reward) for reward in state.company.pending_rewards],
        },
        "company_xp_progress": {
            **asdict(state.company_xp_progress),
            "efficiency_milestones": sorted(state.company_xp_progress.efficiency_milestones),
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
        "inventory_history": asdict(state.inventory_history) if include_histories else None,
        "history_elapsed_seconds": state.history.elapsed_seconds,
        "history": state.history.to_payload(frozen=frozen_history) if include_histories else None,
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
            "priorities": dict(state.contracts.priorities),
            "regular_auto": {**asdict(state.contracts.regular_auto),
                             "resource_ids": list(state.contracts.regular_auto.resource_ids)},
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
            "weekly_period_index": state.contracts.weekly_period_index,
            "daily_period_index": state.contracts.daily_period_index,
            "regular_generation": state.contracts.regular_generation,
            "last_status": state.contracts.last_status,
        },
        "supply": {
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
        "production_progress": {
            "schema_version": state.production_progress.schema_version,
            "lifetime_produced": state.production_progress.lifetime_produced,
            "unlocked_production_ids": sorted(state.production_progress.unlocked_production_ids),
            "pending_unlock_ids": list(state.production_progress.pending_unlock_ids),
            "first_produced_resource_ids": sorted(state.production_progress.first_produced_resource_ids),
            "mastered_family_ids": sorted(state.production_progress.mastered_family_ids),
        },
        "communications": {
            "next_order": state.communications.next_order,
            "messages": [
                {
                    "message_id": message.message_id,
                    "event_type": message.event_type,
                    "title": message.title,
                    "item_ids": list(message.item_ids),
                    "created_order": message.created_order,
                    "read": message.read,
                }
                for message in state.communications.messages
            ],
        },
        "consortium": consortium_to_dict(state.consortium),
        "freight": {
            "facilities": {
                facility_id: {
                    "facility_id": facility.facility_id,
                    "name": facility.name,
                    "facility_type": facility.facility_type,
                    "slot_count": facility.slot_count,
                    "expansion_level": facility.expansion_level,
                    "building_investment": facility.building_investment,
                    "expansion_tier": facility.expansion_tier,
                    "paused": facility.paused,
                    "paused_lines": sorted(facility.paused_lines),
                    "line_capacity": facility.line_capacity,
                    "purchased_slot_indexes": sorted(facility.unlocked_slot_indexes()),
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
            "delivery_statistics": state.freight.delivery_statistics.snapshot(),
        },
        "halls": _serialize_production_units(state.halls),
        "resource_sites": _serialize_production_units(state.resource_sites),
        "energy_plants": _serialize_production_units(state.energy_plants),
    }
    if not include_histories:
        for key in ('history', 'history_elapsed_seconds', 'inventory_history'):
            payload.pop(key)
    return payload


def _serialize_production_units(units: dict[str, FactoryHall]) -> dict[str, object]:
    return {
        unit_id: {
            "hall_id": unit.hall_id,
            "expansion_tier": unit.expansion_tier,
            "name": unit.name,
            "slot_count": unit.slot_count,
            "specialization": unit.specialization,
            "slots": [asdict(slot) for slot in unit.slots],
            "production_lines": [asdict(line) for line in unit.production_lines],
            "board_kind": unit.board_kind,
            "max_lines": unit.max_lines,
            "max_slots_per_line": unit.max_slots_per_line,
            "start_unlocked_lines": unit.start_unlocked_lines,
            "start_slots_per_line": unit.start_slots_per_line,
            "building_investment": unit.building_investment,
            "paused": unit.paused,
        }
        for unit_id, unit in units.items()
    }


def _bounded_history_numbers(values):
    # Preserve frozen block boundaries for current saves; only oversized imports
    # need a trailing slice before constructing the bounded live buffers.
    return values if len(values) <= DEFAULT_HISTORY_MAX_POINTS else values[-DEFAULT_HISTORY_MAX_POINTS:]


def deserialize_game_state(payload: dict[str, object]) -> GameState:
    _validate_ruleset(payload)
    if int(payload.get("state_schema_version", 1)) > STATE_SCHEMA_VERSION:
        raise ValueError("Save was created by a newer Industriova version.")
    cards = {
        card_id: CardInstance(
            card_id=card_data["card_id"],
            definition_id=normalize_legacy_card_definition_id(card_data["definition_id"]),
            card_kind=CardKind(card_data["card_kind"]),
            rarity=Rarity(card_data["rarity"]),
            output_bonus_percent=float(card_data["output_bonus_percent"]),
            power_bonus_percent=float(card_data["power_bonus_percent"]),
            trade_state=TradeState(card_data["trade_state"]),
            collectible_token_id=card_data["collectible_token_id"],
            mk_level=legacy_mk_level(card_data),
            acquisition_cost=card_data.get("acquisition_cost"),
            upgrade_investment=float(card_data.get("upgrade_investment", 0.0)),
            paused=bool(card_data.get("paused", False)),
        )
        for card_id, card_data in payload["cards"].items()
        if card_data.get("card_kind") != "recipe" and not card_data.get("definition_id", "").startswith("recipe.")
    }
    if int(payload.get('infrastructure_pricing_version',0))>PRICING_VERSION:
        raise ValueError('Save uses a newer infrastructure pricing version.')
    source_schema_version = int(payload.get("state_schema_version", 1))
    halls = _deserialize_production_units(payload["halls"], cards, "factory", legacy=source_schema_version < 2)
    resource_sites = _deserialize_production_units(payload.get("resource_sites", {}), cards, "resources")
    energy_plants = _deserialize_production_units(payload.get("energy_plants", {}), cards, "energy")
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
                values=_bounded_history_numbers(series_data["values"]),
                timestamps=_bounded_history_numbers(series_data.get("timestamps", ())),
                bucket_id=series_data.get("bucket_id"),
                bucket_total=float(series_data.get("bucket_total", 0.0)),
                bucket_weight=float(series_data.get("bucket_weight", 0.0)),
            )
            for metric_id, series_data in payload.get("history", {}).items()
        },
        elapsed_seconds=float(payload.get("history_elapsed_seconds", 0.0)),
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
            priorities=dict(contracts_payload.get('priorities', {})),
            regular_auto=RegularContractAutomation(**contracts_payload.get('regular_auto', {})),
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
                        production_value_budget=(
                            None
                            if offer_data.get("production_value_budget") is None
                            else float(offer_data["production_value_budget"])
                        ),
                        selected_resource_id=offer_data.get("selected_resource_id"),
                        difficulty=str(offer_data.get("difficulty", "medium")),
                        balance_version=int(offer_data.get("balance_version",0)),
                        capacity_rates=dict(offer_data.get("capacity_rates",{})),
                        unit_prices=dict(offer_data.get("unit_prices",{})),
                        unit_cash=dict(offer_data.get("unit_cash",{})),
                        target_minutes=float(offer_data.get("target_minutes",0.)),
                        quoted_level=int(offer_data.get("quoted_level",0)),
                        reward_rp=offer_data.get("reward_rp"),
                        capacity_signature=str(offer_data.get("capacity_signature","")),
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
                        production_value_budget=(
                            None
                            if active_data["offer"].get("production_value_budget") is None
                            else float(active_data["offer"]["production_value_budget"])
                        ),
                        selected_resource_id=active_data["offer"].get("selected_resource_id"),
                        difficulty=str(active_data["offer"].get("difficulty", "medium")),
                        balance_version=int(active_data["offer"].get("balance_version",0)),
                        capacity_rates=dict(active_data["offer"].get("capacity_rates",{})),
                        unit_prices=dict(active_data["offer"].get("unit_prices",{})),
                        unit_cash=dict(active_data["offer"].get("unit_cash",{})),
                        target_minutes=float(active_data["offer"].get("target_minutes",0.)),
                        quoted_level=int(active_data["offer"].get("quoted_level",0)),
                        reward_rp=active_data["offer"].get("reward_rp"),
                        capacity_signature=str(active_data["offer"].get("capacity_signature","")),
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
    company_xp_payload = payload.get("company_xp_progress", {})
    company_xp_progress = CompanyXpProgress()
    if isinstance(company_xp_payload, dict):
        company_xp_progress = CompanyXpProgress(
            schema_version=int(company_xp_payload.get("schema_version", 1)),
            utc_day_index=int(company_xp_payload.get("utc_day_index", -1)),
            utc_week_index=int(company_xp_payload.get("utc_week_index", -1)),
            utc_high_water_timestamp=float(company_xp_payload.get("utc_high_water_timestamp", 0.0)),
            efficiency_production_value=float(company_xp_payload.get("efficiency_production_value", 0.0)),
            efficiency_milestones={int(value) for value in company_xp_payload.get("efficiency_milestones", [])},
            regular_full_xp_completions=int(company_xp_payload.get("regular_full_xp_completions", 0)),
            xp_by_source={
                str(source): float(amount)
                for source, amount in company_xp_payload.get("xp_by_source", {}).items()
            },
            last_productive_bucket=int(company_xp_payload.get("last_productive_bucket", -1)),
            productive_event_seconds=float(company_xp_payload.get("productive_event_seconds", 0.0)),
        )
    supply_payload = payload.get("supply", {})
    supply = SupplyBook()
    if isinstance(supply_payload, dict):
        supply = SupplyBook(
            freight_daily_period_index=int(supply_payload.get("freight_daily_period_index", -1)),
            freight_daily_offers=[
                SupplyOffer(
                    offer_id=offer_data["offer_id"],
                    definition_id=normalize_legacy_card_definition_id(offer_data["definition_id"]),
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
                if offer_data.get("card_kind") == "freight"
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
                    definition_id=normalize_legacy_card_definition_id(offer_data["definition_id"]),
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
                if offer_data.get("card_kind") in ("machine", "energy")
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
                    definition_id=normalize_legacy_card_definition_id(card_data["definition_id"]),
                    card_kind=CardKind(card_data["card_kind"]),
                    rarity=Rarity(card_data["rarity"]),
                    output_bonus_percent=float(card_data["output_bonus_percent"]),
                    power_bonus_percent=float(card_data["power_bonus_percent"]),
                    trade_state=TradeState(card_data["trade_state"]),
                    collectible_token_id=card_data["collectible_token_id"],
            mk_level=legacy_mk_level(card_data),
            acquisition_cost=card_data.get("acquisition_cost"),
            upgrade_investment=float(card_data.get("upgrade_investment", 0.0)),
            paused=bool(card_data.get("paused", False)),
                )
                for card_data in packs_payload.get("last_opened_cards", [])
                if card_data.get("card_kind") != "recipe" and not card_data.get("definition_id", "").startswith("recipe.")
            ],
        )
    progress_payload = payload.get("production_progress")
    production_progress = ProductionProgress()
    if isinstance(progress_payload, dict) and progress_payload:
        production_progress = ProductionProgress(
            schema_version=int(progress_payload.get("schema_version", 1)),
            lifetime_produced={
                str(resource_id): float(amount)
                for resource_id, amount in progress_payload.get("lifetime_produced", {}).items()
            },
            unlocked_production_ids={
                str(production_id)
                for production_id in progress_payload.get("unlocked_production_ids", [])
            },
            pending_unlock_ids=[
                str(production_id)
                for production_id in progress_payload.get("pending_unlock_ids", [])
            ],
            first_produced_resource_ids={
                str(resource_id)
                for resource_id in progress_payload.get("first_produced_resource_ids", [])
            },
            mastered_family_ids={
                str(family_id)
                for family_id in progress_payload.get("mastered_family_ids", [])
            },
        )
    else:
        production_progress.lifetime_produced = {
            resource_id: stock.amount
            for resource_id, stock in resources.items()
            if stock.amount > 0
        }
        production_progress.unlocked_production_ids.update(
            str(machine_state.get("selected_production_id"))
            for machine_state in payload.get("machine_production", {}).values()
            if machine_state.get("selected_production_id")
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
                    building_investment=float(facility_data.get("building_investment", 0.0)),
                    expansion_tier=facility_data.get("expansion_tier", 1),
                    paused=bool(facility_data.get("paused", False)),
                    paused_lines={int(n) for n in facility_data.get("paused_lines", [])},
                    line_capacity=int(facility_data.get("line_capacity", 0)),
                    purchased_slot_indexes={int(i) for i in facility_data['purchased_slot_indexes']} if source_schema_version>=8 and 'purchased_slot_indexes' in facility_data else None,
                    slots=[
                            FreightSlot(index=int(slot["index"]), card_id=slot["card_id"] if slot["card_id"] in cards else None)
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
                        freight_definition_id=(
                            normalize_legacy_card_definition_id(shipment_data["freight_definition_id"])
                            if shipment_data.get("freight_definition_id") else None
                        ),
                        freight_type=shipment_data.get("freight_type"),
                        transport_capacity=float(shipment_data.get("transport_capacity", 0.0)),
                        transport_time_seconds=float(shipment_data.get("transport_time_seconds", 0.0)),
                        remaining_seconds=float(shipment_data.get("remaining_seconds", 0.0)),
                        market_price=float(shipment_data.get("market_price", 0.0)),
                        active=bool(shipment_data.get("active", True)),
                        source_facility_id=shipment_data.get("source_facility_id"),
                        economic_processed=bool(shipment_data.get("economic_processed", False)),
                        contract_allocations=dict(shipment_data.get('contract_allocations', {})),
                        cancelled_contract_prices=dict(shipment_data.get('cancelled_contract_prices', {})),
                    )
                    for shipment_id, shipment_data in freight_payload.get("outbound_shipments", {}).items()
                },
                assignments={
                    card_id: FreightAssignment(
                        resource_id=assignment_data["resource_id"],
                        destination_kind=assignment_data["destination_kind"],
                    )
                    for card_id, assignment_data in freight_payload.get("assignments", {}).items()
                },
                next_shipment_sequence=int(freight_payload.get("next_shipment_sequence", 0)),
                delivery_statistics=FreightDeliveryStatistics.from_snapshot(freight_payload.get("delivery_statistics", {})) if source_schema_version >= 7 else FreightDeliveryStatistics(),
            )
        if source_schema_version < 7:
            from production_zero.core.freight import freight_card_facility_id
            for shipment in freight.outbound_shipments.values():
                shipment.source_facility_id = freight_card_facility_id(freight, shipment.freight_card_id)
    communications_payload = payload.get("communications", {})
    communications = CompanyCommunications()
    if isinstance(communications_payload, dict):
        communications = CompanyCommunications(
            messages=[
                CompanyMessage(
                    message_id=str(message["message_id"]),
                    event_type=str(message.get("event_type", "system")),
                    title=str(message.get("title", "COMPANY COMMUNICATION")),
                    item_ids=tuple(str(item) for item in message.get("item_ids", ())),
                    created_order=int(message.get("created_order", index + 1)),
                    read=bool(message.get("read", False)),
                )
                for index, message in enumerate(communications_payload.get("messages", ()))
                if isinstance(message, dict) and "message_id" in message
            ],
            next_order=int(communications_payload.get("next_order", 1)),
        )
    state = GameState(
        rng_seed=int(payload["rng_seed"]),
        tick=int(payload["tick"]),
        cash=CashWallet(amount=float(cash_payload["amount"])),
        statistics=AccountStatistics(total_earnings=float(statistics_payload.get("total_earnings", 0.0))),
        scrap=IndustrialScrapWallet(amount=int(scrap_payload.get("amount", 0))),
        company=company,
        company_xp_progress=company_xp_progress,
        research=research_from_dict(payload.get("research")),
        resources=resources,
        energy=EnergyState(
            generated=float(energy_payload["generated"]),
            consumed=float(energy_payload["consumed"]),
        ),
        market=market,
        history=history,
        inventory_history=InventoryHistory.from_payload(payload.get("inventory_history", {})),
        cards=cards,
        halls=halls,
        resource_sites=resource_sites,
        energy_plants=energy_plants,
        machine_production={
            card_id: MachineProductionState(
                card_id=machine_state["card_id"],
                target_resource_id=machine_state["target_resource_id"],
                selected_production_id=machine_state.get("selected_production_id"),
                progress_seconds=float(machine_state["progress_seconds"]),
                status=machine_state["status"],
            )
            for card_id, machine_state in payload.get("machine_production", {}).items()
            if card_id in cards
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
        production_progress=production_progress,
        communications=communications,
        consortium=consortium_from_dict(payload.get("consortium")),
        freight=freight,
        inventory_storage_level=int(payload.get("inventory_storage_level", 0)),
        warehouse_capacity=float(payload.get("warehouse_capacity", 0.0)),
        infrastructure_tiers=dict(payload.get("infrastructure_tiers", {})),
        building_order={kind: list(ids) for kind, ids in payload.get('building_order', {}).items()},
    )
    from importlib.resources import files
    from production_zero.data.definitions import load_card_definitions

    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    migrate_production_boards(state, definitions, source_schema_version)
    migrate_production_progress(
        state,
        definitions,
        legacy_without_progress=not (isinstance(progress_payload, dict) and bool(progress_payload)),
    )
    from production_zero.core.release_migration import migrate_release_state
    migrate_release_state(state)
    state.economy_version = int(payload.get('economy_version', 1))
    from production_zero.core.economy_migration import migrate_economy
    migrate_economy(state)
    from production_zero.core.infrastructure_prices import migrate_infrastructure_pricing
    from production_zero.data.definitions import load_resource_definitions
    resource_definitions = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    migrate_infrastructure_pricing(state, int(payload.get('infrastructure_pricing_version', 0)), resource_definitions)
    from production_zero.core.supply import reprice_pending_freight_offers
    reprice_pending_freight_offers(state.supply,definitions)
    return state


def _deserialize_production_units(payload, cards, board_kind: str, *, legacy: bool = False) -> dict[str, FactoryHall]:
    units = {}
    for unit_id, unit_data in payload.items():
        default_max_lines = 6 if legacy and board_kind == "factory" else (3 if board_kind != "factory" else 5)
        default_max_slots = 5 if board_kind == "energy" else 10
        default_start_lines = 1 if board_kind != "factory" else 2
        default_start_slots = 1 if board_kind != "factory" else 3
        units[unit_id] = FactoryHall(
            hall_id=unit_data["hall_id"],
            name=unit_data["name"],
            building_investment=float(unit_data.get("building_investment", 0.0)),
            expansion_tier=unit_data.get("expansion_tier", 1),
            paused=bool(unit_data.get("paused", False)),
            slot_count=int(unit_data["slot_count"]),
            specialization=unit_data.get("specialization"),
            slots=[HallSlot(index=int(slot["index"]), card_id=slot["card_id"] if slot["card_id"] in cards else None) for slot in unit_data["slots"]],
            production_lines=[
                ProductionLine(
                    line_id=line["line_id"], name=line["name"],
                    slot_indexes=[int(index) for index in line["slot_indexes"]],
                    unlocked=bool(line["unlocked"]), unlock_cost=float(line.get("unlock_cost", 0.0)),
                    paused=bool(line.get("paused", False)),
                ) for line in unit_data.get("production_lines", [])
            ],
            board_kind=unit_data.get("board_kind", board_kind),
            max_lines=int(unit_data.get("max_lines", default_max_lines)),
            max_slots_per_line=int(unit_data.get("max_slots_per_line", default_max_slots)),
            start_unlocked_lines=int(unit_data.get("start_unlocked_lines", default_start_lines)),
            start_slots_per_line=int(unit_data.get("start_slots_per_line", default_start_slots)),
        )
    return units


def _new_split_unit(board_kind: str) -> FactoryHall:
    if board_kind == "resources":
        return FactoryHall("site-1", "Site 1", 1, board_kind=board_kind, max_lines=3, max_slots_per_line=10, start_unlocked_lines=1, start_slots_per_line=1)
    return FactoryHall("plant-1", "Plant 1", 1, board_kind=board_kind, max_lines=3, max_slots_per_line=5, start_unlocked_lines=1, start_slots_per_line=1)


def migrate_production_boards(state: GameState, definitions: dict[str, object], source_schema_version: int) -> None:
    """Losslessly separate legacy Hall ownership and remove Factory Line 6."""
    from production_zero.core.definitions import EnergyDefinition, MachineDefinition
    from production_zero.core.enums import MachineType
    from production_zero.data.definitions import primary_machine_type_for_resource

    if not state.resource_sites:
        state.resource_sites["site-1"] = _new_split_unit("resources")
    if not state.energy_plants:
        state.energy_plants["plant-1"] = _new_split_unit("energy")
    if source_schema_version >= PRODUCTION_BOARD_SCHEMA_VERSION:
        _repair_split_board_ownership(state, definitions)
        return

    moving_primary: list[str] = []
    moving_energy: list[str] = []
    displaced_factory: list[str] = []
    for hall in state.halls.values():
        valid_indexes = {index for line in hall.production_lines[:5] if line.unlocked for index in line.slot_indexes[:10]}
        for slot in hall.slots:
            if slot.card_id is None:
                continue
            card = state.cards[slot.card_id]
            definition = definitions.get(card.definition_id)
            if isinstance(definition, EnergyDefinition):
                moving_energy.append(card.card_id)
                slot.card_id = None
            elif isinstance(definition, MachineDefinition) and definition.machine_type in {
                MachineType.EXTRACTOR, MachineType.DRILLING, MachineType.AGRICULTURE,
            }:
                moving_primary.append(card.card_id)
                slot.card_id = None
            elif slot.index not in valid_indexes:
                displaced_factory.append(card.card_id)
                slot.card_id = None
        hall.production_lines = hall.production_lines[:5]
        hall.max_lines = 5
        hall.max_slots_per_line = 10
        hall.board_kind = "factory"
        hall.slot_count = sum(len(line.slot_indexes[:10]) for line in hall.production_lines if line.unlocked)

    for card_id in moving_primary:
        card = state.cards[card_id]
        machine_state = state.machine_production.get(card_id)
        resource_id = machine_state.target_resource_id if machine_state is not None else ""
        family = primary_machine_type_for_resource(resource_id)
        target_definition_id = {
            MachineType.EXTRACTOR: "machine.extractor",
            MachineType.DRILLING: "machine.drilling",
            MachineType.AGRICULTURE: "machine.agriculture",
        }[family]
        if card.definition_id != target_definition_id:
            state.cards[card_id] = replace(card, definition_id=target_definition_id)
        _place_in_first_free_slot(state.resource_sites, card_id)
    for card_id in moving_energy:
        _place_in_first_free_slot(state.energy_plants, card_id)
    for card_id in displaced_factory:
        _place_in_first_free_slot(state.halls, card_id)
    _repair_split_board_ownership(state, definitions)


def _repair_split_board_ownership(state: GameState, definitions: dict[str, object]) -> None:
    """Remove invalid placements from current saves and relocate them losslessly."""
    from production_zero.core.definitions import EnergyDefinition, MachineDefinition
    from production_zero.core.enums import MachineType

    primary_types = {MachineType.EXTRACTOR, MachineType.DRILLING, MachineType.AGRICULTURE}
    downstream_types = {MachineType.PROCESSOR, MachineType.FABRICATOR, MachineType.ASSEMBLER}
    destinations: dict[str, dict[str, FactoryHall]] = {
        "factory": state.halls,
        "resources": state.resource_sites,
        "energy": state.energy_plants,
    }
    displaced: list[tuple[str, str | None]] = []
    for actual_board, units in destinations.items():
        for unit in units.values():
            for slot in unit.slots:
                if slot.card_id is None:
                    continue
                card = state.cards.get(slot.card_id)
                definition = definitions.get(card.definition_id) if card is not None else None
                expected_board: str | None = None
                if isinstance(definition, EnergyDefinition):
                    expected_board = "energy"
                elif isinstance(definition, MachineDefinition) and definition.machine_type in primary_types:
                    expected_board = "resources"
                elif isinstance(definition, MachineDefinition) and definition.machine_type in downstream_types:
                    expected_board = "factory"
                if expected_board != actual_board:
                    displaced.append((slot.card_id, expected_board))
                    slot.card_id = None
    for card_id, expected_board in displaced:
        if expected_board is not None:
            _place_in_first_free_slot(destinations[expected_board], card_id)


def _place_in_first_free_slot(units: dict[str, FactoryHall], card_id: str) -> bool:
    for unit in units.values():
        for index in sorted(unit.unlocked_slot_indexes()):
            if unit.slots[index].card_id is None:
                unit.slots[index].card_id = card_id
                return True
    return False
