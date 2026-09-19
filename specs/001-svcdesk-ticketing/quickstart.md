<!-- ai-generated: 85% - Claude Code drafted this quickstart from API.md's worked examples and test vectors; reviewed and accepted as-is -->
# Quickstart: svcdesk Ticketing Service

Validates the feature end-to-end once implemented. Full contract: [contracts/openapi.yaml](contracts/openapi.yaml); data shapes: [data-model.md](data-model.md); authoritative reference: `../API.md`.

## Prerequisites

- `Dockerfile.example` copied to `Dockerfile` (or your own, per `src/README.md`).
- `requirements.txt` at the repo root pinning `fastapi` and `uvicorn`.
- Implementation under `src/svcdesk/` per `plan.md`'s Project Structure.

## Run it

```sh
docker compose up --build --wait svcdesk
curl -s http://localhost:8080/health
# {"status":"ok","service":"svcdesk"}
```

Expected: healthy within 120 s (SC-005 / L1-CORE-1.03-04).

## Story 1 - Log and triage a ticket

Create a P2 ticket at a fixed test instant (T1 from API.md §4) and confirm the computed priority and SLA block, matching API.md's worked example:

```sh
curl -s -X POST http://localhost:8080/tickets \
  -H "Content-Type: application/json" \
  -H "X-Test-Clock: 2026-10-14T10:00:00Z" \
  -d '{"title":"Printer on floor 2 is down","description":"Nobody on the floor can print.",
       "reporter":{"name":"Anna Nowak","email":"anna.nowak@example.com","vip":false},
       "impact":2,"urgency":1,"related_to":null}'
```

Expected (201): `priority == "P2"`, `state == "new"`, `sla.ack_due_at == "2026-10-14T11:00:00Z"`, `sla.resolve_due_at == "2026-10-15T10:00:00Z"` (business-hours clock, crosses Wednesday closing — the T7 vector). Save the returned `id` as `$TICKET_ID`.

VIP floor (spec.md User Story 1, scenario 2): create with `impact:3, urgency:3, reporter.vip:true` → expect `priority == "P2"` (not the matrix's `P4`), per decision C3.

Validation (SC-007): the same request without `title` → 400 or 422 with a top-level `error` object, and no ticket created (`GET /tickets` count unchanged).

## Story 2 - Drive the lifecycle

```sh
curl -s -X POST http://localhost:8080/tickets/$TICKET_ID/ack -H "X-Test-Clock: 2026-10-14T10:05:00Z"
curl -s -X POST http://localhost:8080/tickets/$TICKET_ID/start -H "X-Test-Clock: 2026-10-14T10:10:00Z"
curl -s -X POST http://localhost:8080/tickets/$TICKET_ID/resolve -H "X-Test-Clock: 2026-10-14T12:00:00Z"
curl -s -X POST http://localhost:8080/tickets/$TICKET_ID/close -H "X-Test-Clock: 2026-10-14T13:00:00Z"
```

Expected: each call returns 200 with the state advancing `new -> acknowledged -> in_progress -> resolved -> closed`, and `acknowledged_at`/`resolved_at`/`closed_at` equal to the clocks given.

Shortcut rejected (spec.md User Story 2, scenario 5): on a fresh `new` ticket, `POST /tickets/$ID/resolve` → 409 with an `error` body.

Unknown id (spec.md User Story 2, scenario 6): `POST /tickets/does-not-exist/ack` → 404 with an `error` body.

## Story 3 - Check SLA breach and pause

Reproduce vector T3 (spec.md User Story 3, scenario 5 — the C1 decision in action): create a P1 ticket at `2026-10-16T15:00:00Z` (Friday 17:00 local), then:

```sh
curl -s http://localhost:8080/tickets/$P1_ID/sla -H "X-Test-Clock: 2026-10-16T15:20:00Z"
```

Expected (C1 = `wallclock`, per `DECISIONS.md`): `ack_due_at == "2026-10-16T15:15:00Z"`, `ack_breached == true` — already late 5 minutes after a due instant that fell outside business hours, because P1 never pauses.

Pause check (spec.md User Story 3, scenario 3 / vector-adjacent to T2): a non-P1, still-open ticket, `GET /sla` at a Saturday instant → `paused == true`; at the next business-hours instant → `paused == false`.

## Story 4 - Reopen within the window

```sh
# resolved 3 days ago, reopen now: 200, in_progress
curl -s -X POST http://localhost:8080/tickets/$RESOLVED_ID/reopen -H "X-Test-Clock: <resolved_at + 3d>"

# resolved 8 days ago, reopen now: 409
curl -s -X POST http://localhost:8080/tickets/$OLD_RESOLVED_ID/reopen -H "X-Test-Clock: <resolved_at + 8d>"

# closed ticket, reopen at any time: 409 (decision C2 = immutable)
curl -s -X POST http://localhost:8080/tickets/$CLOSED_ID/reopen -H "X-Test-Clock: <closed_at + 1d>"
```

## Story 5 - List, get, health

```sh
curl -s "http://localhost:8080/tickets?state=in_progress"
curl -s "http://localhost:8080/tickets?priority=P1"
curl -s http://localhost:8080/tickets/$TICKET_ID
curl -s http://localhost:8080/this-route-does-not-exist   # 404 with an error body
```

## Full conformance

Once the golden paths above pass by hand, run the published checker (all 49 `L1-CORE-2` checks plus the compose and decisions-consistency gates):

```sh
./itsmlab.sh verify 1
```

Expected: every Core spec (`L1-CORE-1` through `L1-CORE-4`; `L1-CORE-5` reports `skip` locally) passes, and the printed `observations` line (`C1=wallclock C2=immutable C3=vip`) matches `DECISIONS.md`'s front matter exactly.
