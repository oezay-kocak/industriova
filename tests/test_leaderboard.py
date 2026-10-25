from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabWidget

from production_zero.core.company import title_for_level
from production_zero.core.state import GameState
from production_zero.services.interfaces import LeaderboardEntry
from production_zero.services.local import LocalLeaderboardService
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.theme import APP_STYLESHEET


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _mock_entries() -> tuple[LeaderboardEntry, ...]:
    return (
        LeaderboardEntry(0, "Level Boss", 9, title_for_level(9), 100, 50),
        LeaderboardEntry(0, "Earnings Boss", 2, title_for_level(2), 9_000, 0),
        LeaderboardEntry(0, "Tie Breaker", 4, title_for_level(4), 500, 800),
    )


def _rows(view: LeaderboardView) -> list[QFrame]:
    tabs = view.findChild(QTabWidget, "leaderboardTabs")
    assert tabs is not None
    return tabs.currentWidget().findChildren(QFrame, "leaderboardRow")


def test_local_leaderboard_provider_sorts_company_level_and_total_earnings() -> None:
    state = GameState(rng_seed=1)
    state.company.level = 4
    state.company.current_xp = 1_000
    state.statistics.total_earnings = 1_200
    provider = LocalLeaderboardService(state, mock_entries=_mock_entries())

    level_names = [entry.player_name for entry in provider.ranking("company_level", 4)]
    earnings_names = [entry.player_name for entry in provider.ranking("total_earnings", 4)]

    assert level_names == ["Level Boss", "Your Company", "Tie Breaker", "Earnings Boss"]
    assert earnings_names == ["Earnings Boss", "Your Company", "Tie Breaker", "Level Boss"]
    assert provider.own_entry("company_level").rank == 2
    assert provider.own_entry("total_earnings").total_earnings == 1_200


def test_leaderboard_view_shows_company_level_and_total_earnings_tabs() -> None:
    _app()
    state = GameState(rng_seed=2)
    state.company.level = 4
    state.statistics.total_earnings = 1_200
    view = LeaderboardView(LocalLeaderboardService(state, mock_entries=_mock_entries()), limit=4)

    tabs = view.findChild(QTabWidget, "leaderboardTabs")
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == ["Company Level", "Total Earnings", "Product Production"]
    assert tabs.tabBar().isHidden()

    level_rows = _rows(view)
    assert level_rows[0].findChild(QLabel, "leaderboardPlayer").text() == "Level Boss"
    own_row = next(row for row in level_rows if row.property("ownPlayer") is True)
    assert own_row.findChild(QLabel, "leaderboardPlayer").text() == "Your Company"
    assert own_row.findChild(QLabel, "leaderboardValue").text() == "Level 4"

    tabs.setCurrentIndex(1)
    earnings_rows = _rows(view)
    assert any(row.findChild(QLabel, "leaderboardValue").text() == "$1,200" for row in earnings_rows)


def test_leaderboard_redesign_uses_header_chips_and_rank_highlights() -> None:
    _app()
    state = GameState(rng_seed=4)
    state.company.level = 4
    state.statistics.total_earnings = 1_200
    view = LeaderboardView(LocalLeaderboardService(state, mock_entries=_mock_entries()), limit=4)
    view.resize(1180, 720)
    view.show()
    try:
        QApplication.processEvents()

        header = view.findChild(QFrame, "leaderboardPageHeader")
        assert header is not None
        assert header.findChild(QLabel, "leaderboardHeroTitle").text() == "LEADERBOARD"
        assert header.findChild(QLabel, "leaderboardHeroSubtitle").text() == "GLOBAL RANKINGS / COMPANY DOMINANCE"
        assert not header.findChildren(QLabel, "leaderboardMetricLabel")
        assert not header._monochrome

        chips = view.findChildren(QPushButton, "leaderboardMetricChip")
        assert [chip.text() for chip in chips] == ["COMPANY LEVEL", "TOTAL EARNINGS", "PRODUCTION"]
        assert chips[0].property("active") is True
        assert chips[1].property("active") is False

        rows = _rows(view)
        assert rows[0].property("rankTier") == "gold"
        assert next(row for row in rows if row.property("rank") == 2).property("rankTier") == "silver"
        assert next(row for row in rows if row.property("rank") == 3).property("rankTier") == "bronze"
        assert next(row for row in rows if row.property("ownPlayer") is True).findChild(QLabel, "leaderboardYouBadge").text() == "YOU"

        chips[1].click()
        QApplication.processEvents()
        assert chips[0].property("active") is False
        assert chips[1].property("active") is True
        earnings_rows = _rows(view)
        assert earnings_rows[0].findChild(QLabel, "leaderboardPlayer").text() == "Earnings Boss"
    finally:
        view.close()
        QApplication.processEvents()


def test_leaderboard_view_shows_own_rank_when_outside_top_list() -> None:
    _app()
    state = GameState(rng_seed=3)
    state.company.level = 1
    state.statistics.total_earnings = 0
    provider = LocalLeaderboardService(state, mock_entries=_mock_entries())
    view = LeaderboardView(provider, limit=2)

    own_panels = view.findChildren(QFrame, "leaderboardPinnedContainer")
    own_text = "\n".join(label.text() for panel in own_panels for label in panel.findChildren(QLabel))

    assert "#4" in own_text
    assert "YOU" in own_text
    assert not view.findChildren(QFrame, "leaderboardFooterMetric")
    assert "Your Company" in own_text


def test_leaderboard_redesign_offscreen_preview() -> None:
    _app()
    state = GameState(rng_seed=5)
    state.company.level = 12
    state.statistics.total_earnings = 33_500
    view = LeaderboardView(LocalLeaderboardService(state), limit=8)
    view.resize(1280, 720)
    view.show()
    try:
        QApplication.processEvents()

        artifacts = Path("artifacts")
        artifacts.mkdir(exist_ok=True)
        path = artifacts / "leaderboard_redesign_preview.png"
        assert view.grab().toImage().save(str(path))
        assert path.exists()
    finally:
        view.close()
        QApplication.processEvents()
