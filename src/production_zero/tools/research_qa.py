"""Controlled Research V1 QA: Qt offscreen only, nine review captures."""
from __future__ import annotations
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.research import grant_research_points, purchase_research, research_catalog
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView
from production_zero.ui.market_view import MarketView
from production_zero.tools.ui_contact_sheet import _load_qa_fonts

OUTPUT = Path(__file__).resolve().parents[3] / "artifacts/ui/research-v1"


def main():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    tabs = window.findChild(QTabWidget)
    view = window.findChild(ResearchView)
    state = view._state
    tabs.setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    captures = []

    def settle():
        for _ in range(8):
            app.processEvents()

    def capture(name, widget=window):
        settle()
        path = OUTPUT / f"{name}.png"
        assert widget.grab().save(str(path))
        captures.append(str(path))

    try:
        grant_research_points(state, 45, "Offscreen QA")
        view.refresh()
        capture("01-company-available")
        view.canvas.buttons["company.general.s1.major"].click()
        capture("02-company-purchased")
        view.select_tree("industry.electronics")
        view._purchase("industry.electronics.s1.major")
        view._purchase("industry.electronics.s1.n2")
        view.refresh()
        capture("03-industry-states")
        capture("04-major-node", view.canvas.buttons["industry.electronics.s1.major"])
        for node in research_catalog()[1].values():
            if node.tree_id == "industry.electronics" and node.row < 12 and node.id not in state.research.unlocked_node_ids:
                view._purchase(node.id)
        view.refresh()
        view.scroll.verticalScrollBar().setValue(1450)
        capture("05-deep-vertical-tree")
        view._review_respec()
        capture("06-respec-review")
        view._respec()
        view.scroll.verticalScrollBar().setValue(0)
        view.canvas.buttons["industry.electronics.s1.major"].click()
        capture("07-respec-cooldown")
        window.resize(1366, 768)
        capture("08-compact-1366x768")
        metrics = dict(window_size=[window.width(), window.height()], viewport_width=view.scroll.viewport().width(),
                       horizontal_scroll_max=view.scroll.horizontalScrollBar().maximum(), vertical_scroll_max=view.scroll.verticalScrollBar().maximum(),
                       navigation_width=tabs._navigation_bar.width(), navigation_last_right=tabs._navigation_bar.tabRect(tabs.count() - 1).right())
        market = window.findChild(MarketView)
        tabs.setCurrentWidget(market)
        market._show_detail("microchip")
        window.resize(1600, 900)
        capture("09-market-research-value")
        (OUTPUT / "qa.json").write_text(json.dumps(dict(platform=app.platformName(), captures=captures, compact=metrics), indent=2), encoding="utf-8")
        print(json.dumps(dict(captures=len(captures), compact=metrics)))
    finally:
        window.close()
        window.deleteLater()
        settle()


if __name__ == "__main__":
    main()
