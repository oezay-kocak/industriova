"""Six Product Specialization V1 captures; Qt offscreen only, no player save."""
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.research import grant_research_points, research_catalog
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView

OUTPUT = Path(__file__).resolve().parents[3] / "artifacts/ui/research-specialization-v1"


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

    def capture(name, widget=None):
        settle()
        path = OUTPUT / f"{name}.png"
        assert (widget or window).grab().save(str(path))
        captures.append(str(path))

    try:
        grant_research_points(view._state, 61, "Offscreen QA")
        view.select_tree("industry.electronics")
        settle()
        capture("01-industry-four-side-slots", view.canvas)
        button = view.canvas.specialization_buttons["industry.electronics.specialization.1"]
        capture("02-locked-slot", button)
        for node in research_catalog()[1].values():
            if node.tree_id == "industry.electronics" and node.row <= 3:
                view._purchase(node.id)
        view.scroll.ensureWidgetVisible(button)
        capture("03-available-slot", button)
        button.click()
        capture("04-electronics-product-picker")
        picker_metrics = dict(product_count=len(view.picker.tiles), columns=view.picker._columns,
                              horizontal_scroll_max=view.picker.scroll.horizontalScrollBar().maximum())
        view.picker.search.setText("microchip")
        settle()
        view.picker.tiles["microchip"].selected_product.emit("microchip")
        capture("05-microchip-selected", button)
        window.resize(1366, 768)
        settle()
        view.scroll.ensureWidgetVisible(button, 20, 80)
        capture("06-compact-specialization-1366x768")
        metrics = dict(platform=app.platformName(), captures=captures, picker=picker_metrics,
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
