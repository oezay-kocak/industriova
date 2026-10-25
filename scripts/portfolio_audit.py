"""Build review inventories and bounded privacy/link checks without staging files.

This is a heuristic review aid, not a security certification. Reports never
include matching secret values. Local backups and test outputs stay ignored.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "portfolio-release"
ENTRY_DOCS = ("README.md", "RIGHTS.md", "docs/README.md", "docs/CASE_STUDY.md",
              "docs/PORTFOLIO_RELEASE_REPORT.md", "docs/RIGHTS_REVIEW.md",
              "docs/QA_FINALIZATION.md", "docs/COMMIT_PLAN.md")
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "aws_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential_assignment": re.compile(r'''(?i)(?:api[_-]?key|password|secret)\s*[:=]\s*["'][^"'\r\n]{8,}["']'''),
    "workstation_home": re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\\s<>]+[/\\]"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", *args], cwd=ROOT)


def paths() -> list[str]:
    return sorted(set(filter(None, (git("ls-files", "-z") +
        git("ls-files", "--others", "--exclude-standard", "-z")).decode().split("\0"))))


def write_csv(name: str, rows: list[dict], columns: list[str]) -> None:
    with (ROOT / "docs" / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def findings(name: str, text: str) -> list[dict]:
    return [{"path": name, "line": i, "category": label}
        for i, line in enumerate(text.splitlines(), 1)
        for label, pattern in PATTERNS.items() if pattern.search(line)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = paths()
    head = set(filter(None, git("ls-tree", "-r", "--name-only", "HEAD").decode().splitlines()))
    changed = set(filter(None, git("diff", "HEAD", "--name-only").decode().splitlines()))
    deleted = set(filter(None, git("diff", "HEAD", "--diff-filter=D", "--name-only").decode().splitlines()))
    baseline_path = OUT / "before-manifest.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    provenance_path = ROOT / "docs" / "ASSET_PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8")) if provenance_path.exists() else {}
    reviewed_images = {entry["path"]: entry for entry in provenance.get("files", [])}
    inventory, changes, assets, privacy, syntax = [], [], [], [], []
    for name in candidates:
        path = ROOT / name
        if not path.is_file():
            if name in head:
                changes.append({"path": name, "status_vs_HEAD": "deleted", "portfolio_action": "pre-existing deletion preserved"})
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        inventory.append({"path": name, "bytes": len(data), "sha256": sha})
        status = "added" if name not in head else "modified" if name in changed else "unchanged"
        if status != "unchanged":
            action = ("added by portfolio preparation" if name not in baseline else
                      "updated by portfolio preparation" if baseline[name] != sha else
                      "pre-existing development change preserved")
            changes.append({"path": name, "status_vs_HEAD": status, "portfolio_action": action})
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".ico", ".bmp", ".tiff"}:
            group = path.parent.name
            evidence = {"resources": "resource_asset_batch_01.md; processor_resource_raster_asset_pass.md; extractor_resource_raster_asset_pass.md",
                        "machines": "primary_production_card_integration_2026-09-09.md; resource_asset_inventory_2026-09-07.md",
                        "freight": "freight_asset_pass.md; truck_raster_golden_sample.md; train_raster_red_identity.md; ship_raster_asset.md; aircraft_raster_asset.md",
                        "ui": "research-generic-icon-2026-09-13.md",
                        "images": "images/captures.json; scripts/capture_portfolio.py"}.get(group, "unresolved")
            reviewed = reviewed_images.get(name, {})
            cleared = (provenance.get("owner_declaration", {}).get("no_external_templates") is True
                       and reviewed.get("sha256") == sha
                       and reviewed.get("status") == "cleared_for_project_publication")
            assets.append({"path": name, "bytes": len(data), "sha256": sha,
                           "group_evidence_to_review": evidence,
                           "rights_status": "cleared for owner's project publication" if cleared else "pending; exclude from publication"})
        if b"\0" not in data:
            try:
                content = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            privacy.extend(findings(name, content))
            if path.suffix == ".py":
                try:
                    ast.parse(content, filename=name)
                except SyntaxError as error:
                    syntax.append({"path": name, "line": error.lineno})
    listed = {row["path"] for row in changes}
    for name in sorted(deleted - listed):
        changes.append({"path": name, "status_vs_HEAD": "deleted",
                        "portfolio_action": "generated output excluded; local file retained" if (ROOT / name).exists()
                        else "pre-existing deletion preserved"})
    changes.sort(key=lambda row: row["path"])
    write_csv("PORTFOLIO_CHANGES.csv", changes, ["path", "status_vs_HEAD", "portfolio_action"])
    write_csv("ASSET_INVENTORY.csv", assets, ["path", "bytes", "sha256", "group_evidence_to_review", "rights_status"])
    missing_links = []
    for name in ENTRY_DOCS:
        path = ROOT / name
        if not path.exists():
            missing_links.append({"document": name, "target": "document missing"})
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[a-z]+://", target):
                continue
            resolved = path.parent / unquote(target)
            if not resolved.exists():
                missing_links.append({"document": name, "target": target})
    history_findings = []
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    scanned_blobs = 0
    for row in objects:
        oid, _, name = row.partition(" ")
        if not name or git("cat-file", "-t", oid).strip() != b"blob":
            continue
        data = git("cat-file", "blob", oid)
        if b"\0" in data:
            continue
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        scanned_blobs += 1
        history_findings.extend(dict(item, object=oid) for item in findings(name, content))
    report = {"candidate_files": len(inventory), "proposed_changes": len(changes), "assets": len(assets),
              "uncleared_images": [row["path"] for row in assets if row["rights_status"].startswith("pending")],
              "missing_entry_links": missing_links, "python_syntax_errors": syntax,
              "candidate_privacy_findings": privacy, "history_blobs_scanned": scanned_blobs,
              "history_privacy_findings": history_findings,
              "large_files_over_50_MiB": [r["path"] for r in inventory if r["bytes"] > 50 * 1024**2]}
    (OUT / "candidate-manifest.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
