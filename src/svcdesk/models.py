# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""Request/response schemas (data-model.md, contracts/openapi.yaml).

Server-owned fields (id, priority, state, created_at, acknowledged_at, resolved_at,
closed_at, sla) and any unrecognized field sent on TicketCreate are silently dropped:
pydantic's default `extra="ignore"` behavior does this without any extra code (FR-006, FR-021).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal[1, 2, 3]
Priority = Literal["P1", "P2", "P3", "P4"]
State = Literal["new", "acknowledged", "in_progress", "resolved", "closed"]


class Reporter(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = None
    vip: bool = False


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    reporter: Reporter
    impact: Level
    urgency: Level
    related_to: Optional[str] = None


class Sla(BaseModel):
    ack_due_at: str
    resolve_due_at: str


class Ticket(BaseModel):
    id: str
    title: str
    description: str
    reporter: Reporter
    impact: Level
    urgency: Level
    priority: Priority
    state: State
    created_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    related_to: Optional[str] = None
    sla: Sla


class SlaStatus(BaseModel):
    priority: Priority
    ack_due_at: str
    resolve_due_at: str
    ack_breached: bool
    resolve_breached: bool
    paused: bool


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    error: ErrorDetail
