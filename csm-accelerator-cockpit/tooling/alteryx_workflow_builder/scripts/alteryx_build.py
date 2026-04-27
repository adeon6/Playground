#!/usr/bin/env python3
"""Single entry point for planning, compiling, and packaging Alteryx workflow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from compile import compile_spec_file
from package_yxzp import create_package

DEFAULT_DESIGNER_VERSION = "2025.1"
DETERMINISTIC_OUTPUT_PREFIX_RE = r"^(customgpt_|[0-9]{2}_)"


def _rewrite_local_paths_for_output(spec_doc: dict[str, Any], out_dir: Path, source_base: Path) -> dict[str, Any]:
    """Rewrite file-based input paths so generated workflows resolve them from out_dir.

    Alteryx resolves relative file references from the workflow location, not from the
    original spec location or the shell's current working directory. Normalize known
    input paths to be relative to the output workflow folder.
    """
    rewritten = json.loads(json.dumps(spec_doc))

    def _maybe_rewrite_path(raw_path: Any) -> Any:
        if not isinstance(raw_path, str):
            return raw_path
        text = raw_path.strip()
        if not text:
            return raw_path

        candidate = Path(text)
        if candidate.is_absolute():
            return raw_path

        resolved = (source_base / candidate).resolve()
        try:
            relative = resolved.relative_to(out_dir.resolve())
            return relative.as_posix()
        except ValueError:
            return Path(os.path.relpath(resolved, out_dir.resolve())).as_posix()

    for input_item in rewritten.get("inputs", []):
        if isinstance(input_item, dict) and input_item.get("path"):
            input_item["path"] = _maybe_rewrite_path(input_item["path"])

    for step in rewritten.get("steps", []):
        if not isinstance(step, dict):
            continue
        args = step.get("args")
        if not isinstance(args, dict):
            continue
        if step.get("op") in {"csv_input", "file_input"} and args.get("path"):
            args["path"] = _maybe_rewrite_path(args["path"])

    return rewritten


def _normalize_output_filenames(spec_doc: dict[str, Any]) -> dict[str, Any]:
    """Make output filenames deterministic for repo validation rules."""
    rewritten = json.loads(json.dumps(spec_doc))

    def _normalize_path(raw_path: Any) -> Any:
        if not isinstance(raw_path, str):
            return raw_path
        text = raw_path.strip()
        if not text:
            return raw_path

        path = Path(text)
        name = path.name
        if not name or re.match(DETERMINISTIC_OUTPUT_PREFIX_RE, name, flags=re.IGNORECASE):
            return raw_path

        normalized_name = f"01_{name}"
        parent = path.parent
        if str(parent) in {"", "."}:
            return f"./{normalized_name}"
        return (parent / normalized_name).as_posix()

    for step in rewritten.get("steps", []):
        if not isinstance(step, dict):
            continue
        args = step.get("args")
        if not isinstance(args, dict):
            continue
        if step.get("op") == "output_file" and args.get("path"):
            args["path"] = _normalize_path(args["path"])

    for output in rewritten.get("outputs", []):
        if isinstance(output, dict) and output.get("type") == "file" and output.get("path"):
            output["path"] = _normalize_path(output["path"])

    return rewritten


def draft_spec_from_problem(problem: str, designer_version: str = DEFAULT_DESIGNER_VERSION) -> dict[str, Any]:
    """Create a deterministic draft workflow spec from free-text problem input.

    Replace this heuristic planner with an LLM planner that emits schema-valid JSON.
    In this skill, the primary planning logic should be driven by SKILL.md instructions.
    """
    problem_clean = " ".join(problem.split())
    spec_id = f"draft_{hashlib.sha1(problem_clean.encode('utf-8')).hexdigest()[:10]}"
    lower = problem_clean.lower()

    if "join" in lower and "customerid" in lower:
        steps = [
            {
                "id": "input_left",
                "op": "csv_input",
                "args": {"path": "./left.csv"},
            },
            {
                "id": "input_right",
                "op": "csv_input",
                "args": {"path": "./right.csv"},
            },
            {
                "id": "join_customer",
                "op": "join",
                "depends_on": ["input_left", "input_right"],
                "args": {
                    "left_key": "CustomerID",
                    "right_key": "CustomerID",
                    "join_type": "inner",
                },
            },
            {
                "id": "summarize_joined",
                "op": "summarize",
                "depends_on": ["join_customer"],
                "args": {
                    "group_by": ["CustomerID"],
                    "aggregations": [
                        {"field": "CustomerID", "action": "Count", "as": "RowCount"}
                    ],
                },
            },
            {
                "id": "output_summary",
                "op": "output_file",
                "depends_on": ["summarize_joined"],
                "args": {"path": "./joined_summary.csv"},
            },
        ]
        inputs = [
            {"name": "left", "type": "csv", "path": "./left.csv"},
            {"name": "right", "type": "csv", "path": "./right.csv"},
        ]
        outputs = [{"type": "file", "format": "csv", "path": "./joined_summary.csv"}]
        assumptions = [
            "Both CSV files contain CustomerID.",
            "CustomerID is comparable with matching type across files.",
        ]
    else:
        steps = [
            {
                "id": "input_data",
                "op": "csv_input",
                "args": {"path": "./input.csv"},
            },
            {
                "id": "summarize_data",
                "op": "summarize",
                "depends_on": ["input_data"],
                "args": {
                    "group_by": ["Category"],
                    "aggregations": [
                        {"field": "Category", "action": "Count", "as": "RowCount"}
                    ],
                },
            },
            {
                "id": "output_data",
                "op": "output_file",
                "depends_on": ["summarize_data"],
                "args": {"path": "./output.csv"},
            },
        ]
        inputs = [{"name": "input", "type": "csv", "path": "./input.csv"}]
        outputs = [{"type": "file", "format": "csv", "path": "./output.csv"}]
        assumptions = [
            "Input CSV exists at ./input.csv.",
            "Category is available as a grouping field.",
        ]

    return {
        "id": spec_id,
        "goal": problem_clean,
        "inputs": inputs,
        "steps": steps,
        "outputs": outputs,
        "assumptions": assumptions,
        "metadata": {
            "author": "codex",
            "version": "1.0.0",
            "designer_version": designer_version,
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build Alteryx artifacts from problem text or spec")

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--problem", type=str, help="Natural-language business problem")
    source_group.add_argument("--spec", type=Path, help="Path to workflow_spec.json")

    parser.add_argument("--out_dir", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--schema",
        type=Path,
        default=root / "schemas" / "workflow_spec.schema.json",
        help="Schema path",
    )
    parser.add_argument(
        "--templates_dir",
        type=Path,
        default=root / "templates",
        help="Templates directory",
    )
    parser.add_argument(
        "--designer_version",
        type=str,
        default=DEFAULT_DESIGNER_VERSION,
        help="Target Alteryx yxmdVer value (default: 2025.1)",
    )
    parser.add_argument("--package", action="store_true", help="Create .yxzp package")
    parser.add_argument(
        "--package_name",
        type=str,
        default="package.yxzp",
        help="Package filename (used with --package)",
    )
    parser.add_argument(
        "--sample_data",
        type=Path,
        default=None,
        help="Optional sample file or folder copied into out_dir/data before packaging",
    )

    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for existing_yxmd in out_dir.glob("*.yxmd"):
        existing_yxmd.unlink()

    spec_out_path = out_dir / "workflow_spec.json"

    if args.problem:
        spec_doc = draft_spec_from_problem(args.problem, designer_version=args.designer_version)
        with spec_out_path.open("w", encoding="utf-8") as handle:
            json.dump(spec_doc, handle, indent=2)
        print(f"Draft spec generated at {spec_out_path}")
    else:
        if args.spec is None:
            raise ValueError("--spec is required when --problem is not provided")
        spec_doc = json.loads(args.spec.read_text(encoding="utf-8"))
        metadata = spec_doc.setdefault("metadata", {})
        metadata["designer_version"] = args.designer_version
        spec_doc = _normalize_output_filenames(spec_doc)
        spec_doc = _rewrite_local_paths_for_output(
            spec_doc=spec_doc,
            out_dir=out_dir,
            source_base=Path.cwd(),
        )
        with spec_out_path.open("w", encoding="utf-8") as handle:
            json.dump(spec_doc, handle, indent=2)
        print(f"Copied spec to {spec_out_path}")

    yxmd_path, report_path = compile_spec_file(
        spec_path=spec_out_path,
        out_dir=out_dir,
        schema_path=args.schema,
        templates_dir=args.templates_dir,
    )
    print(f"Wrote {yxmd_path}")
    print(f"Wrote {report_path}")

    if args.package:
        if args.sample_data:
            data_dir = out_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            if args.sample_data.is_dir():
                for item in sorted(args.sample_data.iterdir()):
                    target = data_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, target)
            else:
                shutil.copy2(args.sample_data, data_dir / args.sample_data.name)

        package_path = out_dir / args.package_name
        create_package(source_dir=out_dir, output_path=package_path)
        print(f"Wrote {package_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
