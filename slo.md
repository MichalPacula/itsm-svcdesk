---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.99
      threshold_seconds: 0.25
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.25"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 50% - Claude Code drafted the structure and arithmetic; the numbers come from my own measurement -->

# SLO for `GET /kb/search`

## Availability

Good requests are `/kb/search` answers that are not 5xx; valid are all `/kb/search` answers. Objective 99 % over 28 days:
a budget of 1 % of requests, which is 0.01 x 40,320 min = 403.2 minutes of full outage. `kb-index` fails by itself: in my
runs 4 to 10 of about 2,400 requests came back 502 (0.2 to 0.4 %), and svcdesk turns each of those into a 502 it cannot
avoid, with no retry allowed. 99 % leaves the dependency's own failures using at most about 40 % of the budget in the worst
run I saw; 99.9 % would be burnt by the dependency alone, and a gate (Lab 6) built on it would roll back honest releases.

## Latency

Good requests are those answered in 0.25 s or less (the `le="0.25"` bucket); valid are all `/kb/search` answers. My
measured distribution: p50 about 25 ms, p95 about 60 to 70 ms, p99 about 199 ms, p99.99 about 260 ms. Most requests are in
the fast mode, and about 1 to 3 % sit in a slow mode of roughly 160 to 245 ms. 0.25 s is the first boundary above that slow
mode, so the SLI counts the slow mode as good and flags only a real degradation (a mode shifted past 250 ms, or `kb-index`
degrading). Threshold 0.1 s would count the whole slow mode as bad and burn the budget permanently. Objective 99 % again
(403.2 minutes): the service meets it with a wide margin today (about 0.02 % of requests above 0.25 s), and the threshold
is well below the 1 s ceiling that Lab 6 requires.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity |
|---|---|---|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | 2 % (14.4 x 1 h / 672 h) | P1 (page) |
| KbSearchErrorsBurnSlow | availability | 6 | 6h / 30m | 5 % (6 x 6 h / 672 h) | P2 (chat) |

At 14.4x the whole 28-day budget is gone in under two days; a 1 h window at that rate has already cost 2 % of the
budget, and every further hour costs another 2 %, so it is worth waking one person: waiting until morning would cost
10 to 20 % of the month's budget. At 6x the budget lasts about 4.7 days and 6 hours cost 5 %, which a person can handle on the next working
morning; it goes to chat. The short windows (5 m and 30 m) end an alert soon after the burn stops, so nobody is paged for a
burn that is over. No latency alert is declared: the latency SLI is on the dashboard, and the availability alerts are the
ones that the checker probes.

## Buckets

Ladder (23 finite boundaries): 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125, then every 10 ms from 0.15 to 0.25, then
0.3, 0.5, 1, 2.5, 5. My q was 0.1994 s (an earlier run: 0.2023 s); its bucket (0.19, 0.2] is 10 ms wide, 5.0 % of q. The
10 ms steps cover 0.15 to 0.25 s: a band of about -25 % to +25 % around q, wider than the required +-10 %, with every bucket
in it at most 7 % of its lower end, so another machine's q resolves too. 0.25 is the latency SLI's threshold and a
boundary. The other 12 boundaries are coarse: five below 0.1 s for the fast mode where the median lives, and 0.3 to 5 s so
that a degraded `kb-index` (latency x factor) and the 5 s upstream timeout still land in a finite bucket.
