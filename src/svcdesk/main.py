# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""FastAPI app: route wiring for the svcdesk ticketing API (API.md sec1)."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Query

from . import store
from .clock import format_instant, resolve_now
from .errors import NotFoundError, register_exception_handlers
from .models import SlaStatus, Ticket, TicketCreate
from .priority import compute_priority
from .sla import due_instants, evaluate_sla
from .state_machine import apply_transition, can_reopen


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="svcdesk", lifespan=lifespan)
register_exception_handlers(app)


def _row_to_ticket(row: dict) -> dict:
    created_at = datetime.fromisoformat(row["created_at"])
    ack_due, resolve_due = due_instants(created_at, row["priority"])
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "reporter": {
            "name": row["reporter_name"],
            "email": row["reporter_email"],
            "vip": bool(row["reporter_vip"]),
        },
        "impact": row["impact"],
        "urgency": row["urgency"],
        "priority": row["priority"],
        "state": row["state"],
        "created_at": format_instant(created_at),
        "acknowledged_at": _fmt_or_none(row["acknowledged_at"]),
        "resolved_at": _fmt_or_none(row["resolved_at"]),
        "closed_at": _fmt_or_none(row["closed_at"]),
        "related_to": row["related_to"],
        "sla": {"ack_due_at": format_instant(ack_due), "resolve_due_at": format_instant(resolve_due)},
    }


def _fmt_or_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return format_instant(datetime.fromisoformat(value))


def _get_ticket_or_404(ticket_id: str) -> dict:
    row = store.get_ticket(ticket_id)
    if row is None:
        raise NotFoundError(f"ticket '{ticket_id}' not found")
    return row


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201, response_model=Ticket)
def create_ticket(body: TicketCreate, now: datetime = Depends(resolve_now)) -> dict:
    priority = compute_priority(body.impact, body.urgency, body.reporter.vip)
    row = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "description": body.description,
        "reporter_name": body.reporter.name,
        "reporter_email": body.reporter.email,
        "reporter_vip": int(body.reporter.vip),
        "impact": body.impact,
        "urgency": body.urgency,
        "priority": priority,
        "state": "new",
        "related_to": body.related_to,
        "created_at": format_instant(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
    }
    store.insert_ticket(row)
    return _row_to_ticket(row)


@app.get("/tickets", response_model=list[Ticket])
def list_tickets(
    state: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
) -> list[dict]:
    rows = store.list_tickets(state=state, priority=priority)
    return [_row_to_ticket(r) for r in rows]


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str) -> dict:
    return _row_to_ticket(_get_ticket_or_404(ticket_id))


@app.get("/tickets/{ticket_id}/sla", response_model=SlaStatus)
def get_ticket_sla(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    row = _get_ticket_or_404(ticket_id)
    acknowledged_at = datetime.fromisoformat(row["acknowledged_at"]) if row["acknowledged_at"] else None
    resolved_at = datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
    result = evaluate_sla(
        priority=row["priority"],
        state=row["state"],
        created_at=datetime.fromisoformat(row["created_at"]),
        acknowledged_at=acknowledged_at,
        resolved_at=resolved_at,
        now=now,
    )
    return {
        "priority": row["priority"],
        "ack_due_at": format_instant(result["ack_due_at"]),
        "resolve_due_at": format_instant(result["resolve_due_at"]),
        "ack_breached": result["ack_breached"],
        "resolve_breached": result["resolve_breached"],
        "paused": result["paused"],
    }


def _apply_action(ticket_id: str, action: str, now: datetime) -> dict:
    row = _get_ticket_or_404(ticket_id)
    new_state = apply_transition(row["state"], action)
    updates = {"state": new_state}
    if action == "ack":
        updates["acknowledged_at"] = format_instant(now)
    elif action == "resolve":
        updates["resolved_at"] = format_instant(now)
    elif action == "close":
        updates["closed_at"] = format_instant(now)
    store.update_ticket(ticket_id, **updates)
    row.update(updates)
    return _row_to_ticket(row)


@app.post("/tickets/{ticket_id}/ack", response_model=Ticket)
def ack_ticket(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    return _apply_action(ticket_id, "ack", now)


@app.post("/tickets/{ticket_id}/start", response_model=Ticket)
def start_ticket(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    return _apply_action(ticket_id, "start", now)


@app.post("/tickets/{ticket_id}/resolve", response_model=Ticket)
def resolve_ticket(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    return _apply_action(ticket_id, "resolve", now)


@app.post("/tickets/{ticket_id}/close", response_model=Ticket)
def close_ticket(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    return _apply_action(ticket_id, "close", now)


@app.post("/tickets/{ticket_id}/reopen", response_model=Ticket)
def reopen_ticket(ticket_id: str, now: datetime = Depends(resolve_now)) -> dict:
    row = _get_ticket_or_404(ticket_id)
    resolved_at = datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
    can_reopen(row["state"], resolved_at, now)  # raises InvalidTransitionError (409) if not allowed
    updates = {"state": "in_progress", "resolved_at": None, "closed_at": None}
    store.update_ticket(ticket_id, **updates)
    row.update(updates)
    return _row_to_ticket(row)
