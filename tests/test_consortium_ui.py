from __future__ import annotations
from consortium_freight_fixture import freight_contribute, freight_receive

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget, QTableWidget, QFrame, QProgressBar, QLineEdit, QSpinBox, QScrollArea
from PySide6.QtTest import QTest

from production_zero.core.consortium import (
    APPLICATION,
    INVITE_ONLY,
    BOARD_MEMBER,
    CONSORTIUM_DAILY,
    MEMBER,
    OPEN,
    ConsortiumMember,
)
from production_zero.ui.consortium_view import ConsortiumView, CreateConsortiumDialog, InviteCompanyDialog, ConfirmConsortiumDialog
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_tiles import ResourceSelectionTile
from production_zero.ui.contracts_view import ContractProductPicker
from production_zero.core.progression import production_options


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return instance


def settle(app) -> None:
    for _ in range(4):
        app.processEvents()


def view(app) -> tuple[MainWindow, ConsortiumView]:
    window = MainWindow(development_mode=False)
    result = window.findChild(ConsortiumView)
    assert result is not None
    return window, result


def create_member_view(result: ConsortiumView):
    for option in production_options(result._definitions):
        result._state.production_progress.unlocked_production_ids.add(option.production_id)
        result._state.ensure_resource(option.output_resource).amount = 1
    consortium = result._service.create("Northstar Industries", OPEN, 1)
    result.refresh()
    return consortium


def start(result: ConsortiumView, consortium, kind: str):
    count = 3 if kind == CONSORTIUM_DAILY else 4
    products = result._service.contract_candidates(consortium.consortium_id, kind)[:count]
    return result._service.start_contract(consortium.consortium_id, result._service.current_company_id, kind, products)


def test_directory_create_and_search_filter_survive_refresh(app) -> None:
    window, result = view(app)
    try:
        assert result.stack.currentIndex() == 0
        assert result.create_button.text() == "CREATE CONSORTIUM"
        result.directory_search.setText("north")
        result._set_directory_policy(OPEN)
        result.refresh()
        assert result.directory_search.text() == "north"
        assert result._directory_policy == OPEN and result.directory_filters[OPEN].isChecked()
        dialog = CreateConsortiumDialog(result._service, result)
        dialog.show()
        assert not dialog.isWindow()
        dialog.name_edit.setText("Test Foundry")
        dialog.minimum_level.setText("3")
        assert isinstance(dialog.minimum_level, QLineEdit) and not dialog.findChildren(QSpinBox)
        dialog._create()
        result.refresh()
        assert result.stack.currentIndex() == 1
        assert result._state.consortium.membership()[0].name == "Test Foundry"
    finally:
        window.close()


def test_populated_directory_filters_and_embedded_modal_do_not_create_windows(app) -> None:
    window, result = view(app)
    window.show()
    settle(app)
    try:
        for index, policy in enumerate((OPEN, APPLICATION, INVITE_ONLY)):
            result._service.create(f"Fixture {index}", policy, 1)
            result._state.consortium.current_company_id = f"fixture.{index}"
        result._state.consortium.current_company_id = "viewer"
        result.refresh()
        assert len([row for row in result.directory_host.findChildren(QFrame, "consortiumDirectoryRow") if not row.isHidden()]) == 3
        result._set_directory_policy(APPLICATION)
        result.refresh()
        assert len([row for row in result.directory_host.findChildren(QFrame, "consortiumDirectoryRow") if not row.isHidden()]) == 1
        assert result.directory_filters[APPLICATION].isChecked()
        before = set(app.topLevelWidgets())
        result._show_create()
        settle(app)
        assert not [widget.objectName() for widget in set(app.topLevelWidgets()) - before if widget.isVisible()]
        modal = window.centralWidget().findChild(CreateConsortiumDialog)
        assert not modal.isWindow() and not result.isEnabled()
        modal.close()
        assert result.isEnabled()
    finally:
        window.close()


def test_create_modal_deferred_refresh_keeps_fields_then_updates_on_close(app) -> None:
    window, result = view(app)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(result)
    window.show()
    try:
        result._show_create()
        modal = window.centralWidget().findChild(CreateConsortiumDialog)
        modal.name_edit.setText("Stable Foundry")
        field = modal.name_edit
        before = result._content_rebuild_count
        for _ in range(6):
            result.refresh()
        assert modal.name_edit is field and field.text() == "Stable Foundry"
        assert result._content_rebuild_count == before
        modal._create()
        settle(app)
        assert result.stack.currentIndex() == 1
        assert result._state.consortium.membership()[0].name == "Stable Foundry"
    finally:
        window.close()


