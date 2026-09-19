# ai-generated: 90% - Claude Code wrote this test module; reviewed and accepted as-is
"""Unit tests for SLA due-instant math (API.md sec4 vectors) and breach/pause (sec5)."""

from datetime import datetime, timedelta, timezone

import pytest

from svcdesk.sla import due_instants, evaluate_sla


def _z(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# id, priority, created_at, ack_due(business-or-wallclock-per-C1), resolve_due(same)
# This service's C1 = wallclock, so P1 rows use the wall-clock columns from API.md sec4;
# every other priority always uses the business-hours columns.
VECTORS = [
    ("T1", "P1", "2026-10-14T10:00:00Z", "2026-10-14T10:15:00Z", "2026-10-14T14:00:00Z"),
    ("T2", "P3", "2026-10-16T13:30:00Z", "2026-10-19T09:30:00Z", "2026-10-21T13:30:00Z"),
    ("T3", "P1", "2026-10-16T15:00:00Z", "2026-10-16T15:15:00Z", "2026-10-16T19:00:00Z"),
    ("T4", "P2", "2026-10-17T10:00:00Z", "2026-10-19T07:00:00Z", "2026-10-19T14:00:00Z"),
    ("T5", "P4", "2027-01-14T14:30:00Z", "2027-01-15T14:30:00Z", "2027-01-27T14:30:00Z"),
    ("T6", "P1", "2027-01-15T15:50:00Z", "2027-01-15T16:05:00Z", "2027-01-15T19:50:00Z"),
    ("T7", "P2", "2026-10-14T10:00:00Z", "2026-10-14T11:00:00Z", "2026-10-15T10:00:00Z"),
    ("T8", "P3", "2026-10-23T13:00:00Z", "2026-10-26T10:00:00Z", "2026-10-28T14:00:00Z"),
]


@pytest.mark.parametrize("vector_id,priority,created_at,ack_due,resolve_due", VECTORS)
def test_due_instant_vectors(vector_id, priority, created_at, ack_due, resolve_due):
    got_ack, got_resolve = due_instants(_z(created_at), priority)
    assert got_ack == _z(ack_due), f"{vector_id} ack_due"
    assert got_resolve == _z(resolve_due), f"{vector_id} resolve_due"


def test_ack_breach_equality_is_not_a_breach():
    created_at = _z("2026-10-14T10:00:00Z")  # P1: ack due at +15min, wall clock
    result = evaluate_sla("P1", "new", created_at, None, None, now=created_at + timedelta(minutes=15))
    assert result["ack_breached"] is False


def test_ack_breach_one_second_after_due_is_a_breach():
    created_at = _z("2026-10-14T10:00:00Z")
    now = created_at + timedelta(minutes=15, seconds=1)
    result = evaluate_sla("P1", "new", created_at, None, None, now=now)
    assert result["ack_breached"] is True


def test_ack_breach_false_when_acknowledged_before_due():
    created_at = _z("2026-10-14T10:00:00Z")
    acknowledged_at = created_at + timedelta(minutes=5)
    result = evaluate_sla(
        "P1", "acknowledged", created_at, acknowledged_at, None, now=created_at + timedelta(days=1)
    )
    assert result["ack_breached"] is False


def test_paused_true_on_saturday_for_open_non_p1_ticket():
    created_at = _z("2026-10-16T13:30:00Z")  # P3
    saturday = _z("2026-10-17T10:00:00Z")
    result = evaluate_sla("P3", "in_progress", created_at, None, None, now=saturday)
    assert result["paused"] is True


def test_paused_false_on_monday_business_hours():
    created_at = _z("2026-10-16T13:30:00Z")  # P3
    monday = _z("2026-10-19T09:00:00Z")
    result = evaluate_sla("P3", "in_progress", created_at, None, None, now=monday)
    assert result["paused"] is False


def test_p1_never_paused_even_outside_business_hours():
    created_at = _z("2026-10-16T15:00:00Z")  # P1
    saturday = _z("2026-10-17T10:00:00Z")
    result = evaluate_sla("P1", "in_progress", created_at, None, None, now=saturday)
    assert result["paused"] is False


def test_paused_false_once_resolved():
    created_at = _z("2026-10-16T13:30:00Z")  # P3
    saturday = _z("2026-10-17T10:00:00Z")
    result = evaluate_sla("P3", "resolved", created_at, None, saturday, now=saturday)
    assert result["paused"] is False
