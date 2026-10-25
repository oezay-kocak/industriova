from __future__ import annotations

import time
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.consortium import (
    ACTIVE,
    APPLICATION,
    AVAILABLE,
    BOARD_MEMBER,
    CHAIRMAN,
    COMPLETED,
    CONSORTIUM_CONTRACT_KINDS,
    CONSORTIUM_DAILY,
    CONSORTIUM_WEEKLY,
    CONTRACT_PRODUCT_SLOTS,
    EXPIRED,
    INVITE_ONLY,
    MEMBER,
    MEMBER_CAPACITY_MILESTONES,
    OPEN,
    Consortium,
    ConsortiumContract,
    ConsortiumService,
    consortium_xp_floor,
    consortium_xp_for_next_level,
)
from production_zero.ui.consortium_materials import ConsortiumWorkspaceFrame, ConsortiumStatFrame
from production_zero.core.state import GameState
from production_zero.core.contracts import contract_value_calculator
from production_zero.core.production_values import ContractProductOption, ProductionValueCalculator
from production_zero.ui.contracts_view import ContractProductPicker
from production_zero.ui.game_ui import Accent
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_tiles import ResourceSelectionTile
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.contract_product import ContractProductButton
from production_zero.ui.pz_controls import RaisedPZButton
from production_zero.ui.material_frame import MaterialFrame
from production_zero.ui.game_ui import MaterialLevel


POLICY_LABELS = {OPEN: "OPEN", APPLICATION: "APPLICATION", INVITE_ONLY: "INVITE ONLY"}
ROLE_LABELS = {CHAIRMAN: "CHAIRMAN", BOARD_MEMBER: "BOARD MEMBER", MEMBER: "MEMBER"}


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        child = item.layout()
        if child is not None:
            _clear(child)


def _label(text: str, object_name: str = "consortiumText") -> QLabel:
    value = QLabel(text)
    value.setObjectName(object_name)
    value.setWordWrap(True)
    return value


class EmbeddedConsortiumDialog(QFrame):
    """One in-app scrim and chassis; never becomes an OS window."""
    closed = Signal()

    def __init__(self, parent: QWidget, object_name: str, width: int) -> None:
        host = parent.window().centralWidget() if hasattr(parent.window(), "centralWidget") else parent
        super().__init__(host)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._sibling_states: list[tuple[QWidget, bool]] = []
        self.setGeometry(host.rect())
        host.installEventFilter(self)
        backdrop = QVBoxLayout(self)
        backdrop.setContentsMargins(24, 24, 24, 24)
        backdrop.addStretch(1)
        self.panel = MaterialFrame()
        self.panel.setObjectName("consortiumModalPanel")
        self.panel.setFixedWidth(width)
        backdrop.addWidget(self.panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        backdrop.addStretch(1)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(24, 22, 24, 22)
        self.panel_layout.setSpacing(12)
        self.hide()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def show(self) -> None:
        if not self._sibling_states:
            self._sibling_states = [(child, child.isEnabled()) for child in self.parentWidget().findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly) if child is not self]
            for child, _ in self._sibling_states:
                child.setEnabled(False)
        self.setGeometry(self.parentWidget().rect())
        super().show()
        self.raise_()
        self.setFocus()

    def accept(self) -> None:
        self.close()

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        for child, enabled in self._sibling_states:
            child.setEnabled(enabled)
        self._sibling_states.clear()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.closed.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class CreateConsortiumDialog(EmbeddedConsortiumDialog):
    created = Signal()

    def __init__(self, service: ConsortiumService, parent: QWidget | None = None) -> None:
        super().__init__(parent, "consortiumCreateDialog", 500)
        self.service = service
        layout = self.panel_layout
        layout.addWidget(_label("CREATE CONSORTIUM", "consortiumDialogTitle"))
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("consortiumNameInput")
        self.name_edit.setPlaceholderText("Consortium name")
        self.policy = QComboBox()
        self.policy.setObjectName("consortiumPolicyInput")
        for value in (OPEN, APPLICATION, INVITE_ONLY):
            self.policy.addItem(POLICY_LABELS[value], value)
        self.minimum_level = QLineEdit("1")
        self.minimum_level.setObjectName("consortiumMinimumLevelInput")
        self.minimum_level.setValidator(QIntValidator(1, 999, self))
        form.addRow("CONSORTIUM NAME", self.name_edit)
        form.addRow("JOIN POLICY", self.policy)
        form.addRow("MINIMUM COMPANY LEVEL", self.minimum_level)
        layout.addLayout(form)
        self.policy_help = _label("Eligible companies may join immediately.", "consortiumPolicyHelp")
        layout.addWidget(self.policy_help)
        self.error = _label("", "consortiumFormError")
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QDialogButtonBox()
        cancel = RaisedPZButton("CANCEL", variant="secondary")
        cancel.setMinimumHeight(30)
        buttons.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        self.create_button = buttons.addButton("CREATE CONSORTIUM", QDialogButtonBox.ButtonRole.AcceptRole)
        self.create_button.setObjectName("deliverContractButton")
        buttons.rejected.connect(self.reject)
        cancel.setObjectName("resourcesButton")
        self.create_button.clicked.connect(self._create)
        self.policy.currentIndexChanged.connect(self._update_help)
        layout.addWidget(buttons)

    def _update_help(self) -> None:
        self.policy_help.setText(
            {
                OPEN: "Eligible companies may join immediately.",
                APPLICATION: "Management approves applicants.",
                INVITE_ONLY: "Membership requires an invitation.",
            }[self.policy.currentData()]
        )

    def _create(self) -> None:
        try:
            self.service.create(self.name_edit.text(), self.policy.currentData(), int(self.minimum_level.text() or "0"))
        except (ValueError, PermissionError) as error:
            self.error.setText(str(error).upper())
            self.error.show()
            return
        self.created.emit()
        self.accept()


class InviteCompanyDialog(EmbeddedConsortiumDialog):
    invited = Signal()

    def __init__(self, service: ConsortiumService, consortium: Consortium, parent: QWidget | None = None) -> None:
        super().__init__(parent, "consortiumInviteDialog", 480)
        self.service = service
        self.consortium = consortium
        layout = self.panel_layout
        layout.addWidget(_label("INVITE COMPANY", "consortiumDialogTitle"))
        layout.addWidget(_label("FIND COMPANY BY NAME OR STABLE ID", "consortiumSectionLabel"))
        search = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("supplySearch")
        self.query.setPlaceholderText("FIND COMPANY")
        self.query.textChanged.connect(self._clear_result)
        self.query.returnPressed.connect(self._lookup)
        search.addWidget(self.query, 1)
        find = RaisedPZButton("FIND", variant="secondary")
        find.setObjectName("resourcesButton")
        find.clicked.connect(self._lookup)
        search.addWidget(find)
        layout.addLayout(search)
        self.resolved = _label("ENTER A COMPANY NAME OR ID", "consortiumInviteResolved")
        layout.addWidget(self.resolved)
        self.eligibility = _label("", "consortiumInviteEligibility")
        layout.addWidget(self.eligibility)
        self.error = _label("", "consortiumFormError")
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QDialogButtonBox()
        cancel = RaisedPZButton("CANCEL", variant="secondary")
        cancel.setMinimumHeight(30)
        buttons.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        self.invite_button = buttons.addButton("SEND INVITATION", QDialogButtonBox.ButtonRole.AcceptRole)
        self.invite_button.setObjectName("deliverContractButton")
        self.invite_button.setEnabled(False)
        self.invite_button.clicked.connect(self._invite)
        buttons.rejected.connect(self.reject)
        cancel.setObjectName("resourcesButton")
        layout.addWidget(buttons)

    def _clear_result(self) -> None:
        self.invite_button.setEnabled(False)
        self.resolved.setText("ENTER A COMPANY NAME OR ID")
        self.eligibility.setText("")

    def _lookup(self) -> None:
        identity = self.service.resolve_company(self.query.text())
        if identity is None:
            self.resolved.setText("COMPANY NOT FOUND IN LOCAL DIRECTORY")
            self.eligibility.setText("CHECK THE NAME OR STABLE ID")
            return
        self.resolved.setText(f"{identity.company_name.upper()}  ·  LEVEL {identity.company_level}  ·  {identity.company_id}")
        eligible, reason = self.service.invitation_eligibility(self.consortium.consortium_id, identity)
        self.eligibility.setText(reason)
        self.invite_button.setEnabled(eligible)

    def _invite(self) -> None:
        try:
            self.service.invite_resolved(self.consortium.consortium_id, self.service.current_company_id, self.query.text())
        except (ValueError, PermissionError) as error:
            self.error.setText(str(error).upper())
            self.error.show()
            return
        self.invited.emit()
        self.accept()


