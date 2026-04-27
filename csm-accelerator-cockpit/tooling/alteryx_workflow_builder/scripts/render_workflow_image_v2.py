#!/usr/bin/env python3
"""Compatibility wrapper for the canonical workflow renderer.

`render_workflow_image.py` is now the single maintained implementation.
Keep this shim so older commands continue to work.
"""

from __future__ import annotations

from render_workflow_image import main


if __name__ == "__main__":
    raise SystemExit(main())
