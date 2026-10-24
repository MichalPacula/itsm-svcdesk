---
lab4_postmortem:
  ticket: "42cb082c-3a7e-4830-8322-853f369d1582"
  detecting_alert: CheckoutErrorRate
  onset: 2026-10-24T10:13:48Z
  detection: 2026-10-24T10:18:09Z
  acknowledgement: 2026-10-24T10:18:38Z
  recovery: 2026-10-24T10:20:59Z
  mttd_seconds: 261
  mtta_seconds: 29
  mttr_seconds: 431
  identified_flags: [paymentFailure, emailMemoryLeak, loadGeneratorFloodHomepage]
---
<!-- ai-generated: 85% - Claude Code drafted the text from itsmlab incident 4, the ledger and the injector's flags; the on-call reviewed it -->

# Postmortem: about one checkout in ten failed for the shop's users for seven minutes

## Date

The incident ran on 2026-10-24 from 10:13:48Z to 10:20:59Z; this postmortem was written the same day, after the snapshot.

## Authors

Written by the on-call engineer of the shop, who opened and acknowledged the P1 ticket, with drafting help from an AI assistant.

## Status

Complete for the incident, which is closed because service is restored; the action items are open and the problem record stays open.

## Summary

Three feature flags failed at 10:13:48Z. The one that mattered to users, a 10% payment failure, made about one checkout in ten fail until the flags were switched off at 10:19:23Z. The page fired at 10:18:09Z and the detecting alert resolved at 10:20:59Z.

## Impact

About 10% of checkout requests failed during the incident: `sum(rate(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) / sum(rate(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER"}[5m]))` returned 0.104 at 10:18:00Z and 0.104 at 10:19:00Z, and 0 on the healthy shop. Payment showed the same ratio, so every failed checkout was a failed payment. Checkout latency did not change (p95 stayed below 500 ms). The other two faults raised no alert and no measurable user-facing error in the shop's server spans.

## Root Causes

Three flags of the fault injector were failing: `paymentFailure` at 10% made the payment service reject one charge in ten, and checkout passed that error on to the customer. `emailMemoryLeak` at 100x and `loadGeneratorFloodHomepage` were also on; they were found in the injector's flag list, and no alert or query of this incident showed their effect.

## Trigger

The flags switched on together at the onset, 10:13:48Z, the first sample of `seeded_fault_active`. Nothing was deployed by the team; the change was a flag change.

## Resolution

The flags were switched off through the injector, one at a time: `paymentFailure` at 10:18:43Z, `loadGeneratorFloodHomepage` at 10:19:03Z and `emailMemoryLeak` at 10:19:23Z. Payment went first because it was the flag that matched the page. Each call answered `changed: true`, and the detecting alert resolved at 10:20:59Z, once its 5-minute window had slid past the last failures.

## Detection

CheckoutErrorRate (P1, checkout errors above 5% over 5 minutes, `for: 1m`) started firing at 10:18:09Z, 261 seconds after the onset, and the pager received it at 10:18:29Z. The delay comes from the design: the shop's span metrics arrive once a minute, the rule needs a 5-minute window and a minute of `for:`. PaymentErrorRate (P2) fired in the same minute and was muted by the inhibition. Without the alert, customers would have noticed first, since no dashboard was being watched.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Shorten detection: add a 2-minute error-count alert on payment and checkout so a 10% failure pages in under two minutes | mitigate | on-call engineer | ITSM-101 |
| Add alerts or dashboard panels for email memory and homepage traffic so those two flags would be noticed | prevent | on-call engineer | ITSM-102 |
| Add a runbook step "list the failing feature flags and switch them off" to the P1 checklist | process | on-call engineer | ITSM-103 |
| Require a flag-change notice in the incident channel before any flag is switched on | prevent | platform team | ITSM-104 |

## Lessons Learned

### What went well

The page reached the pager 20 seconds after the alert started, the ticket was acknowledged 29 seconds after the detection, and the flag list in the injector answered the question "what changed" at once.

### What went wrong

Detection took 261 seconds because the rules look at 5-minute windows of metrics sampled once a minute. Two of the three failing flags had no alert at all, so the investigation relied on the flag list rather than on symptoms.

### Where we got lucky

The flag that failed requests was only 10%; at 50% the checkout error rate would have been five times higher for the same four minutes before the page.

## Timeline

All times are UTC, 2026-10-24.

- 10:08:50 injector armed; no alert had fired in the previous 10 minutes.
- 10:13:48 onset: the three flags fail (`seeded_fault_active` starts).
- 10:18:09 detection: CheckoutErrorRate starts firing, with PaymentErrorRate.
- 10:18:29 the page reaches the pager.
- 10:18:37 the P1 ticket is created, with the flag list read from the injector.
- 10:18:38 acknowledgement of the ticket.
- 10:18:43 `paymentFailure` switched off; 10:19:03 `loadGeneratorFloodHomepage` off; 10:19:23 `emailMemoryLeak` off.
- 10:20:59 recovery: CheckoutErrorRate stops firing, and the resolved notification reaches the pager at 10:21:29.
- AI hypotheses: ledger entries H1 and H2 (payment errors, queries in `ai-rca-eval.json`) matched the data and were not acted on; the agent's latency claim H3 was contradicted by the data, and H4 had no query.

## Supporting information

The output of `itsmlab incident 4`, the snapshot `incident/tsdb-snapshot.tar.gz`, the ticket `incident/ticket.json`, the alert rules in `prometheus/demo-alerts.yml`, and the scored investigation in `ai-rca-eval.json` with its transcript `ai-rca/transcript.md`.

## Problem record

- Incident record: 42cb082c-3a7e-4830-8322-853f369d1582
- Root cause: the payment service failed one charge in ten while its failure flag was on, and checkout did not retry or degrade, so each failed charge failed the order.
- Known error: failing payment charges surface directly as failed checkouts, and two co-occurring faults have no alert of their own.
- Workaround: switch the failing flags off through the injector, and check the flag list first in any P1 on checkout.
