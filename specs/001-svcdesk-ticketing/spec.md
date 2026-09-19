<!-- ai-generated: 90% - Claude Code drafted this spec from specs/REQUIREMENTS.md and specs/API.md; the three C1/C2/C3 resolutions were chosen by the course participant via clarification questions -->
# Feature Specification: svcdesk Ticketing Service

**Feature Branch**: `001-svcdesk-ticketing`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "Build the svcdesk service-desk ticketing API described in specs/REQUIREMENTS.md (R-01 to R-25) and specs/API.md for Lab 1: a small HTTP/JSON service for ~400 people across three offices that lets desk agents and monitoring create tickets, computes ticket priority, drives tickets through a fixed lifecycle, tracks SLA acknowledge/resolve clocks (business-hours aware, with a per-request test clock), and reports SLA breach/pause status. The requirements document contains three deliberate contradictions that must be resolved: (C1) whether the P1 SLA clock runs on business hours or the wall clock, (C2) whether a closed ticket can be reopened or is fully immutable, and (C3) whether a VIP reporter's ticket overrides the priority matrix."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log and triage a new ticket (Priority: P1)

A desk agent (or an automated monitor) reports a new issue. The service records it, assigns it an opaque id, and computes its priority automatically from impact and urgency so nobody has to negotiate a priority by hand.

**Why this priority**: Without ticket intake and correct, non-negotiable priority assignment there is no service desk — every other capability (lifecycle, SLA tracking) operates on tickets created here.

**Independent Test**: Can be fully tested by submitting tickets with each impact/urgency combination (including VIP and non-VIP reporters) and confirming the returned priority matches the matrix (with the VIP floor applied), independent of any lifecycle or SLA behavior.

**Acceptance Scenarios**:

1. **Given** no prior tickets, **When** a ticket is submitted with a title, a reporter name, impact = 1 (organisation) and urgency = 1 (work stopped), **Then** the service creates the ticket, assigns it a unique id and returns it with state `new` and priority `P1`.
2. **Given** a ticket submission with impact = 3 and urgency = 3 from a reporter marked VIP, **When** the ticket is created, **Then** its priority is `P2`, not the `P4` the matrix alone would produce, because a VIP reporter's ticket is never lower than P2.
3. **Given** a ticket submission that omits the title, **When** the request is made, **Then** the service refuses it with 400 or 422 and a JSON body carrying an `error` object, and no ticket is created.
4. **Given** a ticket submission that includes a client-supplied `id`, `priority`, or `state` field, **When** the ticket is created, **Then** those fields are ignored and the service assigns its own id, computes priority itself, and sets state to `new`.

---

### User Story 2 - Drive a ticket through its lifecycle (Priority: P1)

An agent acknowledges a ticket, starts work, resolves it, and closes it once the reporter confirms the fix — in that fixed order, with no shortcuts.

**Why this priority**: The lifecycle is what turns a logged issue into tracked, accountable work; it is exercised on every ticket the desk handles and is a precondition for meaningful SLA reporting.

**Independent Test**: Can be fully tested by creating a ticket and calling each transition endpoint in and out of order, independent of priority computation or SLA math, and checking the resulting state and HTTP status.

**Acceptance Scenarios**:

1. **Given** a ticket in state `new`, **When** an agent acknowledges it, **Then** its state becomes `acknowledged` and the service records the acknowledgement instant.
2. **Given** a ticket in state `acknowledged`, **When** an agent starts work on it, **Then** its state becomes `in_progress`.
3. **Given** a ticket in state `in_progress`, **When** an agent resolves it, **Then** its state becomes `resolved` and the service records the resolution instant.
4. **Given** a ticket in state `resolved`, **When** an agent closes it, **Then** its state becomes `closed` and the service records the closure instant.
5. **Given** a ticket in state `new`, **When** an agent attempts to resolve it directly (skipping acknowledge and start), **Then** the service refuses with 409 Conflict and an error body, and the ticket's state is unchanged.
6. **Given** an action addressed to a ticket id that does not exist, **When** the action is requested, **Then** the service answers 404 with a JSON error body.
7. **Given** a ticket in state `closed`, **When** any further transition or edit is attempted (other than a reopen within the reopen rule of User Story 4), **Then** the service refuses it: a closed ticket is immutable, and any further work on the same issue requires a new ticket that references it via `related_to`.

---

### User Story 3 - Check whether a ticket is meeting its SLA (Priority: P2)

The desk needs to know, per ticket, whether its acknowledgement and resolution targets have been or will be breached, so a Monday-morning report can be produced from one call per ticket.

