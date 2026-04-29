#!/usr/bin/env python3
"""Single entry point for planning, compiling, and packaging Alteryx workflow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from compile import compile_spec_file
from package_yxzp import create_package

DEFAULT_DESIGNER_VERSION = "2025.2"
DEFAULT_DESIGNER_PROFILE = "2025.2"
DEFAULT_MODE = "demo"


def draft_spec_from_problem(
    problem: str,
    designer_version: str = DEFAULT_DESIGNER_VERSION,
    designer_profile: str = DEFAULT_DESIGNER_PROFILE,
    mode: str = DEFAULT_MODE,
) -> dict[str, Any]:
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
            "designer_profile": designer_profile,
            "mode": mode,
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
        default=None,
        help="Optional target Alteryx yxmdVer override",
    )
    parser.add_argument(
        "--designer_profile",
        type=str,
        default=None,
        choices=["2025.1", "2025.2"],
        help="Optional capability profile override",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        choices=["starter_kit", "demo"],
        help="Optional governance mode override for validation behavior",
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
    parser.add_argument(
        "--capability_registry",
        type=Path,
        default=root / "references" / "capability_registry.json",
        help="Capability registry JSON path",
    )

    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_out_path = out_dir / "workflow_spec.json"

    if args.problem:
        spec_doc = draft_spec_from_problem(
            args.problem,
            designer_version=args.designer_version or DEFAULT_DESIGNER_VERSION,
            designer_profile=args.designer_profile or DEFAULT_DESIGNER_PROFILE,
            mode=args.mode or DEFAULT_MODE,
        )
        with spec_out_path.open("w", encoding="utf-8") as handle:
            json.dump(spec_doc, handle, indent=2)
        print(f"Draft spec generated at {spec_out_path}")
    else:
        if args.spec is None:
            raise ValueError("--spec is required when --problem is not provided")
        spec_doc = json.loads(args.spec.read_text(encoding="utf-8"))
        metadata = spec_doc.setdefault("metadata", {})
        if args.designer_version:
            metadata["designer_version"] = args.designer_version
        if args.designer_profile:
            metadata["designer_profile"] = args.designer_profile
        if args.mode:
            metadata["mode"] = args.mode
        with spec_out_path.open("w", encoding="utf-8") as handle:
            json.dump(spec_doc, handle, indent=2)
        print(f"Copied spec to {spec_out_path}")

    yxmd_path, report_path = compile_spec_file(
        spec_path=spec_out_path,
        out_dir=out_dir,
        schema_path=args.schema,
        templates_dir=args.templates_dir,
        capability_registry_path=args.capability_registry,
        mode_override=args.mode,
        designer_profile_override=args.designer_profile,
        designer_version_override=args.designer_version,
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
