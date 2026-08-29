from __future__ import annotations

from pathlib import Path

from production_zero.core.cards import CardInstance, RARITY_BONUS_RANGES_TENTHS, create_card_instance, effective_recipe_inputs, effective_recipe_outputs, validate_rarity_bonus
from production_zero.core.definitions import EnergyDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.market import BASE_MARKET_PRICES, MARKET_EVENTS
from production_zero.data.definitions import load_card_definitions, load_resource_definitions


def test_definition_and_instance_are_separate() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.extractor.mk3"]

    card = CardInstance(
        card_id="card-847291",
        definition_id="machine.extractor.mk3",
        card_kind=CardKind.MACHINE,
        rarity=Rarity.EPIC,
        output_bonus_percent=13.7,
        power_bonus_percent=13.7,
    )

    assert isinstance(definition, MachineDefinition)
    assert definition.name == "Extractor MK III"
    assert definitions["machine.mining_drill.mk3"] is definition
    assert definition.machine_type is MachineType.EXTRACTOR
    assert definition.base_output_per_tick == 60
    assert definition.base_power_draw == 25
    assert card.card_id == "card-847291"
    assert card.output_multiplier == 1.137


def test_extractor_definition_lists_selectable_resources() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.extractor.mk1"]
    mk2_definition = definitions["machine.extractor.mk2"]

    assert isinstance(definition, MachineDefinition)
    assert isinstance(mk2_definition, MachineDefinition)
    assert mk2_definition.name == "Extractor MK II"
    assert mk2_definition.mk_level == 2
    assert definition.machine_type is MachineType.EXTRACTOR
    option_outputs = [option.output_resource for option in definition.available_production_options]
    assert option_outputs[:3] == ["iron_ore", "copper_ore", "bauxite"]
    assert {"iron_ore", "coal", "copper_ore", "timber", "wheat", "natural_rubber"}.issubset(option_outputs)
    assert len(option_outputs) >= 49
    assert definition.default_production_id == "resource.iron_ore"


def test_processor_definition_models_processing_chain() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.processor.mk1"]

    assert isinstance(definition, MachineDefinition)
    assert definition.name == "Processor MK I"
    assert definition.machine_type is MachineType.PROCESSOR
    assert definition.input_resources == {"iron_ore": 12}
    assert definition.output_resource == "iron"
    recipes = {
        option.output_resource: (
            option.name,
            option.input_resources,
            option.output_amount_for(definition),
            option.cycle_seconds_for(definition),
        )
        for option in definition.available_production_options
    }
    assert recipes["iron"] == ("Iron", {"iron_ore": 12}, 6, 4)
    assert recipes["copper"] == ("Copper", {"copper_ore": 12}, 6, 4)
    assert recipes["steel"] == ("Steel", {"iron_ore": 12, "coal": 3}, 4, 5)
    assert {"aluminum", "cement", "polymer", "flour", "processed_rubber"}.issubset(recipes)
    assert len(recipes) >= 60
    assert definition.base_output_per_tick == 6
    assert definition.base_power_draw == 8
    assert definitions["machine.furnace.mk1"] is definition
    assert definitions["machine.blast_furnace.mk1"] is definition


def test_processor_steel_recipe_preserves_multi_input_blast_furnace_values() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.processor.mk1"]

    assert isinstance(definition, MachineDefinition)
    steel = definition.production_option("recipe.processor.steel")
    assert steel.stage is MachineType.PROCESSOR
    assert steel.input_resources == {"iron_ore": 12, "coal": 3}
    assert steel.output_resource == "steel"
    assert steel.output_amount_for(definition) == 4
    assert steel.power_draw_for(definition) == 12
    assert steel.cycle_seconds_for(definition) == 5
    assert definition.default_production_id_for_card_definition("machine.blast_furnace.mk1") == "recipe.processor.steel"


