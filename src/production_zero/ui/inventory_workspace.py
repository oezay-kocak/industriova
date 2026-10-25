"""Bounded Inventory presentation; ownership and operations remain in the core."""
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QScrollArea, QSpinBox, QVBoxLayout, QWidget

from production_zero.core.commands import InstallCardInHall, InstallFreightCard, ResetInventoryFreightRoutes, SellMachines
from production_zero.core.definitions import FreightDefinition
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.machine_operations import compatible_free_slots, resale_value
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.ui.release_dialogs import IndustrialDialog, confirm, inform


class InventoryWorkspaceMixin:
    def _build_workspace(self):
        from production_zero.ui.inventory_view import InventoryCardsHeader
        self.setObjectName("inventoryView")
        self._workspace_selected = set()
        self._workspace_pool = []
        self._workspace_rows = ()
        self._workspace_active = None
        self._workspace_columns = 1
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        root.addWidget(InventoryCardsHeader())
        toolbar = QHBoxLayout()
        self._workspace_category = QComboBox()
        self._workspace_category.setObjectName("inventoryCategory")
        self._workspace_category.addItems(["All", "Resources", "Factory", "Energy", "Freight"])
        self._workspace_category.currentTextChanged.connect(self._filter_workspace)
        toolbar.addWidget(self._workspace_category)
        root.addLayout(toolbar)
        self._workspace_scroll = QScrollArea()
        self._workspace_scroll.setObjectName("inventoryCardsScroll")
        self._workspace_scroll.setWidgetResizable(False)
        self._workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._workspace_canvas = QWidget()
        self._workspace_scroll.setWidget(self._workspace_canvas)
        self._workspace_scroll.viewport().installEventFilter(self)
        self._workspace_scroll.verticalScrollBar().valueChanged.connect(self._materialize_workspace)
        root.addWidget(self._workspace_scroll, 1)
        self._workspace_empty = QLabel("NO AVAILABLE CARDS\nPurchase cards in Industrial Supply. Install them when you are ready.", self._workspace_canvas)
        self._workspace_empty.setObjectName("inventoryEmptyState")
        self._workspace_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._workspace_empty.setWordWrap(True)
        self._workspace_menu = None
        self._workspace_anchor = None
        self._refresh_workspace()

    def _workspace_action(self, action):
        try:
            action()
        except (ValueError, KeyError, IndexError) as error:
            inform(self, "Inventory", str(error))

    @staticmethod
    def _workspace_row_category(row):
        from production_zero.core.definitions import EnergyDefinition, MachineDefinition
        from production_zero.core.machine_operations import SITE_TYPES
        if isinstance(row.definition, FreightDefinition):
            return "Freight"
        if isinstance(row.definition, EnergyDefinition):
            return "Energy"
        if isinstance(row.definition, MachineDefinition):
            return "Resources" if row.card.definition_id in SITE_TYPES else "Factory"
        return "Cards"

    def _refresh_workspace(self):
        self._rows = build_card_inventory_rows(self._state, self._definitions)
        available = {cid for row in self._rows if row.status == "Available" for cid in row.card_ids}
        self._workspace_selected.intersection_update(available)
        self._filter_workspace(reset_scroll=False)

    def _filter_workspace(self, *args, reset_scroll=True):
        if reset_scroll:
            self._workspace_selected.clear()
            self._workspace_active = None
            self._workspace_anchor = None
        category = self._workspace_category.currentText()
        self._workspace_rows = tuple(sorted((row for row in self._rows if row.status == "Available"
            and (category == "All" or self._workspace_row_category(row) == category)),
            key=lambda row: (row.definition.name, row.card.mk_level, row.rarity.value, row.card.card_id)))
        self._workspace_by_id = {cid: row for row in self._workspace_rows for cid in row.card_ids}
        if reset_scroll:
            self._workspace_scroll.verticalScrollBar().setValue(0)
        self._layout_workspace()
        self._update_workspace_actions()

    def _layout_workspace(self):
        if not hasattr(self, "_workspace_canvas"):
            return
        from production_zero.ui.inventory_view import INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT, INVENTORY_CARD_SPACING
        width = max(INVENTORY_CARD_WIDTH + 20, self._workspace_scroll.viewport().width())
        pitch = INVENTORY_CARD_WIDTH + INVENTORY_CARD_SPACING
        self._workspace_columns = max(1, (width - 20) // pitch)
        rows = (len(self._workspace_rows) + self._workspace_columns - 1) // self._workspace_columns
        self._workspace_canvas.resize(width, max(self._workspace_scroll.viewport().height(), rows * (INVENTORY_CARD_HEIGHT + INVENTORY_CARD_SPACING) + 20))
        self._workspace_empty.setGeometry(20, 20, width - 40, max(150, self._workspace_scroll.viewport().height() - 40))
        self._workspace_empty.setVisible(not self._workspace_rows)
        self._materialize_workspace()

    def _materialize_workspace(self, *args):
        if not hasattr(self, "_workspace_canvas"):
            return
        from production_zero.ui.inventory_view import InventoryCardFrame, INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT, INVENTORY_CARD_SPACING
        pitch_y = INVENTORY_CARD_HEIGHT + INVENTORY_CARD_SPACING
        first = max(0, self._workspace_scroll.verticalScrollBar().value() // pitch_y - 1) * self._workspace_columns
        count = (self._workspace_scroll.viewport().height() // pitch_y + 4) * self._workspace_columns
        indexes = range(first, min(len(self._workspace_rows), first + count))
        while len(self._workspace_pool) < len(indexes):
            row = self._workspace_rows[0]
            card = InventoryCardFrame(row, title="", family="processor", meta="", detail="", selected=False)
            card.setParent(self._workspace_canvas)
            card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            card.installEventFilter(self)
            card.mousePressEvent = lambda event, widget=card: self._workspace_card_press(widget, event)
            card.hovered.connect(lambda widget=card: self._show_card_hover(widget._inventory_row, widget))
            card.unhovered.connect(self._hide_card_hover)
            self._workspace_pool.append(card)
        focused_id = next((card._inventory_row.card.card_id for card in self._workspace_pool
            if card.hasFocus() and getattr(card, "_inventory_row", None) is not None), None)
        focus_target = None
        for position, card in enumerate(self._workspace_pool):
            if position >= len(indexes):
                card.hide()
                card._inventory_row = None
                card.setProperty("cardId", None)
                card._selected = False
                card.setProperty("selected", False)
                continue
            index = indexes[position]
            row = self._workspace_rows[index]
            if getattr(card, "_inventory_row", None) != row:
                self._hide_card_hover()
            card._inventory_row = row
            if focused_id == row.card.card_id:
                focus_target = card
            card._inventory_index = index
            title = row.definition.name.upper()
            # The shared bitmap lettering has a minimum cell size. Bound its
            # columns here; the complete name remains in details and hover.
            if sum(3 if char == " " else 6 for char in title) > 145:
                title = title[:20].rstrip() + "..."
            card._title = title
            card._family = self._card_game_family(row)
            card._meta = f"MK{row.card.mk_level} · {row.rarity.value.upper()}"
            card._detail = f"+{row.card.output_bonus_percent:.1f}% BONUS"
            card._quantity = row.quantity
            card._status = self._workspace_row_category(row).upper()
            card._selected = bool(self._workspace_selected.intersection(row.card_ids))
            card.setProperty("selected", card._selected)
            card.setProperty("cardId", row.card.card_id)
            card.setProperty("cardMeta", card._meta)
            card.setProperty("rarity", row.rarity.value)
            card.setProperty("cardType", self._card_type_key(row))
            card.setProperty("cardTitle", card._title)
            card.setProperty("cardDetail", card._detail)
            card.setProperty("statusText", row.status)
            card.setProperty("cardStatusText", card._status)
            card.setProperty("quantity", row.quantity)
            card.setAccessibleName(f"{row.definition.name}, {card._meta}, {row.quantity} available")
            selected_count = len(self._workspace_selected.intersection(row.card_ids))
            details = f"{row.definition.name} · {selected_count}/{row.quantity} selected\nRight-click: Install / Sell / Select quantity. Ctrl-click adds a stack; Shift-click selects a range. Ctrl+A selects all."
            route = self._state.freight.assignments.get(row.card.card_id)
            if route:
                from production_zero.core.freight import OUTBOUND_FREIGHT_DESTINATIONS
                valid = route.resource_id in self._state.resources and route.destination_kind in OUTBOUND_FREIGHT_DESTINATIONS
                details += f"\nStored route: {route.resource_id} → {route.destination_kind}" + ("" if valid else " · INVALID: reset before installation")
            card.setToolTip(details)
            card.setGeometry(10 + index % self._workspace_columns * (INVENTORY_CARD_WIDTH + INVENTORY_CARD_SPACING),
                10 + index // self._workspace_columns * pitch_y, INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
            card.show()
            card.update()
        if focused_id is not None:
            if focus_target is not None:
                focus_target.setFocus()
            else:
                self._workspace_scroll.setFocus()

    def _workspace_event(self, watched, event):
        if hasattr(self, "_workspace_scroll") and watched is self._workspace_scroll.viewport() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            QTimer.singleShot(0, self, self._layout_workspace)
        row = getattr(watched, "_inventory_row", None)
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._select_all_workspace()
            return True
        if row is not None and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
                self._choose_workspace_card(row, event.modifiers())
                return True
            delta = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: -self._workspace_columns, Qt.Key.Key_Down: self._workspace_columns}.get(event.key())
            if delta is not None:
                index = max(0, min(len(self._workspace_rows) - 1, watched._inventory_index + delta))
                self._workspace_scroll.ensureVisible(0, 10 + index // self._workspace_columns * 234, 0, 224)
                self._materialize_workspace()
                target = next((card for card in self._workspace_pool if card.isVisible() and card._inventory_index == index), None)
                if target:
                    target.setFocus()
                return True
        return False

    def _workspace_card_press(self, widget, event):
        row = widget._inventory_row
        if row is None:
            return
        if event.button() == Qt.MouseButton.RightButton:
            if not self._workspace_selected.intersection(row.card_ids):
                self._choose_workspace_card(row)
            self._show_workspace_menu(row)
        elif event.button() == Qt.MouseButton.LeftButton:
            self._choose_workspace_card(row, event.modifiers())

    def _choose_workspace_card(self, row, modifiers=Qt.KeyboardModifier.NoModifier):
        index = self._workspace_rows.index(row)
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self._workspace_anchor is not None:
            lo, hi = sorted((self._workspace_anchor, index))
            self._workspace_selected.update(r.card_ids[0] for r in self._workspace_rows[lo:hi + 1])
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            selected = self._workspace_selected.intersection(row.card_ids)
            if selected:
                self._workspace_selected.difference_update(selected)
            else:
                self._workspace_selected.add(row.card_ids[0])
            self._workspace_anchor = index
        else:
            self._workspace_selected = {row.card_ids[0]}
            self._workspace_anchor = index
        self._workspace_active = row.card.card_id
        self._update_workspace_actions()
        self._materialize_workspace()

    def _workspace_quantity_changed(self, quantity):
        row = self._workspace_by_id.get(self._workspace_active)
        if row:
            self._workspace_selected.difference_update(row.card_ids)
            self._workspace_selected.update(row.card_ids[:quantity])
            self._update_workspace_actions()
            self._materialize_workspace()

    def _show_workspace_menu(self, row):
        if self._workspace_menu is not None:
            self._workspace_menu.close()
        ids = self._workspace_ids()
        dialog = IndustrialDialog('Inventory actions', f'{len(ids):,} selected card(s) · Right-click preserves your selection.', self)
        dialog.setObjectName('inventoryContextMenu')
        dialog.accept_button.hide()
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        actions = [('INSTALL', self._install_workspace_card, Accent.BUILD),
                   ('SELL', self._sell_workspace_cards, Accent.DANGER)]
        if ids and all(isinstance(self._definitions[self._state.cards[cid].definition_id], FreightDefinition) for cid in ids):
            actions.append(('RESET ROUTE', self._reset_workspace_route, Accent.STORAGE))
        if row.quantity > 1:
            actions.append(('SELECT QUANTITY', lambda: self._choose_workspace_quantity(row), Accent.BUILD))
        for index, (text, action, accent) in enumerate(actions):
            button = GameButton(text, variant='primary', accent=accent)
            button.setObjectName('inventoryContext' + text.title().replace(' ', ''))
            button.setMinimumSize(230, 44)
            def run(checked=False, action=action):
                dialog.accept()
                self._workspace_action(action)
            button.clicked.connect(run)
            grid.addWidget(button, index // 2, index % 2)
        dialog.layout().itemAt(0).widget().layout().insertLayout(2, grid)
        self._workspace_menu = dialog
        dialog.finished.connect(lambda: self._workspace_menu_closed(dialog))
        dialog.open()

    def _workspace_menu_closed(self, dialog):
        if self._workspace_menu is dialog:
            self._workspace_menu = None
        dialog.deleteLater()

    def _choose_workspace_quantity(self, row):
        self._workspace_active = row.card.card_id
        dialog = IndustrialDialog('Select quantity', f'{row.definition.name} · {row.quantity:,} available. Other selected stacks are retained.', self, quantity=row.quantity, accept_text='SELECT')
        dialog.total.hide()
        dialog.quantity.setValue(max(1, len(self._workspace_selected.intersection(row.card_ids))))
        dialog.quantity.setToolTip('Concrete IDs, in selection order:\n' + '\n'.join(row.card_ids))
        session = self._state.cards
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if session is not self._state.cards:
                    raise ValueError('The game changed. Select cards again.')
                self._workspace_quantity_changed(dialog.quantity.value())
        finally:
            dialog.deleteLater()

    def _clear_workspace_selection(self):
        self._workspace_selected.clear()
        self._workspace_active = None
        self._workspace_anchor = None
        self._update_workspace_actions()
        self._materialize_workspace()

    def _select_all_workspace(self):
        self._workspace_selected = set(self._workspace_by_id)
        self._workspace_active = None
        self._update_workspace_actions()
        self._materialize_workspace()

    def _update_workspace_actions(self):
        self._workspace_selected.intersection_update(self._workspace_by_id)

    def _workspace_ids(self):
        return tuple(sorted(self._workspace_selected))

    def _install_workspace_card(self):
        ids = self._workspace_ids()
        if not ids:
            raise ValueError("Select available cards to install.")
        cid = ids[0]
        definition = self._definitions[self._state.cards[cid].definition_id]
        choices = compatible_free_slots(self._state, definition)
        if not choices:
            from production_zero.core.commands import _card_allowed_on_board
            from production_zero.core.machine_operations import site_accepts
            if isinstance(definition, FreightDefinition):
                matching = [unit for unit in self._state.freight.facilities.values() if unit.facility_type == definition.facility_id]
                if not matching:
                    raise ValueError(f"No compatible freight facility. Build a {definition.facility_name} first.")
            else:
                matching = [unit for board in ("resources", "factory", "energy")
                    if _card_allowed_on_board(self._state.cards[cid], board)
                    for unit in self._state.production_units(board).values()
                    if board != "resources" or site_accepts(self._state, unit, definition.definition_id)]
                if not matching:
                    raise ValueError("No compatible facility or resource specialization. Build the matching facility or select an empty site of the correct machine family.")
            raise ValueError("All compatible unlocked slots are occupied. Unlock another slot or return an installed card to Inventory.")
        dialog = IndustrialDialog("Install card", f"{len(ids):,} card(s) · {definition.name}\nSelect the first compatible facility and free slot. Further selected cards use remaining compatible free slots.\nInstallation is free. Quality and upgrades are preserved.", self, accept_text="INSTALL")
        target = QComboBox()
        target.setObjectName("inventoryInstallTarget")
        for unit, slot in choices:
            target.addItem(f"{unit.name} · Slot {slot.index + 1}")
        dialog.layout().itemAt(0).widget().layout().insertWidget(2, target)
        session = self._state.cards
        result = dialog.exec()
        selected_index = target.currentIndex()
        dialog.deleteLater()
        if result != QDialog.DialogCode.Accepted:
            return
        if session is not self._state.cards:
            raise ValueError('The game changed. Select cards again.')
        from copy import deepcopy
        from production_zero.core.commands import InstallInventoryCards
        prepared = deepcopy(self._state)
        unit, slot = choices[selected_index]
        commands = []
        for index, selected_id in enumerate(ids):
            definition = self._definitions[prepared.cards[selected_id].definition_id]
            if index:
                available = compatible_free_slots(prepared, definition)
                if not available:
                    raise ValueError('Not enough compatible free slots for the entire selection.')
                target_id = getattr(unit, 'hall_id', getattr(unit, 'facility_id', None))
                preferred = [choice for choice in available if getattr(choice[0], 'hall_id', getattr(choice[0], 'facility_id', None)) == target_id]
                selected_unit, selected_slot = (preferred or available)[0]
            else:
                selected_unit, selected_slot = unit, slot
            command = (InstallFreightCard(selected_unit.facility_id, selected_slot.index, selected_id, self._definitions)
                       if isinstance(definition, FreightDefinition) else
                       InstallCardInHall(selected_unit.hall_id, selected_slot.index, selected_id, selected_unit.board_kind))
            command.apply(prepared)
            commands.append(command)
        self._command_bus.dispatch(InstallInventoryCards(tuple(commands)))
        self._workspace_changed()

    def _sell_workspace_cards(self):
        ids = self._workspace_ids()
        if not ids:
            return
        session = self._state.cards
        total = sum(resale_value(self._state.cards[cid], self._definitions[self._state.cards[cid].definition_id]) for cid in ids)
        if confirm(self, "Sell inventory cards", f"{len(ids):,} selected card(s) will be permanently sold.\nMachines: {', '.join(sorted({self._definitions[self._state.cards[cid].definition_id].name for cid in ids}))}\n80% of documented acquisition and paid upgrades.\nProceeds: ${total:,.2f}", "YES – SELL"):
            if session is not self._state.cards:
                raise ValueError('The game changed. Select cards again.')
            installed = self._state.installed_card_ids() | self._state.installed_freight_card_ids()
            if installed.intersection(ids) or not set(ids) <= self._state.cards.keys():
                raise ValueError('The selected inventory cards changed. Review the selection again.')
            current = sum(resale_value(self._state.cards[cid], self._definitions[self._state.cards[cid].definition_id]) for cid in ids)
            if round(current, 2) != round(total, 2):
                raise ValueError('The sale quote changed. Review the selection again.')
            self._command_bus.dispatch(SellMachines(ids, self._definitions))
            self._workspace_changed()

    def _reset_workspace_route(self):
        ids = self._workspace_ids()
        session = self._state.cards
        if confirm(self, "Reset stored route", f"Reset routes for {len(ids):,} available vehicle(s)?\nActive deliveries are protected. Assign a new route on the Freight board after installation.", "RESET ROUTE"):
            if session is not self._state.cards:
                raise ValueError('The game changed. Select cards again.')
            self._command_bus.dispatch(ResetInventoryFreightRoutes(ids))
            self._workspace_changed()

    def _workspace_changed(self):
        if self._on_state_changed:
            self._on_state_changed()
            if self.property("uiDirty"):
                self.refresh()
                self.setProperty("uiDirty", False)
        else:
            self.refresh()

    def reset_for_state_change(self):
        if self._workspace_menu is not None:
            self._workspace_menu.close()
        self._workspace_anchor = None
        self._hide_card_hover()
        self._workspace_selected.clear()
        self._workspace_active = None
        self._rows = self._workspace_rows = ()
        self._workspace_by_id = {}
        for card in self._workspace_pool:
            card._inventory_row = None
            card.setProperty("cardId", None)
            card.hide()
        self._workspace_category.blockSignals(True)
        self._workspace_category.setCurrentIndex(0)
        self._workspace_category.blockSignals(False)
        self._workspace_scroll.verticalScrollBar().setValue(0)
        self._refresh_workspace()
