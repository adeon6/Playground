#!/usr/bin/env python3
"""Smoke test for example workflow compile and package flow."""

from __future__ import annotations

import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from compile import compile_spec_file
from package_yxzp import create_package
from lint_yxmd import lint_workflow


def main() -> int:
    """Run smoke test against examples/support_sla."""
    root = Path(__file__).resolve().parents[1]
    spec_path = root / "examples" / "support_sla" / "workflow_spec.json"
    schema_path = root / "schemas" / "workflow_spec.schema.json"
    templates_dir = root / "templates"
    sample_data_dir = root / "examples" / "support_sla" / "data"

    with tempfile.TemporaryDirectory(prefix="alteryx_builder_smoke_") as temp_dir:
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
        )

        assert yxmd_path.exists(), "main.yxmd was not created"
        assert report_path.exists(), "validation_report.json was not created"

        tree = ET.parse(yxmd_path)
        assert tree.getroot().attrib.get("yxmdVer") == "2025.1", "main.yxmd yxmdVer should default to 2025.1"

        lint_report = lint_workflow(path=yxmd_path, expected_version="2025.1")
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

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