def test_universal_machine_families_are_defined_with_stage_identity() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    expected = {
        "machine.extractor.mk1": MachineType.EXTRACTOR,
        "machine.processor.mk1": MachineType.PROCESSOR,
        "machine.fabricator.mk1": MachineType.FABRICATOR,
        "machine.assembler.mk1": MachineType.ASSEMBLER,
    }

    for definition_id, machine_type in expected.items():
        definition = definitions[definition_id]
        assert isinstance(definition, MachineDefinition)
        assert definition.machine_type is machine_type
        assert definition.stage is machine_type
        production = definition.production_option()
        assert definition.is_compatible_with(production)
        assert production.icon_key
        assert production.accent_key


def test_energy_definitions_include_fuel_based_power_plants() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))

    expected = {
        "energy.solar_array.mk1": ("solar", 20, None, 0.0, None),
        "energy.wind_turbine.mk1": ("wind", 35, None, 0.0, 360),
        "energy.coal_power_plant.mk1": ("coal", 100, "coal", 2.0, 520),
        "energy.gas_power_plant.mk1": ("gas", 180, "natural_gas", 2.0, 1200),
        "energy.nuclear_power_plant.mk1": ("nuclear", 500, "nuclear_fuel_assembly", 0.25, 6000),
    }

    for definition_id, (energy_type, output, fuel, fuel_rate, price) in expected.items():
        definition = definitions[definition_id]
        assert isinstance(definition, EnergyDefinition)
        assert definition.energy_type.value == energy_type
        assert definition.base_power_output == output
        assert definition.fuel_resource_id == fuel
        assert definition.fuel_consumption_per_minute == fuel_rate
        assert definition.supply_price_cash == price


def test_industrial_world_content_defines_broad_four_stage_resource_library() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    unique_cards = {definition.definition_id: definition for definition in cards.values()}

    extractor = cards["machine.extractor.mk1"]
    processor = cards["machine.processor.mk1"]
    fabricator = cards["machine.fabricator.mk1"]
    assembler = cards["machine.assembler.mk1"]

    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)
    assert isinstance(fabricator, MachineDefinition)
    assert isinstance(assembler, MachineDefinition)
    assert len(resources) > 300
    assert len(extractor.available_production_options) >= 49
    assert len(processor.available_production_options) >= 67
    assert len(fabricator.available_production_options) >= 79
    assert len(assembler.available_production_options) >= 150
    assert {
        "bauxite",
        "natural_gas",
        "timber",
        "wheat",
        "natural_rubber",
        "semiconductor_components",
        "packaged_food",
        "fusion_reactor_module",
    }.issubset(resources)
    assert "iron_plate" not in resources
    assert "machine_parts" not in resources
    assert {
        MachineType.PROCESSOR,
        MachineType.FABRICATOR,
        MachineType.ASSEMBLER,
    } == {
        definition.stage
        for definition in unique_cards.values()
        if isinstance(definition, RecipeDefinition)
    }


def test_industrial_world_recipes_reference_defined_resources_and_market_prices() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    resource_ids = set(resources)
    unique_cards = {definition.definition_id: definition for definition in cards.values()}
    recipe_ids = {
        definition.definition_id
        for definition in unique_cards.values()
        if isinstance(definition, RecipeDefinition)
    }
    extractor = cards["machine.extractor.mk1"]
    processor = cards["machine.processor.mk1"]
    fabricator = cards["machine.fabricator.mk1"]
    assembler = cards["machine.assembler.mk1"]
    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)
    assert isinstance(fabricator, MachineDefinition)
    assert isinstance(assembler, MachineDefinition)
    extraction_outputs = {option.output_resource for option in extractor.available_production_options}
    processing_outputs = {option.output_resource for option in processor.available_production_options}
    manufacturing_outputs = {option.output_resource for option in fabricator.available_production_options}

    for definition in unique_cards.values():
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                assert option.output_resource in resource_ids
                assert set(option.input_resources).issubset(resource_ids)
                assert option.output_resource in BASE_MARKET_PRICES
                assert len(option.input_resources) <= 4
        if isinstance(definition, RecipeDefinition):
            assert set(definition.input_resources).issubset(resource_ids)
            assert set(definition.output_resources).issubset(resource_ids)
            assert set(definition.output_resources).issubset(BASE_MARKET_PRICES)
            assert len(definition.input_resources) <= 4

    for option in processor.available_production_options:
        assert set(option.input_resources).issubset(extraction_outputs)
        assert option.production_id in recipe_ids
    for option in fabricator.available_production_options:
        assert set(option.input_resources).issubset(processing_outputs)
        assert option.production_id in recipe_ids
    for option in assembler.available_production_options:
        assert set(option.input_resources).issubset(manufacturing_outputs)
        assert option.production_id in recipe_ids


