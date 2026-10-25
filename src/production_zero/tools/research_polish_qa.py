"""Focused Research polish captures. Never starts a live GUI or writes a player save."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QFrame, QTabWidget
from production_zero.core.research import grant_research_points
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView

OUTPUT = Path(__file__).resolve().parents[3] / "artifacts/ui/research-polish-v1"


def main():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    captures = []

    def settle():
        for _ in range(8):
            app.processEvents()

    def capture(name, widget=window, region=None):
        settle()
        path = OUTPUT / f"{name}.png"
        pixmap = widget.grab(region) if region is not None else widget.grab()
        assert pixmap.save(str(path))
        captures.append(str(path))

    try:
        grant_research_points(view._state, 61, "Offscreen QA")
        view._purchase("company.general.s1.major")
        capture("01-general-1600x900")
        view.select_tree("industry.forestry")
        settle()
        next_major = view.canvas.buttons["industry.forestry.s2.major"]
        bottom = next_major.mapTo(view.canvas, next_major.rect().bottomLeft()).y() + 24
        capture("02-forestry-three-lanes", view.canvas, QRect(0, 0, view.canvas.width(), bottom))
        for suffix in ("major", "n1", "n4", "n2"):
            view._purchase("industry.forestry.s1." + suffix)
        capture("03-forestry-mixed-states")
        capture("04-rp-and-respec", view.findChild(QFrame, "researchHeader"))
        window.resize(1366, 768)
        capture("05-compact-1366x768")
        metrics = dict(platform=app.platformName(), captures=captures,
                       compact_size=[window.width(), window.height()],
                       viewport_width=view.scroll.viewport().width(),
                       horizontal_scroll_max=view.scroll.horizontalScrollBar().maximum())
        (OUTPUT / "qa.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics))
    finally:
        window.close()
        window.deleteLater()
        settle()


if __name__ == "__main__":
    main()
