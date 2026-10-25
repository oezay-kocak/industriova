"""Selection, group operations and drag/drop on the existing production boards."""
import json
from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QMimeData
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QApplication, QHBoxLayout, QRubberBand, QFrame, QComboBox, QLabel
from production_zero.core.machine_operations import (
    SITE_TYPES, pause_machines, sell_machines, resale_value, move_machines,
    copy_configuration, paste_configuration, configure_machines,
)
from production_zero.core.mk_upgrades import upgrade_cards, mk_upgrade_cost
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.ui.release_dialogs import confirm, inform

from production_zero.core.commands import UpgradeMachines, SellMachines, PauseMachines, MoveMachines, ConfigureMachines, PasteMachineConfigurations, SellProductionBuilding

MACHINE_MIME = "application/x-industriova-machine-selection"


class ReleaseBoardMixin:
    def _release_setup(self):
        if not hasattr(self, "_selected_machines"):
            self._selected_machines = set()
            self._selection_anchor = None
            self._configuration_clipboard = ()
            self._rubber_origin = None
            self._focused_line_id = None
            from uuid import uuid4
            from production_zero.ui.drag_feedback import BoardDragFeedback
            self._machine_drag_token = uuid4().hex
            self._machine_intent_token = None
            self._machine_drag_data = self._machine_drag = None
            self._machine_feedback = BoardDragFeedback(self, self._cancel_machine_drag, self._machine_hover)
            from production_zero.ui.production_templates import TemplateShortcuts
            self._template_shortcuts = TemplateShortcuts(self, lambda: self._release_action(self._copy_selection), lambda: self._release_action(self._paste_selection))
        self._selected_machines.intersection_update(self._state.cards)
        if not hasattr(self, "_selected_empty_slots"):
            self._selected_empty_slots = set()
            self._selection_unit_id = self._selected_hall_id
        if self._selection_unit_id != self._selected_hall_id:
            self._selected_machines.clear()
            self._selected_empty_slots.clear()
            self._selection_anchor = None
            self._selection_unit_id = self._selected_hall_id
        hall = self._units[self._selected_hall_id]
        self._selected_machines.intersection_update(s.card_id for s in hall.slots if s.card_id)
        self._selected_empty_slots.intersection_update(
            i for i in hall.unlocked_slot_indexes() if hall.slots[i].card_id is None
        )

    def _release_toolbar(self, layout):
        self._release_setup()
        self._update_selection_visuals()

    def _card_actions(self, card_id):
        from production_zero.ui.release_dialogs import IndustrialDialog
        from PySide6.QtWidgets import QGridLayout
        if card_id not in self._selected_machines:
            slot = next(s for s in self._units[self._selected_hall_id].slots if s.card_id == card_id)
            self._select_slot(slot.index, Qt.KeyboardModifier.NoModifier)
        dialog = IndustrialDialog("Machine actions", f"{len(self._ordered_selection())} selected machines", self)
        dialog.accept_button.hide()
        grid = QGridLayout()
        paused = all(self._state.cards[cid].paused for cid in self._ordered_selection())
        pause_text = "RESUME" if paused else "PAUSE"
        actions = (("Recipe", self._configure_selection), (pause_text, self._pause_selection),
                   ("Copy", self._copy_selection), ("Paste", self._paste_selection),
                   ("RETURN TO INVENTORY", self._return_selection), ("Sell", self._sell_selection),
                   ("MK UPGRADE", self._upgrade_selection))
        for i, (text, callback) in enumerate(actions):
            button = GameButton(text, variant="primary", accent=Accent.DANGER if text == "Sell" else Accent.BUILD)
            button.setObjectName("machineContextAction")
            button.setFixedSize(230, 42)
            if text == "Recipe":button.setEnabled(self._board_config.board_kind != "energy")
            if text == "Paste":button.setEnabled(bool(self._configuration_clipboard))
            def run(checked=False, callback=callback):
                dialog.accept()
                self._release_action(callback)
            button.clicked.connect(run)
            grid.addWidget(button, i // 2, i % 2)
        dialog.layout().itemAt(0).widget().layout().insertLayout(2, grid)
        dialog.exec()
        dialog.deleteLater()

    def _rename_building(self, unit_id=None):
        from production_zero.ui.interaction_polish import rename_building
        unit_id = unit_id or self._selected_hall_id
        unit = self._units[unit_id]
        def apply(name):
            from production_zero.core.commands import RenameHall
            try:
                if self._units.get(unit_id) is not unit:
                    raise ValueError('Building changed. Reopen the dialog.')
                self._command_bus.dispatch(RenameHall(unit_id, name, self._board_config.board_kind))
            except (ValueError, KeyError) as error:
                inform(self, 'Rename building', str(error))
                return
            self.refresh_view()
        rename_building(self, unit.name, apply)

    def _purchase_hall(self):
        if self._board_config.board_kind != "resources":
            return super()._purchase_hall()
        from production_zero.ui.interaction_polish import BuildingChoiceDialog
        from production_zero.core.infrastructure_prices import production_facility_price
        from production_zero.core.commands import PurchaseProductionUnit
        choices = [(key,name,self._definitions[key],production_facility_price(self._state,'resources',key)) for key,name in SITE_TYPES.items()]
        quotes={key:cost for key,_name,_definition,cost in choices}
        dialog = BuildingChoiceDialog(self, "BUILD SITE", choices, self._state.cash.amount)
        if dialog.exec() and dialog.selected_type:
            target=dialog.selected_type;before=set(self._units)
            try:
                self._command_bus.dispatch(PurchaseProductionUnit('resources',SITE_TYPES[target],self._board_config.unit_id_prefix,
                    3,10,1,1,target,quotes[target]))
            except (ValueError,KeyError) as error:
                inform(self,'Build site',str(error));return
            self._selected_hall_id=next(uid for uid in self._units if uid not in before)
            self.refresh_view()

    def _release_action(self, action):
        try:
            action()
        except (ValueError, KeyError, IndexError) as error:
            inform(self, "Industriova", str(error))

    def _ordered_selection(self):
        hall = self._units[self._selected_hall_id]
        return tuple(hall.slots[index].card_id for line in hall.production_lines if line.unlocked
                     for index in line.slot_indexes if hall.slots[index].card_id in self._selected_machines)

    def _on_slot_clicked(self, slot_index):
        self._release_setup()
        hall = self._units[self._selected_hall_id]
        slot = hall.slots[slot_index]
        if slot.card_id is None:
            modifiers = QApplication.keyboardModifiers()
            self._select_slot(slot_index, modifiers)
            if modifiers:
                return
            from production_zero.ui.group_actions import install_snapshot
            self._inventory_target_snapshot = install_snapshot(
                self, self._board_config.board_kind, hall, self._selected_empty_slots,
            )
            return super()._on_slot_clicked(slot_index)
        self._select_slot(slot_index, QApplication.keyboardModifiers())

    def _select_slot(self, slot_index, modifiers):
        self._release_setup()
        hall = self._units[self._selected_hall_id]
        cid = hall.slots[slot_index].card_id
        if slot_index not in hall.unlocked_slot_indexes():
            return
        ordered = [index for line in hall.production_lines if line.unlocked for index in line.slot_indexes]
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self._selection_anchor in ordered:
            low, high = sorted((ordered.index(self._selection_anchor), ordered.index(slot_index)))
            self._select_slot_positions(ordered[low:high + 1], bool(modifiers & Qt.KeyboardModifier.ControlModifier))
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            selection, key = (self._selected_machines, cid) if cid else (self._selected_empty_slots, slot_index)
            if key in selection:
                selection.remove(key)
            else:
                selection.add(key)
            self._selection_anchor = slot_index
        else:
            if not (cid in self._selected_machines if cid else slot_index in self._selected_empty_slots):
                self._select_slot_positions((slot_index,))
            self._selection_anchor = slot_index
        self._update_selection_visuals()

    def _select_slot_positions(self, indexes, additive=False):
        hall = self._units[self._selected_hall_id]
        indexes = set(indexes) & hall.unlocked_slot_indexes()
        machines = {hall.slots[i].card_id for i in indexes if hall.slots[i].card_id}
        empty = {i for i in indexes if hall.slots[i].card_id is None}
        self._selected_machines = self._selected_machines | machines if additive else machines
        self._selected_empty_slots = self._selected_empty_slots | empty if additive else empty

    def _update_selection_visuals(self):
        if not hasattr(self, "_selected_machines"):
            return
        selected_ids = self._ordered_selection()
        hall = self._units[self._selected_hall_id]
        signature = tuple(self._state.cards[s.card_id] for s in hall.slots if s.card_id in self._state.cards)
        if getattr(self, "_mk_quote_signature", None) != signature:
            self._mk_quote_signature = signature
            self._mk_quotes = {c.card_id: mk_upgrade_cost(c, self._definitions[c.definition_id])
                               for c in signature if c.mk_level < 99 and c.definition_id in self._definitions}
        group_eligible = tuple(cid for cid in selected_ids if cid in self._mk_quotes)
        group_total = sum(self._mk_quotes[cid] for cid in group_eligible)
        for index, widget in self._slot_widgets.items():
            cid = self._units[self._selected_hall_id].slots[index].card_id
            selected = cid in self._selected_machines if cid else index in self._selected_empty_slots
            if bool(widget.property("selected")) != selected:
                widget.setProperty("selected", selected)
                widget.update()
            button = getattr(widget, "_upgrade_button", None)
            if button is not None:
                eligible = group_eligible if cid in self._selected_machines else ((cid,) if cid in self._mk_quotes else ())
                button.setEnabled(bool(eligible))
                total = group_total if cid in self._selected_machines else self._mk_quotes.get(cid, 0)
                button.setToolTip(f"Upgrade {len(eligible)} selected machine(s) by one MK level · ${total:,.2f} total"
                                  if eligible else "MK99 · Maximum MK level reached")
        label = getattr(self, "_selection_count", None)
        if label is not None:
            from shiboken6 import isValid
            if isValid(label):
                label.setText(f"{len(self._ordered_selection())} machines · {len(self._selected_empty_slots)} empty slots selected")

    def _install_card_from_selection(self, card_id):
        if self._drawer_slot_index is None:
            return
        from production_zero.ui.group_actions import fill_inventory_slots, install_snapshot
        hall = self._units[self._selected_hall_id]
        snapshot = getattr(self, "_inventory_target_snapshot", None)
        if snapshot is None:
            snapshot = install_snapshot(self, self._board_config.board_kind, hall, (self._drawer_slot_index,))
        try:
            installed = fill_inventory_slots(self, snapshot, card_id)
        except (ValueError, KeyError, IndexError) as error:
            inform(self, "Install cards", str(error))
            return
        self._recent_install_slot_indexes.update(installed)
        self._selected_machines.update(hall.slots[i].card_id for i in installed)
        self._selected_empty_slots.difference_update(installed)
        self._reset_drawer_state()
        self._refresh_hall_tree()
        self._refresh_content()
        if callback := getattr(self, "_card_operation_changed", None):
            callback()

    def _build_factory_card_selection_view(self, hall):
        panel = super()._build_factory_card_selection_view(hall)
        snapshot = getattr(self, "_inventory_target_snapshot", None)
        if snapshot and len(snapshot[3]) > 1:
            hint = QLabel(f"{len(snapshot[3])} empty slots selected · Fill left to right using the chosen Inventory stack; available cards only.")
            hint.setObjectName("groupInstallHint")
            hint.setWordWrap(True)
            panel.layout().insertWidget(1, hint)
        return panel

    def _reset_drawer_state(self):
        self._inventory_target_snapshot = None
        self._production_target_snapshot = None
        return super()._reset_drawer_state()

    def _upgrade_selection(self, only=None):
        self._release_setup()
        ids = self._ordered_selection() if only is None or only in self._selected_machines else (only,)
        self._upgrade_ids(ids)

    def _upgrade_building(self):
        hall = self._units[self._selected_hall_id]
        self._upgrade_ids(tuple(hall.slots[i].card_id for i in sorted(hall.unlocked_slot_indexes()) if hall.slots[i].card_id))

    def _upgrade_ids(self, ids):
        if getattr(self, "_machine_upgrade_pending", False):
            return
        from PySide6.QtCore import QTimer
        self._machine_upgrade_pending = True
        try:
            self._confirm_upgrade_ids(ids)
        finally:
            QTimer.singleShot(QApplication.doubleClickInterval(), self,
                              lambda: setattr(self, "_machine_upgrade_pending", False))

    def _confirm_upgrade_ids(self, ids):
        from production_zero.core.machine_operations import installed_slot_snapshot
        ids = tuple(cid for cid in ids if self._state.cards[cid].mk_level < 99)
        if not ids:
            raise ValueError("No selected machines below MK99.")
        session, unit_id = self._state.cards, self._selected_hall_id
        cards = tuple(session[cid] for cid in ids)
        origins = installed_slot_snapshot(self._state, ids)
        if len(origins) != len(ids) or any(p[0] != self._board_config.board_kind or p[1] != unit_id for p in origins):
            raise ValueError("Select installed machines in this building.")
        total = round(sum(mk_upgrade_cost(card, self._definitions[card.definition_id]) for card in cards), 2)
        if total > self._state.cash.amount:
            raise ValueError(f"Not enough cash. Required: ${total:,.2f}.")
        details = "\n".join(f"{self._definitions[self._state.cards[cid].definition_id].name} MK{self._state.cards[cid].mk_level} → MK{self._state.cards[cid].mk_level + 1}" for cid in ids[:8])
        if confirm(self, "MK Upgrade", f"{len(ids)} machine(s)\n{details}\n\n+0.25× base throughput per machine; inputs and energy scale equally.\nTotal: ${total:,.2f}"):
            if (session is not self._state.cards or unit_id != self._selected_hall_id
                    or installed_slot_snapshot(self._state, ids) != origins
                    or any(self._state.cards.get(cid) is not card for cid, card in zip(ids, cards))):
                raise ValueError("The selected machines changed. Reopen MK Upgrade.")
            self._command_bus.dispatch(UpgradeMachines(tuple(ids), self._definitions))
            self.refresh_view()
            if callback := getattr(self, "_card_operation_changed", None):
                callback()

    def _pause_selection(self):
        ids = self._ordered_selection()
        self._command_bus.dispatch(PauseMachines(tuple(ids), not all(self._state.cards[cid].paused for cid in ids)))
        self.refresh_runtime()

    def _pause_line(self, line):
        hall = self._units[self._selected_hall_id]
        from production_zero.core.commands import PauseProductionScope
        self._command_bus.dispatch(PauseProductionScope(self._board_config.board_kind, hall.hall_id, not line.paused, line.line_id))
        self.refresh_runtime()

    def _configure_selection(self):
        from production_zero.core.definitions import MachineDefinition
        ids = tuple(cid for cid in self._ordered_selection() if isinstance(self._definitions[self._state.cards[cid].definition_id], MachineDefinition))
        if not ids:
            raise ValueError("Select production machines first.")
        self._open_production_drawer(ids[0])

    def _open_production_drawer(self, card_id):
        from production_zero.ui.group_actions import action_targets
        from production_zero.core.machine_operations import installed_slot_snapshot
        self._release_setup()
        ids = action_targets(card_id, self._selected_machines, self._ordered_selection())
        self._production_target_snapshot = (self._state.cards, ids, installed_slot_snapshot(self._state, ids))
        super()._open_production_drawer(card_id)

    def _build_production_selection_view(self):
        panel = super()._build_production_selection_view()
        snapshot = getattr(self, "_production_target_snapshot", None)
        label = panel.findChild(QLabel, "productionCurrentLabel")
        if snapshot and len(snapshot[1]) > 1 and label is not None:
            label.setText(label.text() + f" · {len(snapshot[1])} selected; compatible machines only")
        return panel

    def _apply_production_option(self, production_id, target_resource_id):
        from production_zero.core.machine_operations import installed_slot_snapshot
        snapshot = getattr(self, "_production_target_snapshot", None)
        ids = snapshot[1] if snapshot else self._ordered_selection()
        if snapshot and (snapshot[0] is not self._state.cards or installed_slot_snapshot(self._state, ids) != snapshot[2]):
            inform(self, "Recipe", "The selected machines changed. Reopen recipe selection.")
            return
        if len(ids) > 1 and self._production_drawer_card_id in ids:
            from production_zero.core.definitions import MachineDefinition
            from production_zero.core.progression import production_options_for_machine
            ids = tuple(cid for cid in ids if isinstance(self._definitions[self._state.cards[cid].definition_id], MachineDefinition) and production_id in {p.production_id for p in production_options_for_machine(self._state, self._definitions[self._state.cards[cid].definition_id])})
            try:
                self._command_bus.dispatch(ConfigureMachines(tuple(ids), production_id, self._definitions))
            except ValueError as error:
                inform(self, "Recipe", str(error))
                return
            self._reset_drawer_state()
            self._refresh_content()
        else:
            super()._apply_production_option(production_id, target_resource_id)

    def _copy_selection(self):
        from production_zero.core.production_templates import copy_templates
        ids = self._ordered_selection()
        if not ids:
            hall = self._units[self._selected_hall_id]
            line = next((line for line in hall.production_lines if line.line_id == self._focused_line_id), None)
            if line is None:raise ValueError("Focus a populated line or select machines first.")
            ids = tuple(hall.slots[i].card_id for i in line.slot_indexes if hall.slots[i].card_id)
        self._configuration_clipboard = copy_templates(self._state, ids)
        self.setToolTip(f"{len(self._configuration_clipboard)} machine templates copied; paste buys new MK1 Common machines.")

    def _paste_selection(self):
        from production_zero.ui.production_templates import paste_dialog
        hall = self._units[self._selected_hall_id]
        line_id = self._focused_line_id
        if line_id is None:raise ValueError("Focus an unlocked target line first.")
        paste_dialog(self, self._configuration_clipboard, self._board_config.board_kind, hall.hall_id, line_id)

    def _sell_selection(self, only=None):
        ids = (only,) if only and only not in self._selected_machines else self._ordered_selection()
        if not ids:
            raise ValueError("Select machines first.")
        details = "\n".join(f"{self._definitions[self._state.cards[cid].definition_id].name} MK{self._state.cards[cid].mk_level} · {self._state.cards[cid].rarity.value} · ${resale_value(self._state.cards[cid], self._definitions[self._state.cards[cid].definition_id]):,.2f}" for cid in ids[:10])
        total = sum(resale_value(self._state.cards[cid], self._definitions[self._state.cards[cid].definition_id]) for cid in ids)
        if confirm(self, "Sell machines", f"{details}\n\n{len(ids)} machine(s) will be removed.\nProceeds: ${total:,.2f}", "YES – SELL"):
            self._command_bus.dispatch(SellMachines(tuple(ids), self._definitions))
            self._selected_machines.difference_update(ids)
            self._close_drawer(refresh=False)
            self.refresh_view()
            if callback := getattr(self, "_card_operation_changed", None):
                callback()

    def _return_selection(self, only=None):
        from production_zero.core.commands import ReturnMachinesToInventory
        ids = (only,) if only and only not in self._selected_machines else self._ordered_selection()
        self._command_bus.dispatch(ReturnMachinesToInventory(tuple(ids)))
        self._selected_machines.difference_update(ids)
        self._close_drawer(refresh=False)
        self.refresh_view()
        if callback := getattr(self, "_card_operation_changed", None):
            callback()

    def _sell_building(self, unit_id=None):
        from production_zero.core.infrastructure import sell_production_building, production_building_resale
        unit = self._units[unit_id or self._selected_hall_id]
        value = production_building_resale(self._state, self._board_config.board_kind, unit.hall_id, include_machines=True)
        ids = tuple(s.card_id for s in unit.slots if s.card_id)
        machines = sum(resale_value(self._state.cards[cid], self._definitions[self._state.cards[cid].definition_id]) for cid in ids)
        if confirm(self, "Sell building", f"{unit.name}\n{len(ids)} included machines will be sold and removed.\nBuilding: ${value:,.2f} · Machines: ${machines:,.2f}\nTotal proceeds: ${value + machines:,.2f}", "YES – SELL"):
            self._command_bus.dispatch(SellProductionBuilding(self._board_config.board_kind, unit.hall_id, self._definitions, True))
            self._selected_hall_id = next(iter(self._units))
            self.refresh_view()

    def _change_site_type(self, definition_id):
        unit = self._units[self._selected_hall_id]
        if any(slot.card_id is not None and self._state.cards[slot.card_id].definition_id != definition_id for slot in unit.slots):
            inform(self, "Site type", "Sell or move incompatible machines before changing the site type.")
            self._refresh_content()
            return
        from production_zero.core.infrastructure_prices import resource_retype_price
        from production_zero.core.commands import RenameHall
        cost=resource_retype_price(self._state,unit,definition_id)
        if cost and not confirm(self,'Change site type',f'{SITE_TYPES[definition_id]}\nType change: ${cost:,.2f}','YES – CHANGE'):return
        self._command_bus.dispatch(RenameHall(unit.hall_id,unit.name,'resources',definition_id,cost,unit.specialization))
        self._refresh_hall_tree()

    def _release_bind_widget(self, widget, slot_index):
        widget._release_board = self
        widget._release_slot_index = slot_index
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        line_id = getattr(watched, "_template_line_id", None)
        if line_id is not None and kind == QEvent.Type.MouseButtonPress:
            self._focused_line_id = line_id
            self.setFocus()
        if line_id is not None and kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.RightButton and getattr(watched, "_release_slot_index", None) is None:
            from production_zero.ui.production_templates import line_menu
            self._focused_line_id = line_id
            def copy_line():
                self._selected_machines.clear();self._update_selection_visuals();self._release_action(self._copy_selection)
            line_menu(self, copy_line, lambda: self._release_action(self._paste_selection), bool(self._configuration_clipboard))
            return True
        index = getattr(watched, "_release_slot_index", None)
        if index is not None:
            if (kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton
                    and event.modifiers() and self._units[self._selected_hall_id].slots[index].card_id is None):
                self._select_slot(index, event.modifiers())
                return True
            if kind == QEvent.Type.Wheel and self._machine_feedback.active:
                return self._machine_feedback.wheel(event)
            if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop) and event.mimeData().hasFormat(MACHINE_MIME):
                try:
                    data = json.loads(bytes(event.mimeData().data(MACHINE_MIME)))
                    ids, uid, targets, plan = self._machine_drop_plan(data, index)
                    if self._machine_feedback.active:
                        position = watched.mapToGlobal(event.position().toPoint())
                        self._machine_feedback.update_position(position)
                        self._machine_hover(position, data)
                    if kind == QEvent.Type.Drop:
                        self._command_bus.dispatch(MoveMachines(ids, self._board_config.board_kind, uid, targets,
                                                               expected_origins=tuple(map(tuple, data['origins']))))
                        self._machine_drag = None
                        self._machine_drag_data = None
                        self._machine_intent_token = None
                        self._machine_feedback.stop()
                        self._selected_machines = set(ids)
                        self.refresh_view()
                    event.acceptProposedAction()
                except (ValueError, KeyError, IndexError, TypeError) as error:
                    event.ignore()
                    if self._machine_feedback.active:
                        self._machine_feedback.highlight(watched, 'invalid', str(error))
                    if kind == QEvent.Type.Drop:
                        self._cancel_machine_drag()
                        inform(self, "Move machines", str(error))
                return True
            if kind == QEvent.Type.DragLeave:
                self._machine_feedback.highlight()
        if kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.MouseButtonRelease) and (watched is getattr(self, "_release_selection_surface", None) or getattr(watched, "_release_rectangle_surface", False)):
            if not hasattr(self, "_release_selection_surface"):
                return super().eventFilter(watched, event)
            surface = self._release_selection_surface
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._rubber_origin = watched.mapTo(surface, event.position().toPoint())
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, surface)
                self._rubber_band.setGeometry(QRect(self._rubber_origin, self._rubber_origin))
                self._rubber_band.show()
                return True
            if kind == QEvent.Type.MouseMove and self._rubber_origin is not None:
                self._rubber_band.setGeometry(QRect(self._rubber_origin, watched.mapTo(surface, event.position().toPoint())).normalized())
                return True
            if kind == QEvent.Type.MouseButtonRelease and self._rubber_origin is not None:
                rect = self._rubber_band.geometry()
                indexes = set()
                for slot_index, widget in self._slot_widgets.items():
                    origin = widget.mapTo(surface, QPoint(0, 0))
                    if rect.intersects(QRect(origin, widget.size())):
                        indexes.add(slot_index)
                self._select_slot_positions(indexes, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
                self._rubber_band.deleteLater()
                self._rubber_origin = None
                self._update_selection_visuals()
                return True
        return super().eventFilter(watched, event)

    def _machine_drag_payload(self, ids):
        from production_zero.core.machine_operations import installed_slot_snapshot
        from uuid import uuid4
        self._release_setup()
        self._machine_intent_token = uuid4().hex
        return dict(session=id(self._state), cards=id(self._state.cards), token=self._machine_drag_token,
                    drag=self._machine_intent_token, ids=tuple(ids), origins=installed_slot_snapshot(self._state, ids))

    def _machine_drop_plan(self, data, index):
        from production_zero.core.machine_operations import plan_slot_permutation
        if (not isinstance(data, dict) or data.get('session') != id(self._state)
                or data.get('cards') != id(self._state.cards) or data.get('token') != self._machine_drag_token
                or not self._machine_intent_token or data.get('drag') != self._machine_intent_token):
            raise ValueError('This drag belongs to an earlier company session. Start again.')
        ids = data.get('ids')
        if not isinstance(ids, (list, tuple)) or not data.get('origins'):
            raise ValueError('Invalid or expired card selection.')
        hall = self._units[self._selected_hall_id]
        ordered = [i for line in hall.production_lines if line.unlocked for i in line.slot_indexes]
        if index not in ordered:
            raise ValueError('Choose an unlocked slot.')
        start = ordered.index(index)
        targets = tuple(ordered[start:start + len(ids)])
        plan = plan_slot_permutation(self._state, tuple(ids), self._board_config.board_kind,
            hall.hall_id, targets, expected_origins=data['origins'])
        return tuple(ids), hall.hall_id, targets, plan

    def _machine_target_at(self, position):
        widget = self.childAt(self.mapFromGlobal(position))
        while widget is not None and widget is not self:
            if getattr(widget, '_release_slot_index', None) is not None:
                return widget
            widget = widget.parentWidget()
        return None

    def _machine_hover(self, position, data=None):
        feedback = self._machine_feedback
        target = self._machine_target_at(position)
        if target is feedback.target:
            return
        data = data or self._machine_drag_data
        if target is None or data is None:
            feedback.highlight()
            return
        try:
            ids, uid, targets, plan = self._machine_drop_plan(data, target._release_slot_index)
            selected = set(ids)
            mode = 'swap' if any(slot.card_id is not None and slot.card_id not in selected for slot, cid in plan[0]) else 'move'
            feedback.highlight(target, mode)
        except (ValueError, KeyError, TypeError) as error:
            feedback.highlight(target, 'invalid', str(error))

    def _cancel_machine_drag(self):
        active = getattr(self, '_machine_drag', None)
        if active is not None:
            QDrag.cancel()
        self._machine_drag = None
        self._machine_drag_data = None
        self._machine_intent_token = None
        if feedback := getattr(self, '_machine_feedback', None):
            feedback.stop()

    def _check_machine_drag_sources(self):
        data = getattr(self, '_machine_drag_data', None)
        if data is None:
            return
        from production_zero.core.machine_operations import installed_slot_snapshot
        if (data['cards'] != id(self._state.cards) or not set(data['ids']) <= self._state.cards.keys()
                or installed_slot_snapshot(self._state, data['ids']) != tuple(map(tuple, data['origins']))):
            self._cancel_machine_drag()

    def _begin_machine_drag(self, widget):
        from production_zero.ui.drag_feedback import drag_pixmap
        cid = widget._card.card_id
        if cid not in self._selected_machines:
            self._select_slot(widget._slot.index, Qt.KeyboardModifier.NoModifier)
        ids = self._ordered_selection()
        self._machine_drag_data = self._machine_drag_payload(ids)
        payload = QMimeData()
        payload.setData(MACHINE_MIME, json.dumps(self._machine_drag_data).encode())
        drag = QDrag(widget)
        self._machine_drag = drag
        drag.setMimeData(payload)
        drag.setPixmap(drag_pixmap(widget, len(ids)))
        grip = getattr(widget, '_drag_grip', widget.rect().center())
        drag.setHotSpot(grip)
        self._machine_feedback.start(widget, grip, len(ids))
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            self._machine_drag = None
            self._machine_drag_data = None
            self._machine_intent_token = None
            self._machine_feedback.stop()
            from shiboken6 import isValid
            if isValid(drag):
                drag.deleteLater()
