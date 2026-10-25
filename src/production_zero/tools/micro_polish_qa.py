from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.ui.main_window import MainWindow
from production_zero.ui.market_view import MarketView
from production_zero.ui.supply_view import SupplyView


OUTPUT = Path("artifacts/micro-polish")


def _drain(app: QApplication) -> None:
    for _ in range(6):
        app.processEvents()


def _capture(window: MainWindow, app: QApplication, path: Path) -> None:
    _drain(app)
    assert window.grab().save(str(path))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1600, 980)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    if tabs is None:
        raise RuntimeError("Main tabs not found")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    indexes = {tabs.tabText(index): index for index in range(tabs.count())}
    tabs.setCurrentIndex(indexes["Freight"])
    _capture(window, app, OUTPUT / "freight.png")

    tabs.setCurrentIndex(indexes["Market"])
    market = tabs.currentWidget()
    if not isinstance(market, MarketView):
        raise RuntimeError("Market view not found")
    market._stage_filter.setCurrentText("Assembly")
    assert market._proxy_model.rowCount() > 0
    _capture(window, app, OUTPUT / "market_assembly.png")

    tabs.setCurrentIndex(indexes["Industrial Supply"])
    supply = tabs.currentWidget()
    if not isinstance(supply, SupplyView):
        raise RuntimeError("Industrial Supply view not found")
    supply._show_section(1)
    supply._buy_quantity.setCurrentText("X4")
    supply._type_filter.setCurrentText("Freight")
    _capture(window, app, OUTPUT / "industrial_supply_x4_freight.png")

    tabs.setCurrentIndex(indexes["Leaderboard"])
    _capture(window, app, OUTPUT / "leaderboard.png")
    window.close()
    print(f"Captured 4 offscreen screenshots in {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
