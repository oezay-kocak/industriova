from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtCore import QSize

from production_zero.ui.main_window import MainWindow
from production_zero.ui.window_geometry import clamp_window_size_to_available
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.persistence.paths import default_company_save_path


def main() -> int:
    from production_zero.ui.research_trace import diagnostic_application
    performance_enabled = os.environ.get("PRODUCTION_ZERO_PERFORMANCE_TEST") == "1"
    if performance_enabled:
        from production_zero.ui.performance_diagnostics import create_application, start_diagnostics
        app = create_application(sys.argv)
    else:
        app = diagnostic_application(sys.argv)
    from production_zero.config import APP_NAME, APP_VERSION
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    save_path = default_company_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    probe = start_diagnostics(app, save_path) if performance_enabled else None
    try:
        if probe is not None:
            with probe.recorder.span("window_startup"):
                window = MainWindow(save_store=SQLiteSaveStore(save_path))
            probe.attach_window(window)
        else:
            window = MainWindow(save_store=SQLiteSaveStore(save_path))
            if performance_enabled:
                window.statusBar().showMessage("Performance recording could not start. Gameplay remains available.")
    except BaseException:
        if probe is not None:
            probe.close()
        raise
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        window.resize(clamp_window_size_to_available(QSize(1180, 760), screen.availableGeometry()))
    else:
        window.resize(1180, 760)
    window.show()
    try:
        result = app.exec()
    finally:
        if probe is not None:
            probe.close()
        if getattr(app, "research_trace", None) is not None:
            app.research_trace.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
