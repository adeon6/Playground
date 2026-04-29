#!/usr/bin/env python3
"""Extract normalized tool signatures from workflow XML files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from capability_registry import load_capability_registry, plugin_to_op_map, resolve_profile

TIER2_OPS = {
    "datetime",
    "text_to_columns",
    "multi_row_formula",
    "cross_tab",
    "transpose",
    "sample",
    "data_cleansing",
    "record_id",
    "browse",
}
GENERIC_PLUGIN = "AlteryxBasePluginsGui.ToolContainer.ToolContainer"


def _profile_for_workflow(root: ET.Element, registry: dict[str, Any], default_profile: str = "2025.2") -> str:
    version = (root.get("yxmdVer") or "").strip()
    return resolve_profile(registry, version, version or default_profile)


def _config_keys(cfg: ET.Element | None) -> list[str]:
    if cfg is None:
        return []
    return sorted({child.tag for child in cfg})


def _required_ok(op: str, cfg: ET.Element | None) -> bool:
    if cfg is None:
        return False

    if op == "datetime":
        transforms = cfg.findall("./Transformations/Transformation")
        legacy_ok = bool((cfg.findtext("./InputFieldName") or "").strip()) and bool((cfg.findtext("./OutputFieldName") or "").strip())
        return bool(transforms) or legacy_ok
    if op == "text_to_columns":
        has_delimiter = cfg.find("./Delimiter") is not None or cfg.find("./Delimeters") is not None
        return bool((cfg.findtext("./Field") or "").strip()) and has_delimiter
    if op == "multi_row_formula":
        field_name = (cfg.findtext("./Field") or cfg.findtext("./UpdateField_Name") or "").strip()
        return bool(field_name) and bool((cfg.findtext("./Expression") or "").strip())
    if op == "cross_tab":
        has_groups = bool(cfg.findall("./GroupBy/Group")) or cfg.find("./GroupFields") is not None
        header = cfg.find("./HeaderField")
        data = cfg.find("./DataField")
        method = (cfg.findtext("./Method") or cfg.findtext("./Methods") or "").strip()
        if not method:
            method_el = cfg.find("./Methods/Method")
            if method_el is not None:
                method = (method_el.attrib.get("method", "") or "").strip()
        header_ok = bool((header.text or "").strip()) if header is not None else False
        if header is not None and not header_ok:
            header_ok = bool((header.attrib.get("field", "") or "").strip())
        data_ok = bool((data.text or "").strip()) if data is not None else False
        if data is not None and not data_ok:
            data_ok = bool((data.attrib.get("field", "") or "").strip())
        return has_groups and header_ok and data_ok and bool(method)
    if op == "transpose":
        return bool(cfg.findall("./KeyFields/Key")) and bool(cfg.findall("./DataFields/Data"))
    if op == "sample":
        mode = (cfg.findtext("./Mode") or "").strip()
        if not mode:
            return False
        if mode in {"first_n", "random_n"}:
            return bool((cfg.findtext("./Value") or "").strip())
        return True
    if op == "data_cleansing":
        return bool(cfg.findall("./Fields/Field")) and bool(cfg.findall("./Options/Option"))
    if op == "record_id":
        return bool((cfg.findtext("./FieldName") or "").strip())
    if op == "browse":
        return True
    return True


def extract_signatures(workflow_path: Path, capability_registry: dict[str, Any]) -> dict[str, Any]:
    root = ET.parse(workflow_path).getroot()
    profile = _profile_for_workflow(root, capability_registry)
    plugin_map = plugin_to_op_map(capability_registry, profile)

    signatures: list[dict[str, Any]] = []
    for node in root.findall(".//Nodes/Node"):
        tool_id = node.attrib.get("ToolID", "")
        gs = node.find("./GuiSettings")
        plugin = gs.attrib.get("Plugin", "") if gs is not None else ""
        cfg = node.find("./Properties/Configuration")
        engine = node.find("./EngineSettings")
        op = plugin_map.get(plugin, "")

        generic_operation = ""
        if plugin == GENERIC_PLUGIN and cfg is not None:
            generic_operation = (cfg.findtext("./Operation") or "").strip()
            op = generic_operation or op

        if op not in TIER2_OPS:
            continue

        signatures.append(
            {
                "tool_id": tool_id,
                "op": op,
                "plugin": plugin,
                "engine_entrypoint": (engine.attrib.get("EngineDllEntryPoint", "") if engine is not None else ""),
                "config_keys": _config_keys(cfg),
                "required_semantics_ok": _required_ok(op, cfg),
                "generic_fallback": plugin == GENERIC_PLUGIN,
                "generic_operation": generic_operation,
            }
        )

    signatures.sort(key=lambda item: (item["op"], item["tool_id"]))
    return {
        "workflow": str(workflow_path),
        "profile": profile,
        "yxmdVer": root.get("yxmdVer", ""),
        "tier2_signatures": signatures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract normalized tier-2 tool signatures from workflow XML")
    parser.add_argument("workflows", nargs="+", type=Path, help="Workflow file paths")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    parser.add_argument(
        "--capability-registry",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "capability_registry.json",
        help="Capability registry JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    capability_registry = load_capability_registry(args.capability_registry)

    payload = {
        "workflows": [
            extract_signatures(path.resolve(), capability_registry)
            for path in args.workflows
            if path.exists() and path.suffix.lower() == ".yxmd"
        ]
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
