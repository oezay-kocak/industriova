from __future__ import annotations

import argparse
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from production_zero.core.cards import create_card_instance
from production_zero.core.contracts import DAILY, REGULAR, WEEKLY, accept_contract, deliver_available_to_contract, initialize_contracts, receive_contract_delivery, refresh_contracts
from production_zero.core.crafting import CRAFT_INPUT_COUNT, RARITY_CRAFT_UPGRADES, craft_rarity_card
from production_zero.core.definitions import CardDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import FreightSlot, advance_outbound_shipments, assign_freight_card, build_freight_facility, expand_freight_facility
from production_zero.core.mk_upgrades import next_mk_definition, upgrade_mk_card
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, open_pack
from production_zero.core.recycling import recycle_cards, scrap_value_for_card
from production_zero.core.state import GameState
from production_zero.core.supply import buy_common_supply_card, buy_daily_freight_supply_card, buy_daily_uncommon_supply_card, common_supply_offers, refresh_supply
from production_zero.data.definitions import load_card_definitions


SIMULATION_DAYS = 365
SIMULATION_PLAYERS = 10_000
DEFAULT_SEEDS = (101, 202, 303)
PERFECT_LEGENDARY_BONUS_TENTHS = 200


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    profile_id: str
    weight: float
    starting_cash: float
    regular_contracts_per_day: float
    daily_completion_chance: float
    weekly_completion_chance: float
    daily_supply_purchase_chance: float
    daily_freight_supply_purchase_chance: float
    common_supply_purchase_chance: float
    common_freight_supply_purchase_chance: float
    common_supply_per_purchase: int
    pack_open_chance: float
    recycle_chance_by_rarity: dict[Rarity, float]
    craft_attempt_chance: float
    mk_upgrade_attempt_chance: float
    inventory_maintenance_interval_days: int
    full_pack_category_weights: dict[str, float]


PLAYER_PROFILES: tuple[PlayerProfile, ...] = (
    PlayerProfile(
        profile_id="casual",
        weight=0.45,
        starting_cash=1_250.0,
        regular_contracts_per_day=0.4,
        daily_completion_chance=0.35,
        weekly_completion_chance=0.25,
        daily_supply_purchase_chance=0.2,
        daily_freight_supply_purchase_chance=0.1,
        common_supply_purchase_chance=0.08,
        common_freight_supply_purchase_chance=0.03,
        common_supply_per_purchase=1,
        pack_open_chance=0.85,
        recycle_chance_by_rarity={
            Rarity.COMMON: 0.45,
            Rarity.UNCOMMON: 0.08,
            Rarity.RARE: 0.01,
            Rarity.EPIC: 0.0,
            Rarity.LEGENDARY: 0.0,
        },
        craft_attempt_chance=0.08,
        mk_upgrade_attempt_chance=0.04,
        inventory_maintenance_interval_days=30,
        full_pack_category_weights={"general": 0.52, "extraction": 0.14, "processing": 0.14, "energy": 0.09, "recipes": 0.05, "freight": 0.06},
    ),
    PlayerProfile(
        profile_id="daily_optimizer",
        weight=0.3,
        starting_cash=2_000.0,
        regular_contracts_per_day=1.4,
        daily_completion_chance=0.82,
        weekly_completion_chance=0.7,
        daily_supply_purchase_chance=0.72,
        daily_freight_supply_purchase_chance=0.78,
        common_supply_purchase_chance=0.22,
        common_freight_supply_purchase_chance=0.18,
        common_supply_per_purchase=2,
        pack_open_chance=0.98,
        recycle_chance_by_rarity={
            Rarity.COMMON: 0.72,
            Rarity.UNCOMMON: 0.22,
            Rarity.RARE: 0.03,
            Rarity.EPIC: 0.0,
            Rarity.LEGENDARY: 0.0,
        },
        craft_attempt_chance=0.28,
        mk_upgrade_attempt_chance=0.18,
        inventory_maintenance_interval_days=14,
        full_pack_category_weights={"general": 0.25, "extraction": 0.25, "processing": 0.22, "energy": 0.11, "recipes": 0.07, "freight": 0.10},
    ),
    PlayerProfile(
        profile_id="collector",
        weight=0.18,
        starting_cash=5_000.0,
        regular_contracts_per_day=1.0,
        daily_completion_chance=0.68,
        weekly_completion_chance=0.82,
        daily_supply_purchase_chance=0.9,
        daily_freight_supply_purchase_chance=0.65,
        common_supply_purchase_chance=0.38,
        common_freight_supply_purchase_chance=0.2,
        common_supply_per_purchase=3,
        pack_open_chance=1.0,
        recycle_chance_by_rarity={
            Rarity.COMMON: 0.58,
            Rarity.UNCOMMON: 0.06,
            Rarity.RARE: 0.0,
            Rarity.EPIC: 0.0,
            Rarity.LEGENDARY: 0.0,
        },
        craft_attempt_chance=0.2,
        mk_upgrade_attempt_chance=0.12,
        inventory_maintenance_interval_days=21,
        full_pack_category_weights={"general": 0.6, "extraction": 0.09, "processing": 0.09, "energy": 0.09, "recipes": 0.05, "freight": 0.08},
    ),
    PlayerProfile(
        profile_id="power_user",
        weight=0.07,
        starting_cash=8_000.0,
        regular_contracts_per_day=3.0,
        daily_completion_chance=0.96,
        weekly_completion_chance=0.95,
        daily_supply_purchase_chance=0.98,
        daily_freight_supply_purchase_chance=0.98,
        common_supply_purchase_chance=0.62,
        common_freight_supply_purchase_chance=0.5,
        common_supply_per_purchase=5,
        pack_open_chance=1.0,
        recycle_chance_by_rarity={
            Rarity.COMMON: 0.82,
            Rarity.UNCOMMON: 0.36,
            Rarity.RARE: 0.06,
            Rarity.EPIC: 0.01,
            Rarity.LEGENDARY: 0.0,
        },
        craft_attempt_chance=0.55,
        mk_upgrade_attempt_chance=0.36,
        inventory_maintenance_interval_days=7,
        full_pack_category_weights={"general": 0.16, "extraction": 0.28, "processing": 0.23, "energy": 0.12, "recipes": 0.09, "freight": 0.12},
    ),
)


