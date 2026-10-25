"""Focused human-review follow-up fixtures; no real save or history is modified."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from dataclasses import replace
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QTabWidget, QScrollArea
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.research_view import ResearchView
from production_zero.core.player_profile import local_profile
from production_zero.core.consortium import OPEN
from production_zero.tools.ui_contact_sheet import _load_qa_fonts, _save_contact_sheet
from capture_consortium_v1 import seed_products, start

OUT = Path("artifacts/human_review_followup")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    manifest = []
    for width, height in ((1366, 768), (1600, 980), (1920, 1080)):
        window = MainWindow(development_mode=False)
        for timer in window.findChildren(QTimer):
            timer.stop()
        tabs = window.findChild(QTabWidget, "mainTabs")
        window.resize(width, height)
        window.show()
        captures = []

        def save(screen, state):
            for _ in range(6):
                app.processEvents()
            assert (window.width(), window.height()) == (width, height)
            name = f"{screen}_{state}_{width}x{height}.png".lower()
            pixmap = window.grab()
            assert pixmap.save(str(OUT / name))
            captures.append((f"{screen} / {state}", pixmap))
            manifest.append(dict(screen=screen, state=state, resolution=f"{width}x{height}", path=name))

        for title in ("Resources", "Factory", "Energy"):
            tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i) == title))
            save(title, "reference")
        state = window._session_state
        state.ensure_resource("copper_ore").amount = 18420
        state.production_progress.lifetime_produced["iron_ore"] = 21000
        window.open_player_profile(local_profile(state))
        save("Profile", "no_history")
        window._profile_view.close()
        state.inventory_history.advance(1, {"copper_ore": 500})
        window.open_player_profile(local_profile(state))
        save("Profile", "sparse_history")
        window._profile_view.close()
        for i in range(288):
            state.inventory_history.advance(300, {"copper_ore": 500 + i * 62 + (i % 20) * 15})
        window.open_player_profile(local_profile(state))
        save("Profile", "populated")
        window._profile_view.close()
        consortium = window.findChild(ConsortiumView)
        original = consortium._resource_definitions["copper_ore"]
        consortium._resource_definitions["copper_ore"] = replace(original, name="Copper Ore from the Northern Precision Materials Facility")
        window.open_player_profile(replace(local_profile(state), name="Northstar Precision Manufacturing and Resource Processing Consortium Company", source="EXPLICIT VISUAL TEST FIXTURE"))
        save("Profile", "long_names")
        profile_scroll = window._profile_view.findChild(QScrollArea, "profileScroll")
        profile_scroll.verticalScrollBar().setValue(profile_scroll.verticalScrollBar().maximum())
        save("Profile", "long_names_scrolled")
        window._profile_view.close()
        consortium._resource_definitions["copper_ore"] = original
        seed_products(consortium)
        contracts = window.findChild(ContractsView)
        contracts.refresh()
        tabs.setCurrentWidget(contracts)
        save("Contracts", "empty")
        for controls in list(contracts._selection_controls.values()):
            for i, combo in enumerate(controls["combos"]):
                combo.setCurrentIndex(i + 1)
        save("Contracts", "selected_all_kinds")
        for kind in ("regular", "daily", "weekly"):
            offer = state.contracts.offers[kind][0]
            contracts._accept(kind, offer.contract_id)
        save("Contracts", "active_all_kinds")
        scroll = contracts.findChild(QScrollArea, "contractsBoardScroll")
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        save("Contracts", "scrolled_actions")
        guild = consortium._service.create("Northstar Industries", OPEN, 1)
        consortium.refresh()
        tabs.setCurrentWidget(consortium)
        save("Consortium", "tab_row")
        for kind in ("daily", "weekly"):
            consortium._open_contract(kind)
            save("Consortium", kind + "_empty")
            count = 3 if kind == "daily" else 4
            consortium._draft_products[kind] = list(consortium._service.contract_candidates(guild.consortium_id, kind)[:count])
            consortium._select_contract(kind)
            save("Consortium", kind + "_selected")
            start(consortium, guild, kind)
            consortium._select_contract(kind)
            save("Consortium", kind + "_active")
            consortium.contracts_page.verticalScrollBar().setValue(consortium.contracts_page.verticalScrollBar().maximum())
            save("Consortium", kind + "_active_scrolled")
        research = window.findChild(ResearchView)
        tabs.setCurrentWidget(research)
        save("Research", "top")
        research.navigation_scroll.verticalScrollBar().setValue(research.navigation_scroll.verticalScrollBar().maximum())
        research.select_tree(list(research.navigation_buttons)[-1])
        save("Research", "bottom")
        _save_contact_sheet(captures, OUT / f"contact_{width}x{height}.png")
        window.close()
        window.deleteLater()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(manifest)} captures; exact root size checked throughout.")


if __name__ == "__main__":
    main()
