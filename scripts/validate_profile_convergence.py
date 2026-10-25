"""Run the entire pytest suite with Qt application state isolated per module."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / os.environ.get("PZ_QA_OUTPUT", "artifacts/profile_convergence/tests")


def run(path):
    start = time.monotonic()
    name = path.stem
    with (OUT / f"{name}.log").open("w", encoding="utf-8") as log:
        try:
            bootstrap = ("import sys; from PySide6.QtWidgets import QApplication; "
                         "from production_zero.tools.ui_contact_sheet import _load_qa_fonts; "
                         "app=QApplication([]); _load_qa_fonts(); import pytest; "
                         "raise SystemExit(pytest.main(sys.argv[1:]))")
            result = subprocess.run([sys.executable, "-c", bootstrap, "-q", str(path),
                                     f"--junitxml={OUT / (name + '.xml')}", "-o", "faulthandler_timeout=90"],
                                    cwd=ROOT, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
                                    stdout=log, stderr=subprocess.STDOUT, timeout=360)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    return dict(module=str(path.relative_to(ROOT)), exit_code=code, seconds=round(time.monotonic() - start, 2))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"], cwd=ROOT, check=True)
    retry = "--retry-failed" in sys.argv
    previous = json.loads((OUT / "results.json").read_text(encoding="utf-8")) if retry else []
    paths = [ROOT / row["module"] for row in previous if row["exit_code"]] if retry else sorted((ROOT / "tests").glob("test_*.py"))
    results = [row for row in previous if not row["exit_code"]]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run, path) for path in paths]
        for future in as_completed(futures):
            result = future.result()
            if retry:
                result["previous_attempt"] = next(row for row in previous if row["module"] == result["module"])
            results.append(result)
            print(json.dumps(result), flush=True)
            (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    totals = dict(tests=0, failures=0, errors=0, skipped=0)
    for result in results:
        path = OUT / (Path(result["module"]).stem + ".xml")
        if path.exists():
            for suite in ET.parse(path).getroot().iter("testsuite"):
                for key in totals:
                    totals[key] += int(suite.get(key, "0"))
    summary = dict(modules=len(results), **totals, unsuccessful_modules=[r for r in results if r["exit_code"]])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return bool(summary["unsuccessful_modules"])


if __name__ == "__main__":
    sys.exit(main())
