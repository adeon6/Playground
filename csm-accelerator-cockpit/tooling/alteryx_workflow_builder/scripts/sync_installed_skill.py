#!/usr/bin/env python3
"""Sync repository skill files to an installed skill directory with checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

IGNORED_NAMES = {".DS_Store"}
IGNORED_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def should_skip(path: Path) -> bool:
    if any(part in IGNORED_DIRS for part in path.parts):
        return True
    if path.name in IGNORED_NAMES:
        return True
    if path.suffix in IGNORED_SUFFIXES:
        return True
    return False


def collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if should_skip(rel):
            continue
        files.append(path)
    return files


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def remove_noise(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_file() and (rel.name in IGNORED_NAMES or rel.suffix in IGNORED_SUFFIXES):
            path.unlink(missing_ok=True)
    for path in sorted(root.rglob("*"), reverse=True):
        rel = path.relative_to(root)
        if path.is_dir() and rel.name in {"__pycache__"}:
            shutil.rmtree(path, ignore_errors=True)


def sync_tree(source: Path, target: Path) -> dict:
    source_files = collect_files(source)

    if target.exists():
        for path in sorted(target.rglob("*"), reverse=True):
            if path.is_file():
                rel = path.relative_to(target)
                if should_skip(rel):
                    path.unlink(missing_ok=True)
                    continue
                if not (source / rel).exists():
                    path.unlink(missing_ok=True)
            elif path.is_dir() and path.name in {"__pycache__"}:
                shutil.rmtree(path, ignore_errors=True)

    copied = 0
    for src in source_files:
        rel = src.relative_to(source)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    remove_noise(target)

    rows = []
    for src in source_files:
        rel = src.relative_to(source)
        dst = target / rel
        rows.append(
            {
                "path": rel.as_posix(),
                "source_sha256": sha256_file(src),
                "target_sha256": sha256_file(dst) if dst.exists() else "",
                "match": dst.exists() and sha256_file(src) == sha256_file(dst),
            }
        )

    return {
        "copied_files": copied,
        "file_count": len(rows),
        "all_match": all(row["match"] for row in rows),
        "files": rows,
    }


def run_smoke(source: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(source / "scripts" / "smoke_test.py")],
        cwd=str(source),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def parse_args() -> argparse.Namespace:
    default_source = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Sync repo skill tree into installed skill directory")
    parser.add_argument("--source", type=Path, default=default_source, help="Source skill directory")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("/Users/joshua.burkhow/.codex/skills/alteryx-workflow-builder"),
        help="Installed skill directory target",
    )
    parser.add_argument("--skip-smoke", action="store_true", help="Skip pre-sync smoke tests")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_source / "references" / "installed_sync_manifest.json",
        help="Output manifest JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    target = args.target.resolve()

    if not source.exists() or not source.is_dir():
        print(f"ERROR: source does not exist or is not a directory: {source}")
        return 2

    smoke_status = {"ran": not args.skip_smoke, "returncode": 0, "output": ""}
    if not args.skip_smoke:
        code, output = run_smoke(source)
        smoke_status["returncode"] = code
        smoke_status["output"] = output
        if code != 0:
            print("ERROR: smoke test failed; aborting sync")
            if output:
                print(output)
            return 1

    target.mkdir(parents=True, exist_ok=True)
    remove_noise(source)
    sync = sync_tree(source, target)

    payload = {
        "source": str(source),
        "target": str(target),
        "smoke": smoke_status,
        "sync": sync,
        "status": "PASS" if sync["all_match"] else "FAIL",
    }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.manifest}")
    print(json.dumps({"status": payload["status"], "file_count": sync["file_count"]}, indent=2))
    return 0 if sync["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
