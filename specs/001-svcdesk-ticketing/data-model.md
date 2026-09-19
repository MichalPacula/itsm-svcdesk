<!-- ai-generated: 85% - Claude Code drafted this data model from spec.md and API.md's Ticket model; reviewed and accepted as-is -->
# Data Model: svcdesk Ticketing Service

## Ticket

The single persisted entity. One row per ticket in the SQLite `tickets` table.

| Field | Type | Rules | Source |
|---|---|---|---|
| `id` | string (UUID4) | server-generated, unique, non-empty, never accepted from a client | FR-019, API.md §2 |
| `title` | string | required, 1-200 characters | FR-003, API.md §7 |
| `description` | string | optional, 0-4000 characters, default `""` | FR-003, API.md §2 |
| `reporter_name` | string | required, 1-100 characters | FR-003 |
| `reporter_email` | string \| null | optional, default `null`, not otherwise validated by the source requirements | FR-003, API.md §2 |
| `reporter_vip` | boolean | optional, default `false` | FR-003 |
| `impact` | integer | required, one of `1`, `2`, `3` | FR-003, FR-004 |
| `urgency` | integer | required, one of `1`, `2`, `3` | FR-003, FR-004 |
| `priority` | enum `P1`\|`P2`\|`P3`\|`P4` | server-computed from `impact`/`urgency` (FR-004) plus the VIP floor (FR-005); never accepted from a client | FR-004, FR-005, FR-006 |
| `state` | enum `new`\|`acknowledged`\|`in_progress`\|`resolved`\|`closed` | server-owned; starts at `new`; changes only via the transition table | FR-007, FR-008 |
| `related_to` | string \| null | optional on create; id of an earlier ticket; **not validated** (existence of the referenced id is out of scope, per spec.md Edge Cases) | FR-003, API.md §2 |
| `created_at` | instant (RFC 3339 UTC) | set once, at creation, from the resolved clock (real or test) | FR-018, FR-022 |
| `acknowledged_at` | instant \| null | set on the `ack` transition; cleared on reopen | FR-007, API.md §6 |
| `resolved_at` | instant \| null | set on the `resolve` transition; cleared on reopen | FR-007, API.md §6 |
| `closed_at` | instant \| null | set on the `close` transition | FR-007 |

**Validation rules** (enforced before a row is created; a violation is a 400/422 with `{"error": {...}}`, and creates no row):
- `title`: present, `1 <= len <= 200`.
- `description`: if present, `len <= 4000`.
- `reporter.name`: present, `1 <= len <= 100`.
- `impact`, `urgency`: present, integers, each in `{1, 2, 3}` (a string such as `"high"` is rejected).
- Any of `id`, `priority`, `state`, `created_at`, `acknowledged_at`, `resolved_at`, `closed_at`, `sla`, or an unrecognized field, present in the request body: ignored, never a validation error (FR-006, FR-021).

**State transitions** (see `state_machine.py` in plan.md; authoritative table in API.md §6):

```
new ──ack──> acknowledged ──start──> in_progress ──resolve──> resolved ──close──> closed
                                                        ▲           │
                                                        └──reopen───┘
                                    (closed ──reopen──> in_progress only if C2 = reopen; this service: C2 = immutable, so this edge does not exist)
```

- Any transition not in the table (e.g. `resolve` from `new` or `acknowledged`, `close` from anything but `resolved`, a second `ack`) is refused: 409 with `{"error": {"code": "invalid_transition", ...}}`.
- `reopen` from `resolved`: allowed while `now <= resolved_at + 7 days`; clears `resolved_at` and `closed_at` (already null), sets `state = in_progress`; does **not** change `created_at`, so the original `resolve_due_at` still governs (FR-017).
- `reopen` from `closed`: always refused (409) — decision C2 = `immutable` (FR-009, FR-010).
- Any action addressed to a nonexistent `id`: 404 with `{"error": {...}}`, regardless of the action.
- Once `state == closed`, no further mutation of any kind succeeds (FR-009): every action endpoint, including a repeated `close`, returns 409 (or, for `ack`/`start`/`resolve`/`reopen` which aren't valid from `closed` under any circumstance, the same 409 an invalid-transition lookup naturally produces).

## SLA status (derived, not persisted)

Computed on every `GET /tickets/{id}/sla` call (and embedded as the `sla` block on every `Ticket` response) from the ticket's `priority`, its timestamps, and the resolved "now" (real or test clock). Never stored as its own row.

| Field | Type | Computation |
|---|---|---|
| `priority` | enum | copied from the ticket |
| `ack_due_at` | instant | `created_at` + the priority's acknowledge target (FR-011), on the wall clock if `priority == P1` (FR-013), else on the business-hours clock (FR-012) |
| `resolve_due_at` | instant | `created_at` + the priority's resolve target (FR-011), same clock choice as `ack_due_at` |
| `ack_breached` | boolean | `acknowledged_at` is null and `now > ack_due_at`, or `acknowledged_at > ack_due_at` (FR-015; equality is never a breach) |
| `resolve_breached` | boolean | `resolved_at` is null and `now > resolve_due_at`, or `resolved_at > resolve_due_at` (FR-015; a reopened ticket counts as "not resolved" again, against the same `resolve_due_at`, FR-017) |
| `paused` | boolean | `state` is neither `resolved` nor `closed`, the ticket's resolve target runs on the business-hours clock (i.e. `priority != P1`, decision C1), and `now` falls outside a business window (FR-016) |

## Relationships

- `Ticket.related_to -> Ticket.id`: optional, single-level, unvalidated reference to an earlier ticket. No cascading behavior; no referential-integrity check is required by the source requirements.
- Every `Ticket` has exactly one, always-computed SLA status; there is no independent SLA entity to keep in sync.

## Enumerations

- **impact**: `1` (organisation), `2` (team), `3` (one person).
- **urgency**: `1` (work stopped), `2` (degraded), `3` (cosmetic).
- **priority**: `P1`, `P2`, `P3`, `P4` (most to least severe).
- **state**: `new`, `acknowledged`, `in_progress`, `resolved`, `closed`, in that fixed order along the primary path.
