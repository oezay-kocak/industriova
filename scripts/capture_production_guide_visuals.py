from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabWidget

from production_zero.core.progression import record_lifetime_production
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artifacts" / "production_guide_visual_redesign"
SIZES = (
    ("1366x768", 1366, 768),
    ("1600x980", 1600, 980),
    ("1920x1080", 1920, 1080),
)


class _ClickEvent:
    def button(self):
        return Qt.MouseButton.LeftButton

    def position(self):
        return QPointF(20, 52)


def _load_fonts() -> None:
    for font_path in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/bahnschrift.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/agencyr.ttf"),
    ):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def _drain(app: QApplication, passes: int = 8) -> None:
    for _ in range(passes):
        app.processEvents()


def _select_tab(tabs: QTabWidget, label: str) -> None:
    for index in range(tabs.count()):
        if label.lower() in tabs.tabText(index).lower():
            tabs.setCurrentIndex(index)
            return
    raise RuntimeError(f"Tab not found: {label}")


def _click_guide_tile(factory: FactoryViewV2, name: str) -> None:
    expected = name.upper()
    for tile in factory.findChildren(QFrame, "productionGuideTile"):
        label = tile.findChild(QLabel, "productionGuideTileName")
        if label is not None and label.text().upper() == expected:
            tile.mousePressEvent(_ClickEvent())
            return
    raise RuntimeError(f"Production Guide tile not found: {name}")


def _grab_panel(factory: FactoryViewV2, object_name: str, stem: str, size_label: str) -> None:
    panel = factory.findChild(QFrame, object_name)
    if panel is None:
        raise RuntimeError(f"Panel not found: {object_name}")
    panel.grab().save(str(OUTPUT_DIR / f"{stem}_{size_label}.png"))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _load_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for size_label, width, height in SIZES:
        window = MainWindow()
        window.findChild(FactoryViewV2).pause_simulation()
        window.resize(width, height)
        window.show()
        _drain(app)

        tabs = window.findChild(QTabWidget, "mainTabs")
        factory = window.findChild(FactoryViewV2)
        if tabs is None or factory is None:
            raise RuntimeError("Factory tab not found.")
        _select_tab(tabs, "Factory")
        record_lifetime_production(factory._state, {"steel": 12}, factory._definitions)

        factory._open_production_guide()
        _drain(app)
        _grab_panel(factory, "productionGuideView", "production_guide", size_label)

        _click_guide_tile(factory, "Steel Components")
        _drain(app)
        _grab_panel(factory, "chainInspectorView", "chain_inspector", size_label)

        action = factory.findChild(QPushButton, "guideUsedInOpenButton")
        if action is None or not action.isEnabled():
            raise RuntimeError("Open Used In button not available.")
        action.click()
        _drain(app)
        _grab_panel(factory, "usedInDetailView", "used_in_detail", size_label)
        window.close()
        _drain(app)

    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
