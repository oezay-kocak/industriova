"""Rendered purchase timing and four polish captures; always Qt offscreen."""
import json
import os
from pathlib import Path
from time import perf_counter

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QFrame, QTabWidget, QWidget
from production_zero.core.research import grant_research_points, research_catalog
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView

OUTPUT = Path(__file__).resolve().parents[3] / "artifacts/ui/research-interaction-polish"


def main():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    window = MainWindow(development_mode=False, save_store=SQLiteSaveStore(OUTPUT / "after-qa.sqlite"))
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    captures, samples = [], []

    def settle():
        for _ in range(5):
            app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def capture(name, widget=None):
        settle()
        path = OUTPUT / f"{name}.png"
        assert (widget or window).grab().save(str(path))
        captures.append(str(path))

    try:
        settle()
        grant_research_points(view._state, 61, "Offscreen QA")
        view.refresh()
        settle()
        for suffix in ("major", "n1", "n2", "n3", "n4"):
            before = {id(w) for w in window.findChildren(QWidget)}
            start = perf_counter()
            view.canvas.buttons[f"company.general.s1.{suffix}"].click()
            handler_ms = (perf_counter() - start) * 1000
            updated = view.canvas.last_updated_ids
            after = {id(w) for w in window.findChildren(QWidget)}
            settle()
            samples.append(dict(node=suffix,click_ms=handler_ms,
                                click_and_events_ms=(perf_counter() - start) * 1000,
                                created_widgets=len(after - before), updated_nodes=list(updated)))
        assert window._save_writer.poll(wait=True) is None
        capture("01-raised-research-header", view.findChild(QFrame, "researchHeader"))
        capture("02-research-sidebar-and-controls")
        view.select_tree("industry.electronics")
        for node in research_catalog()[1].values():
            if node.tree_id == "industry.electronics" and node.row <= 3:
                view._purchase(node.id)
        view._purchase_specialization("industry.electronics.specialization.1", "microchip")
        window.resize(1366, 768)
        settle()
        button = view.canvas.specialization_buttons["industry.electronics.specialization.1"]
        view.scroll.ensureWidgetVisible(button, 20, 80)
        capture("03-industry-inset-1366x768")
        capture("04-history-inbox-controls", window._event_feed)
        metrics = dict(platform=app.platformName(), samples=samples, captures=captures,
                       persistence="UI-thread immutable JSON snapshot; ordered worker SQLite commits; close flushes",
                       slot_inset_px=view.canvas.SPECIALIZATION_INSET,
                       compact_size=[window.width(),window.height()],
                       horizontal_scroll_max=view.scroll.horizontalScrollBar().maximum())
        (OUTPUT / "after-timing.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics))
    finally:
        window.close()
        window.deleteLater()
        settle()


if __name__ == "__main__":
    main()
