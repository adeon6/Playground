#!/usr/bin/env python3
"""Static linter for Alteryx .yxmd workflows.

Runs fast XML and content checks that do not require Alteryx Designer runtime.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\[^\s\"'<>]+"),
    re.compile(r"/(?:Users|home|var|tmp)/[^\s\"'<>]+"),
    re.compile(r"\\\\[^\s\"'<>]+"),
]
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z0-9_]+\}\}")


@dataclass
class FileReport:
    """Per-file lint results."""

    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)



def discover_workflows(paths: list[Path], recursive: bool) -> list[Path]:
    """Collect workflow files from files/directories."""
    found: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".yxmd":
            found.add(path.resolve())
            continue

        if path.is_dir():
            iterator = path.rglob("*.yxmd") if recursive else path.glob("*.yxmd")
            for wf in iterator:
                if wf.is_file():
                    found.add(wf.resolve())

    return sorted(found)



def _collect_tool_ids(root: ET.Element) -> tuple[set[str], list[str]]:
    """Return tool IDs and duplicate ID warnings."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for node in root.findall(".//Node"):
        tid = node.attrib.get("ToolID")
        if not tid:
            continue
        if tid in seen:
            duplicates.append(tid)
        seen.add(tid)
    return seen, duplicates



def _check_connections(root: ET.Element, tool_ids: set[str]) -> tuple[list[str], dict[str, int], dict[str, int]]:
    """Validate connection endpoints and collect graph stats."""
    errors: list[str] = []
    incoming: dict[str, int] = {tid: 0 for tid in tool_ids}
    outgoing: dict[str, int] = {tid: 0 for tid in tool_ids}

    for conn in root.findall(".//Connections/Connection"):
        origin = conn.find("./Origin")
        destination = conn.find("./Destination")

        if origin is not None and destination is not None:
            from_id = origin.attrib.get("ToolID", "")
            to_id = destination.attrib.get("ToolID", "")
        else:
            from_id = conn.attrib.get("FromToolID", "")
            to_id = conn.attrib.get("ToToolID", "")

        if not from_id or not to_id:
            errors.append("Connection is missing Origin/Destination or FromToolID/ToToolID metadata")
            continue

        if from_id and from_id not in tool_ids:
            errors.append(f"Connection references missing FromToolID={from_id}")
        if to_id and to_id not in tool_ids:
            errors.append(f"Connection references missing ToToolID={to_id}")

        if from_id in outgoing:
            outgoing[from_id] += 1
        if to_id in incoming:
            incoming[to_id] += 1

    return errors, incoming, outgoing



def lint_workflow(path: Path, expected_version: str | None) -> FileReport:
    """Lint one workflow file."""
    result = FileReport(path=str(path))

    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = path.read_text(encoding="latin-1")
        result.warnings.append("File is not UTF-8 encoded; read with latin-1 fallback")

    if PLACEHOLDER_PATTERN.search(raw_text):
        result.errors.append("Unresolved template placeholder found ({{TOKEN}})")

    for pattern in ABSOLUTE_PATH_PATTERNS:
        for match in pattern.findall(raw_text):
            match_text = match if isinstance(match, str) else "".join(match)
            if match_text:
                result.warnings.append(f"Potential absolute path reference found: {match_text}")

    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError as exc:
        result.errors.append(f"XML parse error: {exc}")
        return result

    yxmd_ver = root.attrib.get("yxmdVer", "")
    if expected_version and yxmd_ver != expected_version:
        result.errors.append(f"yxmdVer is '{yxmd_ver}', expected '{expected_version}'")

    if root.find("./Properties") is None:
        result.errors.append("Workflow is missing top-level Properties block")

    for node in root.findall(".//Nodes/Node"):
        tid = node.attrib.get("ToolID", "<missing>")
        gui = node.find("./GuiSettings")
        if gui is None:
            result.errors.append(f"Node {tid} is missing GuiSettings")
            continue
        if gui.find("./Position") is None:
            result.errors.append(f"Node {tid} GuiSettings is missing nested Position element")

    tool_ids, duplicates = _collect_tool_ids(root)
    for dup in duplicates:
        result.errors.append(f"Duplicate ToolID detected: {dup}")

    conn_errors, incoming, outgoing = _check_connections(root, tool_ids)
    result.errors.extend(conn_errors)

    disconnected = sorted(tid for tid in tool_ids if incoming.get(tid, 0) == 0 and outgoing.get(tid, 0) == 0)
    if disconnected:
        result.warnings.append(
            f"Disconnected tools detected: {', '.join(disconnected[:20])}"
            + (" ..." if len(disconnected) > 20 else "")
        )

    return result



def summarize(reports: list[FileReport]) -> dict[str, Any]:
    """Build aggregate summary."""
    workflows = len(reports)
    errors = sum(len(r.errors) for r in reports)
    warnings = sum(len(r.warnings) for r in reports)
    errored_files = sum(1 for r in reports if r.errors)
    warned_files = sum(1 for r in reports if r.warnings)
    clean_files = workflows - len({r.path for r in reports if r.errors or r.warnings})

    return {
        "workflows": workflows,
        "files_with_errors": errored_files,
        "files_with_warnings": warned_files,
        "clean_files": clean_files,
        "total_errors": errors,
        "total_warnings": warnings,
    }



def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description="Static lint for Alteryx .yxmd files")
    parser.add_argument("paths", nargs="+", type=Path, help="Workflow file(s) or directory path(s)")
    parser.add_argument("--expected-version", default=None, help="Expected yxmdVer (e.g., 2025.1)")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan directories")
    parser.add_argument("--report", type=Path, default=None, help="Optional output JSON report path")
    return parser.parse_args()



def main() -> int:
    """Run linting workflow."""
    args = parse_args()
    workflows = discover_workflows(paths=args.paths, recursive=args.recursive)
    if not workflows:
        print("No .yxmd files found.")
        return 1

    reports = [lint_workflow(path=wf, expected_version=args.expected_version) for wf in workflows]
    summary = summarize(reports)

    payload = {
        "summary": summary,
        "reports": [
            {
                "path": r.path,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in reports
        ],
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote report: {args.report}")

    print(json.dumps(summary, indent=2))

    return 1 if summary["files_with_errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
