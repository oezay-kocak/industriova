import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QStyle, QStyleOptionButton, QTabWidget
from production_zero.core.commands import CommandBus
from production_zero.core.research import grant_research_points, research_catalog
from production_zero.core.state import GameState
from production_zero.ui.research_view import ResearchView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_art import has_resource_raster
from production_zero.persistence.sqlite_store import SQLiteSaveStore


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return instance


def settle(app):
    for _ in range(4):
        app.processEvents()


def test_all_categories_navigation_scroll_node_states_and_icons(app):
    state = GameState(rng_seed=1)
    grant_research_points(state, 2, "test")
    view = ResearchView(state, CommandBus(state))
    view.resize(1300, 550)
    view.show()
    settle(app)
    try:
        assert len(view.navigation_buttons) == 21
        for tid, button in view.navigation_buttons.items():
            button.click()
            settle(app)
            assert view._tree_id == tid and len(view.canvas.buttons) == (35 if tid.startswith("company.") else 29)
            assert view.scroll.verticalScrollBar().maximum() > 1000
            assert view.scroll.horizontalScrollBar().maximum() == 0
        view.select_tree("industry.electronics")
        settle(app)
        major = view.canvas.buttons["industry.electronics.s1.major"]
        small = view.canvas.buttons["industry.electronics.s1.n1"]
        assert major.property("researchState") == "available"
        assert small.property("researchState") == "locked"
        QTest.mouseClick(major, Qt.MouseButton.LeftButton)
        assert state.research.available == 1
        assert major.property("researchState") == "unlocked"
        assert small.property("researchState") == "available"
        QTest.mouseClick(small, Qt.MouseButton.LeftButton)
        assert state.research.available == 0 and view.points.text() == "0 RP"
        assert view.canvas.buttons["industry.electronics.s1.n2"].property("researchState") == "unfunded"
        for node in research_catalog()[1].values():
            assert has_resource_raster(node.icon_resource), node.icon_resource
        view.scroll.verticalScrollBar().setValue(800)
        view.select_tree("company.general")
        settle(app)
        view.select_tree("industry.electronics")
        settle(app)
        assert view.scroll.verticalScrollBar().value() == 800
    finally:
        view.close()
        view.deleteLater()
        settle(app)


def test_respec_review_and_cooldown_ui(app):
    state = GameState(rng_seed=1)
    grant_research_points(state, 1, "test")
    view = ResearchView(state, CommandBus(state))
    view.resize(1300, 600)
    view.show()
    settle(app)
    try:
        view.canvas.buttons["company.general.s1.major"].click()
        view.respec_button.click()
        assert view.review.isVisible()
        view._respec()
        assert state.research.available == 1
        assert not view.respec_button.isEnabled()
        assert "COOLDOWN" in view.cooldown.text()
        view.canvas.buttons["company.general.s1.major"].click()
        assert state.research.spent == 1 and not view.respec_button.isEnabled()
    finally:
        view.close()
        view.deleteLater()
        settle(app)


def test_research_communications_use_existing_activity_without_small_node_spam(app):
    from production_zero.ui.event_feed import EventFeedController, EventFeedWidget
    from production_zero.core.research import purchase_research
    state = GameState(rng_seed=1)
    feed = EventFeedWidget(state=state)
    controller = EventFeedController(state, feed)
    try:
        grant_research_points(state, 3, "Company level up")
        purchase_research(state, "company.general.s1.major")
        purchase_research(state, "company.general.s1.n1")
        assert len(state.communications.pending_activity) == 2
        controller.observe()
        feed.flush_pending()
        rewards = [event for event in feed.history if event.event_type == "rp"]
        research = [event for event in feed.history if event.event_type == "research"]
        assert len(rewards) == 1 and rewards[0].amount == 3
        assert rewards[0].label == "Company level up"
        assert len(research) == 1 and "Foundation" in research[0].label
        assert research[0].count == 1  # The small node produces no activity spam.
        assert not state.communications.messages
        assert not state.communications.pending_activity
    finally:
        feed.close()
        feed.deleteLater()
        settle(app)


@pytest.mark.parametrize("width,height", [(1600, 900), (1366, 768)])
def test_main_window_research_accessible_and_sqlite_purchases(app, tmp_path, width, height):
    store = SQLiteSaveStore(tmp_path / "company.sqlite")
    window = MainWindow(development_mode=False, save_store=store)
    window.resize(width, height)
    tabs = window.findChild(QTabWidget)
    view = window.findChild(ResearchView)
    tabs.setCurrentWidget(view)
    window.show()
    settle(app)
    try:
        assert window.width() == width and window.height() == height
        assert all(tabs.tabText(i) != "Dev" for i in range(tabs.count()))
        assert view.scroll.viewport().width() >= 690
        assert view.scroll.horizontalScrollBar().maximum() == 0
        grant_research_points(view._state, 1, "test")
        view.refresh()
        view.canvas.buttons["company.general.s1.major"].click()
        assert window._save_writer.poll(wait=True) is None
        saved = store.load("company")
        assert saved.research.spent == 1 and saved.research.available == 0
    finally:
        window.close()
        window.deleteLater()
        settle(app)