def test_overview_contract_roles_and_live_refresh_preserve_workspace(app) -> None:
    window, result = view(app)
    try:
        consortium = create_member_view(result)
        assert result.identity_name.text() == "NORTHSTAR INDUSTRIES"
        assert [result.member_tabs.tabText(i) for i in range(result.member_tabs.count())] == [
            "OVERVIEW", "CONTRACTS", "MEMBERS", "PROGRESSION"
        ]
        result._open_contract(CONSORTIUM_DAILY)
        assert result.member_tabs.currentWidget() is result.contracts_page
        assert any(button.text() == "START CONTRACT" for button in result.findChildren(QPushButton))
        start(result, consortium, CONSORTIUM_DAILY)
        before = result._workspace_rebuild_count
        result.refresh()
        assert result.member_tabs.currentWidget() is result.contracts_page
        assert result._selected_contract_kind == CONSORTIUM_DAILY
        assert result._workspace_rebuild_count == before
        assert any(button.text() == "DELIVER VIA FREIGHT" for button in result.findChildren(QPushButton))
        rows = result.contracts_page.findChildren(QFrame, "consortiumRequirementRow")
        bars = [row.findChild(QProgressBar, "consortiumRequirementProgress") for row in rows]
        assert len(bars) == 3
        assert len({bar.mapTo(result.contracts_page, bar.rect().topLeft()).x() for bar in bars}) == 1
        assert len({bar.width() for bar in bars}) == 1

        consortium.members["member"] = ConsortiumMember("member", "Member Company", 20, MEMBER, 2_000)
        result._state.consortium.current_company_id = "member"
        result.refresh()
        current_header = result.contracts_layout.itemAt(1).widget()
        assert not any(button.text() == "START CONTRACT" for button in current_header.findChildren(QPushButton))
        consortium.members["member"].role = BOARD_MEMBER
        consortium.contracts[CONSORTIUM_DAILY].status = "available"
        result.refresh()
        assert any(button.text() == "START CONTRACT" for button in result.findChildren(QPushButton))
    finally:
        window.close()


def test_prestart_slots_picker_preview_and_start_snapshot(app) -> None:
    window, result = view(app)
    try:
        consortium = create_member_view(result)
        result._open_contract(CONSORTIUM_DAILY)
        candidates = result._service.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)
        assert not consortium.contracts[CONSORTIUM_DAILY].requirements
        slots = result.contracts_layout.itemAt(0).widget().findChildren(QPushButton, "contractProductSlot")
        assert len(slots) == 3
        result._open_product_picker(0)
        assert isinstance(result._product_picker, ContractProductPicker)
        assert result._product_picker.property("selectorIndex") == 0
        assert not result._product_picker.isWindow()
        result._choose_product(0, candidates[0])
        assert result.member_tabs.isHidden() is False
        result._open_product_picker(1)
        assert candidates[0] in {tile.property("resourceId") for tile in result._product_picker.tiles if not tile.isEnabled()}
        result._choose_product(1, candidates[0])
        assert result._draft_products[CONSORTIUM_DAILY] == [candidates[0], None, None]
        result._choose_product(1, candidates[1])
        result._open_product_picker(2)
        result._choose_product(2, candidates[2])
        assert result._draft_products[CONSORTIUM_DAILY] == list(candidates[:3])
        from production_zero.ui.contract_product import ContractProductButton
        modules = result.contracts_layout.itemAt(0).widget().findChildren(ContractProductButton)
        assert len(modules) == 3
        preview = result._service.preview_contract(consortium.consortium_id, CONSORTIUM_DAILY, tuple(candidates[:3]))
        assert {m.property("resourceId"): m.amount.property("requiredAmount") for m in modules} == preview
        result._open_product_picker(0)
        result._choose_product(0, candidates[3])
        assert result._draft_products[CONSORTIUM_DAILY] == [candidates[3], candidates[1], candidates[2]]
        result._start_contract(consortium, CONSORTIUM_DAILY)
        contract = consortium.contracts[CONSORTIUM_DAILY]
        assert tuple(contract.requirements) == (candidates[3], candidates[1], candidates[2])
        assert len(contract.requirements) == 3 and contract.started_at is not None
    finally:
        window.close()


