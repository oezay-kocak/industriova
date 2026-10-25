"""Three ordinary application event loops and closes against isolated save data."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def child(number):
    from PySide6.QtCore import QTimer
    import production_zero.app.__main__ as application
    from production_zero.ui.main_window import MainWindow
    class SmokeWindow(MainWindow):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if number > 1:
                assert self._session_state.cash.amount == 7777 + number - 1
            self._session_state.cash.amount = 7777 + number
            QTimer.singleShot(600, self.close)
    application.MainWindow = SmokeWindow
    result = application.main()
    assert result == 0
    print(json.dumps({"launch": number, "exit_code": result, "cash": 7777 + number}))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        child(int(sys.argv[2]))
        return
    root = Path(__file__).resolve().parents[1]
    destination = root / "artifacts/industriova-release/application-smoke"
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LOCALAPPDATA=str(destination), QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(root / "src"))
    results = []
    for number in (1, 2, 3):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child", str(number)], cwd=root, env=env, text=True, capture_output=True, timeout=30)
        results.append({"launch": number, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            break
    database = destination / "Industriova/saves/company.sqlite"
    with closing(sqlite3.connect(database)) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        payload = json.loads(db.execute("SELECT state_json FROM saves WHERE slot='company'").fetchone()[0])
    report = {"launches": results, "integrity": integrity, "final_cash": payload["cash"]["amount"]}
    (destination / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    assert len(results) == 3 and all(r["exit_code"] == 0 for r in results) and integrity == "ok" and payload["cash"]["amount"] == 7780


if __name__ == "__main__":
    main()
