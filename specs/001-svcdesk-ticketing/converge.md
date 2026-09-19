<!-- ai-generated: 85% - Claude Code drafted this comparison after implementing the service; reviewed and accepted as-is -->
# Convergence: svcdesk vs. specs/001-svcdesk-ticketing/spec.md

Comparison of the running implementation (`src/svcdesk/`) against the feature specification and the
underlying course requirements (`specs/REQUIREMENTS.md`), after `./itsmlab.sh verify 1` reported
`core 4/5 passed, 1 skipped -> PASS` with `observations C1=wallclock C2=immutable C3=vip` matching
`DECISIONS.md`'s front matter exactly.

## Converged

- **User Story 1 (ticket intake + priority)**: `src/svcdesk/priority.py` implements the impact/urgency
  matrix (**R-04**) and the VIP floor (**R-06**) exactly as spec.md's requirements specify; `POST /tickets`
  ignores every server-owned and unknown field (**R-20**) via Pydantic's default
  `extra="ignore"` behavior on `TicketCreate`, verified by `test_server_owned_fields_are_ignored` and
  the checker's 2.48.
- **User Story 2 (lifecycle)**: `src/svcdesk/state_machine.py`'s transition table matches API.md
  section 6 and **R-07**/**R-08** (**R-09** for closed-ticket immutability); the checker's full
  L1-CORE-2 conformance bundle, including the shortcut checks (2.25, 2.26, 2.29, 2.31, 2.49), passed.
- **User Story 3 (SLA)**: `src/svcdesk/sla.py`'s business-hours walk was validated against all 8
  published vectors (T1-T8) in `tests/unit/test_sla.py` before the real checker ever ran, and
  L1-CORE-2.36-2.45 confirm the same instants and breach/pause behavior on the live service. The
  wall-clock vs. business-hours split for P1 (**R-13** vs. **R-14**, decision C1) resolved to
  `wallclock`; L1-CORE-4.01 confirms the declared value matches the value the checker observed (2.41).
- **User Story 4 (reopen)**: **R-09** vs. **R-10** (decision C2) resolved to `immutable`; a closed
  ticket refuses reopen unconditionally (`state_machine.can_reopen`), matched by L1-CORE-4.02/2.35.
  The 7-day window itself (**R-10**, **R-11**) is exact-boundary correct (6 days: allowed; 7 days + 1s:
  refused), per L1-CORE-2.32/2.33.
- **User Story 5 (list/get/health)**: `GET /tickets` filters exactly on `state`/`priority`
  (**R-19**), unpaginated; unknown ids and unknown paths both answer 404 with a JSON `error` body
  (**R-25**).
- **Persistence** (**R-23**): tickets are stored in SQLite at `SVCDESK_DB`, on a named volume
  (`svcdesk-data`) per `docker-compose.yml`, so they survive a container restart; not checked by
  Tier A for Lab 1, per CHECKS.md, but present regardless since it costs nothing extra here.

## Deviations / not implemented

- **`related_to` existence is not validated** (spec.md's Edge Cases section states this is
  intentionally out of scope): a ticket can reference a nonexistent id with no error. This matches
  API.md's explicit "not validated in Lab 1" note for that field and required no remediation.
- **No authentication/authorization**: the spec's Assumptions section states this is out of scope
  for Lab 1, and no requirement in R-01..R-25 asks for it.
- **Stretch S1/S2/S3** were not part of `spec.md`'s scope (Core-only); they were added afterward as
  optional, separately-scoped deliverables (this file, `CLAUDE.md`/`AGENT-POLICY.md`, and
  `src/tests/run.py` plus the `tests` compose service) and do not change any Core behavior above.

## Outcome

No remediation tasks were appended to `tasks.md`: the implementation converges with `spec.md` and
with `specs/REQUIREMENTS.md`'s R-01..R-25 on every point the published checks exercise, and the three
deliberately conflicting pairs (C1, C2, C3) are resolved consistently between `DECISIONS.md`, the
spec's Assumptions section, and the running service's observed behavior.
