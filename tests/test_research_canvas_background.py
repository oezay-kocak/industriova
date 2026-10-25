"""Offscreen canvas contrast, scroll continuity and gameplay-scale references."""
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.research import grant_research_points
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView


def test_canvas_contrast_scroll_continuity_and_reference_captures():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    tabs = window.findChild(QTabWidget)
    tabs.setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()

    def settle():
        for _ in range(6):
            app.processEvents()

    settle()
    for timer in window.findChildren(QTimer):
        timer.stop()
    output = Path("artifacts/ui/research-canvas-background")
    output.mkdir(parents=True, exist_ok=True)
    try:
        view.select_tree("industry.agriculture")
        grant_research_points(view._state, 40, "Background QA")
        view._purchase("industry.agriculture.s1.major")
        view._purchase("industry.agriculture.s1.n1")
        settle()
        canvas = view.canvas
        geometry = {key: button.geometry() for key, button in canvas.buttons.items()}
        full = canvas.grab().toImage()
        # Empty margins measure actual paint, independently of node materials.
        for y in (20, 420, 1000, canvas.height() - 20):
            left = full.pixelColor(5, y)
            right = full.pixelColor(canvas.width() - 6, y)
            assert left.red() - right.red() >= 30
            for color in (left, right):
                assert max(color.red(), color.green(), color.blue()) - min(color.red(), color.green(), color.blue()) <= 4
                assert color.alpha() == 255

        for scroll, filename in ((0, "01-research-1600x900.png"), (420, "02-research-scrolled-1600x900.png")):
            view.scroll.verticalScrollBar().setValue(scroll)
            settle()
            assert window.grab().save(str(output / filename))
            viewport = view.scroll.viewport()
            rendered = viewport.grab().toImage()
            origin = canvas.mapTo(viewport, QPoint(0, 0))
            # Same canvas pixel must survive scrolling and partial repaint.
            for x in (5, canvas.width() - 6):
                for y in (30, 150, 330):
                    assert rendered.pixelColor(x + origin.x(), y) == full.pixelColor(x, y - origin.y())
            assert geometry == {key: button.geometry() for key, button in canvas.buttons.items()}
            assert view.scroll.horizontalScrollBar().maximum() == 0

        window.resize(1366, 768)
        settle()
        assert window.size().toTuple() == (1366, 768)
        assert view.scroll.horizontalScrollBar().maximum() == 0
        assert window.grab().save(str(output / "03-research-1366x768.png"))
        window.resize(1600, 900)
        tabs.setCurrentWidget(window.findChild(FreightView))
        settle()
        assert window.grab().save(str(output / "04-freight-garage-reference.png"))
    finally:
        window.close()
        window.deleteLater()
        settle()
