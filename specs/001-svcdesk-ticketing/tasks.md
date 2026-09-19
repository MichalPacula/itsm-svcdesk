<!-- ai-generated: 85% - Claude Code drafted this task list from plan.md, spec.md, data-model.md and contracts/openapi.yaml; reviewed and accepted as-is -->
# Tasks: svcdesk Ticketing Service

**Input**: Design documents from `/specs/001-svcdesk-ticketing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md (all present)

**Tests**: Included. `plan.md`/`research.md` commit to a local `pytest` regression suite specifically so the 49 `L1-CORE-2` checks and the 8 SLA vectors can be caught before spending a real `./itsmlab.sh verify 1` run; they are not required by the grader directly (the grader only runs the published checker) but are cheap insurance given how easy the SLA/state-machine edge cases are to get subtly wrong.

**Organization**: Tasks are grouped by user story (spec.md priorities P1-P4) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project (per `plan.md`): application code under `src/svcdesk/`, the optional Stretch S3 runner under `src/tests/`, local development tests under `tests/unit/` and `tests/integration/` at the repository root.

---

## Phase 1: Setup

**Purpose**: Repository scaffolding so the application package can be built and run.

- [X] T001 Create the package skeleton: `src/svcdesk/__init__.py`, empty `src/svcdesk/main.py`, `src/svcdesk/models.py`, `src/svcdesk/priority.py`, `src/svcdesk/sla.py`, `src/svcdesk/state_machine.py`, `src/svcdesk/clock.py`, `src/svcdesk/store.py`, `src/svcdesk/errors.py`; and `tests/unit/`, `tests/integration/` at the repo root, each with an `__init__.py`
- [X] T002 Create `requirements.txt` at the repository root pinning `fastapi` and `uvicorn` (versions current as of the course package, e.g. `fastapi==0.141.1`, `uvicorn==0.52.4`), matching the comment in `Dockerfile.example`
- [X] T003 [P] Copy `Dockerfile.example` to `Dockerfile` at the repository root (per `src/README.md`); verify it still copies `requirements.txt` then `src/`, sets `SVCDESK_DB=/data/svcdesk.db`, and starts `uvicorn svcdesk.main:app --app-dir /app/src --host 0.0.0.0 --port 8080`
- [X] T004 [P] Add `pytest` (and `httpx`, required by FastAPI's `TestClient`) to a separate `requirements-dev.txt` at the repository root, not installed into the Docker image, so the shipped image gains no test-only dependency

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure every user story's endpoints depend on: request/response schemas, storage, the per-request clock, error shaping, the SLA due-instant calculator, and the FastAPI app skeleton with `/health`.

**⚠️ CRITICAL**: No user story task can start until this phase is complete.

- [X] T005 In `src/svcdesk/models.py`, define the Pydantic schemas from `data-model.md` and `contracts/openapi.yaml`: `Reporter` (`name: str` required, `1 <= len <= 100`; `email: str | None` optional, default `None`; `vip: bool` optional, default `False`), `TicketCreate` (`title: str` required, `1 <= len <= 200`; `description: str` optional, `len <= 4000`, default `""`; `reporter: Reporter` required; `impact: int` required, one of `{1, 2, 3}`; `urgency: int` required, one of `{1, 2, 3}`; `related_to: str | None` optional, default `None`, unvalidated), `Sla` (`ack_due_at`, `resolve_due_at`), `Ticket` (full response: `id`, `title`, `description`, `reporter`, `impact`, `urgency`, `priority`, `state`, `created_at`, `acknowledged_at`, `resolved_at`, `closed_at`, `related_to`, `sla`), `SlaStatus` (`priority`, `ack_due_at`, `resolve_due_at`, `ack_breached`, `resolve_breached`, `paused`), `ErrorBody` (`error: {code, message}`); configure `TicketCreate` to ignore/allow-and-drop any of the server-owned fields (`id`, `priority`, `state`, `created_at`, `acknowledged_at`, `resolved_at`, `closed_at`, `sla`) and any unrecognized field rather than rejecting the request (FR-006, FR-021)
- [X] T006 In `src/svcdesk/store.py`, implement SQLite persistence: on import/startup, `CREATE TABLE IF NOT EXISTS tickets` at the path in the `SVCDESK_DB` environment variable with the columns from `data-model.md`'s Ticket table (`id`, `title`, `description`, `reporter_name`, `reporter_email`, `reporter_vip`, `impact`, `urgency`, `priority`, `state`, `related_to`, `created_at`, `acknowledged_at`, `resolved_at`, `closed_at`), plus functions `insert_ticket(...)`, `get_ticket(id) -> row | None`, `list_tickets(state=None, priority=None) -> list[row]` (exact-match filters, FR-020), `update_ticket(id, **fields)` for transitions; store timestamps as RFC 3339 UTC strings (FR-018)
- [X] T007 [P] In `src/svcdesk/clock.py`, implement clock resolution per FR-022/API.md §8: read `SVCDESK_TEST_CLOCK` once (env var, `1`/`true` enables test-clock mode); expose a FastAPI dependency `resolve_now(x_test_clock: str | None = Header(None))` that, when test-clock mode is enabled and the header is present, parses it as an RFC 3339 instant and returns it (raising a validation error on a value that fails to parse - 400/422), and otherwise returns real UTC `datetime.now(timezone.utc)`; the header MUST be evaluated fresh per request with no cross-request state (R-21)
- [X] T008 [P] In `src/svcdesk/errors.py`, implement the shared `{"error": {"code": ..., "message": ...}}` body builder and FastAPI exception handlers (registered from `main.py`) that convert `RequestValidationError` to 422 and a domain `NotFoundError`/`InvalidTransitionError` (define these two exception classes here) to 404/409, all with the same error body shape (API.md §7)
- [X] T009 In `src/svcdesk/sla.py`, implement the due-instant calculator (shared by every story that reads or writes a `Ticket`, since every `Ticket` response carries an `sla` block): `due_instants(created_at: datetime, priority: str) -> (ack_due_at, resolve_due_at)`, using the target table (P1: 15 min / 4 h, P2: 1 h / 8 h, P3: 4 h / 24 h, P4: 8 h / 72 h — FR-011); for `priority == "P1"`, both targets are wall-clock (`created_at + target`, decision C1 = `wallclock` per `DECISIONS.md`); for every other priority, both targets run on the business-hours clock (`zoneinfo.ZoneInfo("Europe/Warsaw")`, Monday-Friday `[08:00:00, 16:00:00)`, consuming the target across consecutive business windows, with the tie rule that a target ending exactly at closing is due at that closing instant, not the next opening - API.md §4); this function must reproduce all 8 published test vectors T1-T8 exactly
- [X] T010 In `src/svcdesk/main.py`, create the FastAPI app: instantiate `FastAPI()`, register the exception handlers from `errors.py`, initialize the SQLite schema from `store.py` on startup, and implement `GET /health` returning `{"status": "ok", "service": "svcdesk"}` (FR-002)

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Log and triage a new ticket (Priority: P1) 🎯 MVP

**Goal**: A caller can create a ticket and receive it back with a server-assigned id, a computed priority (matrix + VIP floor), and its SLA due instants; invalid submissions are rejected before any ticket is created.

**Independent Test**: Submit tickets covering every impact/urgency cell (both VIP and non-VIP) and confirm the returned priority; submit an invalid ticket and confirm the 400/422 error shape and that no ticket was created — no other endpoint needed.

### Tests for User Story 1

- [X] T011 [P] [US1] Unit tests in `tests/unit/test_priority.py`: all 9 matrix cells (impact/urgency 1-3, FR-004) for a non-VIP reporter; VIP floor cases (FR-005) — impact 3/urgency 3 VIP → `P2` (not the matrix's `P4`), impact 1/urgency 1 VIP → `P1` (unchanged, matrix already at P1), impact 2/urgency 1 VIP → `P2` (unchanged, matrix already at P2)
- [X] T012 [P] [US1] Integration tests in `tests/integration/test_api.py`: `POST /tickets` reproducing API.md §7's worked example (clock `2026-10-14T10:00:00Z`, impact 2/urgency 1, non-VIP) expecting `priority == "P2"`, `state == "new"`, `sla.ack_due_at == "2026-10-14T11:00:00Z"`, `sla.resolve_due_at == "2026-10-15T10:00:00Z"`; the same request without `title` expecting 400/422 with a top-level `error` object and zero tickets persisted; a request that also sends `id`, `priority`, and `state` fields expecting them to be silently ignored (FR-006)

### Implementation for User Story 1

- [X] T013 [P] [US1] In `src/svcdesk/priority.py`, implement `compute_priority(impact: int, urgency: int, vip: bool) -> str`: look up the matrix (FR-004's table), then if `vip` is true and the matrix result is `P3` or `P4`, raise it to `P2`; otherwise (matrix result already `P1`/`P2`, or `vip` false) return the matrix result unchanged (FR-005, decision C3 = `vip`)
- [X] T014 [US1] Implement `POST /tickets` in `src/svcdesk/main.py`: accept a `TicketCreate` body (validation errors flow to the T008 handler automatically via Pydantic), resolve `now` via the T007 `resolve_now` dependency as `created_at`, generate `id = str(uuid.uuid4())` (FR-019), compute `priority` via T013, compute `sla` due instants via T009, persist via T006's `insert_ticket`, and return `201` with the full `Ticket` (state `new`, all event timestamps `null`)

**Checkpoint**: User Story 1 is fully functional and testable independently (`docker compose up` + the `POST /tickets` calls in `quickstart.md`'s Story 1 section).

---

## Phase 4: User Story 2 - Drive a ticket through its lifecycle (Priority: P1)

**Goal**: An agent can acknowledge, start, resolve and close a ticket in the fixed order; any shortcut is refused with 409, and once closed a ticket accepts no further transition.

**Independent Test**: Create one ticket (US1), then call each transition endpoint in and out of order, checking the resulting state, the recorded timestamp, and the HTTP status — independent of priority computation or SLA math.

### Tests for User Story 2

- [X] T015 [P] [US2] Unit tests in `tests/unit/test_state_machine.py`: the valid path `new -> acknowledged -> in_progress -> resolved -> closed`; every documented shortcut is refused (`resolve` from `new`, `resolve` from `acknowledged` per L1-CORE-2.49, `close` from `new`, `close` from `in_progress`, a second `ack`, `start` from `new`) each raising the invalid-transition error
- [X] T016 [US2] Integration tests in `tests/integration/test_api.py`: full lifecycle happy path asserting `acknowledged_at`/`resolved_at`/`closed_at` equal the clock given to each call; a shortcut (`resolve` on a fresh `new` ticket) returns 409 with an `error` body and leaves the ticket's state unchanged; an action on a nonexistent id returns 404 with an `error` body

### Implementation for User Story 2

- [X] T017 [US2] In `src/svcdesk/state_machine.py`, implement the transition table per API.md §6: a dict mapping `(current_state, "ack") -> "acknowledged"`, `(current_state, "start") -> "in_progress"`, `(current_state, "resolve") -> "resolved"`, `(current_state, "close") -> "closed"` (only from their documented `from` state each); a function `apply_transition(current_state, action) -> new_state` that raises the T008 invalid-transition error for any `(state, action)` pair not in the table (FR-008); leave room for the `reopen` entries added in US4
- [X] T018 [US2] Implement `POST /tickets/{id}/ack`, `/start`, `/resolve`, `/close` in `src/svcdesk/main.py`: look up the ticket via `store.get_ticket` (raise the T008 not-found error if missing, FR-024), call `state_machine.apply_transition`, set the corresponding timestamp (`acknowledged_at`/`resolved_at`/`closed_at`) from the `resolve_now` dependency, persist via `store.update_ticket`, return `200` with the full updated `Ticket`

**Checkpoint**: User Stories 1 and 2 both work independently (create a ticket, then drive it through its lifecycle).

---

## Phase 5: User Story 3 - Check whether a ticket is meeting its SLA (Priority: P2)

**Goal**: `GET /tickets/{id}/sla` reports a ticket's priority, both due instants, whether each target is breached, and whether its clock is currently paused, computed from a single "now".

**Independent Test**: Create tickets at known priorities and clock instants (US1), advance the simulated clock, and call the SLA endpoint to confirm due instants, breach flags and pause status — independent of how the ticket later resolves.

### Tests for User Story 3

- [X] T019 [P] [US3] Unit tests in `tests/unit/test_sla.py` for the T009 due-instant calculator: reproduce all 8 published vectors exactly - T1 (P1, business hours, C1 irrelevant), T7 (P2, resolve crosses a weekday closing), T2 (P3, Friday afternoon), T4 (P2, Saturday, resolve ends exactly at closing - the tie rule), T5 (P4, January, CET), T6 (P1, Friday near closing, CET), T3 (P1, Friday 17:00 - the C1 vector: wall-clock values since this service's C1 = `wallclock`), T8 (P3, spans the October DST-end weekend)
- [X] T020 [P] [US3] Unit tests in `tests/unit/test_sla.py` for breach/pause: `ack_breached`/`resolve_breached` false exactly at the due instant and true one second after (FR-015, equality is never a breach); false when the event happened before its due instant even if checked much later; `paused` true for an open, non-P1 ticket at a Saturday instant and false at the next business-hours instant (FR-016); `paused` always false for a P1 ticket (wall-clock, decision C1) regardless of when checked; `paused` false once the ticket is `resolved` or `closed`
- [X] T021 [US3] Integration tests in `tests/integration/test_api.py` reproducing L1-CORE-2.36-2.45: `GET /sla` responses for vectors T1, T7, T2, T4, T5 and the C1 vector T3; ack-breach true/false around T2's due instant; pause true on Saturday vs. false on the following Monday for the same open ticket

### Implementation for User Story 3

- [X] T022 [US3] Extend `src/svcdesk/sla.py` with `evaluate_sla(ticket, now) -> SlaStatus`: `ack_breached` = ticket not yet acknowledged and `now > ack_due_at`, or `acknowledged_at > ack_due_at`; `resolve_breached` = ticket not yet resolved and `now > resolve_due_at`, or `resolved_at > resolve_due_at` (a reopened ticket counts as not-resolved again, against the same, unchanged `resolve_due_at` - FR-017); `paused` = `state not in {"resolved", "closed"}` and the ticket's resolve target runs on the business-hours clock (i.e. `priority != "P1"` under decision C1) and `now` falls outside a business window (FR-016)
- [X] T023 [US3] Implement `GET /tickets/{id}/sla` in `src/svcdesk/main.py`: 404 via T008 if unknown (FR-024); otherwise resolve `now` via `resolve_now`, call T022's `evaluate_sla`, return `200` with the `SlaStatus` body
- [X] T024 [US3] Embed the `sla` block (`ack_due_at`, `resolve_due_at` only, from T009) into every `Ticket` response - `POST /tickets` (T014), `GET /tickets/{id}` (US5), `GET /tickets` (US5) - so the shape always matches `contracts/openapi.yaml`'s `Ticket` schema

**Checkpoint**: All Core SLA behavior (Section 4/5 of API.md) is independently verifiable.

---

## Phase 6: User Story 4 - Reopen a ticket that wasn't actually fixed (Priority: P3)

**Goal**: A resolved ticket can be reopened within 7 days of its resolution; a closed ticket can never be reopened (decision C2 = `immutable`, per `DECISIONS.md`).

**Independent Test**: Resolve a ticket (US1+US2), reopen it inside and outside the 7-day window, and attempt to reopen a closed ticket - independent of the other stories.

### Tests for User Story 4

- [X] T025 [P] [US4] Unit tests in `tests/unit/test_state_machine.py` for the reopen rule: `resolved`, 6 days after `resolved_at` → allowed (→ `in_progress`); `resolved`, 7 days + 1 second after `resolved_at` → refused; a `new` ticket → refused; a `closed` ticket at any age (including 1 day after `closed_at`) → refused, per decision C2 = `immutable`
- [X] T026 [US4] Integration tests in `tests/integration/test_api.py` reproducing L1-CORE-2.32-2.35: reopen a resolved ticket after 6 days (200, `in_progress`); after 7 days + 1s (409); reopen a `new` ticket (409); reopen a ticket closed 1 day earlier (409, recording C2 = `immutable`)

### Implementation for User Story 4

- [X] T027 [US4] Extend `src/svcdesk/state_machine.py`'s reopen handling (separate from the plain transition table, since it needs the resolution timestamp and current time, not just the state): `can_reopen(ticket, now) -> bool` - true only when `ticket.state == "resolved"` and `now <= resolved_at + timedelta(days=7)`; a `closed` ticket is never reopenable under this service's C2 = `immutable` decision (FR-009, FR-010); raise the T008 invalid-transition error otherwise
- [X] T028 [US4] Implement `POST /tickets/{id}/reopen` in `src/svcdesk/main.py`: 404 via T008 if unknown; call T027's `can_reopen`; on success, clear `resolved_at` and `closed_at`, set `state = "in_progress"`, leave `created_at` unchanged so the original `resolve_due_at` (T009) still governs (FR-017); persist via `store.update_ticket`; return `200` with the full `Ticket`

**Checkpoint**: The reopen window and closed-ticket immutability are independently verifiable.

---

## Phase 7: User Story 5 - List and monitor tickets, and confirm the service is alive (Priority: P4)

**Goal**: `GET /tickets/{id}`, `GET /tickets` (with `state`/`priority` filters) and `GET /health` (already built in Foundational) round out the read surface; unknown ids and unknown paths answer 404.

**Independent Test**: Create a handful of tickets (US1) and call the list, get-by-id and health endpoints independently of any other story.

### Tests for User Story 5

- [X] T029 [P] [US5] Integration tests in `tests/integration/test_api.py` reproducing L1-CORE-2.20-2.23: `GET /tickets/{id}` of a created ticket returns the same `id`/`title`; `GET /tickets/does-not-exist` returns 404 with an `error` body; `GET /tickets?state=new` includes a matching ticket's id; `GET /tickets?priority=P1` includes a P1 ticket's id and excludes a P4 ticket's id; `GET /this-route-does-not-exist` returns 404 with a JSON body

### Implementation for User Story 5

- [X] T030 [US5] Implement `GET /tickets/{id}` in `src/svcdesk/main.py`: `200` with the full `Ticket` (including its `sla` block via T024), or the T008 404 if the id is unknown (FR-024)
- [X] T031 [US5] Implement `GET /tickets` in `src/svcdesk/main.py`: optional `?state=` and `?priority=` query parameters, exact match, passed through to `store.list_tickets` (T006); return every matching ticket (each with its `sla` block) in one unpaginated JSON array, in any order (FR-020)

**Checkpoint**: All 5 user stories are independently functional; the full read/write surface of API.md §1 exists.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Course-specific compliance and final verification, spanning all stories.

- [X] T032 [P] Add the AI-disclosure header (`# ai-generated: <0-100>% - <one line on how>`, first ten lines) to every file under `src/` and `tests/` with a checked extension (`.py`), per `specs/HANDOUT.md`'s AI-disclosure rule and `CHECKS.md`'s Advisory `ai-disclosure`
- [X] T033 [P] Confirm `Dockerfile` installs `requirements.txt` at build time only (no network calls in `CMD`/at container start, API.md §9) and that `docker-compose.yml`'s `svcdesk` service still has no host-path bind mounts (named volume `svcdesk-data` only)
- [X] T034 Run `./itsmlab.sh verify 1` and fix any failing check until every Core spec (`L1-CORE-1` through `L1-CORE-4`) passes and the printed `observations` line (`C1=wallclock C2=immutable C3=vip`) matches `DECISIONS.md`'s front matter exactly (L1-CORE-4)
- [X] T035 [P] (Stretch S1, optional) Write `specs/converge.md`: at least 400 characters comparing this implementation against `spec.md`/`REQUIREMENTS.md`, citing at least three distinct `R-nn` ids (all within R-01..R-25), per `CHECKS.md` L1-STRETCH-1
- [X] T036 [P] (Stretch S3, optional) Implement `src/tests/run.py` per `research.md`'s testing strategy: a dependency-free HTTP smoke suite (stdlib `urllib.request` only) against `SVCDESK_URL`, at least 10 assertions, whose last stdout line is exactly `ITSMLAB-TESTS: passed=<n> failed=0`; then uncomment and adapt the `tests` service (`profiles: ["tests"]`) in `docker-compose.yml`, per `CHECKS.md` L1-STRETCH-3

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately.
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS every user story (every story's endpoint touches models, store, clock, errors, or the due-instant calculator).
- **User Stories (Phases 3-7)**: All depend on Foundational. Priority order from `spec.md` is US1 (P1) → US2 (P1) → US3 (P2) → US4 (P3) → US5 (P4); US2 needs a ticket to transition (US1), US3's SLA block needs a ticket to exist (US1) and its pause rule reads `state` (benefits from US2 existing), US4's reopen needs a resolved ticket (US1 + US2), so a strictly sequential build order is recommended even though the checks each story targets are independent of each other's *bugs*.
- **Polish (Phase 8)**: Depends on all five user stories being complete (T034 in particular requires the full read/write surface).

### User Story Dependencies

- **US1 (P1)**: After Foundational. No dependency on another story.
- **US2 (P1)**: After Foundational. Functionally needs a ticket to exist to transition (i.e., needs US1's `POST /tickets` implemented to be exercised), but its own logic (the transition table) has no data dependency on US1's priority/VIP logic.
- **US3 (P2)**: After Foundational. Needs a created ticket (US1) and benefits from US2 existing (to test `paused` turning `false` once resolved/closed), but its due-instant/breach/pause math is independent of US1's and US2's internals.
- **US4 (P3)**: After Foundational + US1 + US2 (needs a ticket that has actually been resolved).
- **US5 (P4)**: After Foundational. Needs created tickets (US1) to list/get meaningfully, but `GET /health` (already in Foundational) needs nothing.

### Within Each User Story

- Tests before implementation (write them first; they should fail until the implementation task lands).
- The shared calculator/table (`priority.py`, `state_machine.py`, `sla.py` extensions) before the endpoint that calls it.
- Story complete (checkpoint) before moving to the next priority.

### Parallel Opportunities

- T003 and T004 (Setup) can run in parallel with each other and with T001/T002.
- T007 and T008 (Foundational) can run in parallel with each other (different files); T005, T006, T009, T010 have a light ordering (models before store/sla, store+clock+errors+sla before the app skeleton) but can be split across contributors if care is taken with import order.
- Within a story, unit tests marked `[P]` run in parallel with each other; the integration test typically waits for that story's endpoint task.
- T032, T033, T035, T036 (Polish) can all run in parallel; T034 should run last, after everything else.

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1, together:
Task: "Unit tests for the priority matrix and VIP floor in tests/unit/test_priority.py"
Task: "Integration tests for POST /tickets (happy path + validation) in tests/integration/test_api.py"

# Implementation, once tests are in place:
Task: "Implement compute_priority in src/svcdesk/priority.py"
# then (depends on the above, and on Foundational's T006/T007/T009):
Task: "Implement POST /tickets in src/svcdesk/main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1): ticket creation with correct priority and SLA due instants.
3. **STOP and VALIDATE**: run `quickstart.md`'s Story 1 section by hand.

Note this lab's grading is not incremental: `L1-CORE-2` is one pass/fail bundle of 49 checks spanning all five stories, with no partial credit inside it (per `CHECKS.md`). Treat US1 as the first *working* slice for your own iteration and debugging, not as a deliverable milestone on its own.

### Incremental Delivery (recommended build order)

1. Setup + Foundational → foundation ready.
2. US1 → validate ticket creation and priority by hand.
3. US2 → validate the full lifecycle and its 409 shortcuts.
4. US3 → validate SLA due instants (all 8 vectors) and breach/pause.
5. US4 → validate the reopen window and closed-ticket immutability.
6. US5 → validate list/get/health.
7. Polish (Phase 8) → run the real checker (T034) until every Core spec passes.

### Solo Course-Lab Strategy

Given the 150-minute budget in `specs/HANDOUT.md` (items 5-7 total 40 minutes for all of intake/validation/priority, the state machine/reopen/test clock, and SLA), work the phases in order above rather than in parallel; the `[P]` markers mainly help you batch same-phase, different-file edits in one sitting (e.g. writing T007 `clock.py` and T008 `errors.py` back to back) rather than implying multiple simultaneous contributors.

---

## Notes

- `[P]` tasks touch different files with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md`'s US1-US5 for traceability.
- Commit after each task or logical group; remember Core spec L1-CORE-5 requires the `specs` receipt (already obtained) to be an ancestor of every commit that adds a file under `src/` other than `src/README.md` - do not rewrite history before the receipted commit.
- Every new file under `src/` needs the AI-disclosure header (T032) before you consider a phase done, not just at the end, so it is never forgotten.
