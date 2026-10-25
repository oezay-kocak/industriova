"""P6 real Contract widgets: complete quotes, preferences and automatic renewal."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFrame, QLabel, QPushButton
from production_zero.ui.pz_controls import RaisedPZButton

from test_ui_interaction_recovery import app, window, board
from production_zero.core.commands import SellMachines
from production_zero.core.contracts import (CONTRACT_KINDS, REGULAR, receive_contract_delivery,
    contract_requirements_for_products, ContractBook)
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.ui.freight_view import FreightView


def offer_controls(view, kind):
    offer = view._state.contracts.offers[kind][0]
    return offer, view._selection_controls[kind, offer.contract_id]


def click_auto(check):
    QTest.mouseClick(check, Qt.MouseButton.LeftButton)


def assert_auto_color(button, enabled):
    assert button.variant == ('primary' if enabled else 'secondary')
    assert button.property('pzButtonVariant') == button.variant
    image = button.grab().toImage()
    yellow = sum(1 for y in range(image.height()) for x in range(image.width())
                 if (color := image.pixelColor(x, y)).red() > 150 and color.green() > 100 and color.blue() < 100)
    assert (yellow > image.width() * image.height() * .15) == enabled


def choose_all(view, kind):
    view._state.ensure_resource('bauxite').amount = max(1, view._state.ensure_resource('bauxite').amount)
    view.refresh()
    offer, controls = offer_controls(view, kind)
    selected = []
    for combo in controls['combos']:
        index = next(i for i in range(1, combo.count()) if combo.itemData(i) not in selected and combo.model().item(i).isEnabled())
        selected.append(combo.itemData(index)); combo.setCurrentIndex(index)
    return offer, controls, tuple(selected)


@pytest.mark.parametrize('kind', CONTRACT_KINDS)
def test_no_delivery_quantity_is_exposed_until_every_product_is_selected(window, kind):
    view = board(window, 'Contracts')
    for rid in ('iron_ore', 'coal', 'copper_ore', 'bauxite'):
        view._state.ensure_resource(rid).amount = 1
    view.refresh(); offer, controls = offer_controls(view, kind)
    chosen = []
    for index, combo in enumerate(controls['combos']):
        for amount in controls['amounts']: assert amount.property('requiredAmount') is None
        assert not controls['accept'].isEnabled()
        candidate = next(i for i in range(1, combo.count()) if combo.itemData(i) not in chosen and combo.model().item(i).isEnabled())
        chosen.append(combo.itemData(candidate)); combo.setCurrentIndex(candidate)
        if index < len(controls['combos']) - 1:
            for button, amount in zip(controls['buttons'], controls['amounts']):
                assert amount.property('requiredAmount') is None
                assert amount.text() == '—'
                assert 'final quantities' in button.toolTip()
    expected = contract_requirements_for_products(view._state, offer, view._definitions, tuple(chosen))
    assert controls['accept'].isEnabled()
    assert [amount.property('requiredAmount') for amount in controls['amounts']] == list(expected.values())
    # Clearing one slot immediately hides every provisional quantity again.
    controls['combos'][-1].setCurrentIndex(0)
    assert all(amount.property('requiredAmount') is None for amount in controls['amounts'])
    assert not controls['accept'].isEnabled()
    controls['combos'][-1].setCurrentIndex(controls['combos'][-1].findData(chosen[-1]))
    controls['accept'].click()
    assert view._state.contracts.active[kind].offer.requirements == expected


@pytest.mark.parametrize('kind', CONTRACT_KINDS)
def test_priority_button_cycles_and_preserves_selection_widgets(window, kind):
    view = board(window, 'Contracts'); offer, controls, chosen = choose_all(view, kind)
    buttons = view.findChildren(QPushButton, 'contractPriorityButton')
    assert len(buttons) == 3
    button = next(b for b in buttons if b.property('kind') == kind)
    card = next(c for c in view.findChildren(QFrame, 'contractCard') if c.property('kind') == kind)
    original = tuple(controls['combos']); rebuilds = view._content_rebuild_count
    for value, text in ((1, 'PRIORITY 1'), (2, 'PRIORITY 2'), (0, 'EVEN')):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton); view.refresh()
        assert view._state.contracts.priorities[kind] == value and button.text() == text
        assert view._content_rebuild_count == rebuilds
        assert controls['combos'] == list(original)
        assert tuple(combo.currentData() for combo in original) == chosen
        assert card in view.findChildren(QFrame, 'contractCard')
    restored = deserialize_game_state(serialize_game_state(view._state))
    assert restored.contracts.priorities == view._state.contracts.priorities


@pytest.mark.parametrize('size', [(1366, 768), (1600, 980), (1920, 1080)])
def test_auto_accept_renew_toggle_and_cancel_at_supported_sizes(window, size):
    window.resize(*size); view = board(window, 'Contracts')
    check = view.findChild(RaisedPZButton, 'regularAutoRepeatButton')
    assert not check.isChecked() and not view._state.contracts.regular_auto.enabled
    assert_auto_color(check, False)
    panel = next(p for p in view.findChildren(QFrame, 'contractPanel') if p.property('kind') == REGULAR)
    priority = panel.findChild(QPushButton, 'contractPriorityButton')
    assert check.parentWidget() is priority.parentWidget()
    assert abs(check.y() - priority.y()) <= 1
    assert priority.x() >= check.geometry().right() + 4
    right_margin = panel.width() - priority.geometry().right()
    for other in view.findChildren(QFrame, 'contractPanel'):
        other_priority = other.findChild(QPushButton, 'contractPriorityButton')
        assert abs(other.width() - other_priority.geometry().right() - right_margin) <= 1
    title = panel.findChild(QLabel, 'contractSectionTitle')
    assert title.fontMetrics().horizontalAdvance(title.text()) <= title.width()
    click_auto(check)
    assert check.isChecked() and not view._state.contracts.regular_auto.enabled
    assert_auto_color(check, True)
    _, controls, selected = choose_all(view, REGULAR)
    controls['accept'].click(); QTest.qWait(10)
    s = view._state; original = s.contracts.active[REGULAR]
    assert s.contracts.regular_auto.enabled and s.contracts.regular_auto.resource_ids == selected
    for rid, quantity in original.offer.requirements.items():
        receive_contract_delivery(s, original.offer.contract_id, rid, quantity, view._definitions)
    view.refresh(); QTest.qWait(10)
    current = s.contracts.active[REGULAR]
    assert current.offer.contract_id != original.offer.contract_id and tuple(current.offer.requirements) == selected
    check = view.findChild(RaisedPZButton, 'regularAutoRepeatButton')
    assert check.isChecked()
    assert_auto_color(check, True)
    assert view.findChild(QLabel, 'regularAutoRepeatStatus').text().startswith('AUTO ON')
    click_auto(check); assert not s.contracts.regular_auto.enabled and s.contracts.active[REGULAR] is current
    assert_auto_color(check, False)
    click_auto(check); assert s.contracts.regular_auto.enabled
    assert_auto_color(check, True)
    panel = next(p for p in view.findChildren(QFrame, 'contractPanel') if p.property('kind') == REGULAR)
    for control in (check, panel.findChild(QPushButton, 'contractPriorityButton')):
        assert control.isVisible() and panel.rect().contains(control.mapTo(panel, control.rect().center()))
    card = next(c for c in view.findChildren(QFrame, 'contractCard') if c.property('kind') == REGULAR)
    cancel = card.findChild(QPushButton, 'cancelContractButton')
    assert cancel.isEnabled() and cancel.height() >= 60
    cancel.click()
    assert not s.contracts.regular_auto.enabled and REGULAR not in s.contracts.active
    assert not view.findChild(RaisedPZButton, 'regularAutoRepeatButton').isChecked()
    assert view._board_scroll.horizontalScrollBar().maximum() == 0


def test_auto_pause_reason_is_visible_and_stopping_it_is_persistent(window):
    view = board(window, 'Contracts'); view.findChild(RaisedPZButton, 'regularAutoRepeatButton').click()
    _, controls, _ = choose_all(view, REGULAR); controls['accept'].click()
    s = view._state
    trucks = tuple(cid for cid, c in s.cards.items() if c.definition_id == 'freight.truck')
    SellMachines(trucks, view._definitions).apply(s)
    active = s.contracts.active[REGULAR]
    for rid, quantity in active.offer.requirements.items():
        receive_contract_delivery(s, active.offer.contract_id, rid, quantity, view._definitions)
    view.refresh()
    label = view.findChild(QLabel, 'regularAutoRepeatStatus')
    assert label.text().startswith('AUTO PAUSED') and label.toolTip() == label.text()
    check = view.findChild(RaisedPZButton, 'regularAutoRepeatButton')
    assert check.isChecked(); check.click()
    assert not s.contracts.regular_auto.enabled
    restored = deserialize_game_state(serialize_game_state(s))
    assert not restored.contracts.regular_auto.enabled


def test_new_session_clears_pending_auto_checkbox_and_priorities(window):
    view = board(window, 'Contracts'); view.findChild(RaisedPZButton, 'regularAutoRepeatButton').click()
    for button in view.findChildren(QPushButton, 'contractPriorityButton'): button.click()
    view._state.contracts = ContractBook()
    view.reset_for_state_change()
    assert not view.findChild(RaisedPZButton, 'regularAutoRepeatButton').isChecked()
    assert all(button.text() == 'EVEN' for button in view.findChildren(QPushButton, 'contractPriorityButton'))


def test_freight_need_display_counts_only_each_targets_reserved_share(window):
    from test_contract_priority_auto import fixed
    from production_zero.core.freight import OutboundFreightShipment
    f = window.findChild(FreightView); s = fixed((20, 20, 20))
    f._state = s
    s.freight.outbound_shipments['shared'] = OutboundFreightShipment('shared', 'contract',
        resource_id='iron_ore', quantity=30, contract_allocations={k: 10 for k in CONTRACT_KINDS})
    assert f._has_matching_contract_need('iron_ore')
    s.freight.outbound_shipments['shared'].quantity = 60
    s.freight.outbound_shipments['shared'].contract_allocations = {k: 20 for k in CONTRACT_KINDS}
    assert not f._has_matching_contract_need('iron_ore')