def test_non_assembly_resources_reach_assembly_products() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    extractor = cards["machine.extractor.mk1"]
    processor = cards["machine.processor.mk1"]
    fabricator = cards["machine.fabricator.mk1"]
    assembler = cards["machine.assembler.mk1"]
    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)
    assert isinstance(fabricator, MachineDefinition)
    assert isinstance(assembler, MachineDefinition)
    extraction_outputs = {option.output_resource for option in extractor.available_production_options}
    processing_outputs = {option.output_resource for option in processor.available_production_options}
    manufacturing_outputs = {option.output_resource for option in fabricator.available_production_options}
    assembly_outputs = {option.output_resource for option in assembler.available_production_options}
    next_outputs: dict[str, set[str]] = {}

    for definition in (processor, fabricator, assembler):
        for option in definition.available_production_options:
            for resource_id in option.input_resources:
                next_outputs.setdefault(resource_id, set()).add(option.output_resource)

    def reaches_assembly(resource_id: str) -> bool:
        frontier = list(next_outputs.get(resource_id, set()))
        seen = set(frontier)
        while frontier:
            current = frontier.pop()
            if current in assembly_outputs:
                return True
            for next_resource in next_outputs.get(current, set()):
                if next_resource not in seen:
                    seen.add(next_resource)
                    frontier.append(next_resource)
        return False

    for resource_id in extraction_outputs | processing_outputs | manufacturing_outputs:
        assert reaches_assembly(resource_id), resource_id


def test_market_events_cover_new_industrial_sectors_without_unknown_resources() -> None:
    affected = set()
    for event in MARKET_EVENTS:
        assert set(event.affected_resources).issubset(BASE_MARKET_PRICES)
        affected.update(event.affected_resources)

    assert {
        "cement",
        "packaged_food",
        "semiconductor_components",
        "grid_battery",
        "biofuel",
        "cargo_aircraft",
    }.issubset(affected)


def test_rarity_bonus_ranges_are_defined_in_tenth_percent_steps() -> None:
    assert RARITY_BONUS_RANGES_TENTHS == {
        Rarity.COMMON: (0, 0),
        Rarity.UNCOMMON: (10, 50),
        Rarity.RARE: (60, 100),
        Rarity.EPIC: (110, 150),
        Rarity.LEGENDARY: (160, 200),
    }
    validate_rarity_bonus(Rarity.RARE, 74)


def test_created_cards_store_rarity_bonus_deterministically_and_tradeability_by_rarity() -> None:
    common = create_card_instance("common-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON)
    rare = create_card_instance("rare-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74)
    repeated = create_card_instance("rare-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, seed=12)

    assert common.output_bonus_tenths == 0
    assert common.is_tradeable_by_rarity is False
    assert rare.output_bonus_percent == 7.4
    assert rare.power_bonus_percent == 3.7
    assert rare.is_tradeable_by_rarity is True
    assert repeated == create_card_instance("rare-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.RARE, seed=12)


def test_recipe_card_rarity_increases_output_and_half_bonus_input_consumption() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["recipe.processor.iron"]
    card = create_card_instance("recipe-rare", "recipe.processor.iron", CardKind.RECIPE, Rarity.RARE, bonus_tenths=100)

    assert isinstance(definition, RecipeDefinition)
    assert round(effective_recipe_outputs(card, definition.output_resources)["iron"], 1) == 6.6
    assert round(effective_recipe_inputs(card, definition.input_resources)["iron_ore"], 1) == 12.6