def test_weekly_four_slots_and_stable_hover_refresh(app) -> None:
    window, result = view(app)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(result)
    window.show()
    try:
        consortium = create_member_view(result)
        result._open_contract("weekly")
        slots = result.contracts_layout.itemAt(1).widget().findChildren(QPushButton, "contractProductSlot")
        assert len(slots) == 4
        before = result._content_rebuild_count
        first = slots[0]
        secondary = result.member_tabs.tabBar()
        for _ in range(8):
            QTest.mouseMove(first)
            result.refresh()
        assert result._content_rebuild_count == before
        assert first is result.contracts_layout.itemAt(1).widget().findChildren(QPushButton, "contractProductSlot")[0]
        assert secondary is result.member_tabs.tabBar()
        result._show_invite(consortium)
        modal = window.centralWidget().findChild(InviteCompanyDialog)
        query = modal.query
        query.setText("unknown")
        for _ in range(5):
            result.refresh()
        assert query is modal.query and modal.query.text() == "unknown"
        modal.close()
    finally:
        window.close()


def test_contribution_uses_canonical_tiles_and_updates_without_workspace_rebuild(app) -> None:
    window, result = view(app)
    try:
        consortium = create_member_view(result)
        contract = start(result, consortium, CONSORTIUM_DAILY)
        resource_id = next(iter(contract.requirements))
        result._state.ensure_resource(resource_id).amount = 20
        result.refresh()
        button=result.findChild(QPushButton,"deliverViaFreightButton")
        assert button is not None
        assert not hasattr(result,"_show_contribution")
        before = result._workspace_rebuild_count
        freight_contribute(result._service,consortium.consortium_id,result._service.current_company_id,CONSORTIUM_DAILY,resource_id,1)
        result.refresh()
        assert contract.member_contribution(result._service.current_company_id) == 1
        assert result._workspace_rebuild_count == before
    finally:
        window.close()


def test_invite_and_confirmation_remain_embedded(app) -> None:
    window, result = view(app)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(result)
    window.show()
    settle(app)
    try:
        consortium = create_member_view(result)
        consortium.join_policy = APPLICATION
        result._service.apply(consortium.consortium_id, "known.co", "Known Company", 15)
        consortium.join_policy = OPEN
        before = {widget for widget in app.topLevelWidgets() if widget.isVisible()}
        result._show_invite(consortium)
        invite = window.centralWidget().findChild(InviteCompanyDialog)
        assert invite is not None and not invite.isWindow()
        assert not invite.findChildren(QSpinBox)
        invite.query.setText("Known Company")
        invite._lookup()
        assert "LEVEL 15" in invite.resolved.text() and invite.invite_button.isEnabled()
        assert {widget for widget in app.topLevelWidgets() if widget.isVisible()} == before
        invite._invite()
        assert consortium.invitations["known.co"].company_level == 15
        result._confirm_disband(consortium)
        confirm = window.centralWidget().findChild(ConfirmConsortiumDialog)
        assert confirm is not None and not confirm.isWindow()
        assert {widget for widget in app.topLevelWidgets() if widget.isVisible()} == before
        confirm.close()
    finally:
        window.close()


def test_late_join_eligibility_member_controls_and_fifty_member_roster(app) -> None:
    window, result = view(app)
    try:
        consortium = create_member_view(result)
        start(result, consortium, CONSORTIUM_DAILY)
        consortium.members["late"] = ConsortiumMember("late", "Late Company", 20, MEMBER, 2_000)
        consortium.member_capacity = 50
        for index in range(2, 50):
            consortium.members[f"company-{index}"] = ConsortiumMember(
                f"company-{index}", f"Company {index}", 10 + index, MEMBER, 2_000
            )
        result._state.consortium.current_company_id = "late"
        result.refresh()
        result._open_contract(CONSORTIUM_DAILY)
        labels = [label.text() for label in result.findChildren(QLabel)]
        assert any("JOINED AFTER CONTRACT START" in text for text in labels)
        result.member_tabs.setCurrentWidget(result.members_page)
        result.refresh()
        current_header = result.members_layout.itemAt(0).widget()
        assert "50 / 50" in current_header.findChild(QLabel, "consortiumSectionTitle").text()
        assert not any(button.text() == "REMOVE FROM CONSORTIUM" for button in result.findChildren(QPushButton))
        assert not result.members_page.findChildren(QTableWidget)
        assert len(result._member_rows) == 50
    finally:
        window.close()


