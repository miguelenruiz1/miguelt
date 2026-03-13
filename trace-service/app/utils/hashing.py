"""SHA-256 chained event hashing."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from app.utils.json_canonical import canonical_json_bytes


def compute_event_hash(
    *,
    asset_id: uuid.UUID,
    event_type: str,
    from_wallet: str | None,
    to_wallet: str | None,
    timestamp: datetime,
    location: dict[str, Any] | None,
    data: dict[str, Any],
    prev_event_hash: str | None,
) -> str:
    """
    Compute SHA-256 hash of a canonical JSON payload representing a custody event.

    The hash is deterministic: same inputs → same output, regardless of field insertion order.
    This forms the cryptographic chain of custody.
    """
    payload: dict[str, Any] = {
        "asset_id": str(asset_id),
        "event_type": event_type,
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "timestamp": timestamp.isoformat(),
        "location": location,
        "data": data,
        "prev_event_hash": prev_event_hash,
    }
    raw = canonical_json_bytes(payload)
    return hashlib.sha256(raw).hexdigest()
