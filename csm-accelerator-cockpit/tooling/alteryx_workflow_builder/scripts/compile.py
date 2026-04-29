#!/usr/bin/env python3
"""Compile workflow_spec JSON into a deterministic Alteryx-like .yxmd XML document."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import xml.etree.ElementTree as ET

from capability_registry import get_capability, load_capability_registry, resolve_profile
from validate_spec import load_json, validate_spec_document

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

INPUT_OPS = {"csv_input", "file_input", "db_input"}
OUTPUT_OPS = {"output_file", "output_db"}
SUPPORTED_MODES = {"starter_kit", "demo"}
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

TEMPLATE_MAP = {
    "csv_input": "input_data.xml",
    "file_input": "input_data.xml",
    "db_input": "input_data.xml",
    "select": "select.xml",
    "cleanse": "formula.xml",
    "formula": "formula.xml",
    "filter": "filter.xml",
    "join": "join.xml",
    "union": "union.xml",
    "summarize": "summarize.xml",
    "sort": "sort.xml",
    "unique": "unique.xml",
    "output_file": "output_data.xml",
    "output_db": "output_data.xml",
    "macro_call": "generic.xml",
    "python_script": "generic.xml",
    "datetime": "datetime.xml",
    "text_to_columns": "text_to_columns.xml",
    "multi_row_formula": "multi_row_formula.xml",
    "cross_tab": "cross_tab.xml",
    "transpose": "transpose.xml",
    "sample": "sample.xml",
    "data_cleansing": "data_cleansing.xml",
    "record_id": "record_id.xml",
    "browse": "browse.xml",
}

DEFAULT_X_STEP = 220
DEFAULT_Y_STEP = 120
DEFAULT_DESIGNER_VERSION = "2025.2"
DEFAULT_MODE = "demo"
DESIGNER_VERSION_RE = re.compile(r"^\d{4}\.\d+$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass
class ToolNode:
    """Internal representation of a workflow node."""

    key: str
    tool_id: int
    op: str
    template_name: str
    x: int
    y: int
    label: str
    args: dict[str, Any]
    plugin: str
    engine_dll: str
    engine_entrypoint: str
    support_state: str
    profile_available: bool


@dataclass
class Connection:
    """Internal representation of a connection between two nodes."""

    from_id: int
    from_anchor: str
    to_id: int
    to_anchor: str


def deterministic_tool_id(identifier: str, used: set[int]) -> int:
    """Build a stable numeric tool ID from a string identifier."""
    digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest()
    candidate = (int(digest[:8], 16) % 900000) + 1000
    while candidate in used:
        candidate += 1
        if candidate > 999999:
            candidate = 1000
    used.add(candidate)
    return candidate


def xml_safe(value: Any) -> str:
    """Escape text for safe XML embedding."""
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def normalize_designer_settings(
    spec_doc: dict[str, Any],
    capability_registry: dict[str, Any],
    report: dict[str, Any],
    designer_profile_override: str | None = None,
    designer_version_override: str | None = None,
) -> tuple[str, str]:
    """Resolve designer version and profile with compatibility defaults."""
    metadata = spec_doc.get("metadata", {})
    if not isinstance(metadata, dict):
        report["warnings"].append(
            "metadata is not an object; defaulting to profile=2025.2, yxmdVer=2025.2"
        )
        base_profile = designer_profile_override or DEFAULT_DESIGNER_VERSION
        base_version = designer_version_override or DEFAULT_DESIGNER_VERSION
        return base_version, base_profile

    raw_profile = (designer_profile_override or str(metadata.get("designer_profile", "")).strip()).strip()
    raw_version = (designer_version_override or str(metadata.get("designer_version", "")).strip()).strip()

    designer_profile = resolve_profile(capability_registry, raw_profile, raw_version)
    profiles = capability_registry.get("profiles", {})
    profile_entry = profiles.get(designer_profile, {}) if isinstance(profiles, dict) else {}
    profile_version = str(profile_entry.get("designer_version", "")).strip() or designer_profile

    if raw_version and not DESIGNER_VERSION_RE.match(raw_version):
        report["warnings"].append(
            f"metadata.designer_version '{raw_version}' is invalid; using profile version {profile_version}"
        )

    if raw_version and DESIGNER_VERSION_RE.match(raw_version) and raw_version != profile_version:
        report["warnings"].append(
            f"designer_profile={designer_profile} implies yxmdVer={profile_version}; ignoring conflicting designer_version={raw_version}"
        )

    return profile_version, designer_profile


def resolve_mode(spec_doc: dict[str, Any], mode_override: str | None, report: dict[str, Any]) -> str:
    """Resolve workflow governance mode from override or metadata."""
    if mode_override and mode_override in SUPPORTED_MODES:
        return mode_override

    metadata = spec_doc.get("metadata", {})
    raw_mode = str(metadata.get("mode", "")).strip()
    if raw_mode in SUPPORTED_MODES:
        return raw_mode

    if raw_mode:
        report["warnings"].append(
            f"metadata.mode '{raw_mode}' is invalid; defaulting to {DEFAULT_MODE}"
        )
    return DEFAULT_MODE


def _looks_absolute_path(path_value: str) -> bool:
    """Check whether a path looks machine-specific or absolute."""
    if not path_value:
        return False
    return (
        path_value.startswith("/")
        or path_value.startswith("~/")
        or path_value.startswith("\\\\")
        or bool(WINDOWS_DRIVE_RE.match(path_value))
    )


def path_quality_warnings(op: str, args: dict[str, Any], label: str) -> list[str]:
    """Collect warnings for path and connection safety."""
    warnings: list[str] = []

    raw_path = str(args.get("path", "")).strip()
    if raw_path:
        if _looks_absolute_path(raw_path):
            warnings.append(f"{label}: args.path appears absolute ({raw_path})")
        if len(raw_path) > 120:
            warnings.append(
                f"{label}: args.path length {len(raw_path)} may cause Windows path issues"
            )

    if op in {"db_input", "output_db"}:
        connection = str(args.get("connection", "")).strip()
        if connection and "password=" in connection.lower():
            warnings.append(f"{label}: connection string appears to contain inline credentials")

    return warnings


def render_template(template_text: str, replacements: dict[str, str]) -> tuple[str, list[str]]:
    """Replace placeholders and report unresolved placeholder names."""
    unresolved: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in replacements:
            unresolved.append(token)
            return ""
        return replacements[token]

    rendered = PLACEHOLDER_RE.sub(_replace, template_text)
    return rendered, unresolved


def read_template(templates_dir: Path, template_name: str) -> tuple[str, bool]:
    """Load template content from disk and report whether generic fallback was used."""
    path = templates_dir / template_name
    if not path.exists():
        fallback = templates_dir / "generic.xml"
        if not fallback.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        return fallback.read_text(encoding="utf-8"), True
    return path.read_text(encoding="utf-8"), False


def _field_xml(fields: list[Any]) -> str:
    lines: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            name = xml_safe(field.get("name", ""))
            selected = "True" if field.get("selected", True) else "False"
            rename = xml_safe(field.get("rename", ""))
        else:
            name = xml_safe(field)
            selected = "True"
            rename = ""
        lines.append(f'<Field name="{name}" selected="{selected}" rename="{rename}" />')
    return "\n        ".join(lines)


def _formula_xml(args: dict[str, Any]) -> str:
    formulas: list[dict[str, Any]]
    if isinstance(args.get("formulas"), list):
        formulas = [f for f in args["formulas"] if isinstance(f, dict)]
    else:
        formulas = [
            {
                "field": args.get("field", ""),
                "expression": args.get("expression", ""),
                "type": args.get("type", "V_WString"),
            }
        ]

    lines: list[str] = []
    for formula in formulas:
        field = xml_safe(formula.get("field", ""))
        expression = xml_safe(formula.get("expression", ""))
        dtype = xml_safe(formula.get("type", "V_WString"))
        size = xml_safe(formula.get("size", 255))
        lines.append(
            f'<FormulaField field="{field}" type="{dtype}" size="{size}" expression="{expression}" />'
        )
    return "\n        ".join(lines)


def _summarize_group_xml(group_by: list[Any]) -> str:
    lines = [f'<Group field="{xml_safe(name)}" />' for name in group_by]
    return "\n        ".join(lines)


def _summarize_agg_xml(aggregations: list[Any]) -> str:
    lines: list[str] = []
    for agg in aggregations:
        if isinstance(agg, dict):
            field = xml_safe(agg.get("field", ""))
            action = xml_safe(agg.get("action", ""))
            out_name = xml_safe(agg.get("as", ""))
        else:
            field = xml_safe(agg)
            action = "Count"
            out_name = ""
        lines.append(
            f'<Aggregate field="{field}" action="{action}" as="{out_name}" />'
        )
    return "\n        ".join(lines)


def _summarize_fields_xml(group_by: list[Any], aggregations: list[Any]) -> str:
    """Build Designer-native SummarizeFields configuration."""
    lines: list[str] = []
    for name in group_by:
        field = xml_safe(name)
        lines.append(f'<SummarizeField field="{field}" action="GroupBy" rename="{field}" />')

    action_map = {
        "Average": "Avg",
        "average": "Avg",
        "avg": "Avg",
        "count": "Count",
        "sum": "Sum",
    }
    for agg in aggregations:
        if isinstance(agg, dict):
            field = xml_safe(agg.get("field", ""))
            raw_action = str(agg.get("action", ""))
            action = xml_safe(action_map.get(raw_action, raw_action))
            out_name = xml_safe(agg.get("as", "") or agg.get("rename", "") or field)
        else:
            field = xml_safe(agg)
            action = "Count"
            out_name = field
        lines.append(
            f'<SummarizeField field="{field}" action="{action}" rename="{out_name}" />'
        )
    return "\n        ".join(lines)


def _generic_args_xml(args: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in sorted(args.keys()):
        value = args[key]
        lines.append(f'<Arg name="{xml_safe(key)}">{xml_safe(value)}</Arg>')
    return "\n        ".join(lines)


def _datetime_transform_xml(transformations: list[Any]) -> str:
    lines: list[str] = []
    for item in transformations:
        if not isinstance(item, dict):
            continue
        lines.append(
            '<Transformation field="{field}" output_field="{output_field}" operation="{operation}" input_format="{input_format}" output_format="{output_format}" />'.format(
                field=xml_safe(item.get("field", "")),
                output_field=xml_safe(item.get("output_field", "")),
                operation=xml_safe(item.get("operation", "")),
                input_format=xml_safe(item.get("input_format", "")),
                output_format=xml_safe(item.get("output_format", "")),
            )
        )
    return "\n        ".join(lines)


def _cross_tab_group_xml(group_by: list[Any]) -> str:
    return "\n        ".join(f'<Group field="{xml_safe(v)}" />' for v in group_by)


def _transpose_fields_xml(values: list[Any], tag_name: str) -> str:
    return "\n        ".join(f'<{tag_name} field="{xml_safe(v)}" />' for v in values)


def _data_cleansing_fields_xml(fields: list[Any]) -> str:
    lines: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            name = xml_safe(field.get("name", ""))
        else:
            name = xml_safe(field)
        lines.append(f'<Field name="{name}" />')
    return "\n        ".join(lines)


def _data_cleansing_options_xml(args: dict[str, Any]) -> str:
    known = [
        "trim_whitespace",
        "remove_null_rows",
        "remove_punctuation",
        "modify_case",
        "remove_numbers",
    ]
    lines: list[str] = []
    for key in known:
        if key in args:
            lines.append(f'<Option name="{xml_safe(key)}" value="{xml_safe(args.get(key))}" />')
    return "\n        ".join(lines)


def _join_keys_xml(args: dict[str, Any]) -> str:
    pairs = args.get("keys", [])
    if isinstance(pairs, list) and pairs:
        lines: list[str] = []
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            lines.append(
                '<Key left="{left}" right="{right}" />'.format(
                    left=xml_safe(pair.get("left", "")),
                    right=xml_safe(pair.get("right", "")),
                )
            )
        if lines:
            return "\n        ".join(lines)

    left = xml_safe(args.get("left_key", ""))
    right = xml_safe(args.get("right_key", ""))
    if left or right:
        return f'<Key left="{left}" right="{right}" />'
    return ""


def _join_info_xml(args: dict[str, Any]) -> str:
    pairs = args.get("keys", [])
    if isinstance(pairs, list) and pairs:
        left_fields: list[str] = []
        right_fields: list[str] = []
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            left = str(pair.get("left", "")).strip()
            right = str(pair.get("right", "")).strip()
            if left:
                left_fields.append(left)
            if right:
                right_fields.append(right)
    else:
        left_fields = [str(args.get("left_key", "")).strip()] if args.get("left_key") else []
        right_fields = [str(args.get("right_key", "")).strip()] if args.get("right_key") else []

    def fields_xml(values: list[str]) -> str:
        return "\n        ".join(f'<Field field="{xml_safe(value)}" />' for value in values)

    return "\n      ".join(
        [
            '<JoinInfo connection="Left">\n        {fields}\n      </JoinInfo>'.format(
                fields=fields_xml(left_fields)
            ),
            '<JoinInfo connection="Right">\n        {fields}\n      </JoinInfo>'.format(
                fields=fields_xml(right_fields)
            ),
        ]
    )


def _join_select_fields_xml(args: dict[str, Any]) -> str:
    fields = args.get("deselect_right_fields", [])
    if not isinstance(fields, list):
        fields = []
    lines: list[str] = []
    for field in fields:
        name = str(field).strip()
        if not name:
            continue
        right_name = name if name.startswith("Right_") else f"Right_{name}"
        safe_name = xml_safe(right_name)
        lines.append(f'<SelectField field="{safe_name}" selected="False" rename="{safe_name}" />')
    lines.append('<SelectField field="*Unknown" selected="True" />')
    return "\n            ".join(lines)


def _sort_fields_xml(args: dict[str, Any]) -> str:
    fields = args.get("fields", [])
    if not isinstance(fields, list):
        fields = []
    lines: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            name = xml_safe(field.get("name", ""))
            order = xml_safe(field.get("order", "Ascending"))
        else:
            name = xml_safe(field)
            order = "Ascending"
        lines.append(f'<Field name="{name}" order="{order}" />')
    return "\n        ".join(lines)


def _unique_fields_xml(args: dict[str, Any]) -> str:
    fields = args.get("fields", [])
    if not isinstance(fields, list):
        fields = []
    lines: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            name = xml_safe(field.get("name", ""))
        else:
            name = xml_safe(field)
        lines.append(f'<Field name="{name}" />')
    return "\n        ".join(lines)


def build_placeholders(node: ToolNode) -> dict[str, str]:
    """Build template placeholders for a tool node."""
    args = node.args
    sample_mode = str(args.get("mode", ""))
    sample_value = ""
    if sample_mode == "first_n":
        sample_value = str(args.get("first_n", ""))
    elif sample_mode == "random_n":
        sample_value = str(args.get("random_n", ""))

    placeholders: dict[str, str] = {
        "TOOL_ID": str(node.tool_id),
        "X": str(node.x),
        "Y": str(node.y),
        "LABEL": xml_safe(node.label),
        "CONFIG_XML": xml_safe(args.get("config_xml", "")),
        "OP_NAME": xml_safe(node.op),
        "ARGS_XML": _generic_args_xml(args),
        "INPUT_PATH": xml_safe(args.get("path", "")),
        "CONNECTION_STRING": xml_safe(args.get("connection", "")),
        "FIELDS": _field_xml(args.get("fields", [])),
        "FORMULAS": _formula_xml(args),
        "CONDITION": xml_safe(args.get("condition", "")),
        "GROUP_BY": _summarize_group_xml(args.get("group_by", [])),
        "AGGREGATIONS": _summarize_agg_xml(args.get("aggregations", [])),
        "SUMMARIZE_FIELDS": _summarize_fields_xml(
            args.get("group_by", []), args.get("aggregations", [])
        ),
        "OUTPUT_PATH": xml_safe(args.get("path", "")),
        "ENGINE_DLL": xml_safe(node.engine_dll),
        "ENGINE_ENTRYPOINT": xml_safe(node.engine_entrypoint),
        "PLUGIN": xml_safe(node.plugin),
        "DATETIME_TRANSFORMATIONS": _datetime_transform_xml(args.get("transformations", [])),
        "TTC_FIELD": xml_safe(args.get("field", "")),
        "TTC_DELIMITER": xml_safe(args.get("delimiter", "")),
        "TTC_SPLIT_TO_ROWS": "True" if bool(args.get("split_to_rows", False)) else "False",
        "TTC_NUM_COLUMNS": xml_safe(args.get("num_columns", "")),
        "MRF_FIELD": xml_safe(args.get("field", "")),
        "MRF_EXPRESSION": xml_safe(args.get("expression", "")),
        "MRF_ROWS": xml_safe(args.get("rows", 1)),
        "MRF_GROUP_BY": _field_xml(args.get("group_by", [])),
        "CROSSTAB_GROUPS": _cross_tab_group_xml(args.get("group_by", [])),
        "CROSSTAB_HEADER_FIELD": xml_safe(args.get("header_field", "")),
        "CROSSTAB_DATA_FIELD": xml_safe(args.get("data_field", "")),
        "CROSSTAB_METHOD": xml_safe(args.get("method", "")),
        "TRANSPOSE_KEY_FIELDS": _transpose_fields_xml(args.get("key_fields", []), "Key"),
        "TRANSPOSE_DATA_FIELDS": _transpose_fields_xml(args.get("data_fields", []), "Data"),
        "SAMPLE_MODE": xml_safe(sample_mode),
        "SAMPLE_VALUE": xml_safe(sample_value),
        "SAMPLE_SEED": xml_safe(args.get("seed", "")),
        "CLEANSE_FIELDS": _data_cleansing_fields_xml(args.get("fields", [])),
        "CLEANSE_OPTIONS": _data_cleansing_options_xml(args),
        "RECORD_ID_FIELD": xml_safe(args.get("field_name", "RecordID")),
        "RECORD_ID_START": xml_safe(args.get("start", 1)),
        "RECORD_ID_INCREMENT": xml_safe(args.get("increment", 1)),
        "BROWSE_LIMIT": xml_safe(args.get("record_limit", "")),
        "JOIN_KEYS": _join_keys_xml(args),
        "JOIN_INFO": _join_info_xml(args),
        "JOIN_SELECT_FIELDS": _join_select_fields_xml(args),
        "JOIN_TYPE": xml_safe(args.get("join_type", "inner")),
        "UNION_AUTO_CONFIG": "True" if bool(args.get("auto_config", True)) else "False",
        "SORT_FIELDS": _sort_fields_xml(args),
        "UNIQUE_FIELDS": _unique_fields_xml(args),
    }

    return placeholders


def resolve_required_fields(op: str, args: dict[str, Any], label: str) -> list[str]:
    """Collect required-field warnings for each operation type."""
    missing: list[str] = []

    if op in {"csv_input", "file_input"} and not args.get("path"):
        missing.append(f"{label}: missing args.path")
    if op == "db_input" and not args.get("connection"):
        missing.append(f"{label}: missing args.connection")
    if op in {"formula", "cleanse"}:
        has_formula_list = isinstance(args.get("formulas"), list) and bool(args.get("formulas"))
        has_single_formula = bool(args.get("field")) and bool(args.get("expression"))
        if not (has_formula_list or has_single_formula):
            missing.append(f"{label}: formula requires args.formulas[] or args.field + args.expression")
    if op == "filter" and not args.get("condition"):
        missing.append(f"{label}: missing args.condition")
    if op == "summarize":
        has_groups = isinstance(args.get("group_by"), list) and bool(args.get("group_by"))
        has_aggs = isinstance(args.get("aggregations"), list) and bool(args.get("aggregations"))
        if not (has_groups or has_aggs):
            missing.append(f"{label}: summarize expects args.group_by and/or args.aggregations")
    if op == "output_file" and not args.get("path"):
        missing.append(f"{label}: missing args.path")
    if op == "output_db" and not args.get("connection"):
        missing.append(f"{label}: missing args.connection")

    if op == "datetime":
        transformations = args.get("transformations")
        if not isinstance(transformations, list) or not transformations:
            missing.append(f"{label}: datetime requires args.transformations[]")
    if op == "text_to_columns":
        if not args.get("field"):
            missing.append(f"{label}: text_to_columns missing args.field")
        if "delimiter" not in args:
            missing.append(f"{label}: text_to_columns missing args.delimiter")
    if op == "multi_row_formula":
        if not args.get("field"):
            missing.append(f"{label}: multi_row_formula missing args.field")
        if not args.get("expression"):
            missing.append(f"{label}: multi_row_formula missing args.expression")
    if op == "cross_tab":
        for key in ("group_by", "header_field", "data_field", "method"):
            if not args.get(key):
                missing.append(f"{label}: cross_tab missing args.{key}")
    if op == "transpose":
        if not isinstance(args.get("key_fields"), list) or not args.get("key_fields"):
            missing.append(f"{label}: transpose missing args.key_fields[]")
        if not isinstance(args.get("data_fields"), list) or not args.get("data_fields"):
            missing.append(f"{label}: transpose missing args.data_fields[]")
    if op == "sample":
        mode = args.get("mode")
        if not mode:
            missing.append(f"{label}: sample missing args.mode")
        elif mode == "first_n" and "first_n" not in args:
            missing.append(f"{label}: sample mode=first_n requires args.first_n")
        elif mode == "random_n" and "random_n" not in args:
            missing.append(f"{label}: sample mode=random_n requires args.random_n")
    if op == "data_cleansing":
        if not isinstance(args.get("fields"), list) or not args.get("fields"):
            missing.append(f"{label}: data_cleansing requires args.fields[]")
    if op == "record_id" and not args.get("field_name"):
        missing.append(f"{label}: record_id requires args.field_name")

    return missing


def build_next_steps(report: dict[str, Any]) -> list[str]:
    """Build action-oriented guidance from the validation report."""
    next_steps: list[str] = []
    if report["missing_fields"]:
        next_steps.append("Fill the required args listed in missing_fields and recompile.")
    if report["connector_placeholders_needed"]:
        next_steps.append("Replace connection placeholders with environment-specific connector settings.")
    if report["unresolved_placeholders"]:
        next_steps.append("Update template placeholders or compiler mappings to resolve unresolved placeholders.")
    if report["generic_fallback_ops"]:
        next_steps.append("Remove generic fallback usage for listed ops before release.")
    if report["unsupported_ops"]:
        next_steps.append("Replace unsupported ops or lower expectations to beta/unsupported behavior.")
    if report["compile_blockers"]:
        next_steps.append("Resolve compile_blockers before retrying build.")
    if not next_steps:
        next_steps.append("Open main.yxmd in Alteryx Designer and validate tool-level settings.")
    return next_steps


def ensure_engine_settings(node_el: ET.Element, node: ToolNode) -> None:
    """Ensure EngineSettings are present when capability metadata provides values."""
    if not node.engine_dll or not node.engine_entrypoint:
        return

    engine = node_el.find("./EngineSettings")
    if engine is None:
        engine = ET.SubElement(node_el, "EngineSettings")

    if not engine.get("EngineDll"):
        engine.set("EngineDll", node.engine_dll)
    if not engine.get("EngineDllEntryPoint"):
        engine.set("EngineDllEntryPoint", node.engine_entrypoint)


def enforce_gui_plugin(node_el: ET.Element, plugin: str) -> None:
    """Set plugin on GuiSettings, creating the element when missing."""
    if not plugin:
        return

    gs = node_el.find("./GuiSettings")
    if gs is None:
        gs = ET.SubElement(node_el, "GuiSettings")
    gs.set("Plugin", plugin)


def compile_spec_document(
    spec_doc: dict[str, Any],
    schema_doc: dict[str, Any],
    templates_dir: Path,
    capability_registry_path: Path | None = None,
    mode_override: str | None = None,
    designer_profile_override: str | None = None,
    designer_version_override: str | None = None,
) -> tuple[ET.ElementTree | None, dict[str, Any]]:
    """Compile a spec document into an XML tree and validation report."""
    report: dict[str, Any] = {
        "unresolved_placeholders": [],
        "missing_fields": [],
        "connector_placeholders_needed": [],
        "warnings": [],
        "generic_fallback_ops": [],
        "unsupported_ops": [],
        "capability_support": [],
        "designer_profile": "",
        "mode": "",
        "compile_blockers": [],
        "next_steps_for_user": [],
    }

    schema_errors = validate_spec_document(spec_doc, schema_doc)
    if schema_errors:
        report["missing_fields"].extend(schema_errors)
        report["warnings"].append("Schema validation failed. Compilation aborted.")
        report["next_steps_for_user"] = build_next_steps(report)
        return None, report

    capability_registry = load_capability_registry(capability_registry_path)
    designer_version, designer_profile = normalize_designer_settings(
        spec_doc,
        capability_registry,
        report,
        designer_profile_override=designer_profile_override,
        designer_version_override=designer_version_override,
    )
    mode = resolve_mode(spec_doc, mode_override, report)
    report["designer_profile"] = designer_profile
    report["mode"] = mode
    strict_native_ops = {
        "csv_input",
        "file_input",
        "db_input",
        "select",
        "filter",
        "formula",
        "summarize",
        "join",
        "union",
        "sort",
        "unique",
        "output_file",
        "output_db",
        *TIER2_OPS,
    }

    root = ET.Element("AlteryxDocument", {"yxmdVer": designer_version})
    nodes_el = ET.SubElement(root, "Nodes")
    conns_el = ET.SubElement(root, "Connections")

    used_ids: set[int] = set()
    nodes_by_key: dict[str, ToolNode] = {}
    node_order: list[str] = []
    branch_counts: dict[str, int] = {}
    outgoing_counts: dict[str, int] = {}
    pending_connections: list[tuple[str, str, str, str]] = []

    steps = spec_doc.get("steps", [])
    inputs = spec_doc.get("inputs", [])
    outputs = spec_doc.get("outputs", [])

    explicit_input_steps = [s for s in steps if s.get("op") in INPUT_OPS]

    def make_node(
        key: str,
        op: str,
        args: dict[str, Any],
        label: str,
        upstream_keys: list[str],
    ) -> ToolNode:
        valid_upstream_keys = [u for u in upstream_keys if u in nodes_by_key]

        if not valid_upstream_keys:
            lane = len([k for k in node_order if nodes_by_key[k].x == 120])
            x = 120
            y = lane * DEFAULT_Y_STEP
        elif len(valid_upstream_keys) == 1:
            parent = nodes_by_key[valid_upstream_keys[0]]
            x = parent.x + DEFAULT_X_STEP
            count = branch_counts.get(parent.key, 0) + 1
            branch_counts[parent.key] = count
            if count == 1:
                y = parent.y
            elif count % 2 == 0:
                y = parent.y + (count // 2) * DEFAULT_Y_STEP
            else:
                y = parent.y - (count // 2) * DEFAULT_Y_STEP
        else:
            parents = [nodes_by_key[u] for u in valid_upstream_keys]
            x = max(p.x for p in parents) + DEFAULT_X_STEP
            y = sum(p.y for p in parents) // len(parents)

        capability = get_capability(capability_registry, op) or {}
        support_state = str(capability.get("support_state", "unsupported"))
        availability = capability.get("availability") or []
        profile_available = designer_profile in availability if availability else True

        if not capability:
            report["warnings"].append(f"{label}: unsupported op '{op}', using generic.xml")
            report["unsupported_ops"].append(op)
        elif not profile_available:
            report["warnings"].append(
                f"{label}: op '{op}' is unavailable for profile {designer_profile}; template will still compile"
            )

        template_name = TEMPLATE_MAP.get(op, "generic.xml")
        if template_name == "generic.xml" and op in TIER2_OPS:
            report["generic_fallback_ops"].append(op)
        if template_name == "generic.xml" and op in strict_native_ops:
            report["compile_blockers"].append(
                f"{label}: op '{op}' requires a native template and cannot use generic fallback"
            )

        if support_state == "unsupported":
            report["unsupported_ops"].append(op)
        if mode == "starter_kit" and op == "browse":
            report["compile_blockers"].append(
                f"{label}: browse is disallowed in starter_kit mode"
            )

        plugin = str(capability.get("plugin", "AlteryxBasePluginsGui.ToolContainer.ToolContainer"))
        engine_dll = str(capability.get("engine_dll", ""))
        engine_entrypoint = str(capability.get("engine_entrypoint", ""))

        node = ToolNode(
            key=key,
            tool_id=deterministic_tool_id(key, used_ids),
            op=op,
            template_name=template_name,
            x=x,
            y=y,
            label=label,
            args=args,
            plugin=plugin,
            engine_dll=engine_dll,
            engine_entrypoint=engine_entrypoint,
            support_state=support_state,
            profile_available=profile_available,
        )

        nodes_by_key[key] = node
        node_order.append(key)
        outgoing_counts[key] = 0
        report["capability_support"].append(
            {
                "step_id": key,
                "op": op,
                "support_state": support_state,
                "profile": designer_profile,
                "profile_available": profile_available,
                "template": template_name,
            }
        )
        return node

    def connect(upstream_key: str, downstream_key: str, index: int) -> None:
        op = nodes_by_key[downstream_key].op
        upstream_op = nodes_by_key[upstream_key].op
        if upstream_op == "filter":
            from_anchor = "True"
        elif upstream_op == "join":
            from_anchor = "Join"
        else:
            from_anchor = "Output"
        if op == "join":
            to_anchor = "Left" if index == 0 else "Right" if index == 1 else f"Input{index + 1}"
        elif op == "union":
            to_anchor = f"Input{index + 1}"
        else:
            to_anchor = "Input"
        pending_connections.append((upstream_key, from_anchor, downstream_key, to_anchor))
        outgoing_counts[upstream_key] = outgoing_counts.get(upstream_key, 0) + 1

    if not explicit_input_steps:
        for input_item in inputs:
            input_name = input_item.get("name", "input")
            input_type = str(input_item.get("type", "file"))
            op = {
                "csv": "csv_input",
                "file": "file_input",
                "db": "db_input",
            }.get(input_type, "file_input")
            key = f"input:{input_name}"
            node = make_node(
                key=key,
                op=op,
                args={
                    "path": input_item.get("path", ""),
                    "connection": input_item.get("connection", ""),
                    "fields": input_item.get("fields", []),
                },
                label=input_name,
                upstream_keys=[],
            )
            report["missing_fields"].extend(resolve_required_fields(node.op, node.args, node.label))
            report["warnings"].extend(path_quality_warnings(node.op, node.args, node.label))
            if node.op == "db_input" and not node.args.get("connection"):
                report["connector_placeholders_needed"].append(
                    f"{node.label}: provide args.connection for db_input"
                )

    last_non_input_key: str | None = None
    for step in steps:
        step_id = str(step.get("id", "step"))
        op = str(step.get("op", ""))
        args = step.get("args", {})
        if not isinstance(args, dict):
            args = {"value": args}

        depends_on = step.get("depends_on")
        if isinstance(depends_on, list) and depends_on:
            upstream_keys = [str(item) for item in depends_on]
        elif op in INPUT_OPS:
            upstream_keys = []
        elif last_non_input_key:
            upstream_keys = [last_non_input_key]
        elif len(nodes_by_key) == 1:
            upstream_keys = [next(iter(nodes_by_key.keys()))]
        elif len(nodes_by_key) > 1 and op in {"join", "union"}:
            upstream_keys = list(nodes_by_key.keys())[:2]
        else:
            upstream_keys = []

        unresolved_deps = [dep for dep in upstream_keys if dep not in nodes_by_key]
        if unresolved_deps:
            report["warnings"].append(
                f"{step_id}: unresolved depends_on references: {', '.join(unresolved_deps)}"
            )

        node = make_node(
            key=step_id,
            op=op,
            args=args,
            label=step_id,
            upstream_keys=upstream_keys,
        )

        report["missing_fields"].extend(resolve_required_fields(node.op, node.args, node.label))
        report["warnings"].extend(path_quality_warnings(node.op, node.args, node.label))
        if node.op == "db_input" and not node.args.get("connection"):
            report["connector_placeholders_needed"].append(
                f"{node.label}: provide args.connection for db_input"
            )
        if node.op == "output_db" and not node.args.get("connection"):
            report["connector_placeholders_needed"].append(
                f"{node.label}: provide args.connection for output_db"
            )

        valid_upstream = [u for u in upstream_keys if u in nodes_by_key and u != node.key]
        for index, upstream in enumerate(valid_upstream):
            connect(upstream, node.key, index)

        if node.op not in INPUT_OPS:
            last_non_input_key = node.key

    explicit_output_steps = [s for s in steps if s.get("op") in OUTPUT_OPS]
    if outputs and not explicit_output_steps:
        terminal_keys = [key for key in node_order if outgoing_counts.get(key, 0) == 0]
        if not terminal_keys and node_order:
            terminal_keys = [node_order[-1]]

        for idx, output in enumerate(outputs):
            target = output if isinstance(output, dict) else {}
            op = "output_db" if target.get("type") == "db" or target.get("connection") else "output_file"
            key = f"auto_output_{idx + 1}"
            node = make_node(
                key=key,
                op=op,
                args={
                    "path": target.get("path", ""),
                    "connection": target.get("connection", ""),
                },
                label=key,
                upstream_keys=[terminal_keys[idx % len(terminal_keys)]] if terminal_keys else [],
            )
            report["missing_fields"].extend(resolve_required_fields(node.op, node.args, node.label))
            report["warnings"].extend(path_quality_warnings(node.op, node.args, node.label))
            if node.op == "output_db" and not node.args.get("connection"):
                report["connector_placeholders_needed"].append(
                    f"{node.label}: provide args.connection for output_db"
                )
            if terminal_keys:
                connect(terminal_keys[idx % len(terminal_keys)], node.key, 0)

    for key in node_order:
        node = nodes_by_key[key]
        template_text, used_generic_file_fallback = read_template(templates_dir, node.template_name)
        if used_generic_file_fallback:
            report["generic_fallback_ops"].append(node.op)
            report["warnings"].append(
                f"{node.key}: template '{node.template_name}' missing; used generic.xml fallback"
            )
            if node.op in strict_native_ops:
                report["compile_blockers"].append(
                    f"{node.key}: native template file '{node.template_name}' missing for op '{node.op}'"
                )
        replacements = build_placeholders(node)
        rendered, unresolved = render_template(template_text, replacements)
        for token in unresolved:
            report["unresolved_placeholders"].append(f"{node.key}: {token}")

        try:
            node_el = ET.fromstring(rendered)
        except ET.ParseError as exc:
            report["warnings"].append(f"{node.key}: template XML parse error: {exc}")
            generic_text = read_template(templates_dir, "generic.xml")
            rendered, unresolved = render_template(generic_text, replacements)
            for token in unresolved:
                report["unresolved_placeholders"].append(f"{node.key} (fallback): {token}")
            node_el = ET.fromstring(rendered)
            report["generic_fallback_ops"].append(node.op)
            if node.op in strict_native_ops:
                report["compile_blockers"].append(
                    f"{node.key}: native template parse failed for op '{node.op}' and fallback is blocked"
                )

        enforce_gui_plugin(node_el, node.plugin)
        ensure_engine_settings(node_el, node)
        nodes_el.append(node_el)

    for from_key, from_anchor, to_key, to_anchor in pending_connections:
        connection = Connection(
            from_id=nodes_by_key[from_key].tool_id,
            from_anchor=from_anchor,
            to_id=nodes_by_key[to_key].tool_id,
            to_anchor=to_anchor,
        )
        conn_el = ET.SubElement(conns_el, "Connection")
        ET.SubElement(
            conn_el,
            "Origin",
            {
                "ToolID": str(connection.from_id),
                "Connection": connection.from_anchor,
            },
        )
        ET.SubElement(
            conn_el,
            "Destination",
            {
                "ToolID": str(connection.to_id),
                "Connection": connection.to_anchor,
            },
        )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    report["unresolved_placeholders"] = sorted(set(report["unresolved_placeholders"]))
    report["missing_fields"] = sorted(set(report["missing_fields"]))
    report["connector_placeholders_needed"] = sorted(set(report["connector_placeholders_needed"]))
    report["warnings"] = sorted(set(report["warnings"]))
    report["generic_fallback_ops"] = sorted(set(report["generic_fallback_ops"]))
    report["unsupported_ops"] = sorted(set(report["unsupported_ops"]))
    report["compile_blockers"] = sorted(set(report["compile_blockers"]))
    report["capability_support"] = sorted(
        report["capability_support"],
        key=lambda item: (str(item.get("step_id", "")), str(item.get("op", ""))),
    )
    report["next_steps_for_user"] = build_next_steps(report)

    if report["compile_blockers"]:
        report["warnings"].append("Compilation blocked by strict native-template policy.")
        report["next_steps_for_user"] = build_next_steps(report)
        return None, report

    return tree, report


def compile_spec_file(
    spec_path: Path,
    out_dir: Path,
    schema_path: Path,
    templates_dir: Path,
    capability_registry_path: Path | None = None,
    mode_override: str | None = None,
    designer_profile_override: str | None = None,
    designer_version_override: str | None = None,
) -> tuple[Path, Path]:
    """Compile a spec file and write outputs to the output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_doc = load_json(spec_path)
    schema_doc = load_json(schema_path)

    tree, report = compile_spec_document(
        spec_doc=spec_doc,
        schema_doc=schema_doc,
        templates_dir=templates_dir,
        capability_registry_path=capability_registry_path,
        mode_override=mode_override,
        designer_profile_override=designer_profile_override,
        designer_version_override=designer_version_override,
    )

    yxmd_path = out_dir / "main.yxmd"
    report_path = out_dir / "validation_report.json"

    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    if tree is None:
        raise ValueError("Compilation failed; see validation_report.json for schema errors or compile_blockers.")

    tree.write(yxmd_path, encoding="utf-8", xml_declaration=True)
    return yxmd_path, report_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Compile workflow_spec JSON into main.yxmd")
    parser.add_argument("--spec", required=True, type=Path, help="Path to workflow_spec.json")
    parser.add_argument("--out_dir", required=True, type=Path, help="Output directory")
    parser.add_argument(
        "--schema",
        type=Path,
        default=root / "schemas" / "workflow_spec.schema.json",
        help="Path to schema file",
    )
    parser.add_argument(
        "--templates_dir",
        type=Path,
        default=root / "templates",
        help="Directory containing XML templates",
    )
    parser.add_argument(
        "--capability_registry",
        type=Path,
        default=root / "references" / "capability_registry.json",
        help="Capability registry JSON path",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=sorted(SUPPORTED_MODES),
        default=None,
        help="Governance mode override (starter_kit|demo)",
    )
    parser.add_argument(
        "--designer_profile",
        type=str,
        default=None,
        choices=["2025.1", "2025.2"],
        help="Optional capability profile override",
    )
    parser.add_argument(
        "--designer_version",
        type=str,
        default=None,
        help="Optional yxmdVer override (e.g., 2025.2)",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    yxmd_path, report_path = compile_spec_file(
        spec_path=args.spec,
        out_dir=args.out_dir,
        schema_path=args.schema,
        templates_dir=args.templates_dir,
        capability_registry_path=args.capability_registry,
        mode_override=args.mode,
        designer_profile_override=args.designer_profile,
        designer_version_override=args.designer_version,
    )
    print(f"Wrote {yxmd_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
