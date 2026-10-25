"""Transient cargo -> delivery target -> confirm UI over existing Freight commands."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout, QDialog
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.game_ui import GameButton, Accent
from production_zero.core.commands import AssignFreightVehicles
from production_zero.core.freight_routes import target_problem, validate_route
from production_zero.core.machine_operations import installed_slot_snapshot
from production_zero.ui.secondary_views import secondary_action_button


class DeliveryTargetDialog(IndustrialDialog):
    def __init__(self, view):
        super().__init__('Select delivery target', view._resources[view._draft_resource].name,
                         view, accept_text='CONFIRM')
        self.setObjectName('freightDeliveryTargetDialog')
        self.setFixedWidth(min(820, max(540, view.window().width() - 48)))
        self.reject_button.setText('CANCEL')
        self.accept_button.setObjectName('freightConfirmRoute')
        self.accept_button.clicked.disconnect()
        self.accept_button.clicked.connect(view._confirm_assignment)
        self.targets = {}
        grid = QGridLayout()
        columns = 4 if self.width() >= 760 else 2
        for index, (key, name) in enumerate((('market', 'MARKET / SELL'), ('contract', 'CONTRACT'),
                                           ('consortium', 'CONSORTIUM CONTRACT'), ('event', 'EVENT'))):
            button = GameButton(name, variant='primary', accent=Accent.NEUTRAL)
            button.setMinimumSize(150, 48)
            button.setObjectName('freightTarget' + key.title())
            button.clicked.connect(lambda checked=False, key=key: view._choose_assignment_destination(key))
            grid.addWidget(button, index // columns, index % columns)
            self.targets[key] = button
        self.layout().itemAt(0).widget().layout().insertLayout(2, grid)


class FreightAssignmentMixin:
    def _route_board_signature(self):
        unit = self._state.freight.facilities.get(self._selected_facility_id)
        return (id(self._state.cards), self._selected_facility_id,
                tuple((s.index, s.card_id) for s in unit.slots) if unit else None)

    def _show_assignment_content(self):
        from production_zero.ui.widget_lifecycle import hide_detach_delete
        item = self._root.takeAt(1)
        if getattr(self, '_assignment_board', None) is None:
            self._assignment_board = item.widget() if item else None
            self._assignment_board_signature = self._route_board_signature()
            if self._assignment_board is not None:
                self._assignment_board.hide()
        elif item is not None:
            hide_detach_delete(item.widget())
        self._hide_freight_hover()
        self._root.addWidget(self._build_assignment_selection_view(), 1)

    def _restore_assignment_board(self):
        from production_zero.ui.widget_lifecycle import hide_detach_delete
        board = getattr(self, '_assignment_board', None)
        ids = self._route_group
        valid = board is not None and self._assignment_board_signature == self._route_board_signature()
        self._reset_assignment_state()
        if not valid:
            self.refresh()
            return
        item = self._root.takeAt(1)
        if item is not None:
            hide_detach_delete(item.widget())
        self._assignment_board = None
        self._root.addWidget(board, 1)
        board.show()
        for cid in ids:
            if widgets := self._runtime_widgets.get(cid):
                self._update_card_runtime(cid, widgets)
        self._update_kpis()

    def _open_assignment_view(self, card_id, card_ids=None):
        self._slot_interaction._finish_pointer_drag()
        self._reset_drawer_state()
        self._reset_assignment_state()
        self._route_group = tuple(card_ids or (card_id,))
        self._assignment_card_id = self._route_group[0]
        self._route_session = self._state.cards
        self._route_origins = installed_slot_snapshot(self._state, self._route_group)
        routes = [self._state.freight.assignments.get(cid) for cid in self._route_group]
        keys = {(r.resource_id, r.destination_kind) if r else (None, None) for r in routes}
        self._route_mixed = len(keys) != 1
        self._draft_resource, self._assignment_destination = next(iter(keys)) if len(keys) == 1 else (None, None)
        self._show_assignment_content()

    def _reset_assignment_state(self):
        dialog = getattr(self, '_route_dialog', None)
        self._route_dialog = None
        if dialog is not None:
            dialog.reject()
        self._assignment_card_id = None
        self._route_group = ()
        self._route_session = None
        self._route_origins = ()
        self._draft_resource = None
        self._assignment_destination = None
        self._assignment_resource_grid = None
        self._assignment_resource_grid_host = None
        self._route_error = self._route_confirm = None

    def _build_assignment_selection_view(self):
        from production_zero.ui.secondary_views import style_secondary
        from production_zero.ui.theme import Theme
        panel = QFrame()
        panel.setObjectName('freightAssignmentSelectionView')
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        title = QLabel('SELECT A RESOURCE')
        title.setObjectName('sectionLabel')
        title.setStyleSheet(f'color: {Theme.TEXT_ON_LIGHT_PRIMARY}; background: transparent;')
        layout.addWidget(title)
        close = GameButton('CANCEL', variant='primary', accent=Accent.DANGER)
        close.setObjectName('freightAssignmentBackButton')
        close.clicked.connect(self._close_assignment_view)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._build_assignment_resource_picker(), 1)
        return panel

    def _select_assignment_resource(self, resource_id):
        if self._assignment_card_id is None or resource_id not in self._resources:
            return
        if self._route_dialog is not None:
            self._route_dialog.reject()
        self._draft_resource = resource_id
        if self._assignment_destination and target_problem(self._state, resource_id, self._assignment_destination):
            self._assignment_destination = None
        self._populate_assignment_resource_grid()
        dialog = DeliveryTargetDialog(self)
        self._route_dialog = dialog
        self._route_confirm = dialog.accept_button
        self._route_error = dialog.message
        dialog.finished.connect(lambda result: self._target_dialog_finished(dialog, result))
        self._update_assignment_targets()
        dialog.open()

    def _target_dialog_finished(self, dialog, result):
        if self._route_dialog is dialog:
            self._route_dialog = None
            self._route_confirm = self._route_error = None
            if result != QDialog.DialogCode.Accepted:
                self._assignment_destination = None
        dialog.deleteLater()

    def _choose_assignment_destination(self, destination):
        if self._route_dialog is None or destination not in self._route_dialog.targets:
            return
        if target_problem(self._state, self._draft_resource, destination):
            return
        self._assignment_destination = destination
        self._update_assignment_targets()

    def _route_validation_problem(self):
        try:
            if self._route_session is not self._state.cards:
                raise ValueError('The game changed. Reopen route assignment.')
            if self._draft_resource not in self._resources:
                raise ValueError('Choose a cargo resource first.')
            validate_route(self._state, self._route_group, self._draft_resource,
                           self._assignment_destination, definitions=self._definitions,
                           expected_origins=self._route_origins, require_target=True)
        except (ValueError, KeyError) as error:
            return str(error)
        return ''

    def _update_assignment_targets(self):
        dialog = self._route_dialog
        if self._assignment_card_id is None or dialog is None:
            return
        for destination, button in dialog.targets.items():
            problem = target_problem(self._state, self._draft_resource, destination)
            button.setEnabled(not problem)
            button.setToolTip(problem or 'Assign future departures to this target.')
            selected = destination == self._assignment_destination
            button.setSelected(selected)
            button._accent = Accent.BUILD if selected else Accent.NEUTRAL
            button.update()
        problem = self._route_validation_problem()
        self._route_error.setText(self._resources[self._draft_resource].name + '\n' +
            (problem or 'Future departures only. Current cargo and reservations remain unchanged.'))
        self._route_confirm.setEnabled(not problem)

    def _confirm_assignment(self):
        if self._assignment_card_id is None or self._route_dialog is None:
            return
        problem = self._route_validation_problem()
        if problem:
            self._route_error.setText(problem)
            self._route_confirm.setEnabled(False)
            return
        try:
            self._command_bus.dispatch(AssignFreightVehicles(
                self._route_group, self._draft_resource, self._assignment_destination,
                definitions=self._definitions, expected_origins=self._route_origins, require_target=True))
        except (ValueError, KeyError) as error:
            self._route_error.setText(str(error))
            return
        self._route_dialog.accept()
        self._close_assignment_view()
