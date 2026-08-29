from __future__ import annotations

from enum import StrEnum


class CardKind(StrEnum):
    MACHINE = "machine"
    ENERGY = "energy"
    RECIPE = "recipe"
    FREIGHT = "freight"


class MachineType(StrEnum):
    EXTRACTOR = "extractor"
    PROCESSOR = "processor"
    FABRICATOR = "fabricator"
    ASSEMBLER = "assembler"

    # Legacy aliases for old saves/tests. New definitions should use the
    # canonical four-stage family values above.
    MINING = "extractor"
    SMELTING = "processor"
    ASSEMBLY = "assembler"


class EnergyType(StrEnum):
    SOLAR = "solar"
    WIND = "wind"
    COAL = "coal"
    GAS = "gas"
    NUCLEAR = "nuclear"


class FreightFamily(StrEnum):
    TRUCK = "truck"
    TRAIN = "train"
    SHIP = "ship"
    AIRCRAFT = "aircraft"


class Rarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class TradeState(StrEnum):
    BOUND = "bound"
    COLLECTIBLE_LOCKED = "collectible_locked"
    COLLECTIBLE_VERIFIED = "collectible_verified"


class ResourceId(StrEnum):
    IRON_ORE = "iron_ore"
    COAL = "coal"
    COPPER_ORE = "copper_ore"
    IRON = "iron"
    COPPER = "copper"
    STEEL = "steel"
    MACHINE_PARTS = "machine_parts"
