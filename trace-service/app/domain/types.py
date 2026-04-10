"""Enumerations and type aliases used across the domain."""
from enum import StrEnum


class WalletStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class AssetState(StrEnum):
    # ─── Core states ──────────────────────────────────────────────────────────
    IN_TRANSIT = "in_transit"
    IN_CUSTODY = "in_custody"
    LOADED = "loaded"
    QC_PASSED = "qc_passed"
    QC_FAILED = "qc_failed"
    RELEASED = "released"
    BURNED = "burned"
    # ─── Extended states (Phase 1A) ───────────────────────────────────────────
    CUSTOMS_HOLD = "customs_hold"
    DAMAGED = "damaged"
    DELIVERED = "delivered"
    SEALED = "sealed"
    RETURNED = "returned"


# Terminal states — no further events allowed
TERMINAL_STATES: frozenset[AssetState] = frozenset({
    AssetState.RELEASED,
    AssetState.BURNED,
    AssetState.DELIVERED,
})

# All non-terminal states (convenience set for RELEASED/BURN/DAMAGED)
_NON_TERMINAL: frozenset[AssetState] = frozenset(
    s for s in AssetState if s not in TERMINAL_STATES
)


class EventType(StrEnum):
    # ─── Original events ──────────────────────────────────────────────────────
    CREATED = "CREATED"
    HANDOFF = "HANDOFF"
    ARRIVED = "ARRIVED"
    LOADED = "LOADED"
    QC = "QC"
    RELEASED = "RELEASED"
    BURN = "BURN"
    # ─── Extended events (Phase 1A) ───────────────────────────────────────────
    PICKUP = "PICKUP"                       # recolección en origen
    GATE_IN = "GATE_IN"                     # ingreso a instalación
    GATE_OUT = "GATE_OUT"                   # salida de instalación
    DEPARTED = "DEPARTED"                   # salió del punto actual
    CUSTOMS_HOLD = "CUSTOMS_HOLD"           # retenido en aduana
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"     # liberado de aduana
    DAMAGED = "DAMAGED"                     # daño reportado
    DELIVERED = "DELIVERED"                 # entregado al consignatario
    SEALED = "SEALED"                       # contenedor/carga sellada
    UNSEALED = "UNSEALED"                   # sello removido
    TEMPERATURE_CHECK = "TEMPERATURE_CHECK" # lectura de temperatura
    INSPECTION = "INSPECTION"               # inspección general
    CONSOLIDATED = "CONSOLIDATED"           # consolidado con otras cargas
    DECONSOLIDATED = "DECONSOLIDATED"       # desconsolidado
    NOTE = "NOTE"                           # nota/anotación libre
    RETURN = "RETURN"                       # devolución / logística inversa
    # ─── Compliance events ───────────────────────────────────────────────────
    COMPLIANCE_VERIFIED = "COMPLIANCE_VERIFIED"  # EUDR screening anclado


# ─── Informational events: do NOT change asset state ──────────────────────────
INFORMATIONAL_EVENTS: frozenset[EventType] = frozenset({
    EventType.TEMPERATURE_CHECK,
    EventType.INSPECTION,
    EventType.CONSOLIDATED,
    EventType.DECONSOLIDATED,
    EventType.NOTE,
    EventType.COMPLIANCE_VERIFIED,
})


# Maps event_type -> resulting asset state
# Informational events are NOT in this map (they preserve current state)
EVENT_STATE_TRANSITIONS: dict[EventType, AssetState] = {
    # Original
    EventType.CREATED: AssetState.IN_CUSTODY,
    EventType.HANDOFF: AssetState.IN_TRANSIT,
    EventType.ARRIVED: AssetState.IN_CUSTODY,
    EventType.LOADED: AssetState.LOADED,
    EventType.RELEASED: AssetState.RELEASED,
    EventType.BURN: AssetState.BURNED,
    # Extended
    EventType.PICKUP: AssetState.IN_TRANSIT,
    EventType.GATE_IN: AssetState.IN_CUSTODY,
    EventType.GATE_OUT: AssetState.IN_TRANSIT,
    EventType.DEPARTED: AssetState.IN_TRANSIT,
    EventType.CUSTOMS_HOLD: AssetState.CUSTOMS_HOLD,
    EventType.CUSTOMS_CLEARED: AssetState.IN_CUSTODY,
    EventType.DAMAGED: AssetState.DAMAGED,
    EventType.DELIVERED: AssetState.DELIVERED,
    EventType.SEALED: AssetState.SEALED,
    EventType.UNSEALED: AssetState.LOADED,
    EventType.RETURN: AssetState.RETURNED,
}


# Defines which asset states are valid origins for each event.
# Operations not in this map (CREATED) are handled separately by the service.
# Informational events accept any non-terminal state.
VALID_FROM_STATES: dict[EventType, frozenset[AssetState]] = {
    # ─── Original events ──────────────────────────────────────────────────────
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
        AssetState.IN_CUSTODY,  # allow QC after arrival
        AssetState.LOADED,
        AssetState.QC_FAILED,  # allow re-inspection after failure
    }),
    EventType.RELEASED: _NON_TERMINAL,
    EventType.BURN: _NON_TERMINAL,
    # ─── Extended events ──────────────────────────────────────────────────────
    EventType.PICKUP: frozenset({
        AssetState.IN_CUSTODY,
    }),
    EventType.GATE_IN: frozenset({
        AssetState.IN_TRANSIT,
    }),
    EventType.GATE_OUT: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.LOADED,
        AssetState.QC_PASSED,
        AssetState.QC_FAILED,
    }),
    EventType.DEPARTED: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.LOADED,
        AssetState.SEALED,
    }),
    EventType.CUSTOMS_HOLD: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.IN_TRANSIT,
    }),
    EventType.CUSTOMS_CLEARED: frozenset({
        AssetState.CUSTOMS_HOLD,
    }),
    EventType.DAMAGED: _NON_TERMINAL,
    EventType.DELIVERED: frozenset({
        AssetState.IN_CUSTODY,
        AssetState.IN_TRANSIT,
        AssetState.QC_PASSED,
    }),
    EventType.SEALED: frozenset({
        AssetState.LOADED,
    }),
    EventType.UNSEALED: frozenset({
        AssetState.SEALED,
    }),
    EventType.RETURN: frozenset({
        AssetState.DELIVERED,
        AssetState.IN_TRANSIT,
        AssetState.IN_CUSTODY,
    }),
    # Informational events — any non-terminal state
    EventType.TEMPERATURE_CHECK: _NON_TERMINAL,
    EventType.INSPECTION: _NON_TERMINAL,
    EventType.CONSOLIDATED: _NON_TERMINAL,
    EventType.DECONSOLIDATED: _NON_TERMINAL,
    EventType.NOTE: _NON_TERMINAL,
    EventType.COMPLIANCE_VERIFIED: _NON_TERMINAL,
}
