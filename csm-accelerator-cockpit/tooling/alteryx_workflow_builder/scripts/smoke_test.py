#!/usr/bin/env python3
"""Smoke tests for example workflow compile/package flows."""

from __future__ import annotations

import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from capability_registry import load_capability_registry
from compile import compile_spec_file
from extract_tool_signatures import extract_signatures
from golden_sanity import check_one as golden_check_one
from lint_yxmd import lint_workflow
from package_yxzp import create_package


def run_support_sla_smoke(root: Path, capability_registry: dict) -> None:
    """Compile and package baseline support_sla example."""
    spec_path = root / "examples" / "support_sla" / "workflow_spec.json"
    schema_path = root / "schemas" / "workflow_spec.schema.json"
    templates_dir = root / "templates"
    sample_data_dir = root / "examples" / "support_sla" / "data"

    with tempfile.TemporaryDirectory(prefix="alteryx_builder_smoke_support_") as temp_dir:
        out_dir = Path(temp_dir) / "dist"
        out_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(spec_path, out_dir / "workflow_spec.json")
        data_out = out_dir / "data"
        data_out.mkdir(parents=True, exist_ok=True)
        for item in sample_data_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, data_out / item.name)

        yxmd_path, report_path = compile_spec_file(
            spec_path=out_dir / "workflow_spec.json",
            out_dir=out_dir,
            schema_path=schema_path,
            templates_dir=templates_dir,
            capability_registry_path=root / "references" / "capability_registry.json",
        )

        assert yxmd_path.exists(), "main.yxmd was not created"
        assert report_path.exists(), "validation_report.json was not created"

        tree = ET.parse(yxmd_path)
        assert tree.getroot().attrib.get("yxmdVer") == "2025.2", "main.yxmd yxmdVer should default to 2025.2"

        lint_report = lint_workflow(
            path=yxmd_path,
            expected_version="2025.2",
            designer_profile="2025.2",
            capability_registry=capability_registry,
            mode="demo",
        )
        assert not lint_report.errors, f"Lint errors: {lint_report.errors}"

        package_path = out_dir / "package.yxzp"
        create_package(source_dir=out_dir, output_path=package_path, data_dir=data_out)
        assert package_path.exists(), "package.yxzp was not created"

        with ZipFile(package_path, "r") as archive:
            names = set(archive.namelist())

        expected_entries = {
            "workflows/main.yxmd",
            "docs/README.md",
            "data/tickets.csv",
        }
        missing_entries = expected_entries - names
        assert not missing_entries, f"Missing expected package entries: {sorted(missing_entries)}"


def run_tier2_smoke(root: Path, capability_registry: dict) -> None:
    """Compile tier-2 coverage fixture and verify emitted signatures."""
    spec_path = root / "examples" / "tier2" / "workflow_spec_tier2.json"
    schema_path = root / "schemas" / "workflow_spec.schema.json"
    templates_dir = root / "templates"

    with tempfile.TemporaryDirectory(prefix="alteryx_builder_smoke_tier2_") as temp_dir:
        out_dir = Path(temp_dir) / "dist"
        out_dir.mkdir(parents=True, exist_ok=True)

        yxmd_path, report_path = compile_spec_file(
            spec_path=spec_path,
            out_dir=out_dir,
            schema_path=schema_path,
            templates_dir=templates_dir,
            capability_registry_path=root / "references" / "capability_registry.json",
        )

        assert yxmd_path.exists(), "tier2 main.yxmd was not created"
        assert report_path.exists(), "tier2 validation_report.json was not created"

        lint_report = lint_workflow(
            path=yxmd_path,
            expected_version="2025.2",
            designer_profile="2025.2",
            capability_registry=capability_registry,
            mode="demo",
        )
        assert not lint_report.errors, f"Tier-2 lint errors: {lint_report.errors}"

        signatures = extract_signatures(yxmd_path, capability_registry)
        tier2_rows = signatures.get("tier2_signatures") or []
        assert tier2_rows, "Tier-2 fixture emitted no tier-2 signatures"
        assert all(not row.get("generic_fallback") for row in tier2_rows), "Tier-2 fixture used generic fallback"
        assert all(row.get("required_semantics_ok") for row in tier2_rows), "Tier-2 fixture failed semantic minimum checks"



def run_golden_sanity_smoke(root: Path) -> None:
    """Validate base and golden workflows for static sanity."""
    paths = [
        root / "golden" / "workflow_01.yxmd",
        root / "golden" / "workflow_02.yxmd",
        root / "templates" / "base.yxmd",
    ]
    for path in paths:
        report = golden_check_one(path)
        assert not report["errors"], f"Golden sanity errors in {path.name}: {report['errors']}"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    capability_registry = load_capability_registry(root / "references" / "capability_registry.json")

    run_support_sla_smoke(root, capability_registry)
    run_tier2_smoke(root, capability_registry)
    run_golden_sanity_smoke(root)

    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
