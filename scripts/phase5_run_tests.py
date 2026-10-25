"""Run every test module in a fresh process, with bounded modal-dialog hangs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import re
import xml.etree.ElementTree as ET
from time import perf_counter


def run(root, destination, *, timeout=180, workers=3):
    root = root.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "tmp").mkdir(exist_ok=True)
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(root / "src"))
    def check(path):
        module_environment = dict(environment, LOCALAPPDATA=str(destination / 'appdata' / path.stem), APPDATA=str(destination / 'appdata' / path.stem))
        start = perf_counter()
        command = [sys.executable, "-u", "-m", "pytest", str(path), "-q", "--tb=short", "--durations=5", f"--junitxml={destination / (path.stem + '.xml')}", "-o", "faulthandler_timeout=45", "-o", f"cache_dir={destination / 'cache' / path.stem}", f"--basetemp={destination / 'tmp' / path.stem}"]
        try:
            result = subprocess.run(command, cwd=root, env=module_environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            output, code = result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
            output = decoded(error.stdout) + decoded(error.stderr)
            output += f"\nTIMEOUT: {timeout} seconds per module.\n"
            code = 124
        (destination / (path.stem + ".txt")).write_text(output, encoding="utf-8")
        summaries = [line for line in output.splitlines() if re.search(r'\d+ (passed|failed|error)', line)]
        counts = {}
        report = destination / (path.stem + '.xml')
        if report.exists():
            suites = ET.parse(report).getroot().iter('testsuite')
            totals = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
            for suite in suites:
                for key in totals:
                    totals[key] += int(suite.get(key, 0))
            counts = dict(totals, passed=totals['tests'] - totals['failures'] - totals['errors'] - totals['skipped'])
        return {"module": path.name, "exit_code": code, "seconds": round(perf_counter() - start, 2), "summary": summaries[-1] if summaries else output.splitlines()[-1] if output.splitlines() else "", **counts}
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = [pool.submit(check, path) for path in sorted((root / "tests").glob("test_*.py"))]
        for job in as_completed(jobs):
            result = job.result()
            results.append(result)
            print(json.dumps(result), flush=True)
            (destination / "results.json").write_text(json.dumps(sorted(results, key=lambda r: r["module"]), indent=2), encoding="utf-8")
    print(json.dumps({"modules": len(results), "passed": sum(r["exit_code"] == 0 for r in results), "failed": sum(r["exit_code"] != 0 for r in results)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    run(args.root, args.destination, timeout=args.timeout, workers=args.workers)