@dataclass(slots=True)
class StressStats:
    seed: int
    players: int
    days: int
    profiles: Counter[str] = field(default_factory=Counter)
    created_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    recycled_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    crafting_consumed_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    crafting_outputs_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    mk_upgrade_consumed_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    mk_upgrade_outputs_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    remaining_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    freight_created_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    freight_recycled_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    freight_crafting_consumed_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    freight_remaining_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    freight_created_by_family: Counter[str] = field(default_factory=Counter)
    freight_remaining_by_family: Counter[str] = field(default_factory=Counter)
    freight_created_by_family_rarity: Counter[tuple[str, Rarity]] = field(default_factory=Counter)
    freight_remaining_by_family_rarity: Counter[tuple[str, Rarity]] = field(default_factory=Counter)
    daily_freight_rotation_by_rarity: Counter[Rarity] = field(default_factory=Counter)
    scrap_generated: int = 0
    scrap_consumed: int = 0
    perfect_legendary_remaining: int = 0
    perfect_legendary_created: int = 0
    player_card_counts: list[int] = field(default_factory=list)
    player_legendary_counts: list[int] = field(default_factory=list)
    player_freight_card_counts: list[int] = field(default_factory=list)
    player_freight_legendary_counts: list[int] = field(default_factory=list)
    by_profile: dict[str, StressStats] = field(default_factory=dict, repr=False)

    @property
    def destroyed_cards(self) -> int:
        return sum(self.recycled_by_rarity.values()) + sum(self.crafting_consumed_by_rarity.values()) + sum(self.mk_upgrade_consumed_by_rarity.values())

    @property
    def total_created_cards(self) -> int:
        return sum(self.created_by_rarity.values())

    @property
    def net_supply_growth(self) -> int:
        return self.total_created_cards - self.destroyed_cards


def run_stress_test(
    *,
    players: int = SIMULATION_PLAYERS,
    days: int = SIMULATION_DAYS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    definitions_path: Path | None = None,
    processes: int = 1,
) -> list[StressStats]:
    definitions = load_card_definitions(definitions_path or Path("src/production_zero/data/game_definitions.json"))
    return [
        _run_seed(seed, players, days, definitions, processes)
        for seed in seeds
    ]


