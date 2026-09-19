# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""SLA due instants, breach and pause (API.md sec4-5; decision C1 = wallclock, DECISIONS.md).

Business-hours algorithm: Monday-Friday, the half-open window [08:00:00, 16:00:00) in
Europe/Warsaw (DST-aware via zoneinfo). A target that ends exactly at closing time is due
at that closing instant, not the next opening (the tie rule, API.md sec4, vector T4).
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
BUSINESS_START = time(8, 0, 0)
BUSINESS_END = time(16, 0, 0)

TARGETS: dict[str, tuple[timedelta, timedelta]] = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}


def _is_business_day(d: date) -> bool:
    return d.weekday() < 5  # Monday=0 .. Friday=4


def _in_business_window(now_utc: datetime) -> bool:
    local = now_utc.astimezone(WARSAW)
    return _is_business_day(local.date()) and BUSINESS_START <= local.time() < BUSINESS_END


def _advance_business(start_utc: datetime, duration: timedelta) -> datetime:
    """Walk forward window by window, consuming `duration` of business time from `start_utc`."""
    cursor = start_utc.astimezone(WARSAW)
    remaining = duration
    while True:
        window_start = None
        day_end = None
        if _is_business_day(cursor.date()):
            day_start = cursor.replace(hour=8, minute=0, second=0, microsecond=0)
            day_end = cursor.replace(hour=16, minute=0, second=0, microsecond=0)
            if cursor < day_start:
                window_start = day_start
            elif cursor < day_end:
                window_start = cursor

        if window_start is not None:
            available = day_end - window_start
            if remaining <= available:
                return (window_start + remaining).astimezone(timezone.utc)
            remaining -= available

        next_day = cursor.date() + timedelta(days=1)
        cursor = datetime.combine(next_day, time(0, 0), tzinfo=WARSAW)


def due_instants(created_at: datetime, priority: str) -> tuple[datetime, datetime]:
    """Ack-due and resolve-due instants for a ticket (FR-011, FR-012, FR-013)."""
    ack_target, resolve_target = TARGETS[priority]
    if priority == "P1":  # decision C1 = wallclock: P1 never pauses
        return created_at + ack_target, created_at + resolve_target
    return _advance_business(created_at, ack_target), _advance_business(created_at, resolve_target)


def evaluate_sla(
    priority: str,
    state: str,
    created_at: datetime,
    acknowledged_at: Optional[datetime],
    resolved_at: Optional[datetime],
    now: datetime,
) -> dict:
    """FR-014, FR-015, FR-016: due instants, breach flags and pause, all evaluated at `now`."""
    ack_due, resolve_due = due_instants(created_at, priority)

    if acknowledged_at is None:
        ack_breached = now > ack_due
    else:
        ack_breached = acknowledged_at > ack_due

    if resolved_at is None:
        resolve_breached = now > resolve_due
    else:
        resolve_breached = resolved_at > resolve_due

    paused = state not in ("resolved", "closed") and priority != "P1" and not _in_business_window(now)

    return {
        "ack_due_at": ack_due,
        "resolve_due_at": resolve_due,
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }
