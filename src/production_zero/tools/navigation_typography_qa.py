"""Capture and verify the 1600x900 global-navigation typography pass."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFrame, QTabBar

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.ui.main_window import MainWindow, NAVIGATION_TAB_HORIZONTAL_INSET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "navigation-typography"
SCREENSHOT = OUTPUT / "01_navigation_labels_1600x900.png"
EXPECTED_LABELS = (
    "Resources",
    "Factory",
    "Energy",
    "Freight",
    "Inventory",
    "Market",
    "Contracts",
    "Industrial Supply",
    "Packs",
    "Leaderboard",
    "Dev",
)


def _settle(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(1600, 900)
    window.show()
    _settle(app)

    navigation = window.findChild(QTabBar, "mainNavigationTabs")
    ticker = window.findChild(EventFeedWidget, "eventFeed")
    row = window.findChild(QFrame, "mainNavigationRow")
    assert navigation is not None and ticker is not None and row is not None
    assert window.width() == 1600 and window.height() == 900
    assert tuple(navigation.tabText(index) for index in range(navigation.count())) == EXPECTED_LABELS

    font = navigation.font()
    assert font.family() == "Bahnschrift"
    assert font.pixelSize() == 11
    assert font.weight() == QFont.Weight.Black
    assert font.stretch() == QFont.Stretch.Condensed

    widths = [navigation.tabRect(index).width() for index in range(navigation.count())]
    assert sum(widths) == navigation.width()
    assert max(widths) - min(widths) <= 24
    for index, width in enumerate(widths):
        label_width = navigation.fontMetrics().horizontalAdvance(navigation.tabText(index))
        assert label_width + NAVIGATION_TAB_HORIZONTAL_INSET <= width
        assert navigation.tabRect(index).height() <= navigation.height()

    assert navigation.width() + ticker.width() + row.layout().spacing() == row.width()
    assert abs(navigation.width() * 47 - ticker.width() * 53) <= 53

    _settle(app)
    assert window.grab().save(str(SCREENSHOT))
    print(f"font={font.family()} {font.pixelSize()}px weight={font.weight()} stretch={font.stretch()}")
    print(f"navigation={navigation.width()} ticker={ticker.width()} tabs={widths}")
    print(SCREENSHOT.resolve())
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
