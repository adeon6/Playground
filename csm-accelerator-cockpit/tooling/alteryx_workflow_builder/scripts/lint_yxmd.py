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

from capability_registry import load_capability_registry, plugin_to_op_map, resolve_profile

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\[^\s\"'<>]+"),
    re.compile(r"/(?:Users|home|var|tmp)/[^\s\"'<>]+"),
    re.compile(r"\\\\[^\s\"'<>]+"),
]
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z0-9_]+\}\}")
GENERIC_PLUGIN = "AlteryxBasePluginsGui.ToolContainer.ToolContainer"
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
CORE_PLUGINS_REQUIRE_ENGINE = {
    "AlteryxBasePluginsGui.DbFileInput.DbFileInput",
    "AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect",
    "AlteryxBasePluginsGui.Select.Select",
    "AlteryxBasePluginsGui.Filter.Filter",
    "AlteryxBasePluginsGui.Formula.Formula",
    "AlteryxBasePluginsGui.Summarize.Summarize",
    "AlteryxBasePluginsGui.Join.Join",
    "AlteryxBasePluginsGui.Union.Union",
    "AlteryxBasePluginsGui.Sort.Sort",
    "AlteryxBasePluginsGui.Unique.Unique",
    "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
    "AlteryxBasePluginsGui.DateTime.DateTime",
    "AlteryxBasePluginsGui.TextToColumns.TextToColumns",
    "AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula",
    "AlteryxBasePluginsGui.CrossTab.CrossTab",
    "AlteryxBasePluginsGui.Transpose.Transpose",
    "AlteryxBasePluginsGui.Sample.Sample",
    "AlteryxBasePluginsGui.DataCleanse.DataCleanse",
    "AlteryxBasePluginsGui.RecordID.RecordID",
    "AlteryxBasePluginsGui.BrowseV2.BrowseV2",
}
NON_EXECUTABLE_GUI_PLUGINS = {
    # Layout/annotation-only nodes in starter kits; these are intentionally disconnected.
    "AlteryxGuiToolkit.TextBox.TextBox",
    "AlteryxGuiToolkit.HtmlBox.HtmlBox",
}
IMPLICIT_DISCONNECTED_OK_PLUGINS = {
    # Starter-kit output tools can be intentionally dependency-driven without
    # explicit Connection edges in the workflow XML.
    "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
}


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
    """Validate canonical connection endpoints and collect graph stats."""
    errors: list[str] = []
    incoming: dict[str, int] = {tid: 0 for tid in tool_ids}
    outgoing: dict[str, int] = {tid: 0 for tid in tool_ids}

    for conn in root.findall(".//Connections/Connection"):
        origin = conn.find("./Origin")
        dest = conn.find("./Destination")

        if origin is None or dest is None:
            errors.append("Connection must use canonical Origin/Destination child nodes")
            continue

        from_id = origin.attrib.get("ToolID", "")
        to_id = dest.attrib.get("ToolID", "")
        if from_id and from_id not in tool_ids:
            errors.append(f"Connection references missing Origin ToolID={from_id}")
        if to_id and to_id not in tool_ids:
            errors.append(f"Connection references missing Destination ToolID={to_id}")

        if from_id in outgoing:
            outgoing[from_id] += 1
        if to_id in incoming:
            incoming[to_id] += 1

    return errors, incoming, outgoing


def _profile_version(registry: dict[str, Any], profile: str) -> str:
    profiles = registry.get("profiles") or {}
    if not isinstance(profiles, dict):
        return profile
    entry = profiles.get(profile, {})
    if not isinstance(entry, dict):
        return profile
    return str(entry.get("designer_version", profile))


def _mode_for_workflow(path: Path, mode_arg: str) -> str:
    if mode_arg in {"starter_kit", "demo"}:
        return mode_arg
    lowered = str(path).lower()
    return "starter_kit" if ("office_of_finance_ai_starter_kits" in lowered or "starter kits" in lowered) else "demo"


