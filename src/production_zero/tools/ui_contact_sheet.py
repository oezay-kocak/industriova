from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = ROOT / "artifacts"
CONTACT_SHEET_PATH = ARTIFACT_DIR / "global_ui_contact_sheet.png"
CONTACT_SHEET_DIR = ARTIFACT_DIR / "ui_contact_sheets"
NATIVE_DIR = ARTIFACT_DIR / "ui_native_screens"
WINDOW_SIZES = (
    ("narrow", 1280, 820),
    ("default", 1600, 980),
    ("large", 1920, 1080),
)


def _safe_name(title: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in title).strip("_")


def _load_qa_fonts() -> None:
    for font_path in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/bahnschrift.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/arialn.ttf"),
        Path("C:/Windows/Fonts/agencyr.ttf"),
    ):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def _drain_events(app: QApplication, passes: int = 6) -> None:
    for _ in range(passes):
        app.processEvents()


def _capture_tabs(
    app: QApplication,
    window: MainWindow,
    tabs: QTabWidget,
    size_label: str,
    width: int,
    height: int,
) -> list[tuple[str, QPixmap]]:
    window.resize(width, height)
    window.show()
    _drain_events(app)

    captures: list[tuple[str, QPixmap]] = []
    native_size_dir = NATIVE_DIR / size_label
    native_size_dir.mkdir(parents=True, exist_ok=True)
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        current = tabs.currentWidget()
        if current is not None and hasattr(current, "refresh"):
            current.refresh()
        _drain_events(app)
        title = tabs.tabText(index)
        pixmap = window.grab()
        pixmap.save(str(native_size_dir / f"{index + 1:02d}_{_safe_name(title)}.png"))
        captures.append((title, pixmap))
    return captures


def _save_contact_sheet(captures: list[tuple[str, QPixmap]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    thumb_size = QSize(520, 319)
    padding = 18
    label_height = 28
    columns = 3
    rows = (len(captures) + columns - 1) // columns
    sheet = QImage(
        columns * thumb_size.width() + (columns + 1) * padding,
        rows * (thumb_size.height() + label_height) + (rows + 1) * padding,
        QImage.Format.Format_ARGB32,
    )
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(QColor("#edf6f2"))
    font = QFont("Segoe UI", 10)
    font.setBold(True)
    painter.setFont(font)

    for index, (title, pixmap) in enumerate(captures):
        row = index // columns
        column = index % columns
        x = padding + column * (thumb_size.width() + padding)
        y = padding + row * (thumb_size.height() + label_height + padding)
        painter.drawText(
            x,
            y,
            thumb_size.width(),
            label_height,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title.upper(),
        )
        scaled = pixmap.scaled(
            thumb_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(x, y + label_height, scaled)

    painter.end()
    sheet.save(str(path))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    if tabs is None:
        raise RuntimeError("Main tab widget not found.")

    ARTIFACT_DIR.mkdir(exist_ok=True)
    for size_label, width, height in WINDOW_SIZES:
        captures = _capture_tabs(app, window, tabs, size_label, width, height)
        contact_sheet_path = CONTACT_SHEET_DIR / f"global_ui_contact_sheet_{size_label}.png"
        _save_contact_sheet(captures, contact_sheet_path)
        if size_label == "default":
            _save_contact_sheet(captures, CONTACT_SHEET_PATH)
    window.close()
    print(CONTACT_SHEET_PATH)


if __name__ == "__main__":
    main()
