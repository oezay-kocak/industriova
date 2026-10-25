import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget, QPushButton

from production_zero.core.state import GameState
from production_zero.core.player_profile import local_profile, leaderboard_profile, member_profile
from production_zero.core.consortium import ConsortiumMember, OPEN
from production_zero.services.local import LocalLeaderboardService
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.inventory_history_chart import InventoryHistoryChart


def test_profile_uses_production_not_stock_and_does_not_mutate_history():
    state = GameState(rng_seed=1)
    state.production_progress.lifetime_produced.update(iron_ore=40, copper_ore=20)
    state.ensure_resource("copper_ore").amount = 500
    state.statistics.total_earnings = 99
    state.inventory_history.advance(1, {"copper_ore": 500})
    profile = local_profile(state)
    assert (profile.resource_id, profile.resource_amount, profile.lifetime_production) == ("iron_ore", 40, 60)
    assert profile.earnings == 99
    state.inventory_history.advance(300, {"copper_ore": 600})
    assert profile.inventory_history == ((1, 500),)
    assert (profile.stock_resource_id, profile.stock_amount) == ("copper_ore", 500)
    demo = leaderboard_profile(state, LocalLeaderboardService(state).ranking("company_level", 10)[0])
    assert demo.company_id is None
    assert demo.lifetime_production is None and demo.consortium is None and not demo.inventory_history
    assert "DEMO" in demo.source


@pytest.mark.parametrize("size", [(1366, 768), (1600, 980), (1920, 1080)])
def test_entry_points_embedded_profile_close_and_resize(size):
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    try:
        window.resize(*size)
        window.show()
        app.processEvents()
        state = window._session_state
        state.production_progress.lifetime_produced["iron_ore"] = 40
        state.ensure_resource("iron_ore").amount = 40
        state.inventory_history.advance(1, {"iron_ore": 40})
        window._global_header._level.click()
        app.processEvents()
        profile = window._profile_view
        assert profile.isVisible() and not profile.isWindow()
        assert profile.findChild(InventoryHistoryChart) is not None
        assert profile.rect().contains(profile.panel.geometry())
        assert (window.width(), window.height()) == size
        assert not window._global_header.isEnabled()
        QTest.keyClick(profile, Qt.Key.Key_Escape)
        app.processEvents()
        assert window._profile_view is None and window._global_header.isEnabled()
        consortium = window.findChild(ConsortiumView)
        guild = consortium._service.create("Test Company Union", OPEN, 1)
        remote = ConsortiumMember("other", "Other Company", 4)
        guild.members["other"] = remote
        consortium.refresh()
        window.findChild(QTabWidget, "mainTabs").setCurrentWidget(consortium)
        consortium.member_tabs.setCurrentWidget(consortium.members_page)
        button = next(b for b in consortium.findChildren(QPushButton, "consortiumProfileLink") if b.text() == "OTHER COMPANY")
        button.click()
        assert window._profile_view.profile == member_profile(state, guild, remote)
        window._profile_view.close()
        leaderboard = window.findChild(LeaderboardView)
        window.findChild(QTabWidget, "mainTabs").setCurrentWidget(leaderboard)
        button = next(b for b in leaderboard.findChildren(QPushButton) if b.text() == "PROFILE" and b.isVisible())
        button.click()
        assert "DEMO" in window._profile_view.profile.source
        window.resize(1366, 768)
        app.processEvents()
        assert window._profile_view.rect().contains(window._profile_view.panel.geometry())
        window._profile_view.close()
    finally:
        window.close()
        window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
