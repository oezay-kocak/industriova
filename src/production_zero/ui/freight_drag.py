"""Native vehicle gestures on the existing Freight slot cards."""
import json
from PySide6.QtCore import QObject, QEvent, Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid
from production_zero.core.freight import plan_freight_moves, is_freight_card_busy
from production_zero.core.machine_operations import installed_slot_snapshot
from production_zero.core.commands import MoveFreightVehicles
from production_zero.ui.release_dialogs import inform
from production_zero.ui.drag_feedback import BoardDragFeedback

FREIGHT_MIME = 'application/x-industriova-freight-vehicle'


class FreightSlotInteraction(QObject):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.start = self.origin = self.block_reason = None
        self.dragging = self.changed = False
        self.ids = self.origins = ()
        self.session = None
        self._press_window = None
        self.feedback = BoardDragFeedback(view, self._finish_pointer_drag, self._hover)
        view.installEventFilter(self)

    def bind(self, widget, facility_id, index, card_id=None):
        widget._freight_destination = (facility_id, index)
        widget._freight_vehicle = card_id
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)
        widget.setProperty('selected', card_id in self.view._selected_vehicles if card_id else index in self.view._selected_empty_slots)
        if card_id:
            widget.setCursor(Qt.CursorShape.OpenHandCursor)

    def _cards(self):
        return [w for w in self.view.findChildren(QWidget, 'freightSlotCard') if hasattr(w, '_freight_destination')]

    def update_selection(self):
        for widget in self._cards():
            selected = (widget._freight_vehicle in self.view._selected_vehicles if widget._freight_vehicle
                        else widget._freight_destination[1] in self.view._selected_empty_slots)
            if bool(widget.property('selected')) != selected:
                widget.setProperty('selected', selected)
                widget.update()
            button = widget.findChild(QWidget, 'freightMkUpgrade')
            if button is not None:
                button.update_quote()

    def select_positions(self, indexes, additive=False):
        view = self.view
        unit = view._state.freight.facilities[view._selected_facility_id]
        indexes = set(indexes) & set(unit.unlocked_slot_indexes())
        ids = {unit.slots[i].card_id for i in indexes if unit.slots[i].card_id}
        empty = {i for i in indexes if unit.slots[i].card_id is None}
        view._selected_vehicles = view._selected_vehicles | ids if additive else ids
        view._selected_empty_slots = view._selected_empty_slots | empty if additive else empty

    def select_position(self, index, modifiers=Qt.KeyboardModifier.NoModifier):
        view = self.view
        unit = view._state.freight.facilities[view._selected_facility_id]
        ordered = sorted(unit.unlocked_slot_indexes())
        if index not in ordered:
            return
        cid = unit.slots[index].card_id
        anchor = getattr(view, '_slot_selection_anchor', None)
        if modifiers & Qt.KeyboardModifier.ShiftModifier and anchor in ordered:
            a, b = sorted((ordered.index(anchor), ordered.index(index)))
            self.select_positions(ordered[a:b+1], bool(modifiers & Qt.KeyboardModifier.ControlModifier))
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            selection, key = (view._selected_vehicles, cid) if cid else (view._selected_empty_slots, index)
            if key in selection:
                selection.remove(key)
            else:
                selection.add(key)
        elif not (cid in view._selected_vehicles if cid else index in view._selected_empty_slots):
            self.select_positions((index,))
        view._slot_selection_anchor = index
        self.update_selection()

    def _select(self, card_id, modifiers=Qt.KeyboardModifier.NoModifier):
        view = self.view
        unit = view._state.freight.facilities[view._selected_facility_id]
        index = next(s.index for s in unit.slots if s.card_id == card_id)
        self.select_position(index, modifiers)
        view._vehicle_selection_anchor = card_id
        view._selected_vehicle_id = card_id
        from production_zero.core.production_pause import freight_line_number
        unit = view._state.freight.facilities[view._selected_facility_id]
        view._focused_freight_line = next(freight_line_number(unit,s.index) for s in unit.slots if s.card_id == card_id)
        self.update_selection()

    def _intent(self, cid, target):
        from production_zero.ui.freight_lines import ordered_selection
        ids = self.ids or (ordered_selection(self.view) if cid in self.view._selected_vehicles else (cid,))
        facility_id, index = target._freight_destination
        unit = self.view._state.freight.facilities.get(facility_id)
        if unit is None:
            raise ValueError('This facility no longer exists.')
        ordered = [s.index for s in unit.slots]
        if index not in ordered:
            raise ValueError('Choose an unlocked freight slot.')
        start = ordered.index(index)
        indexes = tuple(ordered[start:start+len(ids)])
        if self.session is not None and self.session is not self.view._state.cards:
            raise ValueError('This drag belongs to an earlier company session.')
        plan = plan_freight_moves(self.view._state, self.view._definitions, ids, facility_id, indexes,
                                 expected_origins=self.origins if self.ids else None)
        return MoveFreightVehicles(tuple(ids), facility_id, indexes, self.view._definitions,
                                  expected_origins=self.origins if self.ids else None), plan

    def _move(self, cid, target):
        command, plan = self._intent(cid, target)
        self.view._command_bus.dispatch(command)

    def _validate(self, cid, widget):
        return self._intent(cid, widget)[1]

    def _targets(self, cid=None):
        # Kept for existing controller callers. Only the hovered target paints.
        if cid is None:
            self.feedback.highlight()

    def _target_at(self, position):
        widget = self.view.childAt(self.view.mapFromGlobal(position))
        while widget is not None and widget is not self.view:
            if hasattr(widget, '_freight_destination'):
                return widget
            widget = widget.parentWidget()
        return None

    def _hover(self, position):
        if not self.dragging:
            return
        if self.origin is None or not isValid(self.origin) or self.session is not self.view._state.cards:
            self._finish_pointer_drag()
            return
        target = self._target_at(position)
        if target is self.feedback.target:
            return
        if target is None:
            self.feedback.highlight()
            return
        try:
            command, plan = self._intent(self.ids[0], target)
            mode = 'swap' if any(slot.card_id is not None and slot.card_id not in self.ids for slot, cid in plan[0]) else 'move'
            self.feedback.highlight(target, mode)
        except (ValueError, KeyError, TypeError) as error:
            self.feedback.highlight(target, 'invalid', str(error))

    def check_sources(self):
        if self.start is not None and (self.session is not self.view._state.cards
                or not set(self.ids) <= self.view._state.cards.keys()
                or installed_slot_snapshot(self.view._state, self.ids) != self.origins):
            self._finish_pointer_drag()

    def _finish_pointer_drag(self):
        self.feedback.stop()
        if self.origin is not None and isValid(self.origin):
            if QWidget.mouseGrabber() is self.origin:
                self.origin.releaseMouse()
            self.origin.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._press_window is not None and isValid(self._press_window) and self._press_window is not self.view:
            self._press_window.removeEventFilter(self)
        self.start = self.origin = self.session = self._press_window = None
        self.dragging = self.changed = False
        self.ids = self.origins = ()
        self.block_reason = None

    def eventFilter(self, widget, event):
        kind = event.type()
        if widget in (self.view, self._press_window):
            if kind in (QEvent.Type.Hide, QEvent.Type.Close, QEvent.Type.WindowDeactivate):
                self._finish_pointer_drag()
            elif kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape and self.start is not None:
                self._finish_pointer_drag()
                return True
            return False
        if not hasattr(widget, '_freight_vehicle'):
            return False
        if (kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton
                and widget._freight_vehicle is None and widget.property('slotState') == 'empty'):
            index = widget._freight_destination[1]
            self.select_position(index, event.modifiers())
            if not event.modifiers():
                self.view._open_drawer(index)
            return True
        if kind == QEvent.Type.Wheel and self.dragging:
            return self.feedback.wheel(event)
        if kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape and self.start is not None:
            self._finish_pointer_drag()
            return True
        if kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.RightButton and widget._freight_vehicle:
            from production_zero.ui.release_freight import vehicle_actions
            vehicle_actions(self.view, widget._freight_vehicle)
            return True
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton and widget._freight_vehicle:
            self._finish_pointer_drag()
            self._select(widget._freight_vehicle, event.modifiers())
            from production_zero.ui.freight_lines import ordered_selection
            self.ids = ordered_selection(self.view) if widget._freight_vehicle in self.view._selected_vehicles else (widget._freight_vehicle,)
            self.origins = installed_slot_snapshot(self.view._state, self.ids)
            self.session = self.view._state.cards
            self.start = event.position().toPoint()
            self.origin = widget
            self._press_window = self.view.window()
            self._press_window.installEventFilter(self)
            widget.setFocus(Qt.FocusReason.MouseFocusReason)
            event.accept()
            return True
        if kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self.start is not None:
            target = self._target_at(event.globalPosition().toPoint()) if self.dragging else None
            problem, changed = self.block_reason, False
            try:
                if target is not None:
                    self._move(self.ids[0], target)
                    changed = True
            except (ValueError, KeyError, TypeError) as error:
                problem = str(error)
            finally:
                self._finish_pointer_drag()
            if changed:
                QTimer.singleShot(0, self.view, self.view.refresh)
            if problem:
                QTimer.singleShot(0, self.view, lambda text=problem: inform(self.view, 'Move freight vehicle', text))
            return True
        if kind == QEvent.Type.MouseMove and self.start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if not self.dragging and (event.position().toPoint()-self.start).manhattanLength() < QApplication.startDragDistance():
                return True
            if any(is_freight_card_busy(self.view._state.freight, cid) for cid in self.ids):
                self.block_reason = 'Wait for every selected delivery to arrive before moving this group.'
                return True
            if not self.dragging:
                self.view._hide_freight_hover()
                widget.grabMouse(Qt.CursorShape.ClosedHandCursor)
                self.dragging = True
                self.feedback.start(widget, self.start, len(self.ids), ghost=True)
            position = event.globalPosition().toPoint()
            self.feedback.update_position(position)
            self._hover(position)
            return True
        # Foreign/stale MIME drags cannot bypass the captured source snapshot.
        if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop) and event.mimeData().hasFormat(FREIGHT_MIME):
            event.ignore()
            return True
        return super().eventFilter(widget, event)