def _tier2_semantic_checks(root: ET.Element, plugin_map: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for node in root.findall(".//Node"):
        tool_id = node.attrib.get("ToolID", "")
        gs = node.find("./GuiSettings")
        plugin = gs.attrib.get("Plugin", "") if gs is not None else ""
        cfg = node.find("./Properties/Configuration")

        if plugin == GENERIC_PLUGIN:
            op_name = ""
            if cfg is not None:
                op_name = (cfg.findtext("./Operation") or "").strip()
            if op_name in TIER2_OPS:
                errors.append(f"ToolID={tool_id}: tier-2 op '{op_name}' emitted through generic fallback")
            continue

        op = plugin_map.get(plugin, "")
        if op not in TIER2_OPS:
            continue

        if cfg is None:
            errors.append(f"ToolID={tool_id}: missing Configuration for tier-2 op '{op}'")
            continue

        if op == "datetime":
            transforms = cfg.findall("./Transformations/Transformation")
            legacy_ok = bool((cfg.findtext("./InputFieldName") or "").strip()) and bool((cfg.findtext("./OutputFieldName") or "").strip())
            if not transforms and not legacy_ok:
                errors.append(f"ToolID={tool_id}: datetime requires at least one Transformations/Transformation entry")
        elif op == "text_to_columns":
            if not (cfg.findtext("./Field") or "").strip():
                errors.append(f"ToolID={tool_id}: text_to_columns missing Configuration/Field")
            has_delimiter = cfg.find("./Delimiter") is not None or cfg.find("./Delimeters") is not None
            if not has_delimiter:
                errors.append(f"ToolID={tool_id}: text_to_columns missing Configuration/Delimiter")
        elif op == "multi_row_formula":
            field_name = (cfg.findtext("./Field") or cfg.findtext("./UpdateField_Name") or "").strip()
            if not field_name:
                errors.append(f"ToolID={tool_id}: multi_row_formula missing Configuration/Field")
            if not (cfg.findtext("./Expression") or "").strip():
                errors.append(f"ToolID={tool_id}: multi_row_formula missing Configuration/Expression")
        elif op == "cross_tab":
            has_groups = bool(cfg.findall("./GroupBy/Group")) or cfg.find("./GroupFields") is not None
            if not has_groups:
                errors.append(f"ToolID={tool_id}: cross_tab requires GroupBy entries")
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
            if not header_ok:
                errors.append(f"ToolID={tool_id}: cross_tab missing Configuration/HeaderField")
            if not data_ok:
                errors.append(f"ToolID={tool_id}: cross_tab missing Configuration/DataField")
            if not method:
                errors.append(f"ToolID={tool_id}: cross_tab missing Configuration/Method")
        elif op == "transpose":
            if not cfg.findall("./KeyFields/Key"):
                errors.append(f"ToolID={tool_id}: transpose requires KeyFields/Key entries")
            if not cfg.findall("./DataFields/Data"):
                errors.append(f"ToolID={tool_id}: transpose requires DataFields/Data entries")
        elif op == "sample":
            mode = (cfg.findtext("./Mode") or "").strip()
            if not mode:
                errors.append(f"ToolID={tool_id}: sample missing Configuration/Mode")
            if mode in {"first_n", "random_n"} and not (cfg.findtext("./Value") or "").strip():
                errors.append(f"ToolID={tool_id}: sample mode '{mode}' requires Configuration/Value")
        elif op == "data_cleansing":
            if not cfg.findall("./Fields/Field"):
                errors.append(f"ToolID={tool_id}: data_cleansing requires Fields/Field entries")
            has_option_bag = bool(cfg.findall("./Options/Option"))
            has_classic_config = all(
                cfg.find(f"./{tag}") is not None
                for tag in (
                    "RemoveNullRows",
                    "RemoveNullColumns",
                    "RemoveTabsLineBreaksAndDuplicates",
                    "RemoveLeadingAndTrailingWhitespace",
                    "RemoveAllWhitespaces",
                    "RemoveHTMLTags",
                    "RemoveInvisibleCharacters",
                    "RemoveLetters",
                    "RemoveNumbers",
                    "RemovePunctuation",
                    "Letters",
                    "Numbers",
                    "Punctuations",
                    "Exceptions",
                    "Checkbox_ReplaceStringColumns",
                    "Checkbox_ReplaceNumericColumns",
                    "radioButton_ReplaceNullwithBlanks",
                    "radioButton_ReplaceBlankswithNulls",
                    "radioButton_ReplaceNullwithZero",
                    "radioButton_ReplaceZerowithNulls",
                    "ReplaceWithBlanks",
                    "ReplaceWithZero",
                    "CheckBox_ModifyCase",
                    "ModifyCase",
                )
            )
            if not has_option_bag and not has_classic_config:
                errors.append(
                    f"ToolID={tool_id}: data_cleansing requires either Options/Option entries or classic Data Cleanse tags"
                )
        elif op == "record_id":
            if not (cfg.findtext("./FieldName") or "").strip():
                errors.append(f"ToolID={tool_id}: record_id missing Configuration/FieldName")

    return errors


def _all_plugin_map(registry: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    ops = registry.get("ops") or {}
    if not isinstance(ops, dict):
        return out
    for op, capability in ops.items():
        if not isinstance(capability, dict):
            continue
        plugin = str(capability.get("plugin", "")).strip()
        if plugin:
            out[plugin] = op
        for alias in capability.get("plugin_aliases") or []:
            alias_text = str(alias).strip()
            if alias_text:
                out[alias_text] = op
    return out


def _profile_availability_checks(root: ET.Element, profile: str, registry: dict[str, Any]) -> list[str]:
    """Ensure plugins in workflow are available in selected profile."""
    errors: list[str] = []
    ops = registry.get("ops") or {}
    all_plugins = _all_plugin_map(registry)

    for node in root.findall(".//Node"):
        tool_id = node.attrib.get("ToolID", "")
        gs = node.find("./GuiSettings")
        plugin = gs.attrib.get("Plugin", "") if gs is not None else ""
        op = all_plugins.get(plugin)
        if not op:
            continue

        capability = ops.get(op, {})
        availability = capability.get("availability") or []
        if profile not in availability:
            errors.append(
                f"ToolID={tool_id}: plugin '{plugin}' maps to op '{op}' unavailable in designer_profile={profile}"
            )

    return errors


def lint_workflow(
    path: Path,
    expected_version: str | None,
    designer_profile: str,
    capability_registry: dict[str, Any],
    mode: str,
) -> FileReport:
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

    for node in root.findall(".//Node"):
        tool_id = node.attrib.get("ToolID", "")
        gs = node.find("./GuiSettings")
        if gs is None:
            result.errors.append(f"ToolID={tool_id}: missing GuiSettings")
            continue
        plugin = gs.attrib.get("Plugin", "").strip()
        engine = node.find("./EngineSettings")
        macro_path = (engine.attrib.get("Macro", "").strip() if engine is not None else "")
        if not plugin:
            if macro_path:
                plugin = "<macro-backed-empty-plugin>"
            else:
                result.errors.append(f"ToolID={tool_id}: GuiSettings Plugin is empty")
                continue
        if macro_path:
            normalized = macro_path.replace("\\", "/")
            if not normalized.lower().endswith(".yxmc"):
                result.errors.append(f"ToolID={tool_id}: macro path must end with .yxmc, got '{macro_path}'")
            if normalized.startswith("/") or normalized.startswith("\\\\") or re.match(r"^[A-Za-z]:[\\/]", macro_path):
                result.errors.append(f"ToolID={tool_id}: macro path must be relative, got '{macro_path}'")
        if plugin in CORE_PLUGINS_REQUIRE_ENGINE:
            if engine is None:
                result.errors.append(f"ToolID={tool_id}: core plugin '{plugin}' missing EngineSettings")
            elif not (engine.attrib.get("EngineDll", "") or engine.attrib.get("Macro", "")):
                result.errors.append(f"ToolID={tool_id}: core plugin '{plugin}' missing EngineSettings EngineDll/Macro")

    tool_ids, duplicates = _collect_tool_ids(root)
    for dup in duplicates:
        result.errors.append(f"Duplicate ToolID detected: {dup}")

    conn_errors, incoming, outgoing = _check_connections(root, tool_ids)
    result.errors.extend(conn_errors)

    plugin_map = plugin_to_op_map(capability_registry, designer_profile)
    result.errors.extend(_profile_availability_checks(root, designer_profile, capability_registry))
    result.errors.extend(_tier2_semantic_checks(root, plugin_map))

    if mode == "starter_kit":
        stem = path.name
        is_toc = stem.startswith("01_")
        for node in root.findall(".//Node"):
            tool_id = node.attrib.get("ToolID", "")
            gs = node.find("./GuiSettings")
            plugin = gs.attrib.get("Plugin", "") if gs is not None else ""
            if "Browse" in plugin and not is_toc:
                result.errors.append(f"ToolID={tool_id}: Browse tool is disallowed in starter_kit mode for non-TOC workflows")
            if "DbFileOutput" in plugin:
                file_elem = node.find("./Properties/Configuration/File")
                out_name = (file_elem.text or "").strip() if file_elem is not None else ""
                out_base = Path(out_name.replace("\\\\", "/")).name.lower() if out_name else ""
                if out_base and not (out_base.startswith("customgpt_") or re.match(r"^\d{2}_", out_base)):
                    result.errors.append(f"ToolID={tool_id}: starter_kit mode requires deterministic output naming, got '{out_base}'")

    plugin_by_tool_id: dict[str, str] = {}
    for node in root.findall(".//Node"):
        tid = node.attrib.get("ToolID", "")
        if not tid:
            continue
        gs = node.find("./GuiSettings")
        plugin_by_tool_id[tid] = gs.attrib.get("Plugin", "") if gs is not None else ""

    disconnected: list[str] = []
    for tid in sorted(tool_ids):
        if incoming.get(tid, 0) != 0 or outgoing.get(tid, 0) != 0:
            continue
        plugin = plugin_by_tool_id.get(tid, "")
        if plugin in NON_EXECUTABLE_GUI_PLUGINS:
            continue
        node = root.find(f".//Node[@ToolID='{tid}']")
        deps = node.find("./Properties/Dependencies/Implicit") if node is not None else None
        if plugin in IMPLICIT_DISCONNECTED_OK_PLUGINS and deps is not None:
            continue
        # ToolContainer is often decorative, but if it carries a macro path then it is executable
        # and must not be treated as ignorable disconnected UI.
        if plugin == "AlteryxGuiToolkit.ToolContainer.ToolContainer":
            engine = node.find("./EngineSettings") if node is not None else None
            macro_path = (engine.attrib.get("Macro", "").strip() if engine is not None else "")
            if not macro_path:
                continue
        disconnected.append(tid)
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
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Static lint for Alteryx .yxmd files")
    parser.add_argument("paths", nargs="+", type=Path, help="Workflow file(s) or directory path(s)")
    parser.add_argument("--expected-version", default=None, help="Expected yxmdVer (e.g., 2025.2)")
    parser.add_argument("--designer-profile", default=None, choices=["2025.1", "2025.2"], help="Capability profile")
    parser.add_argument("--mode", default="auto", choices=["auto", "starter_kit", "demo"], help="Governance mode")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan directories")
    parser.add_argument("--report", type=Path, default=None, help="Optional output JSON report path")
    parser.add_argument(
        "--capability-registry",
        type=Path,
        default=root / "references" / "capability_registry.json",
        help="Capability registry JSON path",
    )
    return parser.parse_args()


def main() -> int:
    """Run linting workflow."""
    args = parse_args()
    workflows = discover_workflows(paths=args.paths, recursive=args.recursive)
    if not workflows:
        print("No .yxmd files found.")
        return 1

    capability_registry = load_capability_registry(args.capability_registry)
    designer_profile = resolve_profile(capability_registry, args.designer_profile, args.expected_version)
    expected_version = args.expected_version or _profile_version(capability_registry, designer_profile)

    reports = [
        lint_workflow(
            path=wf,
            expected_version=expected_version,
            designer_profile=designer_profile,
            capability_registry=capability_registry,
            mode=_mode_for_workflow(wf, args.mode),
        )
        for wf in workflows
    ]
    summary = summarize(reports)

    payload = {
        "summary": summary,
        "designer_profile": designer_profile,
        "expected_version": expected_version,
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
