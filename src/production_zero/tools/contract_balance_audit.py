from __future__ import annotations

from pathlib import Path

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, BuildHall, CommandBus, InstallCardInHall, SelectMachineProduction
from production_zero.core.contracts import (
    CONTRACT_KINDS,
    CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE,
    CONTRACT_REWARD_XP_PER_PRODUCTION_VALUE,
    contract_capacity_estimate,
    contract_production_value_budgets,
)
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.production_values import contract_required_amount, production_value_for_resource
from production_zero.core.progression import initialize_production_progress
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions


ROOT = Path(__file__).resolve().parents[3]
DEFINITIONS_PATH = ROOT / "src" / "production_zero" / "data" / "game_definitions.json"
REPORT_PATH = ROOT / "artifacts" / "contract_balance_audit.md"


SNAPSHOTS = {
    "very early": (
        ("extractor-iron", "machine.extractor", "resource.iron_ore", "iron_ore"),
    ),
    "early": (
        ("extractor-iron", "machine.extractor", "resource.iron_ore", "iron_ore"),
        ("extractor-coal", "machine.extractor", "resource.coal", "coal"),
        ("processor-iron", "machine.processor", "recipe.processor.iron", "iron"),
    ),
    "lower mid": (
        ("extractor-iron", "machine.extractor", "resource.iron_ore", "iron_ore"),
        ("extractor-coal", "machine.extractor", "resource.coal", "coal"),
        ("processor-iron", "machine.processor", "recipe.processor.iron", "iron"),
        ("processor-steel", "machine.processor", "recipe.processor.steel", "steel"),
        ("fabricator-components", "machine.fabricator", "recipe.fabricator.steel_components", "steel_components"),
    ),
    "mid": (
        ("extractor-iron", "machine.extractor", "resource.iron_ore", "iron_ore"),
        ("extractor-coal", "machine.extractor", "resource.coal", "coal"),
        ("extractor-copper", "machine.extractor", "resource.copper_ore", "copper_ore"),
        ("processor-steel", "machine.processor", "recipe.processor.steel", "steel"),
        ("fabricator-components", "machine.fabricator", "recipe.fabricator.steel_components", "steel_components"),
        ("assembler-equipment", "machine.assembler", "recipe.assembler.industrial_equipment", "industrial_equipment"),
    ),
    "late": (
        ("extractor-iron", "machine.extractor", "resource.iron_ore", "iron_ore"),
        ("extractor-coal", "machine.extractor", "resource.coal", "coal"),
        ("extractor-copper", "machine.extractor", "resource.copper_ore", "copper_ore"),
        ("processor-steel", "machine.processor", "recipe.processor.steel", "steel"),
        ("processor-copper", "machine.processor", "recipe.processor.copper", "copper"),
        ("fabricator-components", "machine.fabricator", "recipe.fabricator.steel_components", "steel_components"),
        ("assembler-equipment", "machine.assembler", "recipe.assembler.industrial_equipment", "industrial_equipment"),
        ("assembler-aircraft", "machine.assembler", "recipe.assembler.cargo_aircraft", "cargo_aircraft"),
    ),
}


SAMPLE_PRODUCTS = ("iron_ore", "steel", "steel_components", "industrial_equipment", "cargo_aircraft")


def _snapshot_state(name: str, definitions) -> GameState:
    state = GameState(rng_seed=7000 + len(name))
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)))
    initialize_production_progress(state, definitions)
    for slot_index, (card_id, definition_id, production_id, output_resource) in enumerate(SNAPSHOTS[name]):
        hall_number = slot_index // 6 + 1
        hall_id = f"hall-{hall_number}"
        local_slot_index = slot_index % 6
        if hall_id not in state.halls:
            bus.dispatch(BuildHall(FactoryHall(hall_id=hall_id, name=f"Hall {hall_number}", slot_count=6)))
        bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)))
        bus.dispatch(InstallCardInHall(hall_id, local_slot_index, card_id))
        state.production_progress.unlocked_production_ids.add(production_id)
        bus.dispatch(SelectMachineProduction(card_id, production_id, output_resource))
    return state


def _completion_minutes(budget: float, pv_per_minute: float) -> str:
    if pv_per_minute <= 0:
        return "n/a"
    return f"{budget / pv_per_minute:.1f}"


def main() -> None:
    definitions = load_card_definitions(DEFINITIONS_PATH)
    lines: list[str] = [
        "# Contract Balance Audit",
        "",
        "Deterministic offscreen audit for capacity-scaled contract budgets. No GUI is launched.",
        "",
        "## Snapshot Budgets",
        "",
        "| Snapshot | Active PV/min | Effective PV/min | Regular budgets | Daily budgets | Weekly budgets | Regular minutes | Daily minutes | Weekly minutes |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    weekly_growth: list[tuple[str, float, float]] = []
    for name in SNAPSHOTS:
        state = _snapshot_state(name, definitions)
        estimate = contract_capacity_estimate(state, definitions)
        budgets_by_kind = {kind: contract_production_value_budgets(kind, state, definitions) for kind in CONTRACT_KINDS}
        weekly_growth.append((name, estimate.effective_pv_per_minute, budgets_by_kind["weekly"][-1]))
        minute_groups = {
            kind: ", ".join(_completion_minutes(budget, estimate.effective_pv_per_minute) for budget in budgets)
            for kind, budgets in budgets_by_kind.items()
        }
        lines.append(
            "| "
            + " | ".join(
                (
                    name,
                    f"{estimate.active_pv_per_minute:.2f}",
                    f"{estimate.effective_pv_per_minute:.2f}",
                    ", ".join(f"{budget:g}" for budget in budgets_by_kind["regular"]),
                    ", ".join(f"{budget:g}" for budget in budgets_by_kind["daily"]),
                    ", ".join(f"{budget:g}" for budget in budgets_by_kind["weekly"]),
                    minute_groups["regular"],
                    minute_groups["daily"],
                    minute_groups["weekly"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Reward And Product Materialization Samples",
            "",
            "| Snapshot | Kind | Budget | Cash / XP reward | Iron Ore amount | Steel amount | Steel Components amount | Industrial Equipment amount | Cargo Aircraft amount |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in SNAPSHOTS:
        state = _snapshot_state(name, definitions)
        for kind in CONTRACT_KINDS:
            budget = contract_production_value_budgets(kind, state, definitions)[1]
            reward = round(budget * CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE[kind] / 5.0) * 5.0
            xp = round(budget * CONTRACT_REWARD_XP_PER_PRODUCTION_VALUE[kind] / 5.0) * 5.0
            amounts = []
            for resource_id in SAMPLE_PRODUCTS:
                value = production_value_for_resource(definitions, resource_id)
                amounts.append(contract_required_amount(budget, value.value_per_unit) if value is not None else 0)
            lines.append(
                "| "
                + " | ".join(
                    (
                        name,
                        kind,
                        f"{budget:g}",
                        f"{reward:,.0f} / {xp:,.0f} XP",
                        *(f"{amount:,.0f}" for amount in amounts),
                    )
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Weekly Growth Scenario",
            "",
            "| Snapshot | Effective PV/min | Largest weekly budget | Completion minutes |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name, pv_per_minute, budget in weekly_growth:
        lines.append(f"| {name} | {pv_per_minute:.2f} | {budget:g} | {_completion_minutes(budget, pv_per_minute)} |")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
