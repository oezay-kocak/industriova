import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.commands import CommandBus
from production_zero.core.research import grant_research_points, purchase_research, research_catalog, research_domains, purchase_specialization
from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_tiles import ResourceSelectionTile


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return instance


def settle(app):
    for _ in range(6):
        app.processEvents()


def unlock(state, tree, through=5):
    grant_research_points(state, 40, "test")
    for node in research_catalog()[1].values():
        if node.tree_id == tree and node.row <= (through - 1) * 3:
            purchase_research(state, node.id)


@pytest.mark.parametrize("width,height", [(1600, 900), (1366, 768)])
def test_picker_navigation_purchase_icon_and_immediate_sqlite_save(app, tmp_path, width, height):
    store = SQLiteSaveStore(tmp_path / "specialization.sqlite")
    window = MainWindow(development_mode=False, save_store=store)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(width, height)
    window.show()
    settle(app)
    try:
        view.select_tree("industry.electronics")
        sid = "industry.electronics.specialization.1"
        button = view.canvas.specialization_buttons[sid]
        button.click()
        assert view.picker is None
        unlock(view._state, "industry.electronics", through=2)
        view.refresh()
        view.scroll.ensureWidgetVisible(button)
        settle(app)
        saved_scroll = view.scroll.verticalScrollBar().value()
        view._state.communications.pending_activity.clear()
        activity = len(view._state.communications.pending_activity)
        button.click()
        settle(app)
        picker = view.picker
        assert picker is not None and picker.isVisible()
        assert len(picker.tiles) == sum(domain == "electronics" for domain in research_domains().values())
        assert all(isinstance(tile, ResourceSelectionTile) for tile in picker.tiles.values())
        assert "copper_wire" not in picker.tiles and "cpu" in picker.tiles
        assert picker.scroll.horizontalScrollBar().maximum() == 0
        assert picker.scroll.verticalScrollBar().maximum() > 0
        picker.search.setText("nothing_matches")
        settle(app)
        assert picker.empty.isVisible() and not picker.visible_product_ids
        picker.search.setText("MICROCHIP")
        settle(app)
        assert picker.visible_product_ids == ["microchip"]
        picker.back_button.click()
        settle(app)
        assert view.picker is None and view.scroll.verticalScrollBar().value() == saved_scroll
        assert len(view._state.communications.pending_activity) == activity
        button.click()
        view.picker.search.setText("microchip")
        settle(app)
        tile = view.picker.tiles["microchip"]
        assert tile.findChild(ResourceIconWidget).resource_id == "microchip"
        QTest.mouseClick(tile, Qt.MouseButton.LeftButton, pos=QPoint(80, 120))
        settle(app)
        assert view.picker is None
        assert view._state.research.specializations == {sid: "microchip"}
        assert window._save_writer.poll(wait=True) is None
        assert store.load("company").research.specializations == {sid: "microchip"}
        assert button.icon.resource_id == "microchip" and button.property("researchState") == "unlocked"
        assert "1 / 4 SPECIALIZED" in view.summary.text()
        button.click()
        assert view.picker is None
        view._respec()
        settle(app)
        assert not view._state.research.specializations and button.icon is None
        assert button.property("researchState") == "locked"
        assert view.cooldown.isVisible()
        assert window._save_writer.poll(wait=True) is None
        assert not store.load("company").research.specializations
    finally:
        window.close()
        window.deleteLater()
        settle(app)


@pytest.mark.parametrize("width,height", [(1600, 900), (1366, 768)])
def test_all_domain_picker_grids_side_placement_and_selected_text_fit(app, width, height):
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(width, height)
    window.show()
    settle(app)
    try:
        for tree in research_catalog()[0].values():
            if tree.family != "industry":
                continue
            unlock(view._state, tree.id)
            view.select_tree(tree.id)
            settle(app)
            assert len(view.canvas.specialization_buttons) == 4
            assert view.scroll.horizontalScrollBar().maximum() == 0
            for button in view.canvas.specialization_buttons.values():
                major = view.canvas.buttons[button.slot.major_node_id]
                major_pos = major.mapTo(view.canvas, major.rect().topLeft())
                slot_pos = button.mapTo(view.canvas, button.rect().topLeft())
                assert slot_pos.x() > major_pos.x() + major.width()
                assert slot_pos.y() + button.height() / 2 == major_pos.y() + major.height() / 2
                assert slot_pos.x() + button.width() <= view.canvas.width()
            button = next(iter(view.canvas.specialization_buttons.values()))
            button.click()
            settle(app)
            picker = view.picker
            expected = {rid for rid, domain in research_domains().items() if domain == tree.id.removeprefix("industry.")}
            assert set(picker.tiles) == expected
            assert picker.scroll.horizontalScrollBar().maximum() == 0
            assert picker._columns >= 4
            for rid, tile in picker.tiles.items():
                assert tile.geometry().right() < picker.scroll.viewport().width()
                assert tile.findChild(ResourceIconWidget).resource_id == rid
                # Exercise the longest canonical product names in the side chassis,
                # without purchasing/changing any real allocation.
                view._state.research.specializations[button.slot.id] = rid
                button.refresh()
                for text, size, rect, wrap in button.text_blocks():
                    font = QFont("Bahnschrift")
                    font.setPixelSize(size)
                    font.setBold(True)
                    flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                    if wrap:
                        flags |= Qt.TextFlag.TextWordWrap
                    bounds = QFontMetricsF(font).boundingRect(rect, flags, text)
                    assert bounds.width() <= rect.width() + 1 and bounds.height() <= rect.height() + 1, (rid, text, bounds, rect)
            del view._state.research.specializations[button.slot.id]
            view._close_picker()
        assert window.size().width() == width and window.size().height() == height
    finally:
        window.close()
        window.deleteLater()
        settle(app)


def test_insufficient_rp_picker_error_and_dev_reset(app):
    from production_zero.ui.dev_tools_view import DevToolsView
    state = GameState(rng_seed=1)
    unlock(state, "industry.electronics", through=2)
    state.research.total_earned = state.research.spent
    view = ResearchView(state, CommandBus(state))
    view.resize(1300, 650)
    view.show()
    settle(app)
    try:
        view.select_tree("industry.electronics")
        button = view.canvas.specialization_buttons["industry.electronics.specialization.1"]
        button.click()
        settle(app)
        view.picker.tiles["microchip"].selected_product.emit("microchip")
        assert view.picker is not None and "1 RP" in view.picker.message.text()
        assert not state.research.specializations
        # Call the existing Dev handler with only its state/callback dependencies.
        class DevHarness:
            _state = state
            _refresh_callback = staticmethod(view.refresh)
        DevToolsView._research_dev(DevHarness(), "grant")
        view.picker.tiles["microchip"].selected_product.emit("microchip")
        assert state.research.specializations
        earned = state.research.total_earned
        DevToolsView._research_dev(DevHarness(), "reset")
        assert not state.research.specializations and not state.research.unlocked_node_ids
        assert state.research.available == earned
        assert button.icon is None
    finally:
        view.close()
        view.deleteLater()
        settle(app)
