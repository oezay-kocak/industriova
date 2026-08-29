from __future__ import annotations

import sys

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from production_zero.ui.main_window import MainWindow
from production_zero.ui.window_geometry import clamp_window_size_to_available


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        window.resize(clamp_window_size_to_available(QSize(1180, 760), screen.availableGeometry()))
    else:
        window.resize(1180, 760)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
