"""Enumerations and type aliases used across the domain."""
from enum import StrEnum


class WalletStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class AssetState(StrEnum):
    IN_TRANSIT = "in_transit"
    IN_CUSTODY = "in_custody"
    LOADED = "loaded"
    QC_PASSED = "qc_passed"
    QC_FAILED = "qc_failed"
    RELEASED = "released"
    BURNED = "burned"


class EventType(StrEnum):
    CREATED = "CREATED"
    HANDOFF = "HANDOFF"
    ARRIVED = "ARRIVED"
    LOADED = "LOADED"
    QC = "QC"
    RELEASED = "RELEASED"
    BURN = "BURN"


# Maps event_type -> resulting asset state
EVENT_STATE_TRANSITIONS: dict[EventType, AssetState] = {
    EventType.CREATED: AssetState.IN_CUSTODY,
    EventType.HANDOFF: AssetState.IN_TRANSIT,
    EventType.ARRIVED: AssetState.IN_CUSTODY,
    EventType.LOADED: AssetState.LOADED,
    EventType.RELEASED: AssetState.RELEASED,
    EventType.BURN: AssetState.BURNED,
}

# Defines which asset states are valid origins for each event.
# Operations not in this map (CREATED) are handled separately by the service.
VALID_FROM_STATES: dict[EventType, frozenset[AssetState]] = {
    EventType.HANDOFF: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.IN_TRANSIT,
        AssetState.LOADED,
        AssetState.QC_PASSED,
        AssetState.QC_FAILED,
    }),
    EventType.ARRIVED: frozenset({
        AssetState.IN_TRANSIT,
    }),
    EventType.LOADED: frozenset({
        AssetState.IN_CUSTODY,
    }),
    EventType.QC: frozenset({
        AssetState.LOADED,
        AssetState.QC_FAILED,  # allow re-inspection after failure
    }),
    EventType.RELEASED: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.IN_TRANSIT,
        AssetState.LOADED,
        AssetState.QC_PASSED,
        AssetState.QC_FAILED,
    }),
    EventType.BURN: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.IN_TRANSIT,
        AssetState.LOADED,
        AssetState.QC_PASSED,
        AssetState.QC_FAILED,
    }),
}
