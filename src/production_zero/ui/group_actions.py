"""Shared targets, inventory placement and controls for board group actions."""
from PySide6.QtCore import Qt

from production_zero.core.commands import InstallCardInHall, InstallFreightCard, InstallInventoryCards
from production_zero.core.freight import is_freight_card_busy
from production_zero.core.definitions import EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.ui.game_ui import Accent, GameButton


def action_targets(card_id, selected, ordered):
    return tuple(cid for cid in ordered if cid in selected) if card_id in selected else (card_id,)


def install_snapshot(view, board, unit, indexes):
    return view._state.cards, board, unit, tuple(sorted(indexes))


def fill_inventory_slots(view, snapshot, card_id):
    session, board, unit, indexes = snapshot
    state = view._state
    units = state.freight.facilities if board == "freight" else state.production_units(board)
    uid = unit.facility_id if board == "freight" else unit.hall_id
    current_uid = view._selected_facility_id if board == "freight" else view._selected_hall_id
    if session is not state.cards or units.get(uid) is not unit or current_uid != uid:
        raise ValueError("The building or inventory changed. Reopen card selection.")
    unlocked = unit.unlocked_slot_indexes()
    if not indexes or len(set(indexes)) != len(indexes) or any(
        i not in unlocked or unit.slots[i].card_id is not None for i in indexes
    ):
        raise ValueError("The selected slots changed. Select empty unlocked slots again.")
    stack = next((s for s in state.inventory_card_stacks() if any(c.card_id == card_id for c in s.cards)), None)
    if stack is None or is_freight_card_busy(state.freight, card_id):
        raise ValueError("The selected card is no longer available in Inventory.")
    # Preserve the chosen stack's rarity, MK and bonuses. Never substitute a
    # different quality when that stack contains fewer cards than target slots.
    cards = sorted(stack.cards, key=lambda c: (c.card_id != card_id, c.card_id))
    cards = [c for c in cards if not is_freight_card_busy(state.freight, c.card_id)]
    commands = tuple(
        InstallFreightCard(uid, index, card.card_id, view._definitions) if board == "freight"
        else InstallCardInHall(uid, index, card.card_id, board)
        for index, card in zip(indexes, cards)
    )
    view._command_bus.dispatch(InstallInventoryCards(commands))
    return tuple(indexes[:len(commands)])


class BuildingMkButton(GameButton):
    def __init__(self, view, card_ids, upgrade):
        super().__init__("⇈", variant="primary", accent=Accent.SUCCESS)
        self.setObjectName("buildingMkUpgrade")
        self.setFixedSize(36, 36)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self._view, self._card_ids = view, card_ids
        self.clicked.connect(upgrade)
        self.refresh_quote()

    def refresh_quote(self):
        state = self._view._state
        ids = tuple(cid for cid in self._card_ids() if cid in state.cards and state.cards[cid].mk_level < 99)
        signature = tuple((state.cards[cid], self._view._definitions.get(state.cards[cid].definition_id)) for cid in ids)
        if getattr(self, "_quote_signature", None) == signature:
            return
        self._quote_signature = signature
        if any(not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)) for _card, definition in signature):
            self.setEnabled(False)
            self.setToolTip("A machine definition is unavailable; this building cannot be upgraded.")
            return
        self.setEnabled(bool(ids))
        total = sum(mk_upgrade_cost(state.cards[cid], self._view._definitions[state.cards[cid].definition_id]) for cid in ids)
        self.setToolTip(f"Upgrade all machines in this building by one MK level · {len(ids)} eligible · ${total:,.2f} total"
                        if ids else "No machines below MK99 in this building")
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