def test_roster_single_and_ten_member_counts_and_selection(app) -> None:
    window, result = view(app)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(result)
    window.resize(1366, 768)
    window.show()
    try:
        consortium = create_member_view(result)
        result.member_tabs.setCurrentWidget(result.members_page)
        result.refresh()
        settle(app)
        assert len(result._member_rows) == 1
        assert result._member_rows[result._service.current_company_id].height() == 48
        assert result._member_rows[result._service.current_company_id].y() == 0
        assert isinstance(result.members_page.findChild(QLineEdit, "consortiumSettingsMinimum"), QLineEdit)
        assert result.members_page.findChild(QSpinBox, "consortiumSettingsMinimum") is None
        for index in range(1, 10):
            consortium.members[f"fixture-{index}"] = ConsortiumMember(f"fixture-{index}", f"Fixture {index}", 20)
        result.refresh()
        settle(app)
        assert len(result._member_rows) == 10
        roster_scroll = next(scroll for scroll in result.members_page.findChildren(QScrollArea, "consortiumRosterScroll") if scroll.isVisible())
        assert roster_scroll.verticalScrollBar().maximum() > 0
        menu = result._member_menu(consortium, "chairman", consortium.members["fixture-1"])
        assert {action.text() for action in menu.actions()} >= {"PROMOTE TO BOARD MEMBER", "REMOVE FROM CONSORTIUM", "TRANSFER LEADERSHIP"}
        menu.deleteLater()
        consortium.member_capacity = 50
        for index in range(10, 50):
            consortium.members[f"fixture-{index}"] = ConsortiumMember(f"fixture-{index}", f"Fixture {index}", 20)
        result.refresh()
        settle(app)
        roster_scroll = next(scroll for scroll in result.members_page.findChildren(QScrollArea, "consortiumRosterScroll") if scroll.isVisible())
        assert len(result._member_rows) == 50 and roster_scroll.verticalScrollBar().maximum() > 0
        assert not result.members_page.findChildren(QFrame, "consortiumMemberActions")
    finally:
        window.close()


def test_completed_expired_and_max_progression_states_render(app) -> None:
    window, result = view(app)
    try:
        consortium = create_member_view(result)
        contract = start(result, consortium, CONSORTIUM_DAILY)
        for resource_id, required in contract.requirements.items():
            result._state.ensure_resource(resource_id).amount = required
            result._state.ensure_resource(resource_id).capacity = required
            freight_contribute(result._service,
                consortium.consortium_id,
                result._service.current_company_id,
                CONSORTIUM_DAILY,
                resource_id,
                required,
            )
        result._open_contract(CONSORTIUM_DAILY)
        assert any(label.text() == "COMPLETED" for label in result.contracts_page.findChildren(QLabel))
        assert any("PERSONAL REWARD GRANTED" in label.text() for label in result.contracts_page.findChildren(QLabel))

        weekly = start(result, consortium, "weekly")
        weekly.expires_at = 0
        result._service.expire_contracts(consortium.consortium_id)
        result._open_contract("weekly")
        assert any(label.text() == "EXPIRED" for label in result.contracts_page.findChildren(QLabel))

        result._service._award_consortium_xp(consortium, 1_000_000)
        result.member_tabs.setCurrentWidget(result.progression_page)
        result.refresh()
        assert any("MAXIMUM CONSORTIUM CAPACITY" in label.text() for label in result.progression_page.findChildren(QLabel))
    finally:
        window.close()


@pytest.mark.parametrize("width,height", [(1366, 768), (1600, 900)])
def test_main_navigation_and_primary_states_fit_without_application_horizontal_scroll(app, width, height) -> None:
    window, result = view(app)
    window.resize(width, height)
    main_tabs = window.findChild(QTabWidget, "mainTabs")
    main_tabs.setCurrentWidget(result)
    window.show()
    settle(app)
    try:
        assert "Consortium" in [main_tabs.tabText(i) for i in range(main_tabs.count())]
        assert window.width() == width and window.height() == height
        consortium = create_member_view(result)
        for index in range(result.member_tabs.count()):
            result.member_tabs.setCurrentIndex(index)
            settle(app)
            page = result.member_tabs.currentWidget()
            assert page.horizontalScrollBar().maximum() == 0
        assert consortium.member_capacity == 10
    finally:
        window.close()
