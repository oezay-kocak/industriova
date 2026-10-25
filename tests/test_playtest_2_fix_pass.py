from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, InstallCardInHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.factory_view_v2 import FactoryV2MachineCard, FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_source_development_window_restores_dev_tab_and_release_override_hides_it() -> None:
    _app()
    development = MainWindow(development_mode=True)
    release = MainWindow(development_mode=False)

    development_tabs = development.findChild(QTabWidget, "mainTabs")
    release_tabs = release.findChild(QTabWidget, "mainTabs")
    assert development_tabs.tabText(development_tabs.count() - 1) == "Dev"
    assert development.findChild(DevToolsView) is not None
    assert "Dev" not in [release_tabs.tabText(index) for index in range(release_tabs.count())]
    assert release.findChild(DevToolsView) is None


def test_contract_delivery_progress_updates_in_place_without_page_rebuild() -> None:
    _app()
    window = MainWindow(development_mode=False)
    view = window.findChild(ContractsView)
    assert view is not None
    card = next(card for card in view.findChildren(QFrame, "contractCard") if card.property("kind") == "regular")
    used = set()
    for selector in card.findChildren(QComboBox, "contractProductSelect"):
        index = next(index for index in range(1, selector.count()) if selector.itemData(index) not in used)
        used.add(selector.itemData(index))
        selector.setCurrentIndex(index)
    accept = card.findChild(QPushButton, "acceptContractButton")
    assert accept.isEnabled()
    accept.click()
    active = view._state.contracts.active["regular"]
    active_card = next(
        card for card in view.findChildren(QFrame, "contractCard")
        if card.property("contractId") == active.offer.contract_id
    )
    rebuild_count = view._content_rebuild_count

    for fraction in (0.2, 0.45, 0.7):
        for resource_id, required in active.offer.requirements.items():
            active.delivered[resource_id] = required * fraction
        view.refresh()
        QApplication.processEvents()
        assert view._content_rebuild_count == rebuild_count
        assert next(
            card for card in view.findChildren(QFrame, "contractCard")
            if card.property("contractId") == active.offer.contract_id
        ) is active_card
        for row in active_card.findChildren(QFrame, "contractRequirementRow"):
            label = row.findChild(QLabel, "contractRequirementAmount")
            assert label.property("deliveredAmount") > 0


@pytest.mark.parametrize(
    "definition_id,first_id,second_id",
    [
        ("machine.extractor", "resource.iron_ore", "resource.coal"),
        ("machine.drilling", "resource.crude_oil", "resource.natural_gas"),
        ("machine.agriculture", "resource.wheat", "resource.corn"),
    ],
)
def test_primary_machine_resource_control_switches_in_place(definition_id: str, first_id: str, second_id: str) -> None:
    _app()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResourcesViewV2)
    assert view is not None
    card_id = f"switch-{definition_id}"
    card = create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)
    view._command_bus.dispatch(AddCard(card))
    view._state.resource_sites["site-1"].specialization = definition_id
    view._command_bus.dispatch(InstallCardInHall("site-1", 0, card_id, "resources"))
    view._state.production_progress.unlocked_production_ids.update({first_id, second_id})
    view._command_bus.dispatch(SelectMachineProduction(card_id, first_id, first_id.removeprefix("resource.")))
    view.refresh_view()

    machine_card = view._slot_widgets[0]
    assert isinstance(machine_card, FactoryV2MachineCard)
    opened = []
    machine_card.production_change_requested.connect(opened.append)
    event = type(
        "Event",
        (),
        {
            "button": lambda self: Qt.MouseButton.LeftButton,
            "position": lambda self: machine_card._resource_control_rect().center(),
        },
    )()
    machine_card.mousePressEvent(event)

    assert opened == [card_id]
    assert view.findChild(QFrame, "productionSelectionView") is not None
    assert view._state.resource_sites["site-1"].slots[0].card_id == card_id
    view._command_bus.dispatch(SelectMachineProduction(card_id, second_id, second_id.removeprefix("resource.")))
    assert view._state.machine_production[card_id].selected_production_id == second_id
    assert view._state.resource_sites["site-1"].slots[0].card_id == card_id


@pytest.mark.parametrize(
    "definition_id,first_id,first_resource,second_id,second_resource",
    [
        ("machine.processor", "recipe.processor.iron", "iron", "recipe.processor.copper", "copper"),
        ("machine.fabricator", "recipe.fabricator.iron_components", "iron_components", "recipe.fabricator.copper_wire", "copper_wire"),
        ("machine.assembler", "recipe.assembler.industrial_equipment", "industrial_equipment", "recipe.assembler.heavy_machinery", "heavy_machinery"),
    ],
)
def test_downstream_machine_recipe_control_switches_in_place(
    definition_id: str,
    first_id: str,
    first_resource: str,
    second_id: str,
    second_resource: str,
) -> None:
    _app()
    window = MainWindow(development_mode=False)
    view = window.findChild(FactoryViewV2)
    assert view is not None
    card_id = f"switch-{definition_id}"
    view._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)))
    view._command_bus.dispatch(InstallCardInHall("hall-1", 0, card_id, "factory"))
    view._state.production_progress.unlocked_production_ids.update({first_id, second_id})
    view._command_bus.dispatch(SelectMachineProduction(card_id, first_id, first_resource))
    view.refresh_view()

    machine_card = view._slot_widgets[0]
    opened: list[str] = []
    removal_clicks: list[int] = []
    machine_card.production_change_requested.connect(opened.append)
    machine_card.clicked.connect(removal_clicks.append)
    event = type(
        "Event",
        (),
        {
            "button": lambda self: Qt.MouseButton.LeftButton,
            "position": lambda self: machine_card._resource_control_rect().center(),
        },
    )()
    machine_card.mousePressEvent(event)

    assert opened == [card_id]
    assert removal_clicks == []
    assert view.findChild(QFrame, "productionSelectionView") is not None
    assert view._state.halls["hall-1"].slots[0].card_id == card_id
    view._command_bus.dispatch(SelectMachineProduction(card_id, second_id, second_resource))
    state = view._state.machine_production[card_id]
    assert state.selected_production_id == second_id
    assert state.target_resource_id == second_resource
    assert view._state.halls["hall-1"].slots[0].card_id == card_id
