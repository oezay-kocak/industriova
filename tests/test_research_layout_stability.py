import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget
from production_zero.core.research import research_catalog
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView


def settle(app):
    for _ in range(6):
        app.processEvents()


@pytest.mark.parametrize("size", [(1600, 900), (1366, 768)])
def test_all_trees_share_main_axis_lanes_and_buses(size):
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(*size)
    window.show()
    settle(app)
    for timer in window.findChildren(QTimer):
        timer.stop()
    signatures = {}
    captures = {"company.general": "01-general", "industry.agriculture": "02-agriculture",
                "industry.electronics": "03-electronics"}
    output = Path("artifacts/ui/research-layout-stability")
    output.mkdir(parents=True, exist_ok=True)
    try:
        for tree_id, tree in research_catalog()[0].items():
            view.select_tree(tree_id)
            settle(app)
            canvas = view.canvas
            view.scroll.verticalScrollBar().setValue(420)
            settle(app)
            assert window.size().toTuple() == size
            assert view.scroll.horizontalScrollBar().maximum() == 0
            assert view.scroll.verticalScrollBar().maximum() > 1000
            assert view.scroll.verticalScrollBar().value() == 420
            suffixes = ["s1.major", *[f"s1.n{i}" for i in range(1, 7)], "s2.major"]
            nodes = [canvas.buttons[f"{tree_id}.{suffix}"] for suffix in suffixes]
            centers = [button.mapTo(window, QPoint(0, 0)).x() + button.width() / 2 for button in nodes]
            lanes = {button.node.position: center for button, center in zip(nodes[1:4], centers[1:4])}
            for button in canvas.buttons.values():
                center = button.mapTo(window, QPoint(0, 0)).x() + button.width() / 2
                assert center == (centers[0] if button.major else lanes[button.node.position])
            major_ii = nodes[-1]
            cutoff = major_ii.mapTo(canvas, QPoint(0, 0)).y() + 2
            offset = canvas.mapTo(window, QPoint(0, 0)).x()
            # Compare the complete first cluster's main split/merge and lane
            # X coordinates. Existing Industry row heights remain unchanged.
            buses = sorted((start[0] + offset, end[0] + offset)
                           for start, end, _ in canvas.connection_segments()
                           if start[1] <= cutoff and end[1] <= cutoff)
            reserves = canvas.findChildren(QWidget, "researchSpecializationReserve")
            assert reserves and all(side.width() == 176 for side in reserves)
            assert len(canvas.specialization_buttons) == (4 if tree.family == "industry" else 0)
            for button in canvas.specialization_buttons.values():
                major = canvas.buttons[button.slot.major_node_id]
                assert button.x() == canvas.width() - 26 - button.width() - 42
                assert button.x() > major.mapTo(canvas, QPoint(0, 0)).x() + major.width()
                assert button.geometry().right() < canvas.width()
            signatures[tree_id] = dict(centers=centers, buses=buses, canvas_width=canvas.width(),
                                       node_widths=[button.width() for button in nodes],
                                       canvas_height=canvas.height())
            reference = signatures["company.general"]
            for key in ("centers", "buses", "canvas_width", "node_widths"):
                assert signatures[tree_id][key] == reference[key], (size, tree_id, key, signatures[tree_id], reference)
            if size == (1600, 900) and tree_id in captures:
                assert window.grab().save(str(output / f"{captures[tree_id]}.png"))
        # Verify returning from Industry to Company, not just the initial tree.
        view.select_tree("company.general")
        settle(app)
        major = view.canvas.buttons["company.general.s1.major"]
        assert major.mapTo(window, QPoint(0, 0)).x() + major.width() / 2 == signatures["company.general"]["centers"][0]
        (output / f"geometry-{size[0]}x{size[1]}.json").write_text(json.dumps(signatures, indent=2), encoding="utf-8")
    finally:
        window.close()
        window.deleteLater()
        settle(app)
