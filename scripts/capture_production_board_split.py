"""Render the production-board split for visual QA without launching the normal GUI."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2
from production_zero.tools.ui_contact_sheet import _load_qa_fonts


OUTPUT_DIR = Path(os.environ.get("PRODUCTION_BOARD_CAPTURE_DIR", "artifacts/production_board_split"))
VIEWPORTS = ((1366, 768, "compact"), (1920, 1080, "desktop"))


def _settle(app: QApplication) -> None:
    for _ in range(10):
        app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    window.findChild(FactoryViewV2).pause_simulation()
    tabs = window.findChild(QTabWidget, "mainTabs")
    boards = (
        ("resources", window.findChild(ResourcesViewV2)),
        ("factory", window.findChild(FactoryViewV2)),
        ("energy", window.findChild(EnergyViewV2)),
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for width, height, viewport_name in VIEWPORTS:
        window.resize(width, height)
        window.show()
        for board_name, board in boards:
            tabs.setCurrentWidget(board)
            board.refresh_view()
            _settle(app)
            path = OUTPUT_DIR / f"{board_name}_{viewport_name}_{width}x{height}.png"
            if not window.grab().save(str(path)):
                raise RuntimeError(f"Could not save {path}")
        resources = boards[0][1]
        tabs.setCurrentWidget(resources)
        resources._on_slot_clicked(0)
        _settle(app)
        drawer_path = OUTPUT_DIR / f"resources_drawer_{viewport_name}_{width}x{height}.png"
        if not window.grab().save(str(drawer_path)):
            raise RuntimeError(f"Could not save {drawer_path}")
        resources._close_drawer()
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
