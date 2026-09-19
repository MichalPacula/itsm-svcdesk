# ai-generated: 90% - Claude Code wrote this smoke suite; reviewed and accepted as-is
"""Stretch S3 own-tests: an HTTP smoke suite against SVCDESK_URL, stdlib only (CHECKS.md L1-STRETCH-3).

Run inside the built image as `python -m tests.run` (docker-compose.yml's `tests` service, profile
"tests"). Prints exactly one summary line, last: `ITSMLAB-TESTS: passed=<n> failed=<n>`.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SVCDESK_URL", "http://svcdesk:8080")

CHECKS: list[tuple[str, callable]] = []


def check(name: str):
    def decorator(fn):
        CHECKS.append((name, fn))
        return fn

    return decorator


def _request(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, json.loads(raw) if raw else None


def _wait_for_health(retries: int = 30, delay: float = 1.0) -> None:
    for _ in range(retries):
        try:
            status, _ = _request("GET", "/health")
            if status == 200:
                return
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(delay)
    raise RuntimeError(f"{BASE_URL}/health did not become ready in time")


def _reporter(name: str = "Own-Tests Reporter", vip: bool = False) -> dict:
    return {"name": name, "email": "own-tests@example.com", "vip": vip}


def _create(title: str, impact: int, urgency: int, vip: bool = False, clock: str = "2026-11-02T10:00:00Z"):
    status, body = _request(
        "POST", "/tickets",
        {"title": title, "reporter": _reporter(vip=vip), "impact": impact, "urgency": urgency},
        headers={"X-Test-Clock": clock},
    )
    assert status == 201, (status, body)
    return body


@check("health returns ok")
def _check_health():
    status, body = _request("GET", "/health")
    assert status == 200, status
    assert body.get("status") == "ok" and body.get("service") == "svcdesk", body


@check("unknown route is 404 with an error body")
def _check_unknown_route():
    status, body = _request("GET", "/this-route-does-not-exist-own-tests")
    assert status == 404, status
    assert "error" in body, body


@check("create ticket computes priority from the matrix")
def _check_create_matrix():
    body = _create("own-tests matrix", impact=1, urgency=1)
    assert body["priority"] == "P1", body
    assert body["state"] == "new", body


@check("vip floor raises a low matrix priority to P2")
def _check_vip_floor():
    body = _create("own-tests vip", impact=3, urgency=3, vip=True)
    assert body["priority"] == "P2", body


@check("missing title is rejected with an error body")
def _check_missing_title():
    status, body = _request(
        "POST", "/tickets",
        {"reporter": _reporter(), "impact": 1, "urgency": 1},
        headers={"X-Test-Clock": "2026-11-02T10:00:00Z"},
    )
    assert status in (400, 422), status
    assert "error" in body, body


@check("get ticket by id round-trips")
def _check_get_by_id():
    created = _create("own-tests get", impact=2, urgency=2)
    status, body = _request("GET", f"/tickets/{created['id']}")
    assert status == 200, status
    assert body["id"] == created["id"], body


@check("get unknown ticket is 404")
def _check_get_unknown():
    status, body = _request("GET", "/tickets/does-not-exist-own-tests")
    assert status == 404, status
    assert "error" in body, body


@check("full lifecycle: ack, start, resolve, close")
def _check_lifecycle():
    created = _create("own-tests lifecycle", impact=1, urgency=1)
    tid = created["id"]
    status, body = _request("POST", f"/tickets/{tid}/ack", headers={"X-Test-Clock": "2026-11-02T10:05:00Z"})
    assert status == 200 and body["state"] == "acknowledged", (status, body)
    status, body = _request("POST", f"/tickets/{tid}/start", headers={"X-Test-Clock": "2026-11-02T10:10:00Z"})
    assert status == 200 and body["state"] == "in_progress", (status, body)
    status, body = _request("POST", f"/tickets/{tid}/resolve", headers={"X-Test-Clock": "2026-11-02T11:00:00Z"})
    assert status == 200 and body["state"] == "resolved", (status, body)
    status, body = _request("POST", f"/tickets/{tid}/close", headers={"X-Test-Clock": "2026-11-02T12:00:00Z"})
    assert status == 200 and body["state"] == "closed", (status, body)


@check("resolve shortcut from new is 409")
def _check_shortcut_409():
    created = _create("own-tests shortcut", impact=1, urgency=1)
    status, body = _request(
        "POST", f"/tickets/{created['id']}/resolve", headers={"X-Test-Clock": "2026-11-02T10:05:00Z"}
    )
    assert status == 409, status
    assert "error" in body, body


@check("action on an unknown ticket id is 404")
def _check_action_unknown_id():
    status, _ = _request(
        "POST", "/tickets/does-not-exist-own-tests/ack", headers={"X-Test-Clock": "2026-11-02T10:05:00Z"}
    )
    assert status == 404, status


@check("sla endpoint reproduces the T1 vector")
def _check_sla_vector():
    created = _create("own-tests sla", impact=1, urgency=1, clock="2026-10-14T10:00:00Z")
    status, body = _request(
        "GET", f"/tickets/{created['id']}/sla", headers={"X-Test-Clock": "2026-10-14T10:00:00Z"}
    )
    assert status == 200, status
    assert body["ack_due_at"] == "2026-10-14T10:15:00Z", body
    assert body["resolve_due_at"] == "2026-10-14T14:00:00Z", body
    assert body["ack_breached"] is False, body


@check("list filters by priority")
def _check_list_filter():
    p1 = _create("own-tests list p1", impact=1, urgency=1)
    p4 = _create("own-tests list p4", impact=3, urgency=3)
    status, body = _request("GET", "/tickets?priority=P1")
    assert status == 200, status
    ids = {t["id"] for t in body}
    assert p1["id"] in ids, body
    assert p4["id"] not in ids, body


def main() -> int:
    _wait_for_health()
    passed = 0
    failed = 0
    for name, fn in CHECKS:
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}", file=sys.stderr)
        except Exception as exc:  # a broken check counts as failed, never crashes the suite
            failed += 1
            print(f"ERROR {name}: {exc}", file=sys.stderr)
    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