**Why this priority**: This is the reporting capability the whole service exists to make possible ("nobody can say at 09:00 on Monday which tickets are late"), but it depends on ticket creation and lifecycle already existing.

**Independent Test**: Can be fully tested by creating tickets at known priorities and clock instants (using the test-clock header), advancing the simulated clock, and calling the SLA endpoint to confirm due instants, breach flags and pause status, independent of how the ticket later resolves.

**Acceptance Scenarios**:

1. **Given** a newly created P1 ticket, **When** its SLA is checked, **Then** the response reports its priority, its acknowledge-due and resolve-due instants (15 minutes and 4 hours from creation, on the wall clock per the C1 decision below), and `false` for both breach flags.
2. **Given** a P3 ticket created on a Friday evening and not yet acknowledged, **When** its SLA is checked at a simulated instant past its business-hours-adjusted acknowledge-due instant, **Then** the acknowledge breach flag is `true`.
3. **Given** an open, non-P1 ticket and a simulated "now" outside business hours (Mon-Fri 08:00-16:00 Europe/Warsaw), **When** its SLA is checked, **Then** the response reports the ticket's clock as currently paused.
4. **Given** a ticket resolved exactly at its resolve-due instant, **When** its SLA is checked, **Then** the resolve breach flag is `false` (reaching the due instant exactly is not a breach).
5. **Given** a P1 ticket raised late on a Friday, **When** its SLA is checked at a simulated instant 20 minutes later (a non-business hour), **Then** its acknowledge target is already reported as breached, because P1 targets run around the clock (the C1 decision).

---

### User Story 4 - Reopen a ticket that wasn't actually fixed (Priority: P3)

A reporter finds that a fix didn't work and reopens the ticket within a limited window, without needing to file a brand-new ticket for the same issue.

**Why this priority**: Improves reporter experience and data quality (avoids duplicate tickets for one issue) but is not required for the desk's core intake/triage/SLA loop to function.

**Independent Test**: Can be fully tested by resolving a ticket, reopening it inside and outside the 7-day window, and confirming the resulting state and status code, independent of the other stories.

**Acceptance Scenarios**:

1. **Given** a ticket resolved 3 days ago, **When** its reporter reopens it, **Then** its state returns to `in_progress` and its original resolution target is not restarted or extended.
2. **Given** a ticket resolved 8 days ago, **When** a reopen is requested, **Then** the service refuses with 409 Conflict and the ticket remains `resolved`.
3. **Given** a ticket that has been closed, **When** a reopen is requested at any point, **Then** the service refuses it: per the C2 decision below, closed tickets are immutable and cannot be reopened; a new ticket referencing the closed one via `related_to` is required instead.

---

### User Story 5 - List and monitor tickets, and confirm the service is alive (Priority: P4)

An agent or a monitoring tool lists tickets filtered by state or priority, retrieves one ticket by id, and checks the service's health.

**Why this priority**: Supporting/operational capability — useful for day-to-day work and deployment monitoring, but the desk's essential value (intake, lifecycle, SLA) does not depend on it.

**Independent Test**: Can be fully tested by creating a handful of tickets and calling the list, get-by-id and health endpoints independently of any other story.

**Acceptance Scenarios**:

1. **Given** several tickets in different states and priorities, **When** the ticket list is requested with `?state=in_progress`, **Then** only tickets currently `in_progress` are returned, in a single response with no pagination.
2. **Given** the service is running, **When** its health endpoint is called, **Then** it answers 200 with `{"status": "ok", "service": "svcdesk"}` within 120 seconds of the service starting.
3. **Given** a request for a ticket id that does not exist, **When** it is requested, **Then** the service answers 404 with a JSON error body.
4. **Given** a request to an unknown path, **When** it is requested, **Then** the service answers 404 with a JSON error body.

### Edge Cases

