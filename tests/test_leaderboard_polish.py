import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import pytest
from PySide6.QtCore import QPoint, Qt, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QFrame
from production_zero.tools.leaderboard_demo import create_demo_provider, demo_entries
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.ui.theme import APP_STYLESHEET


@pytest.fixture
def view():
    app = QApplication.instance() or QApplication([])
    for font in ('segoeui.ttf', 'segoeuib.ttf', 'bahnschrift.ttf', 'agencyr.ttf', 'agencyb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    app.setStyleSheet(APP_STYLESHEET)
    widget = LeaderboardView(create_demo_provider())
    widget.resize(1180, 720)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def search(view, query):
    view._search.setText(query)
    QTest.keyClick(view._search, Qt.Key.Key_Return)
    QApplication.processEvents()


def assert_located_visible(view):
    row = view._located_row
    assert row is not None and row.property('located')
    scroll = view._scrolls[view._current_ranking_id()]
    if not row.property('ownPlayer'):
        point = row.mapTo(scroll.viewport(), QPoint())
        assert 0 <= point.y() <= scroll.viewport().height() - row.height()
    return row


def test_demo_is_deterministic_and_isolated():
    first, second = create_demo_provider(), create_demo_provider()
    assert len(demo_entries()) == 99
    assert len({e.player_name for e in demo_entries()}) == 99
    for metric in ('company_level', 'total_earnings'):
        entries = first.ranking(metric, 1000)
        assert entries == second.ranking(metric, 1000)
        assert len(entries) == 100
        assert [e.rank for e in entries] == list(range(1, 101))
        assert 60 <= first.own_entry(metric).rank <= 90
        values = [getattr(e, metric) for e in entries]
        assert values == sorted(values, reverse=True)
    first._state.company.level = 100
    assert second._state.company.level == 25


def test_clean_header_and_sticky_row(view):
    assert not view._header._monochrome
    from production_zero.ui.main_tab_header import MAIN_TAB_HEADER_HEIGHT
    assert view._header.height() == MAIN_TAB_HEADER_HEIGHT == 116
    assert not view.findChildren(QFrame, 'leaderboardHeaderMetric')
    assert not view.findChildren(QFrame, 'ownLeaderboardPanel')
    assert not view.findChildren(QFrame, 'leaderboardFooterMetric')
    for index, metric in enumerate(('company_level', 'total_earnings')):
        view._set_ranking_index(index)
        QApplication.processEvents()
        scroll = view._scrolls[metric]
        pinned = view._rows_by_rank[metric][view._provider.own_entry(metric).rank]
        before = pinned.mapTo(view, QPoint())
        assert pinned.findChild(QLabel, 'leaderboardYouBadge').text() == 'YOU'
        rows = scroll.widget().findChildren(QFrame, 'leaderboardRow')
        assert len(rows) == 99
        assert all(not row.property('ownPlayer') for row in rows)
        assert all(row.height() >= 46 for row in rows)
        assert scroll.verticalScrollBar().maximum() > 0
        for value in (0, scroll.verticalScrollBar().maximum() // 2, scroll.verticalScrollBar().maximum()):
            scroll.verticalScrollBar().setValue(value)
            QApplication.processEvents()
            assert pinned.isVisible() and pinned.mapTo(view, QPoint()) == before
        identities = [id(row) for row in rows]
        view.refresh()
        assert [id(row) for row in scroll.widget().findChildren(QFrame, 'leaderboardRow')] == identities
        own_rows = [r for r in view._tabs.currentWidget().findChildren(QFrame, 'leaderboardRow') if r.property('ownPlayer')]
        assert own_rows == [pinned]


@pytest.mark.parametrize('query,rank', [('1',1), ('50',50), ('#50',50), ('rank 50',50), ('RANK 100',100), ('# 1',1)])
def test_rank_navigation_keeps_neighbors(view, query, rank):
    search(view, query)
    row = assert_located_visible(view)
    assert row.property('rank') == rank
    assert len(view._rows_by_rank['company_level']) == 100
    if rank == 50:
        rows = view._rows_by_rank['company_level']
        scroll = view._scrolls['company_level']
        for neighbor in (49, 51):
            assert 0 <= rows[neighbor].mapTo(scroll.viewport(), QPoint()).y() < scroll.viewport().height()
    view.grab().save(f'artifacts/leaderboard_jump_{rank}.png')


@pytest.mark.parametrize('query,expected', [('Northstar Steel','Northstar Steel'), ('nOrThStAr StEeL','Northstar Steel'), ('copperline','Copperline Engineering'), ('Process Works','Ironvale Process Works')])
def test_company_navigation(view, query, expected):
    search(view, query)
    assert assert_located_visible(view).findChild(QLabel, 'leaderboardPlayer').text() == expected


@pytest.mark.parametrize('query', ['0', '-1', '101', '999999999999999', '#-2', 'rank nope', 'nonexistent foundry'])
def test_bad_search_is_clean(view, query):
    search(view, '50')
    scroll = view._scrolls['company_level']
    before = scroll.verticalScrollBar().value()
    search(view, query)
    assert view._located_row is None
    assert view._search_status.text() == 'NO MATCH / RANK'
    assert scroll.verticalScrollBar().value() == before
    assert len(view._rows_by_rank['company_level']) == 100


def test_metric_switch_and_live_player_update(view):
    search(view, '50')
    previous = view._located_row.findChild(QLabel, 'leaderboardPlayer').text()
    view._metric_buttons[1].click()
    QApplication.processEvents()
    assert view._scrolls['total_earnings'].verticalScrollBar().value() == 0
    assert view._located_row is None
    search(view, '50')
    assert assert_located_visible(view).findChild(QLabel, 'leaderboardPlayer').text() != previous
    search(view, 'Your Company')
    pinned = assert_located_visible(view)
    assert pinned.property('pinnedPlayer')
    assert pinned.findChild(QLabel, 'leaderboardValue').text() == '$25,500'
    scroll = view._scrolls['total_earnings']
    identities = [id(row) for row in scroll.widget().findChildren(QFrame, 'leaderboardRow')]
    view._provider._state.statistics.total_earnings = 25501
    view.refresh()
    assert [id(row) for row in scroll.widget().findChildren(QFrame, 'leaderboardRow')] == identities
    search(view, 'Your Company')
    assert view._located_row.findChild(QLabel, 'leaderboardValue').text() == '$25,501'
    view._provider._state.company.level = 100
    view.refresh()
    view._set_ranking_index(0)
    search(view, '1')
    assert view._located_row.property('pinnedPlayer')


@pytest.mark.parametrize('width,height', [(1180,720), (1000,650), (1440,900)])
def test_control_and_row_geometry(view, width, height):
    view.resize(width, height)
    QApplication.processEvents()
    assert view._search.width() >= 240
    assert view._search.geometry().left() > view._metric_buttons[-1].geometry().right()
    pinned = view._rows_by_rank['company_level'][75]
    assert pinned.mapTo(view, QPoint()).y() + pinned.height() <= view.height()
    assert view._scrolls['company_level'].horizontalScrollBar().maximum() == 0
    view.grab().save(f'artifacts/leaderboard_polish_{width}.png')



def test_metric_click_fetches_latest_player_score(view):
    view._provider._state.statistics.total_earnings = 200000
    view._metric_buttons[1].click()
    QApplication.processEvents()
    own = view._rows_by_rank['total_earnings'][1]
    assert own.property('pinnedPlayer')
    assert own.findChild(QLabel, 'leaderboardValue').text() == '$200,000'
    search(view, '#1')
    assert view._located_row is own


def test_highlight_timer_is_owned_and_disposed(view):
    from shiboken6 import isValid
    child = LeaderboardView(create_demo_provider())
    child.setParent(view)
    child._search.setText('50')
    child._search_jump()
    timer = child._highlight_timer
    assert timer.isActive()
    child.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(timer)
