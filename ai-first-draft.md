---
lab3_first_draft:
  source: ai
  tool: "Claude Sonnet (fresh Claude Code sub-agent, no tools and no project context, 10 October 2026)"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
  verdict: refuted
  evidence: {p99_seconds: 0.1994, bucket: [0.1, 0.25], relative_width: 0.752}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1994, bucket: [0.04, 0.5], relative_width: 2.307}
---
<!-- ai-generated: 40% - the verdicts and arithmetic are mine, drafted with Claude Code; the exchange below is the assistant's verbatim -->

# The assistant's first draft, and two verdicts

## Prompt

I run a small Python (FastAPI) service called svcdesk with an endpoint GET /kb/search that calls an upstream knowledge-base index on every request. I am adding a Prometheus histogram named http_server_request_duration_seconds (labels: http_request_method, http_route, http_response_status_code). Please give me (1) the histogram bucket boundaries in seconds that I should use, and (2) a Prometheus alerting rule for this endpoint.

## Answer

**(1) Bucket boundaries (seconds)**

The endpoint calls an upstream index on every request, so latencies should run from a few ms (cache or fast index) up to several seconds (slow upstream or timeout). The OpenTelemetry HTTP-server default buckets are a reasonable base. Add finer resolution around the likely SLO threshold and extend the top end to cover your upstream timeout:

```python
from prometheus_client import Histogram

REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP server request duration in seconds",
    ["http_request_method", "http_route", "http_response_status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)
```

(`+Inf` is added automatically.) Guidelines:
- Make sure one boundary sits exactly at your SLO threshold. The alert below uses 0.5s, so 0.5 must be a bucket edge. Otherwise the ratio is only approximate.
- Keep the top bucket at or above your upstream client timeout (10s here). If the timeout is 30s, add 15 and 30.
- Use `http_route` as the route template (`/kb/search`), never the raw path. Don't put query strings or search terms in labels, to avoid high cardinality.

**(2) Alerting rules for GET /kb/search**

```yaml
groups:
  - name: svcdesk-kb-search
    rules:
      # Latency: more than 5% of requests slower than 500ms for 10 minutes
      - alert: KbSearchHighLatency
        expr: |
          (
            1 - (
              sum(rate(http_server_request_duration_seconds_bucket{http_route="/kb/search",http_request_method="GET",le="0.5"}[5m]))
              /
              sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search",http_request_method="GET"}[5m]))
            )
          ) > 0.05
          and
          sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search",http_request_method="GET"}[5m])) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "GET /kb/search: more than 5% of requests slower than 500ms"
          description: "Check the upstream knowledge-base index. Current p95 is {{ with printf `histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{http_route=\"/kb/search\"}[5m])))` | query }}{{ . | first | value | humanizeDuration }}{{ end }}."

      # p95 latency (alternative or complement)
      - alert: KbSearchP95Slow
        expr: |
          histogram_quantile(0.95,
            sum by (le) (rate(http_server_request_duration_seconds_bucket{http_route="/kb/search",http_request_method="GET"}[5m]))
          ) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "GET /kb/search p95 latency above 1s"

      # Errors: 5xx ratio above 5% (upstream failures usually show up as 502/503/504 or 500)
      - alert: KbSearchHighErrorRate
        expr: |
          (
            sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search",http_request_method="GET",http_response_status_code=~"5.."}[5m]))
            /
            sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search",http_request_method="GET"}[5m]))
          ) > 0.05
          and
          sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search",http_request_method="GET"}[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "GET /kb/search 5xx rate above 5%"
```

Notes:
- The `and ... > 0.1` clause suppresses alerts when traffic is too low for the ratio to mean anything (under about 6 requests per minute). Adjust it to your real traffic.
- If the endpoint can return no samples (no traffic), these expressions return nothing and the alert stays inactive. If you also want to catch the endpoint going silent, add a separate `absent_over_time(...)` or a `up == 0` rule.
- Tune the 0.5s and 1s thresholds and the 5% budget to your actual SLO. If the upstream is normally slow, measure a baseline for a few days first.

## Verdict on the draft ladder

I measured q = 199.4 ms with `./itsmlab.sh load 3` (open-loop, 40 req/s, 60 s); I use 0.1994 s. The draft ladder is Python's default, and it puts q in (0.1, 0.25]. That bucket is 0.15 s wide, which is 0.15 / 0.1994 = 75.2 % of q, against a limit of 20 %. `histogram_quantile` assumes the requests inside the bucket are spread evenly, so from this bucket it could report anything between 0.1 and 0.25 s; with the cumulative counts at hand it interpolates linearly, and a true p99 at 0.19 or at 0.24 would look alike to within a few ms of noise. At 0.95q = 0.189 and 1.05q = 0.209 the bucket is the same, so the case is not close to call. **Verdict: refuted.**

## The draft alert rule

The three rules are single-window rules on a 5-minute range with fixed 5 % thresholds, and none has a short window, so none stops soon after a burn stops, and none is tied to an error budget. Its `severity: warning/critical` labels are not the P1/P2/P3 that Lab 4 routes on. I kept from it the idea of a traffic floor and the `http_route="/kb/search"` filter, and I replaced the rest with two multiwindow burn-rate alerts on the availability SLI (`prometheus/alerts.yml`). The latency rule's `le="0.5"` is a boundary of the draft ladder but 0.5 s is far above my p99, so it would never fire on the slow mode; my latency SLI uses 0.25 s, which is a boundary of my ladder.

## Verdict on the instructor's flawed ladder

The flawed ladder spends twelve of its fourteen boundaries below 40 ms, where the median (about 25 ms) lives, and then jumps to 0.5 s. My q = 0.1994 s lands in (0.04, 0.5], 0.46 s wide: 0.46 / 0.1994 = 230.7 % of q (2.307). Prometheus could report any value between 40 ms and 500 ms for it. **Verdict: refuted**, as for every profile.
