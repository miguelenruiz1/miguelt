"""Canonical JSON + SHA-256 hashing for blockchain anchoring.

Produces deterministic hashes: same inputs → same output regardless of
field insertion order. Used to generate anchor hashes for supply chain events.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _canonical_value(obj: Any) -> Any:
    """Recursively sort dict keys and normalize values for canonical JSON."""
    if isinstance(obj, dict):
        return {k: _canonical_value(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_canonical_value(item) for item in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def canonical_json(data: dict[str, Any]) -> str:
    """Serialize data to canonical JSON string."""
    normalized = _canonical_value(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Serialize data to canonical JSON bytes."""
    return canonical_json(data).encode("utf-8")


def compute_anchor_hash(payload: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest of a canonical JSON payload."""
    raw = canonical_json_bytes(payload)
    return hashlib.sha256(raw).hexdigest()
