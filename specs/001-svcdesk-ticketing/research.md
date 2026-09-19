<!-- ai-generated: 85% - Claude Code drafted this research from spec.md, API.md and CHECKS.md; reviewed and accepted as-is -->
# Phase 0 Research: svcdesk Ticketing Service

No `[NEEDS CLARIFICATION]` markers remained in the Technical Context (the course template fixed language, port and persistence style in advance). This document instead records the design decisions Phase 1 depends on, each with the alternative considered and why it lost.

## Web framework and validation

**Decision**: FastAPI, with Pydantic models for both request parsing and response shaping, plus a custom exception handler that converts Pydantic's `RequestValidationError` (and any explicit `HTTPException`) into the required `{"error": {"code": ..., "message": ...}}` body.

**Rationale**: `Dockerfile.example`'s `CMD` already targets `svcdesk.main:app` under `uvicorn`, i.e. an ASGI app — FastAPI is the natural fit. Pydantic gives field-level validation (string lengths, integer ranges 1-3, required vs. optional) for free, satisfying most of FR-003/FR-021 with declarative models; only the *shape* of the error body needs overriding, since FastAPI's default `{"detail": [...]}` does not match `{"error": {...}}` (API.md §7).

**Alternatives considered**: Flask (no built-in async, no automatic request validation, more boilerplate for the same guarantees); a bare stdlib `http.server` (would reimplement routing, JSON (de)serialization and validation by hand for no benefit at this scale).

## Persistence

**Decision**: stdlib `sqlite3`, one `tickets` table, one file at the path in `SVCDESK_DB` (already `/data/svcdesk.db` in `Dockerfile.example`, `/data` already a named volume in `docker-compose.yml`). Timestamps stored as RFC 3339 UTC strings; `state`, `priority`, `impact`, `urgency` stored as their wire values (`TEXT`/`INTEGER`) directly, so no ORM mapping layer is needed for a single-table domain this small.

**Rationale**: FR-023 (tickets survive a restart) rules out an in-memory store. SQLite needs no server process, no network, and no extra runtime dependency to install — consistent with API.md §9's "no network at run time" rule, since the SQLite library ships with Python. Scale (≤100 tickets per checker run, ~400-person desk) is far below anything that would need a client-server database.

**Alternatives considered**: In-memory dict (fails FR-023 outright). PostgreSQL/MySQL (needs a second container, extra compose complexity, and either network access or a bind-mounted socket — disproportionate for one table). An ORM such as SQLAlchemy (adds a dependency and an abstraction layer for a single table with five state values; plain `sqlite3` with one module (`store.py`) owning all SQL is easier to audit against the 49 conformance checks).

## Business-hours SLA due-instant calculation

**Decision**: stdlib `zoneinfo.ZoneInfo("Europe/Warsaw")` to convert instants to local time; a small pure function that, given a start instant and a duration, walks forward one business window at a time (Mon-Fri, local `[08:00:00, 16:00:00)`), consuming the duration from consecutive windows, applying the tie rule from API.md §4 (a target ending exactly at closing is due at that closing time, not the next opening), then converts the result back to UTC.

**Rationale**: `zoneinfo` is stdlib since Python 3.9 and is DST-aware (needed: API.md's test vectors T5/T6/T8 span the CET/CEST boundary and DST-end weekend), so no extra dependency or timezone database bundling decision is needed beyond what `python:3.13-slim` already ships (Debian-based images carry the IANA tz database, per API.md §4's own note). A day-by-day/window-by-window loop is simple enough to verify directly against all 8 published test vectors (T1-T8) and is easy to reason about at the tie boundary, versus a closed-form calendar-arithmetic formula that would need the same edge-case handling but is harder to read and test.

**Alternatives considered**: `pytz` (predates `zoneinfo`, needs its own dependency and periodic tz-data updates; no benefit here). A closed-form formula computing business seconds directly (more compact, but the tie rule and DST edges make it easy to get subtly wrong in ways a step-by-step loop avoids).

## Ticket identifiers

**Decision**: `uuid.uuid4()` rendered as its canonical string form.

**Rationale**: FR-019 requires an opaque, unique, non-predictable id; UUID4 is exactly that, needs no coordination or counter, and API.md's model comment recommends UUIDs directly.

**Alternatives considered**: An auto-incrementing integer (predictable, fails "clients never choose or predict it" in spirit even though clients don't supply it) or a hash of ticket contents (not guaranteed unique across identical submissions).

## Per-request test clock

**Decision**: A FastAPI dependency, resolved once per request, that reads the `SVCDESK_TEST_CLOCK` environment variable (read once at process startup) and, only when it is `1`/`true`, looks at the `X-Test-Clock` header on that request; on a parse failure it raises the validation error path (400/422); otherwise it returns real UTC `now()`. Nothing about this value is stored as process/global state.

**Rationale**: R-21/FR-022 and API.md §8 are explicit that "now" is per-request only — the service must never compare one request's clock to another's or enforce monotonicity. A request-scoped dependency naturally cannot leak into other requests, unlike a global variable that would invite exactly that mistake.

**Alternatives considered**: A module-level mutable "current time" set by middleware (risks accidental cross-request leakage or race conditions under concurrent requests; harder to reason about than a pure per-request value).

## State machine representation

**Decision**: A single dictionary mapping `(current_state, action) -> new_state` (plus the two reopen edges gated by the C2 decision and the 7-day window check), consulted by one function that every action endpoint calls; anything not in the table is a 409.

**Rationale**: Centralizing the table means the five action endpoints (`ack`, `start`, `resolve`, `close`, `reopen`) cannot silently drift out of sync with each other or with API.md §6, and the 409-by-default behavior falls out of "not found in the table" rather than needing to be repeated per endpoint.

**Alternatives considered**: An `if/elif` chain per endpoint (duplicates the "everything else is 409" logic five times and is easy to leave a hole in, e.g. forgetting to block `resolve` from `acknowledged`, which L1-CORE-2.49 specifically checks).

## Testing strategy

**Decision**: `pytest` with FastAPI's `TestClient` for local development (unit tests for `priority.py`/`sla.py`/`state_machine.py` in isolation, plus integration tests driving the HTTP layer end-to-end, reproducing the 8 SLA test vectors and the 49 `L1-CORE-2` checks as a local regression suite before running the real checker). For the optional Stretch S3 profile, a dependency-free script (`src/tests/run.py`, stdlib `urllib.request` only) that talks to `SVCDESK_URL` over real HTTP and prints the exact `ITSMLAB-TESTS: passed=<n> failed=0` line the checker greps for.

**Rationale**: The local `pytest` suite is not graded directly but catches regressions before spending a checker run; using the same `TestClient` approach FastAPI documents keeps it fast (no real sockets needed) for that purpose. The S3 runner is graded on its exact last stdout line and must run inside the built image without installing anything at container start (API.md §9), so it deliberately avoids adding `pytest` (or any dependency) to the shipped image just for this optional line — stdlib `urllib.request` is already available.

**Alternatives considered**: Using `pytest` itself as the S3 runner and parsing its output/exit code to synthesize the summary line (adds a dependency to the runtime image and a fragile output-parsing step for a stretch item that isn't required for the Core grade).
