# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""Transition table and reopen window (API.md sec6; decision C2 = immutable, DECISIONS.md)."""

from datetime import datetime, timedelta
from typing import Optional

from .errors import InvalidTransitionError

TRANSITIONS: dict[tuple[str, str], str] = {
    ("new", "ack"): "acknowledged",
    ("acknowledged", "start"): "in_progress",
    ("in_progress", "resolve"): "resolved",
    ("resolved", "close"): "closed",
}

REOPEN_WINDOW = timedelta(days=7)


def apply_transition(current_state: str, action: str) -> str:
    """Returns the new state, or raises InvalidTransitionError (409) for anything not in the table."""
    key = (current_state, action)
    if key not in TRANSITIONS:
        raise InvalidTransitionError(f"cannot {action} a ticket in state '{current_state}'")
    return TRANSITIONS[key]


def can_reopen(state: str, resolved_at: Optional[datetime], now: datetime) -> None:
    """Raises InvalidTransitionError unless the ticket is `resolved` and within the 7-day window.

    A `closed` ticket is never reopenable under this service's C2 = immutable decision
    (FR-009, FR-010): only the `resolved` branch below ever succeeds.
    """
    if state != "resolved":
        raise InvalidTransitionError(f"cannot reopen a ticket in state '{state}'")
    if resolved_at is None or now > resolved_at + REOPEN_WINDOW:
        raise InvalidTransitionError("reopen window (7 days from resolution) has expired")
