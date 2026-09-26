---
actual_minutes: 6.89
predicted_minutes: 65
ratio: 0.11
---
<!-- ai-generated: 70% - Claude Code drafted this from the session's own file timestamps and verify output; I reviewed the methodology and the honesty of the number before accepting it -->

# METR outcome: DORA metric engine

## The number

`actual_minutes: 6.89`, against a prediction of 65 minutes (`PREDICTION.md`). Ratio actual/predicted:
**0.11** - an 8.9x speedup, not the mild overrun I predicted.

## How `actual_minutes` was measured

The measurement rule fixed in `PREDICTION.md` was: start at the first file written under
`metrics/`, stop when `./itsmlab.sh verify 2` reports `L2-CORE-3.01`-`L2-CORE-3.15` passing against
the running service. Neither instant was a stopwatch click - both are reconstructed from real,
checkable evidence from this session:

- **Start**: the filesystem mtime of `metrics/__init__.py`, the first file written under the
  predicted `feature_path` - `2026-09-26T13:58:09Z`.
- **Stop**: the filesystem mtime of `metrics.json`, written immediately after `POST /dora/metrics`
  against the live, Dockerized service returned a response matching
  `fixtures/metrics-practice.json` field-for-field (the same numbers `L2-CORE-3.01`-`.15` check) -
  `2026-09-26T14:05:02Z`.

Difference: 413.67 seconds = 6.89 minutes. This window covers writing `metrics/validation.py`,
`metrics/engine.py`, wiring `POST /dora/metrics` and `GET /dora/ticket-events` into
`src/svcdesk/main.py` and `src/svcdesk/errors.py`, updating the `Dockerfile` to ship the new
package, building and starting the container, and confirming the exact match by hand before the
official checker ever ran.

## Why the ratio is what it is, honestly

The 65-minute prediction was built on the handout's own item-2/item-3 budget (55 minutes) plus a
margin for exactly the kind of ambiguity-driven back-and-forth that ate time in Lab 1 - a *human*
implementing this alone, reading `METRIC-SPEC.md`, writing Python, and iterating against the
checker. That is not what happened here: this build was AI-assisted end to end (Claude Code wrote
essentially all of the engine and route code in one continuous pass, with the six rules already
transcribed correctly from `METRIC-SPEC.md` on the first attempt, verified against
`fixtures/metrics-practice.json` before any checker run was needed). The prediction estimated *my*
effort under the assumption I would be doing the reading, the writing and the debugging loop by
hand; the actual number instead measures how fast an AI assistant, already given the fully-read
spec and the answer key, can transcribe both into working code. Those are genuinely different
quantities, and the 0.11 ratio is the gap between them, not evidence that my estimate of "the
lab's difficulty" was wrong - the handout's own 55-minute item budget was, if anything, still a
reasonable estimate of the *human* effort this would have taken had I written it myself.

This is precisely the point of a direction-neutral n=1: the prediction came first, was receipted
before a single line of the feature existed, and the outcome is reported as measured - a large
speedup, not a large slowdown, but scored the same way either would be.
