#!/usr/bin/env python3
"""Static sanity checks for golden and base workflow assets."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_PATHS = [
    Path("golden/workflow_01.yxmd"),
    Path("golden/workflow_02.yxmd"),
    Path("templates/base.yxmd"),
]


def _is_absolute_windows(path_value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", path_value))


def _normalize_relative_path(raw: str) -> str:
    # Preserve relative semantics while handling Windows separators.
    text = raw.strip().replace("\\", "/")
    if text.startswith("./"):
        return text[2:]
    if text.startswith(".//"):
        return text[3:]
    return text


def check_one(path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        return {"path": str(path), "errors": [f"XML parse failed: {exc}"], "warnings": []}

    nodes = root.findall(".//Nodes/Node")
    for node in nodes:
        tool_id = node.attrib.get("ToolID", "")
        gs = node.find("./GuiSettings")
        if gs is None:
            errors.append(f"ToolID={tool_id}: missing GuiSettings")
            continue

        plugin = (gs.attrib.get("Plugin", "") or "").strip()
        if not plugin:
            errors.append(f"ToolID={tool_id}: GuiSettings Plugin is empty")

        engine = node.find("./EngineSettings")
        if engine is not None and engine.attrib.get("Macro"):
            macro_path = (engine.attrib.get("Macro") or "").strip()
            normalized = macro_path.replace("\\", "/")
            if not normalized.lower().endswith(".yxmc"):
                errors.append(f"ToolID={tool_id}: macro path must end with .yxmc, got '{macro_path}'")
            if normalized.startswith("/") or normalized.startswith("//") or _is_absolute_windows(macro_path):
                errors.append(f"ToolID={tool_id}: macro path must be relative, got '{macro_path}'")

        if "HtmlBox" in plugin:
            url = (node.findtext("./Properties/Configuration/URL") or "").strip()
            if not url:
                errors.append(f"ToolID={tool_id}: HtmlBox missing Configuration/URL")
            else:
                rel = _normalize_relative_path(url)
                target = (path.parent / rel).resolve()
                if not target.exists():
                    errors.append(f"ToolID={tool_id}: HtmlBox URL target not found: {url}")

    for conn in root.findall(".//Connections/Connection"):
        if conn.find("./Origin") is None or conn.find("./Destination") is None:
            errors.append("Connection must use canonical Origin/Destination child nodes")

    if root.get("yxmdVer", "") not in {"2025.1", "2025.2"}:
        warnings.append(f"Unexpected yxmdVer={root.get('yxmdVer', '')}")

    return {
        "path": str(path),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Golden/base workflow sanity checks")
    parser.add_argument("paths", nargs="*", type=Path, help="Paths to .yxmd files")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    paths = [p.resolve() for p in args.paths] if args.paths else [(root / p).resolve() for p in DEFAULT_PATHS]
    reports = []
    for path in paths:
        if not path.exists():
            reports.append({"path": str(path), "errors": ["file not found"], "warnings": []})
            continue
        reports.append(check_one(path))

    total_errors = sum(len(r["errors"]) for r in reports)
    payload = {
        "status": "PASS" if total_errors == 0 else "FAIL",
        "error_count": total_errors,
        "reports": reports,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")

    print(json.dumps({"status": payload["status"], "error_count": payload["error_count"]}, indent=2))
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
