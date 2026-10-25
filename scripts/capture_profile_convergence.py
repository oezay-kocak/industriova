"""Deterministic offline visual audit; never opens or writes a player save."""
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication, QTabWidget, QScrollArea
from PySide6.QtCore import QTimer
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.research_view import ResearchView
from production_zero.core.consortium import ConsortiumMember, OPEN
from production_zero.core.player_profile import local_profile, member_profile, leaderboard_profile
from production_zero.services.local import LocalLeaderboardService
from production_zero.tools.ui_contact_sheet import _load_qa_fonts, _save_contact_sheet
from capture_consortium_v1 import seed_products, start, main as capture_consortium_details

OUT = Path("artifacts/profile_convergence")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    manifest = []
    for width, height in ((1366, 768), (1600, 980), (1920, 1080)):
        window = MainWindow(development_mode=False)
        for timer in window.findChildren(QTimer):
            timer.stop()
        window.resize(width, height)
        window.show()
        tabs = window.findChild(QTabWidget, "mainTabs")
        captures = []

        def save(screen, state):
            for _ in range(6):
                app.processEvents()
            assert (window.width(), window.height()) == (width, height)
            name = f"{screen}_{state}_{width}x{height}.png".replace(" ", "_").lower()
            pix = window.grab()
            assert pix.save(str(OUT / name))
            captures.append((f"{screen} / {state}", pix))
            manifest.append(dict(screen=screen, state=state, resolution=f"{width}x{height}", path=name))

        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            save(tabs.tabText(index), "default")
        state = window._session_state
        window.open_player_profile(local_profile(state))
        save("Profile", "empty_local")
        window._profile_view.close()
        state.production_progress.lifetime_produced.update(iron_ore=14320, copper_ore=9210)
        state.statistics.total_earnings = 48520
        for index in range(100):
            state.history.append("rate.production.iron_ore", 30 + (index % 13) * 2)
        consortium = window.findChild(ConsortiumView)
        guild = consortium._service.create("Northstar Industries", OPEN, 1)
        guild.members["demo.remote"] = ConsortiumMember("demo.remote", "Long Company Name — Precision Manufacturing Group", 22)
        consortium.refresh()
        tabs.setCurrentWidget(consortium)
        window.open_player_profile(local_profile(state))
        save("Profile", "populated_local")
        window._profile_view.close()
        window.open_player_profile(member_profile(state, guild, guild.members["demo.remote"]))
        save("Profile", "remote_missing_metrics")
        window._profile_view.close()
        window.open_player_profile(leaderboard_profile(state, LocalLeaderboardService(state).ranking("company_level", 10)[0]))
        save("Profile", "demo_leaderboard")
        window._profile_view.close()
        seed_products(consortium)
        start(consortium, guild, "daily")
        guild.member_capacity = 50
        for index in range(48):
            guild.members[f"fixture{index}"] = ConsortiumMember(f"fixture{index}", f"Fixture Industries {index}", 10)
        consortium.refresh()
        for index in range(consortium.member_tabs.count()):
            consortium.member_tabs.setCurrentIndex(index)
            save("Consortium", consortium.member_tabs.tabText(index))
        consortium.member_tabs.setCurrentWidget(consortium.members_page)
        consortium.members_page.verticalScrollBar().setValue(consortium.members_page.verticalScrollBar().maximum())
        save("Consortium", "management_scrolled")
        research = window.findChild(ResearchView)
        tabs.setCurrentWidget(research)
        research.navigation_scroll.verticalScrollBar().setValue(research.navigation_scroll.verticalScrollBar().maximum())
        last = list(research.navigation_buttons)[-1]
        research.select_tree(last)
        save("Research", "navigation_scrolled_locked")
        from production_zero.core.research import grant_research_points
        grant_research_points(state, 100, "visual fixture")
        research.refresh()
        save("Research", "available")
        _save_contact_sheet(captures, OUT / f"contact_{width}x{height}.png")
        comparison = {"Factory / default", "Freight / default", "Inventory / default", "Market / default",
                      "Profile / populated_local", "Consortium / OVERVIEW", "Consortium / MEMBERS",
                      "Research / default", "Leaderboard / default"}
        _save_contact_sheet([capture for capture in captures if capture[0] in comparison],
                            OUT / f"golden_comparison_{width}x{height}.png")
        window.close()
    capture_consortium_details()
    for path in sorted(Path("artifacts/consortium_final_playtest").glob("*.png")):
        manifest.append(dict(screen="Consortium", state=path.stem, resolution="1366x768",
                             path="../consortium_final_playtest/" + path.name))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Captured {len(manifest)} states. Root geometry verified at all three sizes.")


if __name__ == "__main__":
    main()
