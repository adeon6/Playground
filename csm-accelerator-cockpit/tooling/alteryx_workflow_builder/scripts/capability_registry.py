#!/usr/bin/env python3
"""Helpers for loading and querying tool capability registry data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "references" / "capability_registry.json"


def load_capability_registry(path: Path | None = None) -> dict[str, Any]:
    """Load capability registry JSON from disk."""
    registry_path = path or DEFAULT_REGISTRY_PATH
    with registry_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def default_profile(registry: dict[str, Any]) -> str:
    """Return default profile value from registry."""
    return str(registry.get("default_profile", "2025.2"))


def resolve_profile(
    registry: dict[str, Any],
    designer_profile: str | None = None,
    designer_version: str | None = None,
) -> str:
    """Resolve effective capability profile from user metadata."""
    profiles = set((registry.get("profiles") or {}).keys())
    chosen_profile = (designer_profile or "").strip()
    if chosen_profile in profiles:
        return chosen_profile

    version = (designer_version or "").strip()
    if version in profiles:
        return version

    return default_profile(registry)


def get_capability(registry: dict[str, Any], op: str) -> dict[str, Any] | None:
    """Return capability entry for operation name."""
    ops = registry.get("ops", {})
    return ops.get(op)


def is_available_for_profile(capability: dict[str, Any], profile: str) -> bool:
    """Return whether capability is available in the selected profile."""
    availability = capability.get("availability") or []
    return profile in availability


def plugin_to_op_map(registry: dict[str, Any], profile: str) -> dict[str, str]:
    """Build reverse mapping from plugin id to operation name for the profile."""
    out: dict[str, str] = {}
    for op, capability in (registry.get("ops") or {}).items():
        if not isinstance(capability, dict):
            continue
        if not is_available_for_profile(capability, profile):
            continue
        plugin = str(capability.get("plugin", "")).strip()
        if plugin:
            out[plugin] = op
        for alias in capability.get("plugin_aliases") or []:
            alias_text = str(alias).strip()
            if alias_text:
                out[alias_text] = op
    return out

