#!/usr/bin/env python3
"""Compile tier-2 fixtures and validate emitted signatures against baseline rules."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from compile import compile_spec_file
from extract_tool_signatures import extract_signatures
from validate_spec import load_json, validate_spec_document


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Tier-2 signature regression harness")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "references" / "corpus" / "tier2_regression_manifest.json",
        help="Fixture manifest JSON path",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=root / "references" / "corpus" / "tier2_signature_baseline.json",
        help="Baseline expectation JSON path",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=root / "schemas" / "workflow_spec.schema.json",
        help="Schema path",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=root / "templates",
        help="Template directory",
    )
    parser.add_argument(
        "--capability-registry",
        type=Path,
        default=root / "references" / "capability_registry.json",
        help="Capability registry path",
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional full result payload JSON path")
    return parser.parse_args()


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    fixtures = data.get("fixtures") if isinstance(data, dict) else None
    if not isinstance(fixtures, list):
        raise ValueError("manifest must contain {\"fixtures\": [...]} list")
    return [f for f in fixtures if isinstance(f, dict)]


def _validate_spec(spec_path: Path, schema_path: Path) -> list[str]:
    schema_doc = load_json(schema_path)
    spec_doc = load_json(spec_path)
    return validate_spec_document(spec_doc, schema_doc)


def _compare_fixture(actual: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    signatures = actual.get("tier2_signatures") or []
    ops = [row.get("op") for row in signatures]

    expected_ops = baseline.get("required_ops") or []
    for op in expected_ops:
        if op not in ops:
            failures.append(f"missing required op signature: {op}")

    for row in signatures:
        if baseline.get("forbid_generic_fallback", True) and row.get("generic_fallback"):
            failures.append(f"op {row.get('op')} used generic fallback")
        if baseline.get("require_semantics_ok", True) and not row.get("required_semantics_ok"):
            failures.append(f"op {row.get('op')} failed semantic minimum check")

    expected_plugins = baseline.get("expected_plugin_by_op") or {}
    for row in signatures:
        op = row.get("op")
        expected_plugin = expected_plugins.get(op)
        if expected_plugin and row.get("plugin") != expected_plugin:
            failures.append(f"op {op} plugin mismatch expected={expected_plugin} got={row.get('plugin')}")

    return failures


def main() -> int:
    args = parse_args()
    fixtures = _load_manifest(args.manifest)
    baselines = json.loads(args.baseline.read_text(encoding="utf-8"))

    result_rows: list[dict[str, Any]] = []
    total_failures = 0

    for fixture in fixtures:
        fixture_id = str(fixture.get("id", ""))
        spec_path = Path(str(fixture.get("spec", ""))).resolve()

        row: dict[str, Any] = {
            "id": fixture_id,
            "spec": str(spec_path),
            "status": "PASS",
            "failures": [],
        }

        if not spec_path.exists():
            row["status"] = "FAIL"
            row["failures"] = [f"spec not found: {spec_path}"]
            total_failures += 1
            result_rows.append(row)
            continue

        schema_errors = _validate_spec(spec_path, args.schema)
        if schema_errors:
            row["status"] = "FAIL"
            row["failures"] = [f"schema: {err}" for err in schema_errors]
            total_failures += 1
            result_rows.append(row)
            continue

        with tempfile.TemporaryDirectory(prefix=f"tier2_regress_{fixture_id}_") as tmp:
            out_dir = Path(tmp) / fixture_id
            out_dir.mkdir(parents=True, exist_ok=True)
            compile_spec_file(
                spec_path=spec_path,
                out_dir=out_dir,
                schema_path=args.schema,
                templates_dir=args.templates_dir,
                capability_registry_path=args.capability_registry,
            )
            workflow_path = out_dir / "main.yxmd"
            signature_payload = extract_signatures(workflow_path, json.loads(args.capability_registry.read_text(encoding="utf-8")))
            row["signature"] = signature_payload

            baseline = baselines.get(fixture_id, {}) if isinstance(baselines, dict) else {}
            failures = _compare_fixture(signature_payload, baseline if isinstance(baseline, dict) else {})
            if failures:
                row["status"] = "FAIL"
                row["failures"] = failures
                total_failures += len(failures)

        result_rows.append(row)

    payload = {
        "manifest": str(args.manifest),
        "baseline": str(args.baseline),
        "fixtures": result_rows,
        "status": "PASS" if total_failures == 0 else "FAIL",
        "failure_count": total_failures,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")

    print(json.dumps({"status": payload["status"], "failure_count": payload["failure_count"]}, indent=2))
    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
