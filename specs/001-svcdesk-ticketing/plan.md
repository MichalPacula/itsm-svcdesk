<!-- ai-generated: 85% - Claude Code drafted this plan from spec.md, API.md and the course-provided Dockerfile.example/docker-compose.yml; reviewed and accepted as-is -->
# Implementation Plan: svcdesk Ticketing Service

**Branch**: `001-svcdesk-ticketing` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-svcdesk-ticketing/spec.md`

## Summary

Build `svcdesk`, a single HTTP/JSON service that lets desk agents log tickets, computes their priority (impact/urgency matrix with a VIP floor), drives them through a fixed lifecycle, and reports SLA acknowledge/resolve status on two clocks (wall-clock for P1, business-hours for everything else, per decision C1). The service is a small, single-process FastAPI application backed by SQLite (so tickets survive a restart, FR-023), built and run exactly as the course's `Dockerfile.example` / `docker-compose.yml` already scaffold: Python 3.13, listening on port 8080, `SVCDESK_TEST_CLOCK` enabling a per-request `X-Test-Clock` override, no bind mounts, no network access at run time.

## Technical Context

**Language/Version**: Python 3.13 (fixed by the course's `Dockerfile.example`, which this plan keeps)

**Primary Dependencies**: FastAPI (routing + Pydantic request/response validation), Uvicorn (ASGI server), stdlib `sqlite3` (persistence), stdlib `zoneinfo` (Europe/Warsaw business-hours math, DST-aware, no extra dependency), stdlib `uuid` (ticket ids)

**Storage**: SQLite, single file at `SVCDESK_DB` (set to `/data/svcdesk.db` in `Dockerfile.example`), the `/data` path being a named Docker volume (`svcdesk-data` in `docker-compose.yml`) so it survives a container restart without a host bind mount

**Testing**: `pytest` + FastAPI's `TestClient` for local development tests against the business logic and HTTP layer (unit + integration, run outside the image); a small dependency-free script at `src/tests/run.py` for the optional Stretch S3 "own tests" profile, exercising the running service over HTTP via `SVCDESK_URL` and printing the required `ITSMLAB-TESTS: passed=<n> failed=0` summary line

**Target Platform**: Linux container (the course checker's `docker compose` sandbox); no host network access once the image is built

**Project Type**: Single web service (Option 1 - no separate frontend/backend split; the only client is HTTP)

**Performance Goals**: No explicit throughput target in the source requirements; must comfortably serve the checker's sequential HTTP traffic (every request has a 10 s timeout, at most 100 tickets created per run) and a ~400-person, three-office desk's realistic day-to-day volume, which is orders of magnitude below anything requiring more than a single SQLite-backed process

**Constraints**: Peak container RAM about 0.4 GB (course-stated budget); `GET /health` must answer within 120 s of `docker compose up`; every request answered within 10 s; no bind mounts on any service; no outbound network access at container run time (all dependencies installed at build time); every timestamp emitted as RFC 3339 UTC with a `Z` suffix

**Scale/Scope**: ~400 reporters across 3 offices; the checker creates at most 100 tickets per run; 25 source requirements (R-01..R-25) covering 9 HTTP operations (health, create, list, get, sla, and 5 lifecycle actions), a 3x3 priority matrix, an 8-vector SLA due-instant table, and 3 deliberately conflicting requirement pairs resolved in `DECISIONS.md`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template shipped by `specify init` (`[PROJECT_NAME] Constitution` with unresolved `[PRINCIPLE_n_NAME]` placeholders) — no principles have been ratified for this project. There is therefore nothing concrete to gate this plan against; this is recorded rather than skipped silently. No violations, so no entries are needed in Complexity Tracking. If the constitution is filled in later (`/speckit-constitution`), re-run this check against the ratified version before further changes.

**Post-Phase-1 re-check**: Unchanged — the constitution is still unratified. No new gate to evaluate.

## Project Structure

### Documentation (this feature)

```text
specs/001-svcdesk-ticketing/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── openapi.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
requirements.txt         # pinned: fastapi, uvicorn (Dockerfile.example installs this at build time)

src/
└── svcdesk/
    ├── __init__.py
    ├── main.py           # FastAPI app: route wiring, exception handlers ({"error": {...}} shape)
    ├── models.py         # Pydantic request/response models: Reporter, TicketCreate, Ticket, SlaStatus, Error
    ├── priority.py        # impact/urgency matrix + VIP floor (decision C3)
    ├── sla.py             # ack/resolve due-instant computation on both clocks (decision C1), breach + pause
    ├── state_machine.py   # transition table, reopen window incl. closed-ticket rule (decision C2)
    ├── clock.py           # SVCDESK_TEST_CLOCK / X-Test-Clock resolution, per-request only
    ├── store.py           # SQLite schema + CRUD for tickets
    └── errors.py          # shared {"error": {"code", "message"}} construction

    # Stretch S3 (optional): a sibling package the compose "tests" service runs as `python -m tests.run`
    tests/
        ├── __init__.py
        └── run.py          # HTTP smoke suite against SVCDESK_URL; prints ITSMLAB-TESTS: passed=<n> failed=0

tests/                    # local development tests, not shipped in the image (Dockerfile.example copies src/ only)
├── unit/
│   ├── test_priority.py
│   ├── test_sla.py
│   └── test_state_machine.py
└── integration/
    └── test_api.py        # end-to-end HTTP tests against the FastAPI app (TestClient), covering the 8 SLA vectors
```

**Structure Decision**: Single project (Option 1). The application is one small FastAPI service with no independent frontend; internal modules are split by responsibility (priority, SLA math, state machine, storage) purely for testability, not as separate deployable units. `src/svcdesk/` is the package `Dockerfile.example` already expects (`uvicorn svcdesk.main:app --app-dir /app/src`); `src/tests/` is the separate package the commented-out Stretch S3 `tests` compose service already expects (`python -m tests.run` with `working_dir: /app/src`). The root-level `tests/` directory is for local development only (never copied into the image) and is not required by any Core or Stretch check.

## Complexity Tracking

> No entries: the Constitution Check found no ratified principles to violate, and the design above (one service, one process, one datastore, module split by responsibility) introduces no additional projects, layers, or patterns beyond what R-01..R-25 already require.