- What happens when a ticket's impact/urgency combination already yields P1 or P2 from the matrix and the reporter is also VIP? The VIP floor is a minimum, not an addition — priority stays whatever the matrix gave (P1 or P2), never worsened.
- How does the system handle a reopen request that arrives exactly 7 days (to the instant) after resolution? Treated as still within the window (the boundary belongs to the reporter, consistent with "reaching the due instant exactly is not a breach" elsewhere in this spec).
- What happens when `X-Test-Clock` is sent but the service is not running with test-clock mode enabled? The header is ignored and real UTC time is used.
- What happens when `X-Test-Clock` is sent, test-clock mode is enabled, but the value does not parse as an RFC 3339 instant? The request is refused with 400 or 422.
- How does the system handle an action request racing another action request on the same ticket (e.g., two "resolve" calls in flight)? Exactly one succeeds and changes state; the other is refused as an invalid transition (409) or, if it observes the already-updated state, is evaluated against that state.
- What happens when a new ticket names a `related_to` id that does not exist? Out of scope for this spec's success criteria beyond "the field is stored as given"; validation of cross-references is not required by the source requirements.
- What happens to a ticket's SLA pause status once it is resolved or closed? It is never reported as paused — pausing only applies to tickets that are still open (not resolved and not closed).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST expose all functionality over a single HTTP interface where every request and response body is JSON, with no other interface.
- **FR-002**: The service MUST answer a health check with the service's status and name, so that monitoring can confirm it is up, and MUST do so within 120 seconds of the service starting.
- **FR-003**: The service MUST let a caller create a ticket carrying: a title (1-200 characters, required), an optional description (up to 4000 characters), a reporter with a name (1-100 characters, required), an optional reporter e-mail, an optional reporter VIP flag (default false), an impact level (1-3), an urgency level (1-3), and an optional reference to an earlier, related ticket.
- **FR-004**: The service MUST compute each ticket's priority from its impact and urgency using this matrix, and from nothing else supplied by the caller:

  | impact \ urgency | 1 (work stopped) | 2 (degraded) | 3 (cosmetic) |
  |---|---|---|---|
  | **1** (organisation) | P1 | P2 | P3 |
  | **2** (team) | P2 | P3 | P4 |
  | **3** (one person) | P3 | P4 | P4 |

- **FR-005**: **[C3 - resolved]** The service MUST raise the priority of a ticket whose reporter is marked VIP to at least P2 whenever the matrix in FR-004 would otherwise produce P3 or P4, and MUST leave it unchanged when the matrix already produces P1 or P2.
- **FR-006**: The service MUST reject any caller-supplied priority, id, state, or timestamp field on ticket creation or update; these fields are always owned and set by the service.
- **FR-007**: The service MUST move a ticket through the states `new` -> `acknowledged` -> `in_progress` -> `resolved` -> `closed`, each transition available as its own action, and MUST record the instant the acknowledgement, the resolution, and the closure each happened.
- **FR-008**: The service MUST refuse any transition that skips a step or moves a ticket backward outside the reopen rule (FR-010) with 409 Conflict and a JSON error body, and MUST answer 404 for an action addressed to a ticket id that does not exist.
- **FR-009**: **[C2 - resolved]** The service MUST treat a closed ticket as fully immutable: no further transition, edit, or reopen is permitted on a closed ticket; any further work on the same issue requires a new ticket that references the closed one via the related-ticket field.
- **FR-010**: The service MUST let a reporter reopen a ticket that is currently `resolved` (not `closed`, per FR-009) within 7 days of its resolution, returning it to `in_progress` without restarting or extending its original resolution target; a reopen requested outside that 7-day window MUST be refused with 409 Conflict.
- **FR-011**: The service MUST assign, for each priority, an acknowledgement target and a resolution target measured from ticket creation:

  | priority | acknowledge within | resolve within |
  |---|---|---|
  | P1 | 15 min | 4 h |
  | P2 | 1 h | 8 h |
  | P3 | 4 h | 24 h |
  | P4 | 8 h | 72 h |

- **FR-012**: The service MUST pause the SLA clock for a ticket outside business hours (Monday-Friday, 08:00-16:00, Europe/Warsaw), such that time outside those hours does not count against its targets, for every open ticket **except** as resolved for P1 in FR-013.
- **FR-013**: **[C1 - resolved]** The service MUST run a P1 ticket's acknowledge and resolve targets on the wall clock (never paused by business hours), so that a P1 raised outside business hours becomes late exactly 15 minutes and 4 hours after creation.
- **FR-014**: The service MUST let a caller retrieve, for any ticket, its priority, its acknowledge-due and resolve-due instants, whether each target has been breached, and whether its clock is currently paused, in a single call.
- **FR-015**: The service MUST consider a target breached when the corresponding event happened after its due instant, or has not happened yet and the due instant has passed; reaching the due instant exactly MUST NOT be treated as a breach.
- **FR-016**: The service MUST report a ticket's clock as paused only when the ticket is still open (neither resolved nor closed), its resolution target is subject to the business-hours clock, and the current moment is outside business hours.
- **FR-017**: The service MUST treat a reopened ticket as not-yet-resolved again, measured against its original resolution target (not a new one).
- **FR-018**: The service MUST report every timestamp as an RFC 3339 instant in UTC with a `Z` suffix.
- **FR-019**: The service MUST assign every ticket an opaque, unique, non-empty identifier that the caller never chooses or predicts.
- **FR-020**: The service MUST let a caller list tickets, optionally filtered by exact-match state and/or priority, returning every matching ticket in one response without pagination.
- **FR-021**: The service MUST refuse a ticket-creation request that violates its field rules (FR-003) with 400 or 422 and a JSON body carrying an `error` object, while ignoring unknown fields and service-owned fields (FR-006) rather than rejecting the request because of them.
- **FR-022**: The service MUST, when a specific test-clock mode is enabled for the running instance, let a single request override "now" via a request header carrying an RFC 3339 instant, used only for that request; without the header, or when the mode is not enabled, the service MUST use real UTC time; a header value that fails to parse as an instant MUST be refused with 400 or 422.
- **FR-023**: The service's stored tickets MUST survive a restart of the service.
- **FR-024**: The service MUST answer 404 with a JSON error body for an unknown path and for an action or lookup on an unknown ticket id.

