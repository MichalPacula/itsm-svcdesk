---
feature: "DORA metric engine: parse and validate the event log, apply the window, compute the five metrics under the six rules"
predicted_minutes: 65
predicted_at: "2026-09-26T13:47:00Z"
feature_path: "metrics/"
---
<!-- ai-generated: 40% - I set the scope, the number and the reasoning; Claude Code drafted the prose from my notes -->

# METR n=1 prediction

## What I am predicting

The feature is the DORA metric engine that backs `POST /dora/metrics`: the event parser and its
validation, the window filter, the five metric computations, and the six edge-case rules R-06, R-08,
R-09, R-10, R-12 and R-13. All of it lands under `metrics/`, which is the `feature_path` above and a
directory that does not exist in this repository yet, so every commit that touches it will descend
from the receipt of this file.

Deliberately **outside** the scope of this prediction, and therefore outside `metrics/`:

- the HTTP route wiring in `src/svcdesk/main.py` that hands a request body to the engine and
  serialises its answer,
- `GET /dora/ticket-events`, which reads Lab 1's ticket store and touches no metric code,
- the written artifacts (`EDGE-CASES.md`, `gaming/after.jsonl`, `gaming.json`, `metrics.json`).

I am predicting the engine alone because that is the part where the six traps live, and it is the part
whose difficulty I am least able to guess in advance - which is the only interesting thing to measure.

## The number, and how I got to it

**65 minutes.**

The handout's own budget for the matching work is 55 minutes: 30 for item 2 (parse, validate, window,
five metrics) and 25 for item 3 (the six rules, until `metrics-practice.json` matches field for field).
I am starting from that and adding 10 minutes, for two reasons.

First, the handout says plainly that item 3 is the item that overruns, and I have no reason to think I
am the exception: the fixture is 230 events and the six anomalies interact - a revert chain (R-06) and
an off-`main` commit (R-09) can sit on the same change, so getting `counts.changes` and
`counts.lead_time_pairs` right at the same time is not two independent fixes.

Second, my Lab 1 experience points the same way. The work there that took longest was not writing the
state machine, it was the loop of running the checker, reading one failing field, and deciding which of
two defensible readings of the spec the checker meant. Here that loop is cheaper, because
`fixtures/metrics-practice.json` publishes the answer key and I can diff against it locally without
waiting on the checker - but there are sixteen fields in `L2-CORE-3` to bring green, not one.

Working against the estimate: the rulebook is unusually complete. `METRIC-SPEC.md` names every edge case
and assigns it a rule id, so this is a transcription problem rather than a design problem, and the
ambiguity that ate my Lab 1 time is mostly absent. That is why I am adding 10 minutes rather than 25.

## How I will measure `actual_minutes`

To keep the number honest, I am fixing the measurement rule now, before any of the work:

- **Start**: when I begin writing the first file under `metrics/`, recorded as a wall-clock instant in
  `METR.md`, not inferred afterwards from a commit timestamp.
- **Stop**: when `./itsmlab.sh verify 2` reports every check from `L2-CORE-3.01` to `L2-CORE-3.15`
  passing against my own service. `L2-CORE-3.16` (`metrics.json` at the repo root) is excluded: writing
  that file is a deliverable, not engine work.
- **Counted**: reading `METRIC-SPEC.md` while implementing, writing the engine, debugging it, and every
  checker run whose purpose is to find out whether the engine is right.
- **Not counted**: breaks away from the keyboard, time spent on the three items listed as out of scope
  above, and time spent on the written artifacts.
- Interruptions longer than about two minutes come out of the total; I will log each start/stop pair in
  `METR.md` rather than reporting one opaque figure.

`METR.md` will carry those intervals, the resulting `actual_minutes`, the ratio `actual/predicted` to two
decimals against the 65 minutes above, and prose on where the estimate went wrong - in whichever
direction it went wrong. A speedup and a slowdown score the same here, so there is nothing to gain by
shading the number, and the receipt on this file is what makes that credible: the prediction is fixed
before the first line of the feature exists.