class ConfirmConsortiumDialog(EmbeddedConsortiumDialog):
    def __init__(self, title: str, message: str, confirm_label: str, action, parent: QWidget) -> None:
        super().__init__(parent, "consortiumConfirmDialog", 600)
        self.panel.setStyleSheet("QFrame#consortiumModalPanel { background: transparent; border: 0; } QLabel#consortiumConfirmMessage { font-family: 'Segoe UI'; font-size: 14px; color: #171c1c; } QLabel#consortiumDialogTitle { font-family: 'Segoe UI'; font-size: 22px; font-weight: 900; color: #171c1c; }")
        self.panel_layout.addWidget(_label(title, "consortiumDialogTitle"))
        body = _label(message, "consortiumConfirmMessage")
        body.setMinimumHeight(140)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.panel_layout.addWidget(body)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = RaisedPZButton("CANCEL", variant="secondary")
        cancel.setObjectName("resourcesButton")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        confirm = RaisedPZButton(confirm_label, variant="destructive")
        confirm.setMinimumSize(120, 34)
        cancel.setMinimumSize(100, 34)
        confirm.setObjectName("freightRemoveButton")
        confirm.clicked.connect(lambda: (action(), self.accept()))
        buttons.addWidget(confirm)
        self.panel_layout.addLayout(buttons)


