from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton

from production_zero.core.contracts import CONTRACT_REQUIREMENT_COUNTS
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.main_window import MainWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _view_with_four_products() -> ContractsView:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    assert view is not None
    view._test_window = window
    view._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    view._state.ensure_resource("steel").amount = 1
    for rid in ("iron_ore", "coal", "copper_ore"):
        view._state.ensure_resource(rid).amount = 1
    view.refresh()
    return view


def _card(view: ContractsView, kind: str, position: int = 0) -> QFrame:
    return [card for card in view.findChildren(QFrame, "contractCard") if card.property("kind") == kind][position]


def _enabled(combo: QComboBox, resource_id: str) -> bool:
    index = combo.findData(resource_id)
    item = combo.model().item(index)
    return index >= 0 and item is not None and item.isEnabled()


@pytest.mark.parametrize("kind,count", [("regular", 2), ("daily", 3), ("weekly", 4)])
def test_automatic_contract_card_has_complete_unique_fixed_requirements(kind: str, count: int) -> None:
    view = _view_with_four_products()
    card = _card(view, kind)
    assert kind not in view._state.contracts.active
    offer = view._state.contracts.offers[kind][0]
    controls = view._selection_controls[(kind, offer.contract_id)]
    assert not controls['accept'].isEnabled()
    for index, combo in enumerate(controls['combos']):
        candidates = [i for i in range(1, combo.count()) if combo.model().item(i).isEnabled()]
        combo.setCurrentIndex(candidates[0])
    assert controls['accept'].isEnabled()
    controls['accept'].click()
    card = _card(view, kind)
    active = view._state.contracts.active[kind]
    assert len(active.offer.requirements) == count == CONTRACT_REQUIREMENT_COUNTS[kind]
    assert all(amount > 0 for amount in active.offer.requirements.values())
    assert len(view._state.contracts.offers[kind]) == 1
    assert card.property("state") == "active"
    assert not card.findChildren(QComboBox, "contractProductSelect")
    assert card.findChild(QPushButton, "acceptContractButton") is None
    identities = tuple(id(widget) for widget in card.findChildren(QLabel))
    before = dict(active.offer.requirements)
    view.refresh()
    assert tuple(id(widget) for widget in card.findChildren(QLabel)) == identities
    assert active.offer.requirements == before
    assert card.findChild(QPushButton, "cancelContractButton").isEnabled()


def test_automatic_delivery_progress_updates_without_rebuilding_cards() -> None:
    from production_zero.core.contracts import receive_contract_delivery
    view = _view_with_four_products()
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(view._state, view._definitions, 'daily')
    view.refresh()
    card = _card(view, "daily")
    active = view._state.contracts.active["daily"]
    rid, required = next(iter(active.offer.requirements.items()))
    before = view._content_rebuild_count
    labels = tuple(id(label) for label in card.findChildren(QLabel))
    receive_contract_delivery(view._state, active.offer.contract_id, rid, required / 2, view._definitions)
    view.refresh()
    assert active.delivered[rid] == required / 2
    assert view._content_rebuild_count == before
    assert tuple(id(label) for label in card.findChildren(QLabel)) == labels
    assert active.offer.requirements[rid] == required