### Key Entities

- **Ticket**: The unit of work tracked by the desk. Attributes: opaque id; title; optional description; embedded reporter (name, optional e-mail, VIP flag); impact (1-3); urgency (1-3); computed priority (P1-P4); state (`new`, `acknowledged`, `in_progress`, `resolved`, `closed`); optional reference to a related, earlier ticket; timestamps for creation, acknowledgement, resolution and closure. Relationships: may reference one earlier ticket via `related_to`; is the subject of one SLA record.
- **SLA status**: A derived view of a ticket's timing, not separately stored: acknowledge-due instant, resolve-due instant, whether each has been breached, and whether the ticket's clock is currently paused. Always computed from the ticket's priority, its recorded timestamps, and the current instant (real or test).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every ticket's priority, at the moment of creation, matches the impact/urgency matrix (with the VIP floor applied where relevant) in 100% of cases, with no caller-supplied value ever accepted.
- **SC-002**: For any ticket, one API call returns whether it is currently late on acknowledgement or resolution, letting a Monday status report be produced with exactly one call per ticket and no client-side clock arithmetic.
- **SC-003**: 100% of transition requests that violate the fixed lifecycle order (new -> acknowledged -> in_progress -> resolved -> closed, plus the single reopen rule) are rejected, with zero tickets ever observed in a state reached by an invalid transition.
- **SC-004**: A reporter can recover a wrongly resolved ticket without opening a duplicate: reopen succeeds for 100% of requests made within 7 days of resolution and is refused for 100% made after, or on any closed ticket.
- **SC-005**: The service reports itself healthy within 120 seconds of starting, every time it is started.
- **SC-006**: Tickets and their recorded history are present and unchanged after a restart of the service, with zero data loss.
- **SC-007**: A malformed or out-of-range ticket submission is rejected before any ticket record is created, in 100% of cases.

## Assumptions

- **C1 (SLA clock for P1) resolved as wall clock**: R-14's "around the clock" wording governs; only P1 ignores the business-hours pause that R-13 applies to every other priority. Rationale: P1 means the whole organisation has stopped working, so the desk owner accepts round-the-clock urgency for the single most severe class of ticket while keeping business-hours pausing (cheaper, calmer operations) for everything less severe.
- **C2 (closed tickets and reopening) resolved as immutable**: R-09's immutability governs for `closed` tickets; R-10's 7-day reopen window applies only to tickets in state `resolved`. Rationale: "closed" is treated as the desk's true, audit-safe end state (confirmed by the reporter), so history under a closed id never changes; a wrong fix must be caught before the reporter confirms and closes it, and after that a fresh ticket linked via `related_to` keeps the record honest.
- **C3 (VIP reporters and the priority matrix) resolved as VIP override**: R-06's VIP floor governs; R-05's "from nothing else" is read as ruling out manual/requested priority, not this one automatic, disclosed business rule. Rationale: making executive-reported issues visible immediately is a named goal of the requirements document itself.
- Business hours for the pause rule are Monday-Friday, 08:00-16:00, Europe/Warsaw, applied uniformly regardless of which office reported the ticket (the requirements do not describe per-office calendars).
- No authentication or authorization scheme is specified in the source requirements; this spec assumes none is required for Lab 1 and that access control, if any, is out of scope.
- The desk's scale (~400 people, at most ~100 tickets per test run) means unpaginated list responses and in-process/on-disk persistence are acceptable; nothing in the requirements implies a need for horizontal scaling.
- The test-clock override (a request header honored only when a specific mode is enabled on the running service) is a testing aid, not a feature exposed to real reporters or agents in normal operation.
- Ticket identifiers are opaque strings; no particular format (UUID, sequential, etc.) is required by the source requirements beyond uniqueness and unpredictability.
- "Immutable" for a closed ticket (FR-009) means no field changes and no transition succeeds, including a repeated close; the only recorded outcome of any request against a closed ticket other than read access is a refusal.