@pytest.mark.parametrize("width,height", [(1600, 900), (1366, 768)])
def test_polished_header_sidebar_and_all_node_text_fit(app, width, height):
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(width, height)
    window.show()
    settle(app)
    try:
        grant_research_points(view._state, 8, "test")
        view._purchase("company.general.s1.major")
        view.select_tree("industry.forestry")
        view._purchase("industry.forestry.s1.major")
        view._purchase("industry.forestry.s1.n3")
        view._purchase("industry.forestry.s1.n6")
        assert view.summary.text() == "+0.9% DOMAIN VALUE  ·  3 / 29 RESEARCHED  ·  0 / 4 SPECIALIZED"
        assert view.cooldown.isHidden() and not view.cooldown.text()
        assert not hasattr(view, "feedback")
        labels = [label.text() for label in view.findChildren(QLabel)]
        assert not any("EARN RP" in label or "company-wide" in label or "Starts a 24-hour" in label for label in labels)
        assert view.layout().indexOf(view.notice) == -1 and view.notice.isHidden()
        for tid, button in view.navigation_buttons.items():
            view.select_tree(tid)
            settle(app)
            font = QFont(button.font())
            option = QStyleOptionButton()
            button.initStyleOption(option)
            content = button.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, button)
            assert QFontMetricsF(font).horizontalAdvance(button.text().replace("&&", "&")) <= content.width(), tid
            before = (button.geometry(), button.sizeHint(), font.toString(), content)
            button.setChecked(False)
            QTest.mouseMove(button, QPoint(10, 10))
            settle(app)
            button.initStyleOption(option)
            after_content = button.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, button)
            assert before == (button.geometry(), button.sizeHint(), button.font().toString(), after_content), tid
            button.setChecked(True)
            assert QFontMetricsF(view.title.font()).horizontalAdvance(view.title.text()) <= view.title.width(), tid
            assert QFontMetricsF(view.summary.font()).horizontalAdvance(view.summary.text()) <= view.summary.width(), tid
            for node_button in view.canvas.buttons.values():
                for text, pixels, rect, wrap, _ in node_button.text_blocks():
                    node_font = QFont("Bahnschrift")
                    node_font.setBold(True)
                    node_font.setPixelSize(pixels)
                    flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    if wrap:
                        flags |= Qt.TextFlag.TextWordWrap
                    bounds = QFontMetricsF(node_font).boundingRect(rect, flags, text)
                    assert bounds.width() <= rect.width() + 1 and bounds.height() <= rect.height() + 1, (tid, text, bounds, rect)
            assert view.scroll.horizontalScrollBar().maximum() == 0
    finally:
        window.close()
        window.deleteLater()
        settle(app)


def test_rendered_connections_are_unique_orthogonal_vertical_lanes(app):
    state = GameState(rng_seed=1)
    view = ResearchView(state, CommandBus(state))
    view.resize(1300, 600)
    view.show()
    try:
        for tid in view.navigation_buttons:
            view.select_tree(tid)
            settle(app)
            segments = view.canvas.connection_segments()
            # 5 splitters (5 segments each), 15 straight lanes, 4 merges (5 each).
            expected = 60 if tid.startswith("company.") else 56
            assert len(segments) == expected
            assert len({(start, end) for start, end, _ in segments}) == expected
            for start, end, _ in segments:
                assert start[0] == end[0] or start[1] == end[1]
                assert 26 < start[0] < view.canvas.width() - 26
                assert 26 < end[0] < view.canvas.width() - 26
            for section in range(1, 6 if tid.startswith("company.") else 5):
                for lane in (1, 2, 3):
                    first = view.canvas.buttons[f"{tid}.s{section}.n{lane}"]
                    second = view.canvas.buttons[f"{tid}.s{section}.n{lane + 3}"]
                    start = first.mapTo(view.canvas, first.rect().topLeft())
                    end = second.mapTo(view.canvas, second.rect().topLeft())
                    assert start.x() + first.width() / 2 == end.x() + second.width() / 2
                    assert ((start.x() + first.width() / 2, start.y() + first.height() - 5),
                            (end.x() + second.width() / 2, end.y() + 2), False) in segments
    finally:
        view.close()
        view.deleteLater()
        settle(app)


def test_research_palette_has_no_olive_or_green_surfaces():
    import inspect
    import re
    import production_zero.ui.research_view as module
    from PySide6.QtGui import QColor
    for color in re.findall(r"#[0-9a-fA-F]{6}", inspect.getsource(module)):
        rgb = QColor(color)
        assert not (rgb.green() > rgb.red() + 8 and rgb.green() > rgb.blue()), color
    source = inspect.getsource(module)
    assert "Theme.SURFACE" not in inspect.getsource(module.ResearchTreeCanvas)
    assert "QPushButton#researchNavigation:focus" in source
    assert "Theme.RESOURCE" in source and "Theme.SAFETY_YELLOW" in source
