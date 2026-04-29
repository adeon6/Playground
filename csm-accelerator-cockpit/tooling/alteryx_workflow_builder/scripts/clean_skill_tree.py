#!/usr/bin/env python3
"""Remove non-distributable artifacts from a skill tree."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


IGNORE_FILE_NAMES = {".DS_Store"}
IGNORE_SUFFIXES = {".pyc", ".pyo"}
IGNORE_DIR_NAMES = {"__pycache__"}


def clean_tree(root: Path, dry_run: bool) -> dict:
    removed_files: list[str] = []
    removed_dirs: list[str] = []

    for path in sorted(root.rglob("*")):
        if path.is_file() and (path.name in IGNORE_FILE_NAMES or path.suffix in IGNORE_SUFFIXES):
            removed_files.append(str(path))
            if not dry_run:
                path.unlink(missing_ok=True)

    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and path.name in IGNORE_DIR_NAMES:
            removed_dirs.append(str(path))
            if not dry_run:
                shutil.rmtree(path, ignore_errors=True)

    return {
        "root": str(root),
        "dry_run": dry_run,
        "removed_file_count": len(removed_files),
        "removed_dir_count": len(removed_dirs),
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove .DS_Store/__pycache__/pyc artifacts")
    parser.add_argument("root", type=Path, nargs="?", default=Path("."), help="Root directory to clean")
    parser.add_argument("--dry-run", action="store_true", help="Only report removals")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root must be an existing directory: {root}")
        return 2

    payload = clean_tree(root, args.dry_run)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")

    print(json.dumps({
        "removed_file_count": payload["removed_file_count"],
        "removed_dir_count": payload["removed_dir_count"],
        "dry_run": payload["dry_run"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
