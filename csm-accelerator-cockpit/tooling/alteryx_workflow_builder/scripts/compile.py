#!/usr/bin/env python3
"""Compile workflow_spec JSON into a deterministic Alteryx-like .yxmd XML document."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import xml.etree.ElementTree as ET

from validate_spec import load_json, validate_spec_document

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

INPUT_OPS = {"csv_input", "file_input", "db_input"}
OUTPUT_OPS = {"output_file", "output_db"}

TEMPLATE_MAP = {
    "csv_input": "input_data.xml",
    "file_input": "input_data.xml",
    "db_input": "input_data.xml",
    "select": "select.xml",
    "cleanse": "formula.xml",
    "formula": "formula.xml",
    "filter": "filter.xml",
    "join": "generic.xml",
    "union": "generic.xml",
    "summarize": "summarize.xml",
    "sort": "generic.xml",
    "unique": "generic.xml",
    "output_file": "output_data.xml",
    "output_db": "output_data.xml",
    "macro_call": "generic.xml",
    "python_script": "generic.xml",
}

DEFAULT_X_STEP = 220
DEFAULT_Y_STEP = 120
DEFAULT_DESIGNER_VERSION = "2025.1"
DESIGNER_VERSION_RE = re.compile(r"^\d{4}\.\d+$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
SUMMARIZE_ACTION_ALIASES = {
    "average": "Avg",
    "avg": "Avg",
    "countdistinct": "CountDistinct",
    "count_distinct": "CountDistinct",
    "groupby": "GroupBy",
    "group_by": "GroupBy",
    "stddev": "StdDev",
}



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


def derive_workflow_filename(spec_doc: dict[str, Any]) -> str:
    """Build a validator-friendly workflow filename from spec metadata."""
    raw_name = str(spec_doc.get("id") or spec_doc.get("goal") or "workflow").strip()
    normalized = unicodedata.normalize("NFKD", raw_name).encode("ascii", "ignore").decode("ascii")
    slug = SAFE_FILENAME_RE.sub("_", normalized).strip("._-")
    if not slug:
        slug = "workflow"
    if not re.match(r"^\d{2}_", slug):
        slug = f"01_{slug}"
    return f"{slug}.yxmd"


def xml_safe(value: Any) -> str:
    """Escape text for safe XML embedding."""
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def normalize_designer_version(spec_doc: dict[str, Any], report: dict[str, list[str]]) -> str:
    """Return a safe yxmd version value with a stable default."""
    metadata = spec_doc.get("metadata", {})
    if not isinstance(metadata, dict):
        report["warnings"].append(
            f"metadata is not an object; defaulting yxmdVer to {DEFAULT_DESIGNER_VERSION}"
        )
        return DEFAULT_DESIGNER_VERSION

    raw_version = str(metadata.get("designer_version", "")).strip()
    if not raw_version:
        return DEFAULT_DESIGNER_VERSION

    if not DESIGNER_VERSION_RE.match(raw_version):
        report["warnings"].append(
            f"metadata.designer_version '{raw_version}' is invalid; defaulting to {DEFAULT_DESIGNER_VERSION}"
        )
        return DEFAULT_DESIGNER_VERSION

    return raw_version


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


def read_template(templates_dir: Path, template_name: str) -> str:
    """Load template content from disk."""
    path = templates_dir / template_name
    if not path.exists():
        fallback = templates_dir / "generic.xml"
        if not fallback.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        return fallback.read_text(encoding="utf-8")
    return path.read_text(encoding="utf-8")


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
        size = xml_safe(formula.get("size", "255"))
        lines.append(
            f'<FormulaField expression="{expression}" field="{field}" size="{size}" type="{dtype}" />'
        )
    return "\n        ".join(lines)


def _summarize_fields_xml(group_by: list[Any], aggregations: list[Any]) -> str:
    lines: list[str] = []
    for group in group_by:
        field = xml_safe(group.get("field", "")) if isinstance(group, dict) else xml_safe(group)
        rename = field
        lines.append(
            f'<SummarizeField field="{field}" action="GroupBy" rename="{rename}" />'
        )

    for agg in aggregations:
        if isinstance(agg, dict):
            field = xml_safe(agg.get("field", ""))
            raw_action = str(agg.get("action", ""))
            normalized_action = SUMMARIZE_ACTION_ALIASES.get(
                raw_action.replace(" ", "").replace("-", "_").lower(),
                raw_action,
            )
            action = xml_safe(normalized_action)
            out_name = xml_safe(agg.get("as", ""))
        else:
            field = xml_safe(agg)
            action = "Count"
            out_name = ""
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


def build_placeholders(node: ToolNode) -> dict[str, str]:
    """Build template placeholders for a tool node."""
    args = node.args
    placeholders: dict[str, str] = {
        "TOOL_ID": str(node.tool_id),
        "X": str(node.x),
        "Y": str(node.y),
        "LABEL": xml_safe(node.label),
        "CONFIG_XML": xml_safe(args.get("config_xml", "")),
        "OP_NAME": xml_safe(node.op),
        "ARGS_XML": _generic_args_xml(args),
    }

    placeholders.update(
        {
            "INPUT_PATH": xml_safe(args.get("path", "")),
            "CONNECTION_STRING": xml_safe(args.get("connection", "")),
            "FIELDS": _field_xml(args.get("fields", [])),
            "FORMULAS": _formula_xml(args),
            "CONDITION": xml_safe(args.get("condition", "")),
            "SUMMARIZE_FIELDS": _summarize_fields_xml(
                args.get("group_by", []),
                args.get("aggregations", []),
            ),
            "OUTPUT_PATH": xml_safe(args.get("path", "")),
        }
    )

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

    return missing


def build_next_steps(report: dict[str, list[str]]) -> list[str]:
    """Build action-oriented guidance from the validation report."""
    next_steps: list[str] = []
    if report["missing_fields"]:
        next_steps.append("Fill the required args listed in missing_fields and recompile.")
    if report["connector_placeholders_needed"]:
        next_steps.append("Replace connection placeholders with environment-specific connector settings.")
    if report["unresolved_placeholders"]:
        next_steps.append("Update template placeholders or compiler mappings to resolve unresolved placeholders.")
    if not next_steps:
        next_steps.append("Open main.yxmd in Alteryx Designer and validate tool-level settings.")
    return next_steps


def compile_spec_document(
    spec_doc: dict[str, Any],
    schema_doc: dict[str, Any],
    templates_dir: Path,
) -> tuple[ET.ElementTree | None, dict[str, list[str]]]:
    """Compile a spec document into an XML tree and validation report."""
    report: dict[str, list[str]] = {
        "unresolved_placeholders": [],
        "missing_fields": [],
        "connector_placeholders_needed": [],
        "warnings": [],
        "next_steps_for_user": [],
    }

    schema_errors = validate_spec_document(spec_doc, schema_doc)
    if schema_errors:
        report["missing_fields"].extend(schema_errors)
        report["warnings"].append("Schema validation failed. Compilation aborted.")
        report["next_steps_for_user"] = build_next_steps(report)
        return None, report

    designer_version = normalize_designer_version(spec_doc, report)
    base_path = templates_dir / "base.yxmd"
    if base_path.exists():
        root = ET.parse(base_path).getroot()
        root.attrib["yxmdVer"] = designer_version
        nodes_el = root.find("./Nodes")
        conns_el = root.find("./Connections")
        if nodes_el is None:
            nodes_el = ET.SubElement(root, "Nodes")
        if conns_el is None:
            conns_el = ET.SubElement(root, "Connections")
        nodes_el.clear()
        conns_el.clear()
    else:
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

        template_name = TEMPLATE_MAP.get(op, "generic.xml")
        if op not in TEMPLATE_MAP:
            report["warnings"].append(f"{label}: unsupported op '{op}', using generic.xml")

        node = ToolNode(
            key=key,
            tool_id=deterministic_tool_id(key, used_ids),
            op=op,
            template_name=template_name,
            x=x,
            y=y,
            label=label,
            args=args,
        )

        nodes_by_key[key] = node
        node_order.append(key)
        outgoing_counts[key] = 0
        return node

    def connect(upstream_key: str, downstream_key: str, index: int) -> None:
        op = nodes_by_key[downstream_key].op
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
        template_text = read_template(templates_dir, node.template_name)
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
    report["next_steps_for_user"] = build_next_steps(report)

    return tree, report


def compile_spec_file(
    spec_path: Path,
    out_dir: Path,
    schema_path: Path,
    templates_dir: Path,
) -> tuple[Path, Path]:
    """Compile a spec file and write outputs to the output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_doc = load_json(spec_path)
    schema_doc = load_json(schema_path)

    tree, report = compile_spec_document(
        spec_doc=spec_doc,
        schema_doc=schema_doc,
        templates_dir=templates_dir,
    )

    yxmd_path = out_dir / derive_workflow_filename(spec_doc)
    report_path = out_dir / "validation_report.json"

    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    if tree is None:
        raise ValueError("Schema validation failed; see validation_report.json for details.")

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
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    yxmd_path, report_path = compile_spec_file(
        spec_path=args.spec,
        out_dir=args.out_dir,
        schema_path=args.schema,
        templates_dir=args.templates_dir,
    )
    print(f"Wrote {yxmd_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
