#!/usr/bin/env python3
"""Index a Weekly Challenge corpus of .yxmd files for tool-coverage analysis."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from capability_registry import load_capability_registry, plugin_to_op_map, resolve_profile


def discover_workflows(root: Path) -> list[Path]:
    return sorted(p.resolve() for p in root.rglob("*.yxmd") if p.is_file())


def profile_for_root(root: ET.Element, registry: dict[str, Any]) -> str:
    version = (root.get("yxmdVer") or "").strip()
    return resolve_profile(registry, version, version or "2025.2")


def index_one(path: Path, registry: dict[str, Any]) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    profile = profile_for_root(root, registry)
    plugin_map = plugin_to_op_map(registry, profile)

    plugins: list[str] = []
    ops: list[str] = []
    for node in root.findall(".//Nodes/Node"):
        gs = node.find("./GuiSettings")
        plugin = gs.attrib.get("Plugin", "") if gs is not None else ""
        if not plugin:
            continue
        plugins.append(plugin)
        op = plugin_map.get(plugin)
        if op:
            ops.append(op)

    counts = Counter(ops)
    return {
        "workflow": str(path),
        "yxmdVer": root.get("yxmdVer", ""),
        "designer_profile": profile,
        "tool_count": len(plugins),
        "recognized_op_counts": dict(sorted(counts.items())),
        "plugins": sorted(set(plugins)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index Weekly Challenge corpus by plugin/op coverage")
    parser.add_argument("--root", type=Path, required=True, help="Root directory containing challenge workflows")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("references/corpus/weekly_challenge_manifest.json"),
        help="Output manifest JSON path",
    )
    parser.add_argument(
        "--capability-registry",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "capability_registry.json",
        help="Capability registry JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.root.exists():
        print(f"ERROR: root path does not exist: {args.root}")
        return 2

    registry = load_capability_registry(args.capability_registry)
    workflows = discover_workflows(args.root)

    indexed = [index_one(path, registry) for path in workflows]
    aggregate = Counter()
    for row in indexed:
        aggregate.update(row["recognized_op_counts"])

    payload = {
        "root": str(args.root.resolve()),
        "workflow_count": len(indexed),
        "aggregate_recognized_op_counts": dict(sorted(aggregate.items())),
        "workflows": indexed,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
