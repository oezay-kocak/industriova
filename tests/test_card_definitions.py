from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from production_zero.core.cards import CardInstance, RARITY_BONUS_RANGES_TENTHS, create_card_instance, validate_rarity_bonus
from production_zero.core.definitions import EnergyDefinition, MachineDefinition
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.market import BASE_MARKET_PRICES, MARKET_EVENTS
from production_zero.data.definitions import load_card_definitions, load_resource_definitions


def test_definition_and_instance_are_separate() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.extractor"]

    card = CardInstance(
        card_id="card-847291",
        definition_id="machine.extractor",
        card_kind=CardKind.MACHINE,
        rarity=Rarity.EPIC,
        output_bonus_percent=13.7,
        power_bonus_percent=13.7,
    )

    assert isinstance(definition, MachineDefinition)
    assert definition.name == "Extractor"
    assert definitions["machine.extractor"] is definition
    assert definition.machine_type is MachineType.EXTRACTOR
    assert definition.base_output_per_tick == 12
    assert definition.base_power_draw == 6
    assert card.card_id == "card-847291"
    assert card.output_multiplier == 1.137


def test_extractor_definition_lists_selectable_resources() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.extractor"]

    assert isinstance(definition, MachineDefinition)
    assert definition.name == "Extractor"
    assert definition.machine_type is MachineType.EXTRACTOR
    option_outputs = [option.output_resource for option in definition.available_production_options]
    assert option_outputs[:3] == ["iron_ore", "copper_ore", "bauxite"]
    assert {"iron_ore", "coal", "copper_ore", "limestone", "quartz"}.issubset(option_outputs)
    assert "timber" not in option_outputs
    assert len(option_outputs) == 37
    drilling = definitions["machine.drilling"]
    harvester = definitions["machine.agriculture"]
    assert drilling.name == "Drilling Rig"
    assert drilling.machine_type is MachineType.DRILLING
    assert {option.output_resource for option in drilling.available_production_options} == {"crude_oil", "natural_gas"}
    assert harvester.name == "Harvester"
    assert harvester.machine_type is MachineType.AGRICULTURE
    assert len(harvester.available_production_options) == 10
    assert definition.default_production_id == "resource.iron_ore"


def test_processor_definition_models_processing_chain() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.processor"]

    assert isinstance(definition, MachineDefinition)
    assert definition.name == "Processor"
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
    assert recipes["iron"] == ("Iron", {"iron_ore": 12}, 6, 6)
    assert recipes["copper"] == ("Copper", {"copper_ore": 12}, 6, 6)
    assert recipes["steel"] == ("Steel", {"iron_ore": 12, "coal": 3}, 4, 6)
    assert {"aluminum", "cement", "polymer", "flour", "processed_rubber"}.issubset(recipes)
    assert len(recipes) >= 60
    assert definition.base_output_per_tick == 6
    assert definition.base_power_draw == 8
    assert definitions["machine.processor"] is definition
    assert definitions["machine.processor"] is definition


def test_processor_steel_recipe_preserves_multi_input_blast_furnace_values() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    definition = definitions["machine.processor"]

    assert isinstance(definition, MachineDefinition)
    steel = definition.production_option("recipe.processor.steel")
    assert steel.stage is MachineType.PROCESSOR
    assert steel.input_resources == {"iron_ore": 12, "coal": 3}
    assert steel.output_resource == "steel"
    assert steel.output_amount_for(definition) == 4
    assert steel.power_draw_for(definition) == 12
    assert steel.cycle_seconds_for(definition) == 6
    assert definition.default_production_id_for_card_definition("machine.processor") == "recipe.processor.iron"


def test_universal_machine_families_are_defined_with_stage_identity() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    expected = {
        "machine.extractor": MachineType.EXTRACTOR,
        "machine.processor": MachineType.PROCESSOR,
        "machine.fabricator": MachineType.FABRICATOR,
        "machine.assembler": MachineType.ASSEMBLER,
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
        "energy.solar_array": ("solar", 20, None, 0.0, None),
        "energy.wind_turbine": ("wind", 35, None, 0.0, 360),
        "energy.coal_power_plant": ("coal", 60, "coal", 60.0, 520),
        "energy.gas_power_plant": ("gas", 180, "natural_gas", 60.0, 1200),
        "energy.nuclear_power_plant": ("nuclear", 500, "nuclear_fuel_assembly", 10.0, 6000),
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

    extractor = cards["machine.extractor"]
    drilling = cards["machine.drilling"]
    agriculture = cards["machine.agriculture"]
    processor = cards["machine.processor"]
    fabricator = cards["machine.fabricator"]
    assembler = cards["machine.assembler"]

    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)
    assert isinstance(fabricator, MachineDefinition)
    assert isinstance(assembler, MachineDefinition)
    assert len(resources) > 300
    assert sum(len(definition.available_production_options) for definition in (extractor, drilling, agriculture)) == 49
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
        MachineType.DRILLING,
        MachineType.AGRICULTURE,
    } == {
        definition.machine_type
        for definition in unique_cards.values()
        if isinstance(definition, MachineDefinition) and definition.machine_type is not MachineType.EXTRACTOR
    }


