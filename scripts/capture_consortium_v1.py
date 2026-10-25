"""Focused offscreen Consortium playtest audit at 1366x768."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

from production_zero.core.consortium import APPLICATION, INVITE_ONLY, OPEN, BOARD_MEMBER, MEMBER, CONSORTIUM_DAILY, CONSORTIUM_WEEKLY, ConsortiumMember
from production_zero.core.progression import production_options
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.main_window import MainWindow


OUTPUT = Path("artifacts/consortium_final_playtest")


def settle(app: QApplication) -> None:
    for _ in range(8):
        app.processEvents()


def build(app: QApplication) -> tuple[MainWindow, ConsortiumView]:
    window = MainWindow(development_mode=False)
    window.resize(1366, 768)
    view = window.findChild(ConsortiumView)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(view)
    window.show()
    settle(app)
    return window, view


def save(app: QApplication, window: MainWindow, name: str) -> None:
    settle(app)
    if not window.grab().save(str(OUTPUT / f"{name}.png")):
        raise RuntimeError(f"Failed to save {name}")


def seed_products(view: ConsortiumView) -> None:
    for option in production_options(view._definitions):
        view._state.production_progress.unlocked_production_ids.add(option.production_id)
        view._state.ensure_resource(option.output_resource).amount = 25


def start(view: ConsortiumView, consortium, kind: str) -> None:
    candidates = view._service.contract_candidates(consortium.consortium_id, kind)
    preferred = [rid for rid in ("crude_oil", "processed_gypsum", "stainless_components", "silicon_substrate", "orbital_vehicle") if rid in candidates]
    selected = tuple((preferred + [rid for rid in candidates if rid not in preferred])[:3 if kind == CONSORTIUM_DAILY else 4])
    view._service.start_contract(consortium.consortium_id, view._service.current_company_id, kind, selected)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()

    window, view = build(app)
    save(app, window, "01_directory_empty_1366x768")
    view._show_create()
    save(app, window, "03_create_embedded_1366x768")
    for dialog in window.centralWidget().findChildren(QWidget, "consortiumCreateDialog"):
        dialog.close()
    fixture = (("Open Foundry", OPEN, 1), ("Application Works", APPLICATION, 1), ("Private Assembly", INVITE_ONLY, 1), ("Full Collective", OPEN, 1), ("High Level Guild", OPEN, 99))
    for name, policy, minimum in fixture:
        consortium = view._service.create(name, policy, minimum)
        if name == "Full Collective":
            for index in range(1, 10):
                consortium.members[f"full-{index}"] = ConsortiumMember(f"full-{index}", f"Full Member {index}", 20)
        view._state.consortium.current_company_id = f"fixture.{name.replace(' ', '.').lower()}"
    view._state.consortium.current_company_id = "directory.viewer"
    view._state.company.level = 20
    view.refresh()
    save(app, window, "02_directory_populated_1366x768")
    window.close()

    window, view = build(app)
    seed_products(view)
    consortium = view._service.create("Northstar Industries", OPEN, 1)
    view.refresh()
    save(app, window, "04_overview_1366x768")
    view._open_contract(CONSORTIUM_DAILY)
    save(app, window, "05_daily_three_empty_slots_1366x768")
    view._open_product_picker(0)
    save(app, window, "06_daily_product_picker_1366x768")
    view._close_product_picker()
    preferred = ("crude_oil", "processed_gypsum", "stainless_components")
    view._draft_products[CONSORTIUM_DAILY] = [rid for rid in preferred if rid in view._service.contract_candidates(consortium.consortium_id, CONSORTIUM_DAILY)]
    view._select_contract(CONSORTIUM_DAILY)
    save(app, window, "07_daily_selected_preview_1366x768")
    weekly_preferred = ("crude_oil", "processed_gypsum", "stainless_components", "silicon_substrate")
    view._draft_products[CONSORTIUM_WEEKLY] = [rid for rid in weekly_preferred if rid in view._service.contract_candidates(consortium.consortium_id, CONSORTIUM_WEEKLY)]
    view._open_contract(CONSORTIUM_WEEKLY)
    save(app, window, "08_weekly_selected_preview_1366x768")
    start(view, consortium, CONSORTIUM_DAILY)
    view._open_contract(CONSORTIUM_DAILY)
    save(app, window, "09_active_contract_1366x768")
    view.member_tabs.setCurrentWidget(view.members_page)
    view.refresh()
    save(app, window, "10_members_one_1366x768")
    for index in range(1, 10):
        role = BOARD_MEMBER if index in (1, 2) else MEMBER
        consortium.members[f"fixture-{index}"] = ConsortiumMember(f"fixture-{index}", f"Fixture Industries {index:02d}", 8 + index, role, 1_500 + index, index * 125)
    view.refresh()
    save(app, window, "11_members_ten_1366x768")
    consortium.member_capacity = 15
    consortium.join_policy = APPLICATION
    view._service.apply(consortium.consortium_id, "external.steel", "Steel Works", 12)
    consortium.join_policy = OPEN
    view._show_invite(consortium)
    invite = window.centralWidget().findChild(QWidget, "consortiumInviteDialog")
    invite.query.setText("Steel Works")
    invite._lookup()
    save(app, window, "12_invite_resolved_1366x768")
    invite.close()
    consortium.member_capacity = 50
    for index in range(10, 50):
        consortium.members[f"fixture-{index}"] = ConsortiumMember(f"fixture-{index}", f"Fixture Industries {index:02d}", 8 + index, MEMBER, 1_500 + index, index * 125)
    view.refresh()
    save(app, window, "11b_members_fifty_1366x768")
    view.members_page.verticalScrollBar().setValue(view.members_page.verticalScrollBar().maximum())
    save(app, window, "11c_members_management_1366x768")
    view._service._award_consortium_xp(consortium, 35_000)
    view.member_tabs.setCurrentWidget(view.progression_page)
    view.refresh()
    save(app, window, "13_progression_1366x768")
    window.close()
    print(f"Captured 13 requested Consortium states plus 50-member and management details in {OUTPUT}")


if __name__ == "__main__":
    main()
