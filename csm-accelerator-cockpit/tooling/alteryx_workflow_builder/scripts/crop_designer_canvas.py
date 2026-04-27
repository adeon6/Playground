#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def crop_canvas(src: Path, dst: Path) -> None:
    img = Image.open(src)
    width, height = img.size

    # Pragmatic crop tuned for current Designer layout:
    # remove title/menu/tool palette area, left configuration pane, and bottom results pane.
    left = int(width * 0.35)
    top = int(height * 0.12)
    right = width - 6
    bottom = int(height * 0.83)

    cropped = img.crop((left, top, right, bottom))
    dst.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dst)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crop a full Designer screenshot down to the canvas area.")
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    src = Path(args.source).resolve()
    dst = Path(args.out).resolve()
    crop_canvas(src, dst)
    print(f"Cropped {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
