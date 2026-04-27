#!/usr/bin/env python3
"""Validate workflow_spec JSON files against the workflow schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


def load_json(path: Path) -> Any:
    """Load JSON content from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_validation_errors(errors: Iterable[Any]) -> list[str]:
    """Return deterministic, user-friendly error messages."""
    formatted: list[str] = []
    for err in sorted(errors, key=lambda e: list(e.path)):
        location = "$." + ".".join(str(p) for p in err.path) if err.path else "$"
        formatted.append(f"{location}: {err.message}")
    return formatted


def validate_spec_document(spec_doc: dict[str, Any], schema_doc: dict[str, Any]) -> list[str]:
    """Validate a parsed spec document and return validation errors."""
    validator = Draft202012Validator(schema_doc)
    return format_validation_errors(validator.iter_errors(spec_doc))


def validate_spec_file(spec_path: Path, schema_path: Path) -> list[str]:
    """Validate a spec file and return a list of errors."""
    spec_doc = load_json(spec_path)
    schema_doc = load_json(schema_path)
    return validate_spec_document(spec_doc, schema_doc)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    default_schema = Path(__file__).resolve().parents[1] / "schemas" / "workflow_spec.schema.json"

    parser = argparse.ArgumentParser(description="Validate workflow_spec JSON against schema.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to workflow_spec.json")
    parser.add_argument(
        "--schema",
        default=default_schema,
        type=Path,
        help="Path to workflow_spec schema JSON",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    errors = validate_spec_file(args.spec, args.schema)

    if errors:
        print("Validation failed:")
        for line in errors:
            print(f"- {line}")
        return 1

    print("Spec is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
