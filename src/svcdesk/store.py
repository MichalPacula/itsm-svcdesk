# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""SQLite persistence for tickets (FR-023: tickets survive a restart)."""

import os
import sqlite3
import threading
from typing import Optional

_write_lock = threading.Lock()

_COLUMNS = (
    "id", "title", "description", "reporter_name", "reporter_email", "reporter_vip",
    "impact", "urgency", "priority", "state", "related_to",
    "created_at", "acknowledged_at", "resolved_at", "closed_at",
)


def _db_path() -> str:
    return os.environ.get("SVCDESK_DB", "svcdesk.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reporter_name TEXT NOT NULL,
                reporter_email TEXT,
                reporter_vip INTEGER NOT NULL,
                impact INTEGER NOT NULL,
                urgency INTEGER NOT NULL,
                priority TEXT NOT NULL,
                state TEXT NOT NULL,
                related_to TEXT,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT,
                closed_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_ticket(ticket: dict) -> None:
    with _write_lock:
        conn = _connect()
        try:
            placeholders = ", ".join(f":{c}" for c in _COLUMNS)
            conn.execute(
                f"INSERT INTO tickets ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
                ticket,
            )
            conn.commit()
        finally:
            conn.close()


def get_ticket(ticket_id: str) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row is not None else None
    finally:
        conn.close()


def list_tickets(state: Optional[str] = None, priority: Optional[str] = None) -> list[dict]:
    conn = _connect()
    try:
        query = "SELECT * FROM tickets WHERE 1=1"
        params: list[str] = []
        if state is not None:
            query += " AND state = ?"
            params.append(state)
        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_ticket(ticket_id: str, **fields) -> None:
    with _write_lock:
        conn = _connect()
        try:
            set_clause = ", ".join(f"{k} = :{k}" for k in fields)
            params = dict(fields)
            params["id"] = ticket_id
            conn.execute(f"UPDATE tickets SET {set_clause} WHERE id = :id", params)
            conn.commit()
        finally:
            conn.close()
