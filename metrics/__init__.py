# ai-generated: 85% - Claude Code drafted this package from METRIC-SPEC.md; reviewed and accepted
"""The DORA metrics engine (lab2/METRIC-SPEC.md).

A pure, framework-free computation over a parsed event log: no I/O, no clock, no HTTP. The route
that calls this (POST /dora/metrics) lives in src/svcdesk/main.py, outside this package, per
PREDICTION.md's feature_path.
"""

from datetime import datetime

from .engine import compute
from .errors import MetricsError
from .validation import parse_and_validate

__all__ = ["MetricsError", "compute_metrics"]


def compute_metrics(raw_events: object, window_from: datetime, window_to: datetime) -> dict:
    """Validate `raw_events` against METRIC-SPEC.md sec 1, then compute the metric object.

    Raises MetricsError on a malformed log. Does not validate the window itself (that is the
    caller's HTTP-contract concern); window_from/window_to must already be timezone-aware UTC
    instants with window_to > window_from.
    """
    log = parse_and_validate(raw_events)
    return compute(log, window_from, window_to)
