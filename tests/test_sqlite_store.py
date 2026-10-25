from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.commands import AcceptContract, AddCard, AddCash, AddIndustrialScrap, AddResource, AssignFreightCard, BuildHall, CommandBus, ConfigureAutoSell, DeliverAvailableToContract, ExpandInventoryStorage, InstallCardInHall, InstallFreightCard, PurchaseHall, RecordMetric, RenameHall, SetResourceCapacity, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.contracts import REGULAR, contract_requirements_for_selection, initialize_contracts
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack, open_pack
from production_zero.core.production_values import contract_required_amount, production_value_for_resource
from production_zero.core.progression import initialize_production_progress
from production_zero.core.state import FactoryHall, GameState
from production_zero.core.supply import refresh_supply
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def test_sqlite_store_roundtrips_game_state(tmp_path) -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resource_definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=42)
    bus = CommandBus(state)
    bus.dispatch(AddCash(100))
    bus.dispatch(AddCash(500))
    bus.dispatch(ExpandInventoryStorage(resource_definitions))
    bus.dispatch(AddIndustrialScrap(42))
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(AddResource("iron_ore", 25))
    bus.dispatch(ConfigureAutoSell("iron_ore", True, 70))
    initialize_production_progress(state, definitions)
    initialize_contracts(state)
    offer = state.contracts.offers[REGULAR][0]
    contract_resource_id = "iron_ore"
    value = production_value_for_resource(definitions, contract_resource_id)
    assert value is not None
    required = contract_required_amount(offer.production_value_budget or 0.0, value.value_per_unit)
    bus.dispatch(SetResourceCapacity(contract_resource_id, required * 2))
    bus.dispatch(AddResource(contract_resource_id, required / 2))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(AddResource("coal", 1))
    freight_card = create_card_instance("save-ship", "freight.ship", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(freight_card))
    harbor_id = build_freight_facility(state.freight, "harbor").facility_id
    bus.dispatch(InstallFreightCard(harbor_id, 0, freight_card.card_id, definitions))
    bus.dispatch(AssignFreightCard(freight_card.card_id, contract_resource_id, "contract"))
    bus.dispatch(AcceptContract(REGULAR, offer.contract_id, definitions, contract_resource_id))
    accepted_requirements = dict(state.contracts.active[REGULAR].offer.requirements)
    accepted_xp = state.contracts.active[REGULAR].offer.reward_xp
    bus.dispatch(DeliverAvailableToContract(REGULAR, definitions))
    expected_shipment_quantity = next(iter(state.freight.outbound_shipments.values())).quantity
    expected_iron_ore_amount = state.resources["iron_ore"].amount
    state.market.ensure_resource("iron_ore").current_price = 1.75
    state.market.market_tick = 4
    bus.dispatch(RecordMetric("cash", 100))
    state.statistics.total_earnings = 3210
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=3)))
    bus.dispatch(AddCash(18_840))
    bus.dispatch(UnlockProductionLine("hall-1", "hall-1.line-3"))
    bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))
    bus.dispatch(PurchaseHall())
    bus.dispatch(RenameHall("hall-2", "Coal Annex"))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="card-1",
                definition_id="machine.extractor",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.EPIC,
                output_bonus_percent=13.7,
                power_bonus_percent=13.7,
            )
        )
    )
    bus.dispatch(
        AddCard(
            create_card_instance(
                "rare-card",
                "machine.extractor",
                CardKind.MACHINE,
                Rarity.RARE,
                bonus_tenths=74,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="card-2",
                definition_id="machine.extractor",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.EPIC,
                output_bonus_percent=13.7,
                power_bonus_percent=13.7,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "card-1"))
    machine_state = state.ensure_machine_production("card-1", "coal", "resource.coal")
    machine_state.progress_seconds = 1.5
    state.production_progress.lifetime_produced["coal"] = 144
    state.production_progress.unlocked_production_ids.update({"resource.coal", "recipe.processor.steel"})
    refresh_supply(state, definitions)
    state.supply.machine_daily_purchased_period_index = state.supply.machine_daily_period_index
    state.supply.machine_daily_purchased_offer_id = state.supply.machine_daily_offers[1].offer_id
    state.supply.freight_daily_purchased_period_index = state.supply.freight_daily_period_index
    state.supply.freight_daily_purchased_offer_id = state.supply.freight_daily_offers[1].offer_id
    state.supply.machine_daily_purchased_period_index = state.supply.machine_daily_period_index
    state.supply.machine_daily_purchased_offer_id = state.supply.machine_daily_offers[1].offer_id
    grant_pack(state, DAILY_MINI_PACK, "save-test")
    opened_pack_id = grant_pack(state, FULL_PACK, "save-test")
    open_pack(state, definitions, opened_pack_id, "general")

    store = SQLiteSaveStore(tmp_path / "save.sqlite3")
    store.initialize()
    store.save("slot-1", state)

    loaded = store.load("slot-1")

    assert loaded.rng_seed == 42
    assert loaded.cash.amount == 350
    assert loaded.statistics.total_earnings == 3210
    assert loaded.inventory_storage_level == 1
    assert loaded.warehouse_capacity == state.warehouse_capacity
    assert loaded.scrap.amount == 42
    assert loaded.resources["iron_ore"].amount == expected_iron_ore_amount
    assert loaded.resources["iron_ore"].capacity == required * 2
    assert loaded.auto_sell["iron_ore"].enabled is True
    assert loaded.auto_sell["iron_ore"].threshold_percent == 70
    assert loaded.contracts.active[REGULAR].offer.contract_id == offer.contract_id
    assert loaded.contracts.active[REGULAR].offer.reward_xp == accepted_xp
    assert loaded.contracts.active[REGULAR].offer.production_value_budget == offer.production_value_budget
    assert loaded.contracts.active[REGULAR].offer.selected_resource_id == contract_resource_id
    assert loaded.contracts.active[REGULAR].offer.requirements == accepted_requirements
    assert loaded.contracts.active[REGULAR].delivered == {}
    shipment = next(iter(loaded.freight.outbound_shipments.values()))
    assert shipment.destination_kind == "contract"
    assert shipment.target_id == offer.contract_id
    assert shipment.resource_id == contract_resource_id
    assert shipment.quantity == expected_shipment_quantity
    assert len(loaded.contracts.offers[REGULAR]) == 1
    assert loaded.company.level == state.company.level
    assert loaded.company.current_xp == state.company.current_xp
    assert loaded.company.current_title == state.company.current_title
    assert loaded.supply.machine_daily_period_index == state.supply.machine_daily_period_index
    assert loaded.supply.machine_daily_purchased_offer_id == state.supply.machine_daily_purchased_offer_id
    assert [offer.offer_id for offer in loaded.supply.machine_daily_offers] == [
        offer.offer_id for offer in state.supply.machine_daily_offers
    ]
    assert loaded.supply.freight_daily_period_index == state.supply.freight_daily_period_index
    assert loaded.supply.freight_daily_purchased_offer_id == state.supply.freight_daily_purchased_offer_id
    assert [offer.offer_id for offer in loaded.supply.freight_daily_offers] == [
        offer.offer_id for offer in state.supply.freight_daily_offers
    ]
    assert loaded.supply.machine_daily_period_index == state.supply.machine_daily_period_index
    assert loaded.supply.machine_daily_purchased_offer_id == state.supply.machine_daily_purchased_offer_id
    assert [offer.offer_id for offer in loaded.supply.machine_daily_offers] == [
        offer.offer_id for offer in state.supply.machine_daily_offers
    ]
    assert [pack.pack_type for pack in loaded.packs.unopened] == []
    assert loaded.packs.opened_count == 1
    assert loaded.packs.last_opened_cards == []
    assert loaded.market.market_tick == 4
    assert loaded.market.resources["iron_ore"].current_price == 1.75
    assert loaded.history.values_for("cash") == (350.0, 100.0, 15590.0, 15550.0, 350.0)
    assert loaded.cards["card-1"].definition_id == "machine.extractor"
    assert loaded.cards["rare-card"].output_bonus_tenths == 74
    assert loaded.cards["rare-card"].power_bonus_tenths == 37
    assert loaded.cards["rare-card"].is_tradeable_by_rarity is True
    assert loaded.inventory_card_stacks()[0].quantity == 1
    assert loaded.halls["hall-1"].slot_count == 10
    assert loaded.halls["hall-1"].production_lines[0].slot_indexes == [0, 1, 2, 9]
    assert loaded.halls["hall-1"].production_lines[1].unlocked is True
    assert loaded.halls["hall-1"].production_lines[1].slot_indexes == [3, 4, 5]
    assert loaded.halls["hall-1"].production_lines[2].unlocked is True
    assert loaded.halls["hall-1"].production_lines[2].slot_indexes == [6, 7, 8]
    assert loaded.halls["hall-2"].name == "Coal Annex"
    assert loaded.halls["hall-2"].slot_count == 3
    assert loaded.halls["hall-2"].production_lines[0].unlocked is True
    assert loaded.halls["hall-2"].production_lines[2].unlocked is False
    assert loaded.machine_production["card-1"].selected_production_id == "resource.coal"
    assert loaded.machine_production["card-1"].target_resource_id == "coal"
    assert loaded.machine_production["card-1"].progress_seconds == 1.5
    assert loaded.production_progress.lifetime_produced["coal"] == 144
    assert "recipe.processor.steel" in loaded.production_progress.unlocked_production_ids


def test_sqlite_store_loads_legacy_save_without_inventory_storage_level(tmp_path) -> None:
    state = GameState(rng_seed=43)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(AddResource("iron_ore", 25))
    store = SQLiteSaveStore(tmp_path / "legacy.sqlite3")
    store.initialize()
    store.save("legacy", state)

    with sqlite3.connect(tmp_path / "legacy.sqlite3") as connection:
        payload = json.loads(connection.execute("SELECT state_json FROM saves WHERE slot = ?", ("legacy",)).fetchone()[0])
        payload.pop("inventory_storage_level", None)
        payload.pop("production_progress", None)
        connection.execute(
            "UPDATE saves SET state_json = ? WHERE slot = ?",
            (json.dumps(payload, sort_keys=True), "legacy"),
        )

    loaded = store.load("legacy")

    assert loaded.inventory_storage_level == 0
    assert loaded.resources["iron_ore"].amount == 25
    assert loaded.resources["iron_ore"].capacity == 500
    assert loaded.production_progress.lifetime_produced["iron_ore"] == 25
    assert "resource.iron_ore" in loaded.production_progress.unlocked_production_ids


def test_sqlite_store_preserves_large_card_stack_quantities(tmp_path) -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=44)
    bus = CommandBus(state)
    for index in range(150):
        bus.dispatch(
            AddCard(
                create_card_instance(
                    f"bulk-saved-drill-{index:03d}",
                    "machine.extractor",
                    CardKind.MACHINE,
                    Rarity.COMMON,
                )
            )
        )
    store = SQLiteSaveStore(tmp_path / "large-stack.sqlite")
    store.initialize()

    store.save("slot", state)
    loaded = store.load("slot")
    rows = build_card_inventory_rows(loaded, definitions)

    assert loaded.inventory_card_stacks()[0].quantity == 150
    assert [row.quantity for row in rows if row.definition.definition_id == "machine.extractor"] == [150]
