import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import json
from threading import Event, get_ident
from time import perf_counter

import pytest
from PySide6.QtCore import QPoint, Qt, QEvent
from PySide6.QtGui import QFontMetricsF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget, QWidget
from production_zero.core.research import grant_research_points, purchase_research
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.ui.main_window import MainWindow
from production_zero.ui.market_view import MarketView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.research_view import ResearchView
from production_zero.ui.pz_controls import RaisedPZButton, RaisedRPBadge


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return instance


def settle(app):
    for _ in range(5):
        app.processEvents()


def test_purchase_keeps_widgets_skips_hidden_views_and_does_not_wait_for_disk(app, tmp_path, monkeypatch):
    store = SQLiteSaveStore(tmp_path / "timing.sqlite")
    window = MainWindow(development_mode=False, save_store=store)
    view = window.findChild(ResearchView)
    tabs = window.findChild(QTabWidget)
    tabs.setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    settle(app)
    gate, entered = Event(), Event()
    commits = []
    original = store.save_snapshot
    ui_thread = get_ident()

    def slow_commit(slot, payload):
        entered.set()
        assert gate.wait(5)
        commits.append((get_ident(), payload))
        original(slot, payload)

    monkeypatch.setattr(store, "save_snapshot", slow_commit)
    calls = []
    from production_zero.ui.supply_view import SupplyView
    market, contracts = window.findChild(SupplyView), window.findChild(ContractsView)
    monkeypatch.setattr(market, "refresh", lambda: calls.append("market"))
    monkeypatch.setattr(contracts, "refresh", lambda: calls.append("contracts"))
    try:
        grant_research_points(view._state, 10, "test")
        purchase_research(view._state, "company.general.s1.major")
        view.refresh()
        settle(app)
        identities = {id(widget) for widget in window.findChildren(QWidget)}
        nodes, navigation = dict(view.canvas.buttons), dict(view.navigation_buttons)
        start = perf_counter()
        view.canvas.buttons["company.general.s1.n1"].click()
        duration = (perf_counter() - start) * 1000
        assert duration < 100, duration
        assert not calls and view.points.text() == "8 RP"
        assert set(view.canvas.last_updated_ids) == {"company.general.s1.n1", "company.general.s1.n4"}
        assert {id(widget) for widget in window.findChildren(QWidget)} == identities
        assert nodes == view.canvas.buttons and navigation == view.navigation_buttons
        assert entered.wait(1) and not commits
        view.canvas.buttons["company.general.s1.n2"].click()
        assert set(view.canvas.last_updated_ids) == {"company.general.s1.n2", "company.general.s1.n5"}
        gate.set()
        assert window._save_writer.poll(wait=True) is None
        assert [record[1]["research"]["spent"] for record in commits] == [2, 3]
        assert all(thread != ui_thread for thread, _ in commits)
        assert store.load("company").research.spent == 3
        view.refresh()
        assert view.canvas.last_updated_ids == ()
        tabs.setCurrentWidget(contracts)
        assert calls == ["contracts"]
        tabs.setCurrentWidget(contracts)
        assert calls == ["contracts"]
    finally:
        gate.set()
        window.close()
        window.deleteLater()
        settle(app)


def test_failed_save_prevents_close_and_latest_snapshot_can_retry(app, tmp_path, monkeypatch):
    store = SQLiteSaveStore(tmp_path / "retry.sqlite")
    window = MainWindow(development_mode=False, save_store=store)
    window.show()
    settle(app)
    original = store.save_snapshot
    def fail(*args):
        raise OSError("test disk failure")
    monkeypatch.setattr(store, "save_snapshot", fail)
    try:
        view = window.findChild(ResearchView)
        grant_research_points(view._state, 5, "test")
        view._purchase("company.general.s1.major")
        assert not window.close()
        assert window.isVisible() and "save failed" in window.statusBar().currentMessage()
        assert view._state.research.spent == 1
        monkeypatch.setattr(store, "save_snapshot", original)
        assert window.close()
        assert store.load("company").research.spent == 1
    finally:
        monkeypatch.setattr(store, "save_snapshot", original)
        if window.isVisible():
            window.close()
        window.deleteLater()
        settle(app)


@pytest.mark.parametrize("width,height", [(1600, 900), (1366, 768)])
def test_raised_controls_sidebar_and_slot_inset(app, width, height):
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(width, height)
    window.show()
    settle(app)
    try:
        view.select_tree("industry.electronics")
        settle(app)
        assert isinstance(view.points, RaisedRPBadge)
        assert isinstance(view.respec_button, RaisedPZButton) and view.respec_button.variant == "primary"
        assert view.findChild(QLabel, "researchHeading").font().pixelSize() == 24
        assert all(label.font().pixelSize() == 17 for label in view.findChildren(QLabel, "researchGroup"))
        for name in ("eventFeedHistoryButton", "companyInboxButton"):
            button = window.findChild(QPushButton, name)
            assert isinstance(button, RaisedPZButton) and button.variant == "secondary"
            assert button.height() >= 42
            assert QFontMetricsF(button.font()).horizontalAdvance(button.text()) < button.width() - 8
            # Same geometry as the former native QPushButton with these object styles.
            reference = QPushButton(button.text(), button.parentWidget())
            reference.setObjectName(name)
            reference.setStyleSheet(button.styleSheet())
            reference.ensurePolished()
            assert reference.sizeHint() == button.sizeHint()
            reference.deleteLater()
        for button in view.canvas.specialization_buttons.values():
            major = view.canvas.buttons[button.slot.major_node_id]
            major_pos = major.mapTo(view.canvas, QPoint(0, 0))
            assert button.x() == view.canvas.width() - 26 - button.width() - 42
            assert button.x() > major_pos.x() + major.width()
            assert view.canvas.childAt(button.geometry().center()) is button
        assert view.scroll.horizontalScrollBar().maximum() == 0
        button = view.respec_button
        button.setEnabled(True)
        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        normal = button.grab().toImage()
        QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
        hovered = button.grab().toImage()
        button.setDown(True)
        pressed = button.grab().toImage()
        button.setDown(False)
        button.setEnabled(False)
        disabled = button.grab().toImage()
        assert normal != hovered and hovered != pressed and pressed != disabled
    finally:
        window.close()
        window.deleteLater()
        settle(app)