class ConsortiumView(QWidget):
    profile_requested = Signal(object, object)
    freight_requested = Signal()

    def __init__(self, state: GameState, definitions, resource_definitions, on_changed=None) -> None:
        super().__init__()
        self.setObjectName("consortiumView")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._state = state
        self._definitions = definitions
        self._resource_definitions = resource_definitions
        self._service = ConsortiumService(state, definitions)
        self._on_changed = on_changed
        self._workspace_signature = None
        self._workspace_rebuild_count = 0
        self._render_signature = None
        self._content_rebuild_count = 0
        self._selected_contract_kind = CONSORTIUM_DAILY
        self._rendered_contract_kind = CONSORTIUM_DAILY
        self._selected_member_id: str | None = None
        self._directory_policy: str | None = None
        self._draft_products: dict[str, list[str | None]] = {kind: [None] * CONTRACT_PRODUCT_SLOTS[kind] for kind in CONSORTIUM_CONTRACT_KINDS}
        self._product_picker: ContractProductPicker | None = None
        self._roster_scroll_position = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.setObjectName("consortiumStack")
        root.addWidget(self.stack)
        self.landing = self._build_landing()
        self.member_workspace = self._build_member_workspace()
        self.stack.addWidget(self.landing)
        self.stack.addWidget(self.member_workspace)
        self.refresh()

    def show_frontscreen(self):
        self._close_product_picker()
        for dialog in self.findChildren(EmbeddedConsortiumDialog):
            dialog.close()
        self.member_tabs.setCurrentIndex(0)
        self._selected_member_id = None
        if any(any(value is not None for value in values) for values in self._draft_products.values()):
            self._draft_products = {kind: [None] * CONTRACT_PRODUCT_SLOTS[kind] for kind in CONSORTIUM_CONTRACT_KINDS}
            self._render_signature = None

    def _build_landing(self) -> QWidget:
        page = QWidget()
        page.setObjectName("consortiumLanding")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 16)
        header = MainTabHeader(
            object_name="consortiumMainHeader", title="CONSORTIUM", subtitle="BUILD TOGETHER. GROW TOGETHER.",
            title_object_name="consortiumHeroTitle", subtitle_object_name="consortiumHeroSubtitle", accent=Accent.SUCCESS,
        )
        self.find_button = QPushButton("FIND CONSORTIUM")
        self.find_button.setObjectName("resourcesButton")
        self.find_button.clicked.connect(lambda: self.directory_search.setFocus())
        header.add_status_module(self.find_button)
        self.create_button = QPushButton("CREATE CONSORTIUM")
        self.create_button.setObjectName("deliverContractButton")
        self.create_button.clicked.connect(self._show_create)
        header.add_status_module(self.create_button)
        layout.addWidget(header)

        controls = QHBoxLayout()
        self.directory_search = QLineEdit()
        self.directory_search.setObjectName("supplySearch")
        self.directory_search.setPlaceholderText("SEARCH CONSORTIUM")
        self.directory_filters: dict[str | None, QPushButton] = {}
        for policy in (None, OPEN, APPLICATION, INVITE_ONLY):
            chip = QPushButton("ALL" if policy is None else POLICY_LABELS[policy])
            chip.setObjectName("inventoryFilterChip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda checked=False, value=policy: self._set_directory_policy(value))
            self.directory_filters[policy] = chip
        self.directory_search.textChanged.connect(self._refresh_directory)
        controls.addWidget(self.directory_search, 1)
        for chip in self.directory_filters.values():
            controls.addWidget(chip)
        self.directory_filters[None].setChecked(True)
        self.directory_filters[None].setProperty("active", True)
        layout.addLayout(controls)
        self.directory_scroll = QScrollArea()
        self.directory_scroll.setObjectName("consortiumDirectoryScroll")
        self.directory_scroll.setWidgetResizable(True)
        self.directory_host = QWidget()
        self.directory_host.setObjectName("consortiumDirectoryHost")
        self.directory_layout = QVBoxLayout(self.directory_host)
        self.directory_layout.setContentsMargins(16, 16, 16, 16)
        self.directory_layout.setSpacing(8)
        self.directory_scroll.setWidget(self.directory_host)
        layout.addWidget(self.directory_scroll, 1)
        return page

    def _set_directory_policy(self, policy: str | None) -> None:
        self._directory_policy = policy
        for value, chip in self.directory_filters.items():
            chip.setChecked(value == policy)
            chip.setProperty("active", value == policy)
            chip.style().unpolish(chip)
            chip.style().polish(chip)
        self._refresh_directory()

    def _build_member_workspace(self) -> QWidget:
        page = QWidget()
        page.setObjectName("consortiumMemberWorkspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 12, 18, 12)
        self._member_workspace_layout = layout
        self.identity_frame = MainTabHeader(
            object_name="consortiumIdentityHeader", title="", subtitle="",
            title_object_name="consortiumIdentityName", subtitle_object_name="consortiumIdentityMeta", accent=Accent.SUCCESS,
        )
        self.identity_name = self.identity_frame.title_label
        self.identity_meta = self.identity_frame.subtitle_label
        progress_module = ConsortiumWorkspaceFrame(level=MaterialLevel.INSET)
        progress_module.setObjectName("consortiumHeaderProgressModule")
        progress_module.setFixedWidth(390)
        module_layout = QVBoxLayout(progress_module)
        module_layout.setContentsMargins(12, 7, 12, 7)
        module_layout.setSpacing(3)
        module_heading = QHBoxLayout()
        self.identity_level = _label("", "consortiumIdentityLevel")
        module_heading.addWidget(self.identity_level)
        self.identity_next = _label("", "consortiumNextMilestone")
        module_heading.addWidget(self.identity_next, 1, alignment=Qt.AlignmentFlag.AlignRight)
        module_layout.addLayout(module_heading)
        self.identity_xp = QProgressBar()
        self.identity_xp.setObjectName("consortiumXpProgress")
        module_layout.addWidget(self.identity_xp)
        self.identity_frame.add_status_module(progress_module)
        layout.addWidget(self.identity_frame)
        self.member_tabs = QTabWidget()
        self.member_tabs.setObjectName("consortiumMemberTabs")
        self.overview_page, self.overview_layout = self._scroll_page("consortiumOverview")
        self.contracts_page, self.contracts_layout = self._scroll_page("consortiumContracts")
        self.members_page, self.members_layout = self._scroll_page("consortiumMembers")
        self.progression_page, self.progression_layout = self._scroll_page("consortiumProgression")
        self.member_tabs.addTab(self.overview_page, "OVERVIEW")
        self.member_tabs.addTab(self.contracts_page, "CONTRACTS")
        self.member_tabs.addTab(self.members_page, "MEMBERS")
        self.member_tabs.addTab(self.progression_page, "PROGRESSION")
        layout.addWidget(self.member_tabs, 1)
        return page

    @staticmethod
    def _scroll_page(object_name: str) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setObjectName(object_name)
        scroll.setWidgetResizable(True)
        host = ConsortiumWorkspaceFrame()
        host.setObjectName("consortiumPageChassis")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(14, 14, 14, 14)
        if object_name == "consortiumProgression":
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(host)
        scroll.viewport().setObjectName("consortiumWorkspaceViewport")
        # setWidget enables autofill. Let the concrete parent show around the
        # custom rounded chassis instead of the global QWidget dark background.
        scroll.viewport().setAutoFillBackground(False)
        host.setAutoFillBackground(False)
        return scroll, layout

    def refresh(self) -> None:
        host = self.window().centralWidget() if hasattr(self.window(), "centralWidget") else self
        if self._product_picker is not None or any(dialog.isVisible() for dialog in host.findChildren(EmbeddedConsortiumDialog)):
            return
        membership = self._state.consortium.membership()
        if membership is not None:
            self._service.expire_contracts(membership[0].consortium_id)
            self._service._ensure_offers(membership[0], rotate_completed=False)
        signature = self._content_signature()
        if signature == self._render_signature:
            self._update_contract_timer()
            return
        self._render_signature = signature
        self._content_rebuild_count += 1
        active_tab = self.member_tabs.currentIndex()
        scroll_positions = tuple(
            page.verticalScrollBar().value()
            for page in (self.overview_page, self.contracts_page, self.members_page, self.progression_page)
        )
        target = 0 if membership is None else 1
        signature = (target, membership[0].consortium_id if membership else None)
        if signature != self._workspace_signature:
            if self._workspace_signature is not None and signature[1] != self._workspace_signature[1]:
                self._draft_products = {kind: [None] * CONTRACT_PRODUCT_SLOTS[kind] for kind in CONSORTIUM_CONTRACT_KINDS}
            self._workspace_signature = signature
            self._workspace_rebuild_count += 1
            self.stack.setCurrentIndex(target)
        if membership is None:
            self._refresh_directory()
            return
        consortium, member = membership
        self._refresh_identity(consortium)
        self._refresh_overview(consortium)
        self._refresh_contracts(consortium, member.role)
        self._refresh_members(consortium, member.role)
        self._refresh_progression(consortium)
        self.member_tabs.setCurrentIndex(active_tab)
        for page, value in zip(
            (self.overview_page, self.contracts_page, self.members_page, self.progression_page),
            scroll_positions,
        ):
            page.verticalScrollBar().setValue(value)

    def _content_signature(self) -> tuple:
        network = self._state.consortium
        directory = tuple(sorted((item.consortium_id, item.name, item.level, item.member_capacity, len(item.members), item.join_policy, item.minimum_company_level, tuple(item.applications), tuple(item.invitations)) for item in network.consortiums.values()))
        membership = network.membership()
        if membership is None:
            return (network.current_company_id, self._state.company.level, directory)
        consortium, member = membership
        members = tuple(sorted((value.company_id, value.company_name, value.company_level, value.role, value.lifetime_contribution) for value in consortium.members.values()))
        contracts = tuple((kind, contract.contract_id, contract.status, tuple(contract.requirements.items()), tuple(sorted(contract.delivered.items())), tuple(contract.eligible_member_ids), contract.member_count_at_start, tuple(sorted(contract.contributions.get(network.current_company_id, {}).items()))) for kind, contract in sorted(consortium.contracts.items()))
        activity = tuple((event.activity_id, event.label) for event in consortium.activity[-5:])
        return (network.current_company_id, directory, member.role, members, contracts, consortium.consortium_xp, activity)

    def _update_contract_timer(self) -> None:
        for label, contract in getattr(self, "_contract_timers", ()):
            remaining = max(0.0, contract.expires_at - time.time())
            value = f"{int(remaining // 86400)}D {int((remaining % 86400) // 3600)}H" if remaining >= 86400 else f"{int(remaining // 3600)}H {int((remaining % 3600) // 60)}M"
            if label.text() != value:
                label.setText(value)

    def _refresh_directory(self) -> None:
        if not hasattr(self, "directory_layout"):
            return
        scroll = self.directory_scroll.verticalScrollBar().value()
        _clear(self.directory_layout)
        query = self.directory_search.text().strip().casefold()
        policy = self._directory_policy
        matches = [
            consortium
            for consortium in self._state.consortium.consortiums.values()
            if (not query or query in consortium.name.casefold()) and (policy is None or consortium.join_policy == policy)
        ]
        for consortium in sorted(matches, key=lambda item: (-item.level, item.name.casefold())):
            row = QFrame()
            row.setObjectName("consortiumDirectoryRow")
            line = QHBoxLayout(row)
            name = _label(consortium.name.upper(), "consortiumDirectoryName")
            line.addWidget(name, 3)
            for value in (f"LV. {consortium.level}", f"{len(consortium.members)} / {consortium.member_capacity}", POLICY_LABELS[consortium.join_policy], f"MIN LV. {consortium.minimum_company_level}"):
                meta = _label(value, "consortiumDirectoryMeta")
                meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
                line.addWidget(meta, 1)
            action = RaisedPZButton("JOIN" if consortium.join_policy == OPEN else "APPLY" if consortium.join_policy == APPLICATION else "INVITE ONLY", variant="primary")
            action.setObjectName("deliverContractButton")
            reason = ""
            if self._state.company.level < consortium.minimum_company_level:
                reason = "LEVEL TOO LOW"
            elif len(consortium.members) >= consortium.member_capacity:
                reason = "CONSORTIUM FULL"
            elif consortium.join_policy == INVITE_ONLY and self._service.current_company_id not in consortium.invitations:
                reason = "INVITE ONLY"
            if reason:
                action.setText(reason)
                action.setEnabled(False)
            elif self._service.current_company_id in consortium.applications:
                action.setText("APPLICATION PENDING")
                action.setEnabled(False)
            else:
                action.clicked.connect(lambda checked=False, item=consortium: self._directory_action(item))
            line.addWidget(action)
            action.setFixedWidth(145)
            self.directory_layout.addWidget(row)
        if not matches:
            action = RaisedPZButton("CREATE CONSORTIUM", variant="primary")
            action.setObjectName("deliverContractButton")
            action.clicked.connect(self._show_create)
            empty = EmptyStatePanel("NO CONSORTIUMS FOUND", "Adjust your filters, search again, or establish a new Consortium.", action=action, object_name="consortiumDirectoryEmpty", show_icon=False)
            empty.findChild(QLabel, "emptyStateTitle").setMinimumWidth(440)
            empty.findChild(QLabel, "emptyStateMessage").setMinimumWidth(440)
            self.directory_layout.addWidget(empty)
        self.directory_layout.addStretch(1)
        self.directory_scroll.verticalScrollBar().setValue(scroll)

    def _directory_action(self, consortium: Consortium) -> None:
        if consortium.join_policy == APPLICATION:
            self._service.apply(consortium.consortium_id)
        else:
            self._service.join(consortium.consortium_id)
        self._changed()

    def _show_create(self) -> None:
        dialog = CreateConsortiumDialog(self._service, self)
        dialog.created.connect(self._changed)
        dialog.closed.connect(self.refresh)
        dialog.show()

    def _refresh_identity(self, consortium: Consortium) -> None:
        self.identity_name.setText(consortium.name.upper())
        self.identity_level.setText(f"CONSORTIUM LV. {consortium.level}")
        self.identity_meta.setText(
            f"CHAIRMAN  {consortium.chairman().company_name.upper()}    ·    "
            f"MEMBERS  {len(consortium.members)} / {consortium.member_capacity}    ·    {POLICY_LABELS[consortium.join_policy]}"
        )
        floor = consortium_xp_floor(consortium.level)
        required = consortium_xp_for_next_level(consortium.level)
        current = max(0.0, consortium.consortium_xp - floor)
        self.identity_xp.setRange(0, max(1, int(required)))
        self.identity_xp.setValue(int(current))
        self.identity_xp.setFormat(f"CONSORTIUM XP  {current:,.0f} / {required:,.0f}")
        future = next(((level, capacity) for level, capacity in MEMBER_CAPACITY_MILESTONES if level > consortium.level), None)
        self.identity_next.setText(
            "50 MEMBER MAXIMUM CAPACITY" if future is None else f"NEXT CAPACITY  {future[1]} MEMBERS · LEVEL {future[0]}"
        )

    def _refresh_overview(self, consortium: Consortium) -> None:
        _clear(self.overview_layout)
        grid = QGridLayout()
        grid.addWidget(self._status_card(consortium), 0, 0)
        grid.addWidget(self._activity_card(consortium), 0, 1)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.overview_layout.addLayout(grid)

    def _status_card(self, consortium: Consortium) -> QFrame:
        frame = ConsortiumWorkspaceFrame(level=MaterialLevel.INSET)
        frame.setObjectName("consortiumOperationCard")
        frame.setProperty("operation", "status")
        frame.setMinimumHeight(310)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(_label("CONSORTIUM STATUS", "consortiumSectionTitle"))
        stats = QGridLayout()
        stats.setSpacing(10)
        values = (
            ("CONSORTIUM LEVEL", str(consortium.level)),
            ("MEMBER CAPACITY", f"{len(consortium.members)} / {consortium.member_capacity}"),
            ("NEXT CAPACITY", self.identity_next.text().removeprefix("NEXT CAPACITY ")),
            ("JOIN POLICY", POLICY_LABELS[consortium.join_policy]),
        )
        for index, (title, value) in enumerate(values):
            module = ConsortiumStatFrame()
            module.setObjectName("consortiumStatModule")
            content = QVBoxLayout(module)
            content.setContentsMargins(14, 10, 14, 10)
            content.addWidget(_label(title, "consortiumMetricLabel"))
            content.addWidget(_label(value, "consortiumBigStat" if index < 2 else "consortiumMetricValue"))
            stats.addWidget(module, index // 2, index % 2)
        layout.addLayout(stats)
        layout.addWidget(_label("CHAIRMAN", "consortiumMetricLabel"))
        chairman = QPushButton(consortium.chairman().company_name.upper())
        chairman.setObjectName("consortiumProfileLink")
        chairman.clicked.connect(lambda: self.profile_requested.emit(consortium, consortium.chairman()))
        layout.addWidget(chairman)
        progress = QProgressBar()
        progress.setObjectName("consortiumXpProgress")
        floor = consortium_xp_floor(consortium.level)
        required = consortium_xp_for_next_level(consortium.level)
        progress.setRange(0, max(1, int(required)))
        progress.setValue(int(max(0.0, consortium.consortium_xp - floor)))
        progress.setFormat(f"XP  {max(0.0, consortium.consortium_xp - floor):,.0f} / {required:,.0f}")
        layout.addWidget(progress)
        layout.addStretch(1)
        return frame

    def _activity_card(self, consortium: Consortium) -> QFrame:
        frame = ConsortiumWorkspaceFrame(level=MaterialLevel.INSET)
        frame.setObjectName("consortiumOperationCard")
        frame.setProperty("operation", "activity")
        frame.setMinimumHeight(310)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(_label("RECENT ACTIVITY", "consortiumSectionTitle"))
        for activity in reversed(consortium.activity[-5:]):
            entry = QFrame()
            entry.setObjectName("consortiumActivityEntry")
            line = QHBoxLayout(entry)
            line.setContentsMargins(9, 3, 9, 3)
            line.addWidget(_label(activity.label, "consortiumActivityLine"))
            layout.addWidget(entry)
        if not consortium.activity:
            layout.addWidget(_label("NO RECENT ACTIVITY", "consortiumMutedText"))
        layout.addStretch(1)
        return frame

    def _open_contract(self, kind: str) -> None:
        self._selected_contract_kind = kind
        self.member_tabs.setCurrentWidget(self.contracts_page)
        membership = self._state.consortium.membership()
        if membership:
            self._refresh_contracts(membership[0], membership[1].role)

    def _refresh_contracts(self, consortium: Consortium, role: str) -> None:
        _clear(self.contracts_layout)
        self._rendered_contract_kind = self._selected_contract_kind
        self._contract_timers = []
        for kind in CONSORTIUM_CONTRACT_KINDS:
            contract = consortium.contracts[kind]
            section = ConsortiumWorkspaceFrame(level=MaterialLevel.INSET)
            section.setObjectName("consortiumContractSection")
            section.setProperty("kind", kind)
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(12, 10, 12, 10)
            section_layout.setSpacing(5)
            header_frame = QFrame()
            header_frame.setObjectName("consortiumLayoutHost")
            header_frame.setFixedHeight(34)
            header = QHBoxLayout(header_frame)
            header.setContentsMargins(0, 0, 0, 0)
            header.addWidget(_label(f"{kind.upper()} CONTRACT", "consortiumSectionTitle"), 1)
            header.addWidget(_label(contract.status.upper(), "consortiumContractState"))
            if contract.status == AVAILABLE and role in (CHAIRMAN, BOARD_MEMBER):
                start = RaisedPZButton("START CONTRACT", variant="primary")
                start.setObjectName("deliverContractButton")
                start.setEnabled(all(self._draft_products[kind]))
                start.clicked.connect(lambda checked=False, k=kind, cid=contract.contract_id: self._start_contract(consortium, k, cid))
                header.addWidget(start)
            elif contract.status == AVAILABLE:
                header.addWidget(_label("WAITING FOR MANAGEMENT", "consortiumMutedText"))
            elif contract.status == ACTIVE:
                contribute = RaisedPZButton("DELIVER VIA FREIGHT", variant="primary")
                contribute.setObjectName("deliverViaFreightButton")
                contribute.setToolTip("Choose vehicles, cargo and CONSORTIUM CONTRACT in Freight. Confirm the route. Only completed deliveries count.")
                contribute.clicked.connect(self.freight_requested.emit)
                header.addWidget(contribute)
            elif contract.status in (COMPLETED, EXPIRED) and role in (CHAIRMAN, BOARD_MEMBER):
                renew = RaisedPZButton("NEW CONTRACT", variant="primary")
                renew.setObjectName("renewConsortiumContractButton")
                renew.clicked.connect(lambda checked=False,k=kind:self._renew_contract(consortium,k))
                header.addWidget(renew)
            section_layout.addWidget(header_frame)
            if contract.status == AVAILABLE and not contract.capacity_rates:
                section_layout.addWidget(_label("SUITABLE FREIGHT CAPACITY REQUIRED · Install vehicles and provide a powered production chain.", "consortiumFreightRequired"))
            if contract.status == AVAILABLE:
                section_layout.addWidget(self._product_selection(consortium, contract, role))
            else:
                requirement_housing = QFrame()
                requirement_housing.setObjectName("consortiumActiveRequirements")
                products = QHBoxLayout(requirement_housing)
                products.setContentsMargins(0, 0, 0, 0)
                products.setSpacing(8)
                for rid, required in contract.requirements.items():
                    product = QFrame()
                    product.setObjectName("consortiumRequirementRow")
                    column = QVBoxLayout(product)
                    column.setContentsMargins(0, 0, 0, 0)
                    column.setSpacing(3)
                    definition = self._resource_definitions.get(rid)
                    delivered = contract.delivered.get(rid, 0.0)
                    module = ContractProductButton(compact=False)
                    module.set_product(rid, definition.name if definition else rid, required, delivered=delivered)
                    module.setEnabled(False)
                    column.addWidget(module)
                    progress = QProgressBar()
                    progress.setObjectName("consortiumRequirementProgress")
                    progress.setRange(0, 1000)
                    progress.setValue(round(1000*min(1.,max(0.,delivered/required))) if required>0 else 0)
                    progress.setTextVisible(False)
                    column.addWidget(progress)
                    own = contract.contributions.get(self._service.current_company_id, {}).get(rid, 0.0)
                    column.addWidget(_label(f"YOUR CONTRIBUTION  {own:,.0f} · REMAINING  {max(0, required-delivered):,.0f}", "consortiumMutedText"))
                    products.addWidget(product, 1)
                section_layout.addWidget(requirement_housing)
            section_layout.addWidget(self._contract_metadata(contract, consortium.consortium_id))
            if contract.status in (ACTIVE, COMPLETED):
                section_layout.addWidget(self._eligibility_panel(consortium, contract))
            self.contracts_layout.addWidget(section, 1)

    def _select_contract(self, kind: str) -> None:
        self._selected_contract_kind = kind
        membership = self._state.consortium.membership()
        if membership:
            self._refresh_contracts(membership[0], membership[1].role)

    def _start_contract(self, consortium: Consortium, kind: str, expected_contract_id=None) -> None:
        try:
            self._service.start_contract(consortium.consortium_id, self._service.current_company_id, kind, tuple(self._draft_products[kind]), expected_contract_id=expected_contract_id or consortium.contracts[kind].contract_id)
        except (ValueError, PermissionError):
            self.setToolTip("Contract offer or permissions changed. Review the current preview.")
            self.refresh()
            return
        self._draft_products[kind] = [None] * CONTRACT_PRODUCT_SLOTS[kind]
        self._changed()

    def _renew_contract(self, consortium, kind):
        try:
            self._service.renew_contract_offer(consortium.consortium_id,self._service.current_company_id,kind)
        except (ValueError,PermissionError):
            self.refresh()
            return
        self._draft_products[kind]=[None]*CONTRACT_PRODUCT_SLOTS[kind]
        self._changed()

    def _product_selection(self, consortium: Consortium, contract: ConsortiumContract, role: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("consortiumProductSelection")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(panel)
        slots = CONTRACT_PRODUCT_SLOTS[contract.kind]
        candidates = self._service.contract_candidates(consortium.consortium_id, contract.kind)
        selected = self._draft_products[contract.kind]
        selected[:] = [rid if rid in candidates else None for rid in selected[:slots]]
        layout.addWidget(_label(f"SELECT REQUIRED PRODUCTS  {sum(rid is not None for rid in selected)} / {slots}", "consortiumSectionTitle"))
        if not candidates:
            layout.addWidget(_label("NO ELIGIBLE PRODUCTS · Set up an unlocked, powered production chain.", "consortiumEligibilityReason"))
            return panel
        row = QHBoxLayout()
        row.setSpacing(8)
        for index, resource_id in enumerate(selected):
            choice = QFrame()
            choice.setObjectName("contractRequirementChoice")
            cell = QHBoxLayout(choice)
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(4)
            name = self._resource_definitions[resource_id].name.upper() if resource_id in self._resource_definitions else f"PRODUCT {index + 1}"
            slot = ContractProductButton(f"PRODUCT {index + 1}", compact=False)
            slot.setObjectName("contractProductSlot")
            slot.setProperty("selectorIndex", index)
            slot.setProperty("selected", resource_id is not None)
            slot.setEnabled(role in (CHAIRMAN, BOARD_MEMBER))
            slot.clicked.connect(lambda checked=False, value=index, kind=contract.kind: self._open_product_picker(value, kind))
            cell.addWidget(slot, 1)
            required = 0.0
            if resource_id is not None:
                if contract.balance_version and all(selected):
                    required = self._service.preview_contract(consortium.consortium_id, contract.kind, tuple(selected))[resource_id]
                elif not contract.balance_version:
                    value = contract_value_calculator(self._state,self._definitions).values()[resource_id]
                    from production_zero.core.production_values import contract_required_amount
                    from production_zero.core.consortium import MEMBER_SCALE_EXPONENT
                    per_product = contract.scaling_inputs["production_value_budget"] / slots
                    required = max(1.0, round(contract_required_amount(per_product, value.value_per_unit) * len(consortium.members) ** MEMBER_SCALE_EXPONENT))
            slot.set_product(resource_id, name, required)
            row.addWidget(choice, 1)
        layout.addLayout(row)
        if all(selected):
            preview = self._service.preview_contract(consortium.consortium_id, contract.kind, tuple(selected))
            reward, xp = self._service.preview_contract_rewards(consortium.consortium_id, contract.kind)
            summary = _label(f"READY TO START  ·  +{xp:,.0f} CONSORTIUM XP  ·  ${reward.cash:,.0f} / {reward.company_xp:,.0f} XP SHARED BY GOODS VALUE; RESEARCH FROZEN", "consortiumProductPreviewReward")
            minimum = self._service.rp_minimum_shares(consortium,contract,preview).get(self._service.current_company_id,0.) if contract.balance_version else 0.
            summary.setToolTip(f"Maximum pool: ${reward.cash:,.2f}, {reward.company_xp:,.2f} XP. Weekly reward: {reward.research_points} RP for a meaningful contributor. Your minimum: {minimum:.2%} of base goods value, fixed at START. Quantities use reachable production because direct Global Storage contributions are available. Limited Freight can take longer.")
            layout.addWidget(summary)
        return panel

    def _open_product_picker(self, slot_index: int, kind: str | None = None) -> None:
        if kind is not None:
            self._selected_contract_kind = kind
        membership = self._state.consortium.membership()
        if membership is None or membership[1].role not in (CHAIRMAN, BOARD_MEMBER):
            return
        consortium = membership[0]
        kind = self._selected_contract_kind
        candidates = self._service.contract_candidates(consortium.consortium_id, kind)
        values = contract_value_calculator(self._state,self._definitions).values()
        products = tuple(ContractProductOption(rid, values[rid].production_id, values[rid].name, values[rid].value_per_unit, 0.0) for rid in candidates)
        selected = self._draft_products[kind]
        unavailable = {rid for index, rid in enumerate(selected) if index != slot_index and rid is not None}
        current = selected[slot_index]
        picker = ContractProductPicker(products, self._resource_definitions, unavailable, values[current].name if current else "", self.member_workspace)
        picker.setProperty("selectorIndex", slot_index)
        picker.product_selected.connect(lambda rid, index=slot_index: self._choose_product(index, rid))
        picker.back_requested.connect(self._close_product_picker)
        self._product_picker = picker
        self.member_tabs.hide()
        self._member_workspace_layout.addWidget(picker, 1)
        picker.show()

    def _choose_product(self, slot_index: int, resource_id: str) -> None:
        kind = self._selected_contract_kind
        selected = self._draft_products[kind]
        if resource_id in (rid for index, rid in enumerate(selected) if index != slot_index):
            return
        selected[slot_index] = resource_id
        scroll_position = self.contracts_page.verticalScrollBar().value()
        self._close_product_picker()
        membership = self._state.consortium.membership()
        if membership:
            self._refresh_contracts(membership[0], membership[1].role)
            self.contracts_page.verticalScrollBar().setValue(scroll_position)

    def _close_product_picker(self) -> None:
        if self._product_picker is not None:
            self._member_workspace_layout.removeWidget(self._product_picker)
            self._product_picker.hide()
            self._product_picker.deleteLater()
            self._product_picker = None
        self.member_tabs.show()

    def _requirement_row(self, contract: ConsortiumContract, resource_id: str, required: float) -> QFrame:
        definition = self._resource_definitions.get(resource_id)
        delivered = contract.delivered.get(resource_id, 0.0)
        own = contract.contributions.get(self._service.current_company_id, {}).get(resource_id, 0.0)
        row = QFrame()
        row.setObjectName("consortiumRequirementRow")
        layout = QGridLayout(row)
        layout.setContentsMargins(9, 3, 9, 3)
        layout.setColumnMinimumWidth(0, 48)
        layout.setColumnMinimumWidth(1, 270)
        layout.setColumnStretch(2, 1)
        layout.setColumnMinimumWidth(3, 132)
        module = ContractProductButton(compact=False)
        module.set_product(resource_id, definition.name if definition else resource_id.replace("_", " "), required, delivered=delivered)
        module.setEnabled(False)
        layout.addWidget(module, 0, 0, 2, 2)
        info = _label(f"YOUR CONTRIBUTION  {own:,.0f}  ·  REMAINING  {max(0, required-delivered):,.0f}", "consortiumMutedText")
        layout.addWidget(info, 0, 2)
        progress = QProgressBar()
        progress.setObjectName("consortiumRequirementProgress")
        progress.setRange(0, 1000)
        progress.setValue(round(1000*min(1.,max(0.,delivered/required))) if required>0 else 0)
        progress.setTextVisible(False)
        layout.addWidget(progress, 1, 2, 1, 2)
        return row

    def _contract_metadata(self, contract: ConsortiumContract, consortium_id: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("consortiumContractMetadata")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QGridLayout(frame)
        remaining = max(0.0, contract.expires_at - time.time())
        timer = f"{int(remaining // 86400)}D {int((remaining % 86400) // 3600)}H" if remaining >= 86400 else f"{int(remaining // 3600)}H {int((remaining % 3600) // 60)}M"
        reward, consortium_xp = (self._service.preview_contract_rewards(consortium_id, contract.kind) if contract.status == AVAILABLE else (contract.personal_reward, contract.consortium_xp_reward))
        from production_zero.ui.contract_product import contract_quantity_text
        values = (
            ("TIME REMAINING", timer),
            ("ELIGIBLE MEMBERS AT START", str(contract.member_count_at_start) if contract.started_at else "SET AT START"),
            ("CONSORTIUM XP", f"+{contract_quantity_text(consortium_xp)}"),
            ("SHARED POOL UP TO" if contract.balance_version else "PERSONAL REWARD", f"${contract_quantity_text(reward.cash)} · {contract_quantity_text(reward.company_xp)} XP" + (f" · {reward.research_points} RP" if reward.research_points else "")),
        )
        for index, (title, value) in enumerate(values):
            layout.addWidget(_label(title, "consortiumMetricLabel"), 0, index)
            value_label = _label(value, "consortiumMetricValue")
            if index == 3:
                value_label.setToolTip(f"Accepted maximum: ${reward.cash:,.2f} · {reward.company_xp:,.2f} XP. Paid by contribution using the frozen prices; unused/forfeited shares stay unpaid.")
            layout.addWidget(value_label, 1, index)
            if index == 0:
                self._contract_timer_label = value_label
                self._contract_timer_contract = contract
                self._contract_timers.append((value_label, contract))
        return frame

    def _eligibility_panel(self, consortium: Consortium, contract: ConsortiumContract) -> QFrame:
        flags = self._service.reward_eligibility(consortium.consortium_id, contract.kind)
        personal = self._service.personal_reward_quote(contract, self._service.current_company_id)
        panel = QFrame()
        panel.setObjectName("consortiumEligibilityPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QGridLayout(panel)
        panel.setToolTip(f"Your current contribution: ${personal.cash:,.2f}, {personal.company_xp:,.2f} XP, {personal.research_points} RP. Minimum RP contribution: {contract.rp_minimum_shares.get(self._service.current_company_id,0.):.2%} of base goods value. Cash follows your fixed goods value plus Research captured at START; XP follows fixed base goods value. Pool is a maximum reserve, unused/forfeited shares are not redistributed. Weekly RP requires the meaningful share fixed at START from your verified capability; inactive identities cannot lower it. Half your expected capability share is sufficient; stock-only donors use the smallest verified share. Leaving forfeits rewards; late members cannot earn rewards.")
        entries = (
            ("ELIGIBLE AT START", flags["eligible_at_start"]),
            ("CONTRIBUTED", flags["contributed"]),
            ("CURRENT MEMBER", flags["current_member"]),
            ("REWARD ELIGIBLE", flags["reward_eligible"]),
        )
        for index, (title, enabled) in enumerate(entries):
            layout.addWidget(_label(title, "consortiumMetricLabel"), 0, index)
            value = _label("YES" if enabled else "NO", "consortiumEligibilityValue")
            value.setProperty("satisfied", enabled)
            layout.addWidget(value, 1, index)
        if not flags["eligible_at_start"]:
            layout.addWidget(_label("JOINED AFTER CONTRACT START · ELIGIBLE FOR THE NEXT CONTRACT", "consortiumEligibilityReason"), 2, 0, 1, 4)
        elif contract.status == COMPLETED and not flags["reward_eligible"]:
            layout.addWidget(_label("NO PERSONAL REWARD", "consortiumEligibilityReason"), 2, 0, 1, 4)
        elif contract.status == COMPLETED:
            layout.addWidget(_label("PERSONAL REWARD GRANTED", "consortiumEligibilityGranted"), 2, 0, 1, 4)
        return panel

    def _refresh_members(self, consortium: Consortium, role: str) -> None:
        old_roster = next((scroll for scroll in self.members_page.findChildren(QScrollArea, "consortiumRosterScroll") if not scroll.isHidden()), None)
        if old_roster is not None:
            self._roster_scroll_position = old_roster.verticalScrollBar().value()
        _clear(self.members_layout)
        header_frame = QFrame()
        header_frame.setObjectName("consortiumLayoutHost")
        header_frame.setFixedHeight(36)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(_label(f"MEMBERS  {len(consortium.members)} / {consortium.member_capacity}", "consortiumSectionTitle"), 1)
        if role in (CHAIRMAN, BOARD_MEMBER):
            invite = RaisedPZButton("INVITE PLAYER", variant="primary")
            invite.setMinimumHeight(0)
            invite.setObjectName("resourcesButton")
            invite.clicked.connect(lambda: self._show_invite(consortium))
            header.addWidget(invite)
        self.members_layout.addWidget(header_frame)
        housing = ConsortiumWorkspaceFrame(level=MaterialLevel.INSET)
        housing.setObjectName("consortiumRosterHousing")
        housing_layout = QVBoxLayout(housing)
        housing_layout.setContentsMargins(8, 8, 8, 8)
        housing_layout.setSpacing(2)
        columns = ("COMPANY", "LEVEL", "ROLE", "CONTRIBUTION")
        heading = QFrame()
        heading.setObjectName("consortiumRosterHeader")
        heading.setFixedHeight(32)
        heading_layout = QGridLayout(heading)
        heading_layout.setContentsMargins(12, 6, 12, 6)
        heading_layout.setColumnStretch(0, 1)
        for index, title in enumerate(columns):
            label = _label(title, "consortiumRosterHeading")
            if index:
                label.setFixedWidth((82, 150, 130)[index - 1])
            heading_layout.addWidget(label, 0, index)
        housing_layout.addWidget(heading)
        roster_scroll = QScrollArea()
        roster_scroll.setObjectName("consortiumRosterScroll")
        roster_scroll.setWidgetResizable(True)
        roster_scroll.setMinimumHeight(0)
        # Row count must affect the inner scroll range, never the outer page's
        # preferred height or the management footer's position.
        roster_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        housing.setMinimumHeight(100)
        housing.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        roster_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        roster_host = QWidget()
        roster_host.setObjectName("consortiumRosterBody")
        roster_layout = QVBoxLayout(roster_host)
        roster_layout.setContentsMargins(0, 0, 0, 0)
        roster_layout.setSpacing(1)
        roster_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._member_rows = {}
        for member in sorted(consortium.members.values(), key=lambda value: (value.role != CHAIRMAN, value.role != BOARD_MEMBER, value.company_name)):
            member_row = QFrame()
            member_row.setObjectName("consortiumRosterRow")
            member_row.setProperty("role", member.role)
            member_row.setProperty("selected", member.company_id == self._selected_member_id)
            member_row.setFixedHeight(48)
            member_row.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            member_row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            member_row.customContextMenuRequested.connect(lambda point, m=member, row=member_row: self._member_menu(consortium, role, m, row.mapToGlobal(point)))
            cells = QGridLayout(member_row)
            cells.setContentsMargins(12, 2, 12, 2)
            cells.setColumnStretch(0, 1)
            values = (member.company_name.upper(), str(member.company_level), ROLE_LABELS[member.role], f"{member.lifetime_contribution:,.0f}")
            for index, value in enumerate(values):
                label = _label(value, "consortiumRosterRole" if index == 2 else "consortiumRosterCell")
                label.setWordWrap(False)
                if index == 0:
                    label = QPushButton(value)
                    label.setObjectName("consortiumProfileLink")
                    label.setCursor(Qt.CursorShape.PointingHandCursor)
                    label.setAccessibleName(f"Open profile for {member.company_name}")
                    label.setToolTip(f"Open profile · {member.company_name}")
                    label.clicked.connect(lambda checked=False, m=member: self.profile_requested.emit(consortium, m))
                    label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    label.customContextMenuRequested.connect(lambda point, m=member, button=label: self._member_menu(consortium, role, m, button.mapToGlobal(point)))
                if index:
                    label.setFixedWidth((82, 150, 130)[index - 1])
                cells.addWidget(label, 0, index)

            roster_layout.addWidget(member_row)
            self._member_rows[member.company_id] = member_row
        roster_scroll.setWidget(roster_host)
        roster_scroll.verticalScrollBar().setValue(self._roster_scroll_position)
        housing_layout.addWidget(roster_scroll, 1)
        self.members_layout.addWidget(housing, 1)
        if role == CHAIRMAN:
            self.members_layout.addWidget(self._chairman_settings(consortium))
        else:
            leave = RaisedPZButton("LEAVE CONSORTIUM", variant="destructive")
            leave.setObjectName("freightRemoveButton")
            leave.clicked.connect(lambda: self._confirm_leave(consortium))
            self.members_layout.addWidget(leave, alignment=Qt.AlignmentFlag.AlignRight)
        if role in (CHAIRMAN, BOARD_MEMBER) and consortium.applications:
            roster_layout.addWidget(_label("PENDING APPLICATIONS", "consortiumSectionTitle"))
            for application in consortium.applications.values():
                row = QFrame()
                row.setObjectName("consortiumApplicationRow")
                actions = QHBoxLayout(row)
                actions.addWidget(_label(f"{application.company_name.upper()} · LEVEL {application.company_level}", "consortiumDirectoryName"), 1)
                accept = RaisedPZButton("ACCEPT", variant="secondary")
                accept.setObjectName("resourcesButton")
                accept.clicked.connect(lambda checked=False, cid=application.company_id: self._process_application(consortium, cid, True))
                reject = QPushButton("REJECT")
                reject.setObjectName("freightRemoveButton")
                reject.clicked.connect(lambda checked=False, cid=application.company_id: self._process_application(consortium, cid, False))
                actions.addWidget(accept)
                actions.addWidget(reject)
                roster_layout.addWidget(row)

    def _member_menu(self, consortium: Consortium, role: str, member, position=None):
        menu = QMenu(self)
        menu.setObjectName("consortiumMemberMenu")
        menu.addAction("OPEN PLAYER PROFILE", lambda: self.profile_requested.emit(consortium, member))
        if role == CHAIRMAN and member.role != CHAIRMAN:
            menu.addSeparator()
            menu.addAction("DEMOTE TO MEMBER" if member.role == BOARD_MEMBER else "PROMOTE TO BOARD MEMBER",
                           lambda: self._change_role(consortium, member))
            menu.addAction("REMOVE FROM CONSORTIUM", lambda: self._remove_member(consortium, member.company_id))
            menu.addAction("TRANSFER LEADERSHIP", lambda: self._confirm_transfer(consortium, member))
        menu.aboutToHide.connect(menu.deleteLater)
        self._context_menu = menu
        if position is not None:
            menu.popup(position)
        return menu

    def _confirm_transfer(self, consortium: Consortium, member) -> None:
        def transfer():
            self._service.transfer_leadership(consortium.consortium_id, self._service.current_company_id, member.company_id)
            self._changed()
        dialog = ConfirmConsortiumDialog("TRANSFER LEADERSHIP", f"Appoint {member.company_name} as Chairman? You will become a Board Member and lose chairman-only management permissions.", "TRANSFER", transfer, self)
        dialog.closed.connect(self.refresh)
        dialog.show()

    def _change_role(self, consortium: Consortium, member) -> None:
        role = MEMBER if member.role == BOARD_MEMBER else BOARD_MEMBER
        self._service.set_role(consortium.consortium_id, self._service.current_company_id, member.company_id, role)
        self._changed()

    def _remove_member(self, consortium: Consortium, company_id: str) -> None:
        self._service.remove(consortium.consortium_id, self._service.current_company_id, company_id)
        self._selected_member_id = None
        self._changed()

    def _chairman_settings(self, consortium: Consortium) -> QFrame:
        panel = QFrame()
        panel.setObjectName("consortiumChairmanSettings")
        panel.setFixedHeight(148)
        outer = QVBoxLayout(panel)
        outer.addWidget(_label("MANAGEMENT SETTINGS", "consortiumSectionTitle"))
        controls = QGridLayout()
        policy = QComboBox()
        policy.setObjectName("consortiumSettingsPolicy")
        for value in (OPEN, APPLICATION, INVITE_ONLY):
            policy.addItem(POLICY_LABELS[value], value)
        policy.setCurrentIndex(policy.findData(consortium.join_policy))
        minimum = QLineEdit(str(consortium.minimum_company_level))
        minimum.setObjectName("consortiumSettingsMinimum")
        minimum.setValidator(QIntValidator(1, 999, minimum))
        save = RaisedPZButton("SAVE SETTINGS", variant="primary")
        save.setMinimumHeight(0)
        save.setObjectName("resourcesButton")
        minimum.textChanged.connect(lambda: save.setEnabled(minimum.hasAcceptableInput()))
        save.clicked.connect(lambda: self._save_settings(consortium, policy.currentData(), int(minimum.text() or "0")))
        danger = RaisedPZButton("DISBAND CONSORTIUM", variant="destructive")
        danger.setObjectName("freightRemoveButton")
        danger.clicked.connect(lambda: self._confirm_disband(consortium))
        controls.addWidget(_label("JOIN POLICY", "consortiumMetricLabel"), 0, 0)
        controls.addWidget(policy, 1, 0)
        controls.addWidget(_label("MINIMUM LEVEL", "consortiumMetricLabel"), 0, 1)
        controls.addWidget(minimum, 1, 1)
        controls.addWidget(save, 1, 2)
        controls.setColumnStretch(3, 1)
        outer.addLayout(controls)
        outer.addWidget(danger, alignment=Qt.AlignmentFlag.AlignRight)
        return panel

    def _save_settings(self, consortium: Consortium, policy: str, minimum: int) -> None:
        self._service.update_settings(consortium.consortium_id, self._service.current_company_id, policy, minimum)
        self._changed()

    def _show_invite(self, consortium: Consortium) -> None:
        dialog = InviteCompanyDialog(self._service, consortium, self)
        dialog.invited.connect(self._changed)
        dialog.closed.connect(self.refresh)
        dialog.show()

    def _process_application(self, consortium: Consortium, company_id: str, accept: bool) -> None:
        self._service.process_application(
            consortium.consortium_id, self._service.current_company_id, company_id, accept
        )
        self._changed()

    def _confirm_leave(self, consortium: Consortium) -> None:
        active = any(contract.status == ACTIVE for contract in consortium.contracts.values())
        consequence = " Leaving forfeits personal rewards for every active Contract." if active else ""
        def leave() -> None:
            self._service.leave(consortium.consortium_id, self._service.current_company_id)
            self._selected_member_id = None
            self._changed()
        dialog = ConfirmConsortiumDialog("LEAVE CONSORTIUM", f"Membership in {consortium.name} ends immediately. Delivered goods are not returned.{consequence} The Consortium retains its progress.", "LEAVE CONSORTIUM", leave, self)
        dialog.closed.connect(self.refresh)
        dialog.show()

    def _confirm_disband(self, consortium: Consortium) -> None:
        def disband() -> None:
            self._service.disband(consortium.consortium_id, self._service.current_company_id)
            self._selected_member_id = None
            self._changed()
        dialog = ConfirmConsortiumDialog("DISBAND CONSORTIUM", "The Consortium will be permanently dissolved, including its XP, level and membership records. Active Contracts expire and their pending personal rewards are forfeited. Delivered goods are not returned. Rewards already granted to companies are retained.", "DISBAND", disband, self)
        dialog.closed.connect(self.refresh)
        dialog.show()

    def _refresh_progression(self, consortium: Consortium) -> None:
        _clear(self.progression_layout)
        self.progression_layout.addWidget(_label(f"CONSORTIUM LEVEL  {consortium.level}", "consortiumProgressionLevel"))
        floor = consortium_xp_floor(consortium.level)
        required = consortium_xp_for_next_level(consortium.level)
        progress = QProgressBar()
        progress.setObjectName("consortiumXpProgressLarge")
        progress.setRange(0, int(required))
        progress.setValue(int(max(0.0, consortium.consortium_xp - floor)))
        progress.setFormat(f"{max(0.0, consortium.consortium_xp-floor):,.0f} / {required:,.0f} XP")
        self.progression_layout.addWidget(progress)
        for level, capacity in MEMBER_CAPACITY_MILESTONES:
            row = QFrame()
            row.setObjectName("consortiumMilestoneRow")
            state = "COMPLETE" if consortium.level >= level else "CURRENT" if level == next((item[0] for item in MEMBER_CAPACITY_MILESTONES if item[0] > consortium.level), -1) else "LOCKED"
            row.setProperty("milestoneState", state.lower())
            layout = QHBoxLayout(row)
            layout.addWidget(_label(f"LEVEL {level}", "consortiumMilestoneLevel"))
            layout.addWidget(_label(f"{capacity} MEMBER CAPACITY", "consortiumMilestoneCapacity"), 1)
            layout.addWidget(_label(state, "consortiumMilestoneState"))
            self.progression_layout.addWidget(row)
        if consortium.member_capacity == 50:
            self.progression_layout.addWidget(_label("50 / 50 MAXIMUM CONSORTIUM CAPACITY", "consortiumMaximumState"))

    def _changed(self) -> None:
        self.refresh()
        if self._on_changed is not None:
            self._on_changed()
