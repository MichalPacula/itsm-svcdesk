# ai-generated: 80% - Claude Code wrote the RED histogram middleware and /metrics; ladder chosen from my measurement
"""RED instrumentation (MONITORING-SPEC M-03..M-07): one histogram, route templates, constant-cardinality labels."""

import time

from prometheus_client import Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

# Finite `le` boundaries in seconds (M-06: at most 30). Measured q (p99) of /kb/search was ~0.20 s (slow mode
# roughly 0.17-0.25 s): 10 ms steps over 0.15-0.25 s resolve a band well beyond +-10 % around it; the rest is coarse.
BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125,
    0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25,
    0.3, 0.5, 1.0, 2.5, 5.0,
)

UNMATCHED_ROUTE = "unmatched"
EXPOSITION_TYPE = "text/plain; version=0.0.4; charset=utf-8"  # M-03

REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP server requests.",
    ["http_request_method", "http_route", "http_response_status_code"],
    buckets=BUCKETS,
)


class MetricsMiddleware:
    """Pure ASGI middleware: times the whole request and observes it exactly once, after the route is known."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            template = getattr(route, "path", None) or UNMATCHED_ROUTE
            REQUEST_DURATION.labels(scope["method"], template, str(status["code"])).observe(
                time.perf_counter() - start
            )


def metrics_response(_: Request) -> Response:
    return Response(generate_latest(), headers={"Content-Type": EXPOSITION_TYPE})
