# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""Per-request test clock resolution (R-21, API.md sec8)."""

import os
from datetime import datetime, timezone

from fastapi import Header, HTTPException

from .errors import error_body


def test_clock_enabled() -> bool:
    return os.environ.get("SVCDESK_TEST_CLOCK", "").strip().lower() in ("1", "true")


def parse_instant(value: str) -> datetime:
    """Parse an RFC 3339 instant. Raises ValueError on anything malformed or naive."""
    dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        raise ValueError("naive timestamp is not an RFC 3339 instant")
    return dt.astimezone(timezone.utc)


def format_instant(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    if dt.microsecond == 0:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.isoformat().replace("+00:00", "Z")


def resolve_now(x_test_clock: str | None = Header(default=None, alias="X-Test-Clock")) -> datetime:
    """FastAPI dependency: real UTC time, unless test-clock mode is enabled and the header is present."""
    if test_clock_enabled() and x_test_clock is not None:
        try:
            return parse_instant(x_test_clock)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=error_body("validation", f"X-Test-Clock does not parse as an RFC 3339 instant: {exc}"),
            ) from exc
    return datetime.now(timezone.utc)
