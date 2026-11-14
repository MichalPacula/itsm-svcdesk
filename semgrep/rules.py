# ai-generated: 70% - Claude Code wrote the test cases for semgrep/rules.yml
import sqlite3
from datetime import datetime


def sql(conn: sqlite3.Connection, name, clause):
    # ruleid: svcdesk-fstring-sql
    conn.execute(f"UPDATE tickets SET {clause} WHERE id = 1")
    # ruleid: svcdesk-fstring-sql
    conn.executemany(f"INSERT INTO t VALUES ({name})", [])
    # ok: svcdesk-fstring-sql
    conn.execute("SELECT * FROM tickets WHERE id = ?", (1,))
    query = "SELECT 1"
    # ok: svcdesk-fstring-sql
    conn.execute(query)


def times(value):
    # ruleid: svcdesk-bare-fromisoformat
    a = datetime.fromisoformat(value)
    # ok: svcdesk-bare-fromisoformat
    b = datetime.now()
    # ok: svcdesk-bare-fromisoformat
    c = value.isoformat()
    return a, b, c