def test_industrial_world_recipes_reference_defined_resources_and_market_prices() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    resource_ids = set(resources)
    unique_cards = {definition.definition_id: definition for definition in cards.values()}
    recipe_ids = {
        option.production_id
        for definition in unique_cards.values()
        if isinstance(definition, MachineDefinition)
        for option in definition.available_production_options
    }
    extractor = cards["machine.extractor"]
    drilling = cards["machine.drilling"]
    agriculture = cards["machine.agriculture"]
    processor = cards["machine.processor"]
    fabricator = cards["machine.fabricator"]
    assembler = cards["machine.assembler"]
    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)
    assert isinstance(fabricator, MachineDefinition)
    assert isinstance(assembler, MachineDefinition)
    extraction_outputs = {
        option.output_resource
        for definition in (extractor, drilling, agriculture)
        for option in definition.available_production_options
    }
    processing_outputs = {option.output_resource for option in processor.available_production_options}
    manufacturing_outputs = {option.output_resource for option in fabricator.available_production_options}

    for definition in unique_cards.values():
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                assert option.output_resource in resource_ids
                assert set(option.input_resources).issubset(resource_ids)
                assert option.output_resource in BASE_MARKET_PRICES
                assert len(option.input_resources) <= 4

    for option in processor.available_production_options:
        assert set(option.input_resources).issubset(extraction_outputs)
        assert option.production_id in recipe_ids
    for option in fabricator.available_production_options:
        assert set(option.input_resources).issubset(processing_outputs)
        assert option.production_id in recipe_ids
    for option in assembler.available_production_options:
        assert set(option.input_resources).issubset(manufacturing_outputs)
        assert option.production_id in recipe_ids


def test_alpha_rebalance_former_d_recipe_inputs_have_playable_ratios() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    unique_machines = {
        definition.definition_id: definition
        for definition in cards.values()
        if isinstance(definition, MachineDefinition)
    }
    options = [
        (definition, option)
        for definition in unique_machines.values()
        for option in definition.available_production_options
    ]
    producer_output_per_minute = {
        option.output_resource: (
            Fraction(str(option.output_amount_for(definition)))
            * Fraction(60)
            / Fraction(str(option.cycle_seconds_for(definition)))
        )
        for definition, option in options
    }
    checked_edges = {
        ("recipe.processor.carbon_fiber", "graphite"),
        ("recipe.processor.cellulose", "crude_oil"),
        ("recipe.processor.cellulose", "natural_gas"),
        ("recipe.processor.high_purity_silicon", "crude_oil"),
        ("recipe.processor.high_purity_silicon", "natural_gas"),
        ("recipe.processor.industrial_resin", "crude_oil"),
        ("recipe.processor.industrial_resin", "natural_gas"),
        ("recipe.processor.superconducting_alloy", "rare_earth_ore"),
        ("recipe.processor.treated_lumber", "crude_oil"),
        ("recipe.processor.treated_lumber", "natural_gas"),
        ("recipe.processor.wood_pulp", "crude_oil"),
        ("recipe.processor.wood_pulp", "natural_gas"),
        ("recipe.fabricator.avionics_components", "copper"),
        ("recipe.fabricator.computing_components", "copper"),
        ("recipe.fabricator.control_electronics", "copper"),
        ("recipe.fabricator.electrical_components", "copper"),
        ("recipe.fabricator.insulated_wire", "copper"),
        ("recipe.fabricator.motor_components", "copper"),
        ("recipe.fabricator.network_components", "copper"),
        ("recipe.fabricator.telecom_components", "copper"),
        ("recipe.fabricator.transformer_components", "copper"),
    }

    edge_blocks: dict[tuple[str, str], int] = {}
    for definition, option in options:
        for resource_id, amount in option.input_resources.items():
            edge = (option.production_id, resource_id)
            if edge not in checked_edges:
                continue
            input_per_minute = (
                Fraction(str(amount))
                * Fraction(60)
                / Fraction(str(option.cycle_seconds_for(definition)))
            )
            ratio = input_per_minute / producer_output_per_minute[resource_id]
            edge_blocks[edge] = ratio.numerator + ratio.denominator

    assert set(edge_blocks) == checked_edges
    assert max(edge_blocks.values()) <= 24


def test_non_assembly_resources_reach_assembly_products() -> None:
    cards = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    extractor = cards["machine.extractor"]
    processor = cards["machine.processor"]
    fabricator = cards["machine.fabricator"]
    assembler = cards["machine.assembler"]
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
    common = create_card_instance("common-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)
    rare = create_card_instance("rare-1", "machine.extractor", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74)
    repeated = create_card_instance("rare-1", "machine.extractor", CardKind.MACHINE, Rarity.RARE, seed=12)

    assert common.output_bonus_tenths == 0
    assert common.is_tradeable_by_rarity is False
    assert rare.output_bonus_percent == 7.4
    assert rare.power_bonus_percent == 3.7
    assert rare.is_tradeable_by_rarity is True
    assert repeated == create_card_instance("rare-1", "machine.extractor", CardKind.MACHINE, Rarity.RARE, seed=12)