def _run_seed(seed: int, players: int, days: int, definitions: dict[str, CardDefinition], processes: int) -> StressStats:
    if processes <= 1 or players < 100:
        return _run_seed_player_range(seed, players, days, definitions, 0, players)
    chunk_size = max(1, players // processes)
    chunks = [
        (seed, players, days, definitions, start, min(players, start + chunk_size))
        for start in range(0, players, chunk_size)
    ]
    with ProcessPoolExecutor(max_workers=processes) as executor:
        return _combine_seed_chunks(list(executor.map(_run_seed_player_range_from_args, chunks)))


def _run_seed_player_range_from_args(args) -> StressStats:
    return _run_seed_player_range(*args)


def _run_seed_player_range(
    seed: int,
    players: int,
    days: int,
    definitions: dict[str, CardDefinition],
    start_player: int,
    end_player: int,
) -> StressStats:
    stats = StressStats(seed=seed, players=players, days=days)
    for player_index in range(start_player, end_player):
        profile = _choose_profile(random.Random(f"{seed}:profile-selection:{player_index}"))
        stats.profiles[profile.profile_id] += 1
        profile_stats = stats.by_profile.setdefault(
            profile.profile_id,
            StressStats(seed=seed, players=0, days=days),
        )
        profile_stats.players += 1
        player_seed = seed * 1_000_003 + player_index
        _simulate_player(player_seed, profile, days, definitions, profile_stats)
    for profile_stats in stats.by_profile.values():
        _merge_stats(stats, profile_stats, include_profile_breakdown=False)
    return stats


def _combine_seed_chunks(chunks: list[StressStats]) -> StressStats:
    if not chunks:
        return StressStats(seed=0, players=0, days=0)
    combined = StressStats(seed=chunks[0].seed, players=chunks[0].players, days=chunks[0].days)
    for chunk in chunks:
        _merge_stats(combined, chunk)
    return combined


def _simulate_player(
    player_seed: int,
    profile: PlayerProfile,
    days: int,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    rng = random.Random(f"{player_seed}:economy-stress")
    state = GameState(rng_seed=player_seed)
    state.cash.add(profile.starting_cash)
    initialize_contracts(state)
    _install_stress_contract_freight_fleet(state)
    common_offers = common_supply_offers(definitions)

    for day in range(days):
        state.market.elapsed_seconds = day * 86_400.0
        refresh_contracts(state)
        refresh_supply(state, definitions)
        _complete_regular_contracts(state, rng, profile, definitions, stats)
        _maybe_complete_contract(state, rng, DAILY, profile.daily_completion_chance, definitions, stats)
        if day % 7 == 0:
            _maybe_complete_contract(state, rng, WEEKLY, profile.weekly_completion_chance, definitions, stats)
        _maybe_buy_supply(state, rng, profile, definitions, common_offers, stats)
        _open_available_packs(state, rng, profile, definitions, stats)
        if _runs_inventory_maintenance(day, days, profile):
            _maybe_recycle_cards(state, rng, profile, stats)
            _maybe_craft_cards(state, rng, profile, definitions, stats)
            _maybe_upgrade_mk(state, rng, profile, definitions, stats)

    _record_remaining_player_state(state, definitions, stats)


def _runs_inventory_maintenance(day: int, total_days: int, profile: PlayerProfile) -> bool:
    return day == total_days - 1 or day % profile.inventory_maintenance_interval_days == 0


def _complete_regular_contracts(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    count = int(profile.regular_contracts_per_day)
    if rng.random() < profile.regular_contracts_per_day - count:
        count += 1
    for _ in range(count):
        _maybe_complete_contract(state, rng, REGULAR, 1.0, definitions, stats)


def _maybe_complete_contract(
    state: GameState,
    rng: random.Random,
    kind: str,
    chance: float,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    if rng.random() > chance:
        return
    refresh_contracts(state)
    offers = state.contracts.offers.get(kind, [])
    if not offers or kind in state.contracts.active:
        return
    offer = offers[rng.randrange(len(offers))]
    for resource_id, amount in offer.requirements.items():
        stock = state.ensure_resource(resource_id)
        stock.capacity = max(stock.capacity, amount)
        stock.add(amount)
    accept_contract(state, kind, offer.contract_id)
    _deliver_contract_with_stress_freight(state, kind, definitions)


def _install_stress_contract_freight_fleet(state: GameState) -> None:
    for facility_type in ("rail_station", "harbor"):
        if not any(facility.facility_type == facility_type for facility in state.freight.facilities.values()):
            build_freight_facility(state.freight, facility_type)
    assignments = (
        ("harbor", "freight.ship.class1", "iron_ore"),
        ("harbor", "freight.ship.class1", "coal"),
        ("harbor", "freight.ship.class1", "copper_ore"),
        ("rail_station", "freight.train.class1", "iron"),
        ("rail_station", "freight.train.class1", "copper"),
        ("rail_station", "freight.train.class1", "steel"),
    )
    for index, (facility_type, definition_id, resource_id) in enumerate(assignments):
        slot = _available_stress_freight_slot(state, facility_type)
        card_id = f"stress-freight-contract-{index}"
        state.cards[card_id] = create_card_instance(card_id, definition_id, CardKind.FREIGHT, Rarity.COMMON)
        slot.card_id = card_id
        assign_freight_card(state.freight, card_id, resource_id, "contract")


def _available_stress_freight_slot(state: GameState, facility_type: str) -> FreightSlot:
    facilities = [
        facility
        for facility in state.freight.facilities.values()
        if facility.facility_type == facility_type
    ]
    if not facilities:
        facilities.append(build_freight_facility(state.freight, facility_type))
    for facility in facilities:
        slot = _first_open_freight_slot(facility.slots)
        if slot is not None:
            return slot
    for facility in facilities:
        try:
            return expand_freight_facility(facility)
        except ValueError:
            continue
    return build_freight_facility(state.freight, facility_type).slots[0]


def _first_open_freight_slot(slots: list[FreightSlot]) -> FreightSlot | None:
    return next((slot for slot in slots if slot.card_id is None), None)


def _deliver_contract_with_stress_freight(
    state: GameState,
    kind: str,
    definitions: dict[str, CardDefinition],
) -> None:
    for _ in range(16):
        active = state.contracts.active.get(kind)
        if active is None or active.status == "completed":
            return
        try:
            deliver_available_to_contract(state, kind, definitions)
        except ValueError:
            return
        if not state.freight.outbound_shipments:
            return
        completed_shipments = advance_outbound_shipments(state.freight, 420)
        for shipment in completed_shipments:
            if shipment.destination_kind == "contract" and shipment.target_id and shipment.resource_id:
                receive_contract_delivery(state, shipment.target_id, shipment.resource_id, shipment.quantity)


def _maybe_buy_supply(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    definitions: dict[str, CardDefinition],
    common_offers,
    stats: StressStats,
) -> None:
    if state.supply.daily_offers and rng.random() < profile.daily_supply_purchase_chance:
        offer = max(state.supply.daily_offers, key=lambda item: (item.bonus_tenths, -item.price_cash))
        _capture_new_cards(stats, state, definitions, lambda: buy_daily_uncommon_supply_card(state, definitions, offer.offer_id))

    if state.supply.freight_daily_offers and rng.random() < profile.daily_freight_supply_purchase_chance:
        offer = max(state.supply.freight_daily_offers, key=lambda item: (item.bonus_tenths, -item.price_cash))
        _capture_new_cards(
            stats,
            state,
            definitions,
            lambda: buy_daily_freight_supply_card(state, definitions, offer.offer_id),
            source="daily_freight_rotation",
        )

    if common_offers and rng.random() < profile.common_supply_purchase_chance:
        for _ in range(profile.common_supply_per_purchase):
            affordable = [
                offer for offer in common_offers
                if offer.price_cash <= state.cash.amount and offer.card_kind is not CardKind.FREIGHT
            ]
            if not affordable:
                break
            offer = rng.choice(affordable)
            _capture_new_cards(stats, state, definitions, lambda offer=offer: buy_common_supply_card(state, definitions, offer.definition_id))

    if common_offers and rng.random() < profile.common_freight_supply_purchase_chance:
        affordable_freight = [
            offer for offer in common_offers
            if offer.price_cash <= state.cash.amount and offer.card_kind is CardKind.FREIGHT
        ]
        if affordable_freight:
            offer = rng.choice(affordable_freight)
            _capture_new_cards(stats, state, definitions, lambda offer=offer: buy_common_supply_card(state, definitions, offer.definition_id))


def _open_available_packs(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    for pack in tuple(state.packs.unopened):
        if rng.random() > profile.pack_open_chance:
            continue
        category_id = "general" if pack.pack_type == DAILY_MINI_PACK else _choose_weighted(rng, profile.full_pack_category_weights)
        _capture_new_cards(stats, state, definitions, lambda pack_id=pack.pack_id, category_id=category_id: open_pack(state, definitions, pack_id, category_id))


def _maybe_recycle_cards(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    stats: StressStats,
) -> None:
    selected = []
    for card in tuple(state.cards.values()):
        if _is_stress_freight_card(card.card_id):
            continue
        chance = profile.recycle_chance_by_rarity.get(card.rarity, 0.0)
        if chance > 0 and rng.random() < chance:
            selected.append(card.card_id)
    if not selected:
        return
    cards = tuple(state.cards[card_id] for card_id in selected)
    generated = sum(scrap_value_for_card(card) for card in cards)
    recycle_cards(state, tuple(selected))
    stats.scrap_generated += generated
    for card in cards:
        stats.recycled_by_rarity[card.rarity] += 1
        if card.card_kind is CardKind.FREIGHT:
            stats.freight_recycled_by_rarity[card.rarity] += 1


def _maybe_craft_cards(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    if rng.random() > profile.craft_attempt_chance:
        return
    target_definitions = tuple(
        definition
        for definition in definitions.values()
        if isinstance(definition, (MachineDefinition, RecipeDefinition, FreightDefinition))
    )
    for rarity in (Rarity.EPIC, Rarity.RARE, Rarity.UNCOMMON):
        cards = [
            card for card in state.cards.values()
            if card.rarity is rarity and not _is_stress_freight_card(card.card_id)
        ]
        rng.shuffle(cards)
        while len(cards) >= CRAFT_INPUT_COUNT and rng.random() <= profile.craft_attempt_chance:
            selected = tuple(card.card_id for card in cards[:CRAFT_INPUT_COUNT])
            target = rng.choice(target_definitions)
            before_ids = set(state.cards)
            input_cards = tuple(state.cards[card_id] for card_id in selected)
            output = craft_rarity_card(state, definitions, selected, target.definition_id)
            stats.crafting_outputs_by_rarity[output.rarity] += 1
            stats.created_by_rarity[output.rarity] += 1
            if output.rarity is Rarity.LEGENDARY and output.output_bonus_tenths == PERFECT_LEGENDARY_BONUS_TENTHS:
                stats.perfect_legendary_created += 1
            _record_freight_created(stats, output, definitions)
            for card in input_cards:
                stats.crafting_consumed_by_rarity[card.rarity] += 1
                if card.card_kind is CardKind.FREIGHT:
                    stats.freight_crafting_consumed_by_rarity[card.rarity] += 1
            cards = [card for card in cards[CRAFT_INPUT_COUNT:] if card.card_id in state.cards and card.card_id not in before_ids]
            cards.extend(
                card for card in state.cards.values()
                if card.rarity is rarity and not _is_stress_freight_card(card.card_id)
            )
            seen = set()
            cards = [card for card in cards if not (card.card_id in seen or seen.add(card.card_id))]
            rng.shuffle(cards)


def _maybe_upgrade_mk(
    state: GameState,
    rng: random.Random,
    profile: PlayerProfile,
    definitions: dict[str, CardDefinition],
    stats: StressStats,
) -> None:
    if rng.random() > profile.mk_upgrade_attempt_chance:
        return
    candidates = []
    for card in state.cards.values():
        if _is_stress_freight_card(card.card_id):
            continue
        try:
            if next_mk_definition(card, definitions) is not None:
                candidates.append(card)
        except ValueError:
            continue
    rng.shuffle(candidates)
    for card in candidates[:3]:
        if rng.random() > profile.mk_upgrade_attempt_chance:
            continue
        before_scrap = state.scrap.amount
        try:
            upgraded = upgrade_mk_card(state, definitions, card.card_id)
        except ValueError:
            continue
        stats.scrap_consumed += before_scrap - state.scrap.amount
        stats.mk_upgrade_consumed_by_rarity[card.rarity] += 1
        stats.mk_upgrade_outputs_by_rarity[upgraded.rarity] += 1
        stats.created_by_rarity[upgraded.rarity] += 1
        _record_freight_created(stats, upgraded, definitions)
        if upgraded.rarity is Rarity.LEGENDARY and upgraded.output_bonus_tenths == PERFECT_LEGENDARY_BONUS_TENTHS:
            stats.perfect_legendary_created += 1


def _record_remaining_player_state(state: GameState, definitions: dict[str, CardDefinition], stats: StressStats) -> None:
    counted_cards = [card for card in state.cards.values() if not _is_stress_freight_card(card.card_id)]
    by_rarity = Counter(card.rarity for card in counted_cards)
    freight_cards = [card for card in counted_cards if card.card_kind is CardKind.FREIGHT]
    freight_by_rarity = Counter(card.rarity for card in freight_cards)
    stats.remaining_by_rarity.update(by_rarity)
    stats.freight_remaining_by_rarity.update(freight_by_rarity)
    for card in freight_cards:
        family_id = _freight_family_id(card, definitions)
        if family_id:
            stats.freight_remaining_by_family[family_id] += 1
            stats.freight_remaining_by_family_rarity[(family_id, card.rarity)] += 1
    legendary_count = by_rarity[Rarity.LEGENDARY]
    freight_legendary_count = freight_by_rarity[Rarity.LEGENDARY]
    stats.player_legendary_counts.append(legendary_count)
    stats.player_card_counts.append(len(counted_cards))
    stats.player_freight_legendary_counts.append(freight_legendary_count)
    stats.player_freight_card_counts.append(len(freight_cards))
    stats.perfect_legendary_remaining += sum(
        1
        for card in counted_cards
        if card.rarity is Rarity.LEGENDARY and card.output_bonus_tenths == PERFECT_LEGENDARY_BONUS_TENTHS
    )


def _capture_new_cards(
    stats: StressStats,
    state: GameState,
    definitions: dict[str, CardDefinition],
    operation,
    source: str | None = None,
) -> None:
    before_ids = set(state.cards)
    try:
        operation()
    except ValueError:
        return
    new_cards = [
        card
        for card_id, card in state.cards.items()
        if card_id not in before_ids
    ]
    for card in new_cards:
        stats.created_by_rarity[card.rarity] += 1
        _record_freight_created(stats, card, definitions)
        if source == "daily_freight_rotation":
            stats.daily_freight_rotation_by_rarity[card.rarity] += 1
        if card.rarity is Rarity.LEGENDARY and card.output_bonus_tenths == PERFECT_LEGENDARY_BONUS_TENTHS:
            stats.perfect_legendary_created += 1


def _is_stress_freight_card(card_id: str) -> bool:
    return card_id.startswith("stress-freight-")


def _record_freight_created(stats: StressStats, card, definitions: dict[str, CardDefinition]) -> None:
    if card.card_kind is not CardKind.FREIGHT:
        return
    stats.freight_created_by_rarity[card.rarity] += 1
    family_id = _freight_family_id(card, definitions)
    if family_id:
        stats.freight_created_by_family[family_id] += 1
        stats.freight_created_by_family_rarity[(family_id, card.rarity)] += 1


def _freight_family_id(card, definitions: dict[str, CardDefinition]) -> str:
    definition = definitions.get(card.definition_id)
    if isinstance(definition, FreightDefinition):
        return definition.family.value
    return ""


def _choose_profile(rng: random.Random) -> PlayerProfile:
    roll = rng.random() * sum(profile.weight for profile in PLAYER_PROFILES)
    cursor = 0.0
    for profile in PLAYER_PROFILES:
        cursor += profile.weight
        if roll <= cursor:
            return profile
    return PLAYER_PROFILES[-1]


def _choose_weighted(rng: random.Random, weights: dict[str, float]) -> str:
    roll = rng.random() * sum(weights.values())
    cursor = 0.0
    for key, weight in weights.items():
        cursor += weight
        if roll <= cursor:
            return key
    return next(reversed(weights))


def summarize(stats_by_seed: list[StressStats]) -> dict[str, object]:
    aggregate = _aggregate_stats(stats_by_seed)
    player_years = len(aggregate.player_card_counts) * (aggregate.days / 365.0)
    return {
        "seeds": [stats.seed for stats in stats_by_seed],
        "players_per_seed": stats_by_seed[0].players if stats_by_seed else 0,
        "days": stats_by_seed[0].days if stats_by_seed else 0,
        "profiles": dict(aggregate.profiles),
        "cards_created_total": aggregate.total_created_cards,
        "cards_recycled_total": sum(aggregate.recycled_by_rarity.values()),
        "cards_consumed_through_rarity_crafting": sum(aggregate.crafting_consumed_by_rarity.values()),
        "crafts_total": sum(aggregate.crafting_outputs_by_rarity.values()),
        "mk_upgrades_total": sum(aggregate.mk_upgrade_outputs_by_rarity.values()),
        "created_cards_by_rarity": _rarity_dict(aggregate.created_by_rarity),
        "recycled_cards_by_rarity": _rarity_dict(aggregate.recycled_by_rarity),
        "crafting_consumed_by_rarity": _rarity_dict(aggregate.crafting_consumed_by_rarity),
        "crafting_outputs_by_rarity": _rarity_dict(aggregate.crafting_outputs_by_rarity),
        "mk_upgrade_consumed_by_rarity": _rarity_dict(aggregate.mk_upgrade_consumed_by_rarity),
        "mk_upgrade_outputs_by_rarity": _rarity_dict(aggregate.mk_upgrade_outputs_by_rarity),
        "scrap_generated": aggregate.scrap_generated,
        "scrap_consumed": aggregate.scrap_consumed,
        "scrap_surplus": aggregate.scrap_generated - aggregate.scrap_consumed,
        "remaining_cards_by_rarity": _rarity_dict(aggregate.remaining_by_rarity),
        "cards_remaining": sum(aggregate.remaining_by_rarity.values()),
        "legendarys_per_player": _distribution(aggregate.player_legendary_counts),
        "perfect_legendarys_remaining": aggregate.perfect_legendary_remaining,
        "perfect_legendarys_created": aggregate.perfect_legendary_created,
        "cards_per_player": _distribution(aggregate.player_card_counts),
        "net_supply_growth": aggregate.net_supply_growth,
        "net_supply_growth_per_player": round(aggregate.net_supply_growth / max(1, len(aggregate.player_card_counts)), 3),
        "per_player_year": _per_player_year_summary(aggregate, player_years),
        "freight": _freight_summary(aggregate),
        "by_profile": {
            profile_id: _profile_summary(profile_stats)
            for profile_id, profile_stats in sorted(aggregate.by_profile.items())
        },
        "per_seed": [_seed_summary(stats) for stats in stats_by_seed],
    }


def format_summary(summary: dict[str, object]) -> str:
    lines = [
        "Production Zero Economy Stress Test",
        f"Seeds: {', '.join(str(seed) for seed in summary['seeds'])}",
        f"Players per seed: {summary['players_per_seed']:,}",
        f"Days: {summary['days']}",
        "",
        "Aggregate",
        f"Cards created / recycled / remaining: {summary['cards_created_total']:,} / {summary['cards_recycled_total']:,} / {summary['cards_remaining']:,}",
        f"Created cards by rarity: {summary['created_cards_by_rarity']}",
        f"Recycled cards by rarity: {summary['recycled_cards_by_rarity']}",
        f"Crafting consumed by rarity: {summary['crafting_consumed_by_rarity']}",
        f"Crafting outputs by rarity: {summary['crafting_outputs_by_rarity']}",
        f"Crafts total / MK upgrades total: {summary['crafts_total']:,} / {summary['mk_upgrades_total']:,}",
        f"MK upgrade consumed by rarity: {summary['mk_upgrade_consumed_by_rarity']}",
        f"MK upgrade outputs by rarity: {summary['mk_upgrade_outputs_by_rarity']}",
        f"Scrap generated / consumed / surplus: {summary['scrap_generated']:,} / {summary['scrap_consumed']:,} / {summary['scrap_surplus']:,}",
        f"Remaining cards by rarity: {summary['remaining_cards_by_rarity']}",
        f"Legendarys per player: {summary['legendarys_per_player']}",
        f"Perfect Legendarys remaining / created: {summary['perfect_legendarys_remaining']:,} / {summary['perfect_legendarys_created']:,}",
        f"Cards per player: {summary['cards_per_player']}",
        f"Net supply growth: {summary['net_supply_growth']:,} ({summary['net_supply_growth_per_player']} per player)",
        f"Per player-year: {summary['per_player_year']}",
        f"Freight: {summary['freight']}",
        "",
        "By Profile",
    ]
    for profile_id, profile_summary in summary["by_profile"].items():
        lines.extend(
            [
                f"{profile_id}:",
                f"  Players: {profile_summary['players']:,}",
                f"  Created: {profile_summary['created_cards_by_rarity']}",
                f"  Recycled: {profile_summary['recycled_cards_by_rarity']}",
                f"  Crafting consumed: {profile_summary['crafting_consumed_by_rarity']}",
                f"  Crafting outputs: {profile_summary['crafting_outputs_by_rarity']}",
                f"  MK upgrade consumed: {profile_summary['mk_upgrade_consumed_by_rarity']}",
                f"  Scrap generated / consumed: {profile_summary['scrap_generated']:,} / {profile_summary['scrap_consumed']:,}",
                f"  Remaining: {profile_summary['remaining_cards_by_rarity']}",
                f"  Cards/player: {profile_summary['cards_per_player']}",
                f"  Legendarys/player: {profile_summary['legendarys_per_player']}",
                f"  Perfect Legendarys remaining / created: {profile_summary['perfect_legendarys_remaining']:,} / {profile_summary['perfect_legendarys_created']:,}",
                f"  Freight: {profile_summary['freight']}",
                f"  Net supply growth: {profile_summary['net_supply_growth']:,}",
            ]
        )
    return "\n".join(lines)


def _aggregate_stats(stats_by_seed: list[StressStats]) -> StressStats:
    if not stats_by_seed:
        return StressStats(seed=0, players=0, days=0)
    aggregate = StressStats(seed=-1, players=sum(stats.players for stats in stats_by_seed), days=stats_by_seed[0].days)
    for stats in stats_by_seed:
        _merge_stats(aggregate, stats)
    return aggregate


def _seed_summary(stats: StressStats) -> dict[str, object]:
    return {
        "seed": stats.seed,
        "cards_created_total": stats.total_created_cards,
        "cards_recycled_total": sum(stats.recycled_by_rarity.values()),
        "cards_consumed_through_rarity_crafting": sum(stats.crafting_consumed_by_rarity.values()),
        "crafts_total": sum(stats.crafting_outputs_by_rarity.values()),
        "mk_upgrades_total": sum(stats.mk_upgrade_outputs_by_rarity.values()),
        "created_cards_by_rarity": _rarity_dict(stats.created_by_rarity),
        "recycled_cards_by_rarity": _rarity_dict(stats.recycled_by_rarity),
        "crafting_consumed_by_rarity": _rarity_dict(stats.crafting_consumed_by_rarity),
        "crafting_outputs_by_rarity": _rarity_dict(stats.crafting_outputs_by_rarity),
        "remaining_cards_by_rarity": _rarity_dict(stats.remaining_by_rarity),
        "scrap_generated": stats.scrap_generated,
        "scrap_consumed": stats.scrap_consumed,
        "scrap_surplus": stats.scrap_generated - stats.scrap_consumed,
        "legendarys_per_player": _distribution(stats.player_legendary_counts),
        "cards_per_player": _distribution(stats.player_card_counts),
        "net_supply_growth": stats.net_supply_growth,
        "freight": _freight_summary(stats),
        "by_profile": {
            profile_id: _profile_summary(profile_stats)
            for profile_id, profile_stats in sorted(stats.by_profile.items())
        },
    }


def _profile_summary(stats: StressStats) -> dict[str, object]:
    players = len(stats.player_card_counts)
    return {
        "players": players,
        "cards_created_total": stats.total_created_cards,
        "cards_recycled_total": sum(stats.recycled_by_rarity.values()),
        "cards_consumed_through_rarity_crafting": sum(stats.crafting_consumed_by_rarity.values()),
        "crafts_total": sum(stats.crafting_outputs_by_rarity.values()),
        "mk_upgrades_total": sum(stats.mk_upgrade_outputs_by_rarity.values()),
        "created_cards_by_rarity": _rarity_dict(stats.created_by_rarity),
        "recycled_cards_by_rarity": _rarity_dict(stats.recycled_by_rarity),
        "crafting_consumed_by_rarity": _rarity_dict(stats.crafting_consumed_by_rarity),
        "crafting_outputs_by_rarity": _rarity_dict(stats.crafting_outputs_by_rarity),
        "mk_upgrade_consumed_by_rarity": _rarity_dict(stats.mk_upgrade_consumed_by_rarity),
        "mk_upgrade_outputs_by_rarity": _rarity_dict(stats.mk_upgrade_outputs_by_rarity),
        "scrap_generated": stats.scrap_generated,
        "scrap_consumed": stats.scrap_consumed,
        "scrap_surplus": stats.scrap_generated - stats.scrap_consumed,
        "remaining_cards_by_rarity": _rarity_dict(stats.remaining_by_rarity),
        "cards_remaining": sum(stats.remaining_by_rarity.values()),
        "legendarys_per_player": _distribution(stats.player_legendary_counts),
        "perfect_legendarys_remaining": stats.perfect_legendary_remaining,
        "perfect_legendarys_created": stats.perfect_legendary_created,
        "cards_per_player": _distribution(stats.player_card_counts),
        "net_supply_growth": stats.net_supply_growth,
        "net_supply_growth_per_player": round(stats.net_supply_growth / max(1, players), 3),
        "freight": _freight_summary(stats),
    }


def _freight_summary(stats: StressStats) -> dict[str, object]:
    freight_players = max(1, len(stats.player_freight_card_counts))
    legendary_counts = stats.player_freight_legendary_counts
    return {
        "created_total": sum(stats.freight_created_by_rarity.values()),
        "remaining_total": sum(stats.freight_remaining_by_rarity.values()),
        "recycled_total": sum(stats.freight_recycled_by_rarity.values()),
        "consumed_through_crafting_total": sum(stats.freight_crafting_consumed_by_rarity.values()),
        "created_by_rarity": _rarity_dict(stats.freight_created_by_rarity),
        "remaining_by_rarity": _rarity_dict(stats.freight_remaining_by_rarity),
        "recycled_by_rarity": _rarity_dict(stats.freight_recycled_by_rarity),
        "crafting_consumed_by_rarity": _rarity_dict(stats.freight_crafting_consumed_by_rarity),
        "created_by_family": dict(sorted(stats.freight_created_by_family.items())),
        "remaining_by_family": dict(sorted(stats.freight_remaining_by_family.items())),
        "created_by_family_rarity": _family_rarity_dict(stats.freight_created_by_family_rarity),
        "remaining_by_family_rarity": _family_rarity_dict(stats.freight_remaining_by_family_rarity),
        "cards_per_player": _distribution(stats.player_freight_card_counts),
        "rare_per_player_year": round(stats.freight_created_by_rarity[Rarity.RARE] / freight_players, 3),
        "epic_per_player_year": round(stats.freight_created_by_rarity[Rarity.EPIC] / freight_players, 3),
        "legendary_per_player_year": round(stats.freight_created_by_rarity[Rarity.LEGENDARY] / freight_players, 3),
        "legendary_players_at_least_1": _share_at_least(legendary_counts, 1),
        "legendary_players_at_least_2": _share_at_least(legendary_counts, 2),
        "legendary_players_at_least_3": _share_at_least(legendary_counts, 3),
        "daily_freight_rotation_total": sum(stats.daily_freight_rotation_by_rarity.values()),
        "daily_freight_rotation_by_rarity": _rarity_dict(stats.daily_freight_rotation_by_rarity),
    }


def _per_player_year_summary(stats: StressStats, player_years: float) -> dict[str, float]:
    divisor = max(1.0, player_years)
    return {
        "cards_created": round(stats.total_created_cards / divisor, 3),
        "cards_recycled": round(sum(stats.recycled_by_rarity.values()) / divisor, 3),
        "crafting_consumed": round(sum(stats.crafting_consumed_by_rarity.values()) / divisor, 3),
        "crafts": round(sum(stats.crafting_outputs_by_rarity.values()) / divisor, 3),
        "mk_upgrades": round(sum(stats.mk_upgrade_outputs_by_rarity.values()) / divisor, 3),
        "scrap_generated": round(stats.scrap_generated / divisor, 3),
        "scrap_consumed": round(stats.scrap_consumed / divisor, 3),
        "net_supply_growth": round(stats.net_supply_growth / divisor, 3),
    }


def _merge_stats(target: StressStats, source: StressStats, include_profile_breakdown: bool = True) -> None:
    target.profiles.update(source.profiles)
    target.created_by_rarity.update(source.created_by_rarity)
    target.recycled_by_rarity.update(source.recycled_by_rarity)
    target.crafting_consumed_by_rarity.update(source.crafting_consumed_by_rarity)
    target.crafting_outputs_by_rarity.update(source.crafting_outputs_by_rarity)
    target.mk_upgrade_consumed_by_rarity.update(source.mk_upgrade_consumed_by_rarity)
    target.mk_upgrade_outputs_by_rarity.update(source.mk_upgrade_outputs_by_rarity)
    target.remaining_by_rarity.update(source.remaining_by_rarity)
    target.freight_created_by_rarity.update(source.freight_created_by_rarity)
    target.freight_recycled_by_rarity.update(source.freight_recycled_by_rarity)
    target.freight_crafting_consumed_by_rarity.update(source.freight_crafting_consumed_by_rarity)
    target.freight_remaining_by_rarity.update(source.freight_remaining_by_rarity)
    target.freight_created_by_family.update(source.freight_created_by_family)
    target.freight_remaining_by_family.update(source.freight_remaining_by_family)
    target.freight_created_by_family_rarity.update(source.freight_created_by_family_rarity)
    target.freight_remaining_by_family_rarity.update(source.freight_remaining_by_family_rarity)
    target.daily_freight_rotation_by_rarity.update(source.daily_freight_rotation_by_rarity)
    target.scrap_generated += source.scrap_generated
    target.scrap_consumed += source.scrap_consumed
    target.perfect_legendary_remaining += source.perfect_legendary_remaining
    target.perfect_legendary_created += source.perfect_legendary_created
    target.player_card_counts.extend(source.player_card_counts)
    target.player_legendary_counts.extend(source.player_legendary_counts)
    target.player_freight_card_counts.extend(source.player_freight_card_counts)
    target.player_freight_legendary_counts.extend(source.player_freight_legendary_counts)
    if include_profile_breakdown:
        for profile_id, profile_stats in source.by_profile.items():
            target_profile = target.by_profile.setdefault(
                profile_id,
                StressStats(seed=target.seed, players=0, days=target.days),
            )
            target_profile.players += profile_stats.players
            _merge_stats(target_profile, profile_stats, include_profile_breakdown=False)


def _rarity_dict(counter: Counter[Rarity]) -> dict[str, int]:
    return {rarity.value: int(counter[rarity]) for rarity in Rarity}


def _family_rarity_dict(counter: Counter[tuple[str, Rarity]]) -> dict[str, dict[str, int]]:
    families = sorted({family for family, _ in counter})
    return {
        family: {rarity.value: int(counter[(family, rarity)]) for rarity in Rarity}
        for family in families
    }


def _distribution(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "avg": 0.0, "p50": 0, "p90": 0, "p99": 0, "max": 0}
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "avg": round(mean(ordered), 3),
        "p50": _percentile(ordered, 0.5),
        "p90": _percentile(ordered, 0.9),
        "p99": _percentile(ordered, 0.99),
        "max": ordered[-1],
    }


def _percentile(ordered: list[int], percentile: float) -> int:
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _share_at_least(values: list[int], threshold: int) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value >= threshold) / len(values), 4)


def _parse_seeds(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the internal Production Zero economy stress test.")
    parser.add_argument("--players", type=int, default=SIMULATION_PLAYERS)
    parser.add_argument("--days", type=int, default=SIMULATION_DAYS)
    parser.add_argument("--seeds", type=_parse_seeds, default=DEFAULT_SEEDS)
    parser.add_argument("--processes", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of text.")
    args = parser.parse_args(argv)

    stats = run_stress_test(players=args.players, days=args.days, seeds=args.seeds, processes=args.processes)
    summary = summarize(stats)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
