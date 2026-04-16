"""Pure unit tests for the custody state machine.

These exercise the `VALID_FROM_STATES` / `EVENT_STATE_TRANSITIONS` /
`TERMINAL_STATES` mappings without any DB, HTTP, or Redis dependency.

Catching a regression here is the single cheapest line of defense against
breaking the chain of custody invariants.
"""
from __future__ import annotations

import pytest

from app.domain.types import (
    AssetState,
    EventType,
    EVENT_STATE_TRANSITIONS,
    INFORMATIONAL_EVENTS,
    TERMINAL_STATES,
    VALID_FROM_STATES,
)


# ── HANDOFF ─────────────────────────────────────────────────────────────────


class TestValidTransitionsHANDOFF:
    def test_handoff_from_in_custody(self) -> None:
        assert AssetState.IN_CUSTODY in VALID_FROM_STATES[EventType.HANDOFF]

    def test_handoff_from_in_transit(self) -> None:
        assert AssetState.IN_TRANSIT in VALID_FROM_STATES[EventType.HANDOFF]

    def test_handoff_lands_in_transit(self) -> None:
        assert EVENT_STATE_TRANSITIONS[EventType.HANDOFF] == AssetState.IN_TRANSIT


# ── RELEASED / BURN (terminal transitions from any non-terminal) ────────────


class TestTerminalTransitions:
    def test_invalid_transition_RELEASED_to_HANDOFF(self) -> None:
        """RELEASED is terminal → cannot HANDOFF from RELEASED."""
        assert AssetState.RELEASED in TERMINAL_STATES
        assert AssetState.RELEASED not in VALID_FROM_STATES[EventType.HANDOFF]

    def test_burned_cannot_be_handed_off(self) -> None:
        assert AssetState.BURNED in TERMINAL_STATES
        assert AssetState.BURNED not in VALID_FROM_STATES[EventType.HANDOFF]

    @pytest.mark.parametrize(
        "state",
        [
            AssetState.IN_CUSTODY,
            AssetState.IN_TRANSIT,
            AssetState.LOADED,
            AssetState.QC_PASSED,
            AssetState.QC_FAILED,
            AssetState.CUSTOMS_HOLD,
            AssetState.DAMAGED,
            AssetState.SEALED,
            AssetState.RETURNED,
        ],
    )
    def test_burn_from_any_non_terminal(self, state: AssetState) -> None:
        """BURN must be allowed from every non-terminal state."""
        assert state in VALID_FROM_STATES[EventType.BURN]

    @pytest.mark.parametrize("state", list(TERMINAL_STATES))
    def test_burn_rejected_from_terminal(self, state: AssetState) -> None:
        """BURN must be rejected from terminal states."""
        assert state not in VALID_FROM_STATES[EventType.BURN]


# ── ARRIVED (tight: only from IN_TRANSIT) ───────────────────────────────────


class TestARRIVED:
    def test_arrived_only_from_in_transit(self) -> None:
        assert VALID_FROM_STATES[EventType.ARRIVED] == frozenset({AssetState.IN_TRANSIT})

    def test_arrived_rejected_from_in_custody(self) -> None:
        assert AssetState.IN_CUSTODY not in VALID_FROM_STATES[EventType.ARRIVED]


# ── Informational events preserve state ────────────────────────────────────


class TestInformationalEvents:
    @pytest.mark.parametrize("event", list(INFORMATIONAL_EVENTS))
    def test_informational_not_in_state_transitions(self, event: EventType) -> None:
        """Informational events must not resolve to a new state."""
        assert event not in EVENT_STATE_TRANSITIONS

    def test_compliance_verified_is_informational(self) -> None:
        assert EventType.COMPLIANCE_VERIFIED in INFORMATIONAL_EVENTS
