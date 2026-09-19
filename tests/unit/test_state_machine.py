# ai-generated: 90% - Claude Code wrote this test module; reviewed and accepted as-is
"""Unit tests for the transition table and the reopen window (API.md sec6; decision C2 = immutable)."""

from datetime import datetime, timedelta, timezone

import pytest

from svcdesk.errors import InvalidTransitionError
from svcdesk.state_machine import apply_transition, can_reopen


def test_valid_lifecycle_path():
    assert apply_transition("new", "ack") == "acknowledged"
    assert apply_transition("acknowledged", "start") == "in_progress"
    assert apply_transition("in_progress", "resolve") == "resolved"
    assert apply_transition("resolved", "close") == "closed"


@pytest.mark.parametrize(
    "state,action",
    [
        ("new", "resolve"),
        ("acknowledged", "resolve"),  # L1-CORE-2.49
        ("new", "close"),
        ("in_progress", "close"),
        ("acknowledged", "ack"),
        ("new", "start"),
        ("closed", "ack"),
    ],
)
def test_invalid_shortcuts_are_refused(state, action):
    with pytest.raises(InvalidTransitionError):
        apply_transition(state, action)


def _now():
    return datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)


def test_reopen_allowed_within_7_days():
    resolved_at = _now() - timedelta(days=6)
    can_reopen("resolved", resolved_at, _now())  # must not raise


def test_reopen_refused_after_7_days_and_1_second():
    resolved_at = _now() - timedelta(days=7, seconds=1)
    with pytest.raises(InvalidTransitionError):
        can_reopen("resolved", resolved_at, _now())


def test_reopen_refused_for_new_ticket():
    with pytest.raises(InvalidTransitionError):
        can_reopen("new", None, _now())


def test_reopen_refused_for_closed_ticket_even_recently():
    resolved_at = _now() - timedelta(days=1)
    with pytest.raises(InvalidTransitionError):
        can_reopen("closed", resolved_at, _now())
