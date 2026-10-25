"""Shared single/group Freight upgrade confirmation, using the production command."""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QWidget
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.ui.release_dialogs import confirm, inform
from production_zero.core.commands import UpgradeMachines
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.machine_operations import installed_slot_snapshot
from production_zero.core.definitions import FreightDefinition


class FreightMkButton(GameButton):
    def __init__(self, view, card_id, parent):
        super().__init__('⇈', variant='primary', accent=Accent.SUCCESS)
        shield = QWidget(parent)
        shield.setObjectName('freightMkControl')
        shield.setFixedSize(36, 34)
        shield.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self.setParent(shield)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self.setObjectName('freightMkUpgrade')
        self.setFixedSize(36, 34)
        self.clicked.connect(lambda: upgrade_vehicles(view, vehicle_upgrade_targets(view, card_id)))
        self._view, self._card_id = view, card_id
        self.update_quote()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def update_quote(self):
        card = self._view._state.cards.get(self._card_id)
        definition = self._view._definitions.get(card.definition_id) if card else None
        ids = vehicle_upgrade_targets(self._view, self._card_id) if card else ()
        ids = tuple(cid for cid in ids if cid in self._view._state.cards and self._view._state.cards[cid].mk_level < 99)
        eligible = (card is not None and isinstance(definition, FreightDefinition) and bool(ids)
                    and all(isinstance(self._view._definitions.get(self._view._state.cards[cid].definition_id), FreightDefinition) for cid in ids))
        self.setEnabled(eligible)
        if eligible:
            cost = sum(mk_upgrade_cost(self._view._state.cards[cid], self._view._definitions[self._view._state.cards[cid].definition_id]) for cid in ids)
            cash_note = ' · Not enough cash' if cost > self._view._state.cash.amount else ''
            self.setToolTip(f'Upgrade this vehicle: MK{card.mk_level} → MK{card.mk_level + 1} · ${cost:,.2f}{cash_note}')
            if len(ids) > 1 or self._card_id not in ids:
                self.setToolTip(f'Upgrade {len(ids)} selected vehicles by one MK level · ${cost:,.2f} total{cash_note}')
        else:
            self.setToolTip('MK99 · Maximum MK level reached' if card and card.mk_level == 99 else 'Vehicle definition unavailable')
        # Disabled controls must retain their explanatory tooltip.
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)


def vehicle_upgrade_targets(view, card_id):
    from production_zero.ui.group_actions import action_targets
    from production_zero.ui.freight_lines import ordered_selection
    return action_targets(card_id, view._selected_vehicles, ordered_selection(view))


def upgrade_vehicles(view, ids):
    if getattr(view, '_freight_upgrade_pending', False):
        return
    view._freight_upgrade_pending = True
    try:
        session = view._state.cards
        facility_id = view._selected_facility_id
        eligible = tuple(cid for cid in ids if session[cid].mk_level < 99)
        if not eligible:
            return
        cards = tuple(session[cid] for cid in eligible)
        origins = installed_slot_snapshot(view._state, eligible)
        if len(origins) != len(eligible) or any(p[0] != 'freight' for p in origins):
            raise ValueError('Select installed Freight vehicles.')
        total = round(sum(mk_upgrade_cost(card, view._definitions[card.definition_id]) for card in cards), 2)
        if total > view._state.cash.amount:
            inform(view, 'MK Upgrade', f'Not enough cash. Required: ${total:,.2f}.')
            return
        if not confirm(view, 'MK Upgrade', f'{len(eligible)} vehicle(s). Total: ${total:,.2f}\nCurrent deliveries keep their original cargo and travel time.'):
            return
        if (session is not view._state.cards or facility_id != view._selected_facility_id
                or installed_slot_snapshot(view._state, eligible) != origins
                or any(view._state.cards.get(cid) is not card for cid, card in zip(eligible, cards))):
            raise ValueError('The selected vehicles changed. Reopen MK Upgrade.')
        if total != round(sum(mk_upgrade_cost(card, view._definitions[card.definition_id]) for card in cards), 2):
            raise ValueError('The upgrade price changed. Reopen MK Upgrade.')
        view._command_bus.dispatch(UpgradeMachines(eligible, view._definitions))
        for cid in eligible:
            widgets = view._runtime_widgets.get(cid)
            if widgets:
                view._update_card_runtime(cid, widgets)
        for button in view.findChildren(GameButton, "buildingMkUpgrade"):
            button.refresh_quote()
        if callback := getattr(view, '_card_operation_changed', None):
            callback()
    except (ValueError, KeyError) as error:
        inform(view, 'MK Upgrade', str(error))
    finally:
        # Include the trailing release/click of a physical double-click.
        QTimer.singleShot(QApplication.doubleClickInterval(), view,
                          lambda: setattr(view, '_freight_upgrade_pending', False))
