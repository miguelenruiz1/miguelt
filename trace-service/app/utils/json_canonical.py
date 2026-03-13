"""Canonical JSON serialization for deterministic hashing.

Rules:
- Keys sorted lexicographically (recursive)
- No whitespace
- ensure_ascii=True for byte-level reproducibility
- None values included as JSON null (not omitted)
"""
from __future__ import annotations

import json
from typing import Any


def _canonical_value(obj: Any) -> Any:
    """Recursively sort dict keys and normalize values."""
    if isinstance(obj, dict):
        return {k: _canonical_value(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_canonical_value(item) for item in obj]
    return obj


def canonical_json(data: dict[str, Any]) -> str:
    """Serialize data to canonical JSON string."""
    normalized = _canonical_value(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Serialize data to canonical JSON bytes."""
    return canonical_json(data).encode("utf-8")
