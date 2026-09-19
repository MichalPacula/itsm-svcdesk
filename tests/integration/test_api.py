# ai-generated: 90% - Claude Code wrote this test module; reviewed and accepted as-is
"""End-to-end HTTP tests against the FastAPI app, reproducing key CHECKS.md L1-CORE-2 scenarios."""


def _reporter(name="Anna Nowak", vip=False):
    return {"name": name, "email": "anna.nowak@example.com", "vip": vip}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "svcdesk"}


def test_unknown_route_is_404(client):
    resp = client.get("/this-route-does-not-exist-9f3c")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_create_ticket_worked_example(client):
    # API.md sec7 worked example.
    resp = client.post(
        "/tickets",
        headers={"X-Test-Clock": "2026-10-14T10:00:00Z"},
        json={
            "title": "Printer on floor 2 is down",
            "description": "Nobody on the floor can print.",
            "reporter": _reporter(),
            "impact": 2,
            "urgency": 1,
            "related_to": None,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority"] == "P2"
    assert body["state"] == "new"
    assert body["created_at"] == "2026-10-14T10:00:00Z"
    assert body["sla"]["ack_due_at"] == "2026-10-14T11:00:00Z"
    assert body["sla"]["resolve_due_at"] == "2026-10-15T10:00:00Z"
    assert body["acknowledged_at"] is None
    assert isinstance(body["id"], str) and body["id"]


def test_create_ticket_missing_title_rejected(client):
    resp = client.post(
        "/tickets",
        headers={"X-Test-Clock": "2026-10-14T10:00:00Z"},
        json={"reporter": _reporter(), "impact": 1, "urgency": 1},
    )
    assert resp.status_code in (400, 422)
    assert "error" in resp.json()
    assert client.get("/tickets").json() == []


def test_server_owned_fields_are_ignored(client):
    resp = client.post(
        "/tickets",
        headers={"X-Test-Clock": "2026-10-14T10:00:00Z"},
        json={
            "title": "t", "reporter": _reporter(vip=True), "impact": 3, "urgency": 3,
            "id": "client-chosen-id", "priority": "P1", "state": "closed",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] != "client-chosen-id"
    assert body["priority"] == "P2"  # VIP floor, never the client-supplied P1
    assert body["state"] == "new"


def test_malformed_test_clock_rejected(client):
    resp = client.post(
        "/tickets",
        headers={"X-Test-Clock": "yesterday"},
        json={"title": "t", "reporter": _reporter(), "impact": 1, "urgency": 1},
    )
    assert resp.status_code in (400, 422)


def _create(client, impact=1, urgency=1, vip=False, clock="2026-10-14T10:00:00Z"):
    resp = client.post(
        "/tickets",
        headers={"X-Test-Clock": clock},
        json={"title": "t", "reporter": _reporter(vip=vip), "impact": impact, "urgency": urgency},
    )
    assert resp.status_code == 201
    return resp.json()


def test_get_ticket_by_id(client):
    created = _create(client)
    resp = client.get(f"/tickets/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_unknown_ticket_404(client):
    resp = client.get("/tickets/does-not-exist-9f3c")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_list_filters_by_state_and_priority(client):
    p1 = _create(client, impact=1, urgency=1)
    p4 = _create(client, impact=3, urgency=3)

    by_state = client.get("/tickets", params={"state": "new"}).json()
    assert {t["id"] for t in by_state} == {p1["id"], p4["id"]}

    by_priority = client.get("/tickets", params={"priority": "P1"}).json()
    ids = {t["id"] for t in by_priority}
    assert p1["id"] in ids
    assert p4["id"] not in ids


def test_full_lifecycle_happy_path(client):
    ticket = _create(client, clock="2026-10-14T10:00:00Z")
    tid = ticket["id"]

    r = client.post(f"/tickets/{tid}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    assert r.status_code == 200 and r.json()["state"] == "acknowledged"
    assert r.json()["acknowledged_at"] == "2026-10-14T10:05:00Z"

    r = client.post(f"/tickets/{tid}/start", headers={"X-Test-Clock": "2026-10-14T10:10:00Z"})
    assert r.status_code == 200 and r.json()["state"] == "in_progress"

    r = client.post(f"/tickets/{tid}/resolve", headers={"X-Test-Clock": "2026-10-14T12:00:00Z"})
    assert r.status_code == 200 and r.json()["state"] == "resolved"
    assert r.json()["resolved_at"] == "2026-10-14T12:00:00Z"

    r = client.post(f"/tickets/{tid}/close", headers={"X-Test-Clock": "2026-10-14T13:00:00Z"})
    assert r.status_code == 200 and r.json()["state"] == "closed"
    assert r.json()["closed_at"] == "2026-10-14T13:00:00Z"


def test_resolve_shortcut_from_new_is_409(client):
    ticket = _create(client)
    resp = client.post(f"/tickets/{ticket['id']}/resolve", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    assert resp.status_code == 409
    assert "error" in resp.json()


def test_resolve_on_acknowledged_is_409(client):
    # L1-CORE-2.49
    ticket = _create(client)
    client.post(f"/tickets/{ticket['id']}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    resp = client.post(f"/tickets/{ticket['id']}/resolve", headers={"X-Test-Clock": "2026-10-14T10:06:00Z"})
    assert resp.status_code == 409


def test_action_on_unknown_id_is_404(client):
    resp = client.post("/tickets/does-not-exist/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    assert resp.status_code == 404


def test_sla_endpoint_t1_vector(client):
    ticket = _create(client, impact=1, urgency=1, clock="2026-10-14T10:00:00Z")
    resp = client.get(f"/tickets/{ticket['id']}/sla", headers={"X-Test-Clock": "2026-10-14T10:00:00Z"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["priority"] == "P1"
    assert body["ack_due_at"] == "2026-10-14T10:15:00Z"
    assert body["resolve_due_at"] == "2026-10-14T14:00:00Z"
    assert body["ack_breached"] is False
    assert body["paused"] is False


def test_sla_endpoint_c1_p1_never_pauses_and_breaches_off_hours(client):
    # T3 vector: P1 created Friday 17:00 local; C1 = wallclock for this service.
    ticket = _create(client, impact=1, urgency=1, clock="2026-10-16T15:00:00Z")
    resp = client.get(f"/tickets/{ticket['id']}/sla", headers={"X-Test-Clock": "2026-10-16T15:20:00Z"})
    body = resp.json()
    assert body["ack_due_at"] == "2026-10-16T15:15:00Z"
    assert body["ack_breached"] is True
    assert body["paused"] is False


def test_reopen_resolved_after_6_days(client):
    ticket = _create(client, clock="2026-10-14T10:00:00Z")
    tid = ticket["id"]
    client.post(f"/tickets/{tid}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    client.post(f"/tickets/{tid}/start", headers={"X-Test-Clock": "2026-10-14T10:10:00Z"})
    client.post(f"/tickets/{tid}/resolve", headers={"X-Test-Clock": "2026-10-14T12:00:00Z"})

    resp = client.post(f"/tickets/{tid}/reopen", headers={"X-Test-Clock": "2026-10-20T12:00:00Z"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "in_progress"


def test_reopen_after_7_days_and_1s_is_409(client):
    ticket = _create(client, clock="2026-10-14T10:00:00Z")
    tid = ticket["id"]
    client.post(f"/tickets/{tid}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    client.post(f"/tickets/{tid}/start", headers={"X-Test-Clock": "2026-10-14T10:10:00Z"})
    client.post(f"/tickets/{tid}/resolve", headers={"X-Test-Clock": "2026-10-14T12:00:00Z"})

    resp = client.post(f"/tickets/{tid}/reopen", headers={"X-Test-Clock": "2026-10-21T12:00:01Z"})
    assert resp.status_code == 409


def test_reopen_closed_ticket_is_always_409(client):
    # Decision C2 = immutable.
    ticket = _create(client, clock="2026-10-14T10:00:00Z")
    tid = ticket["id"]
    client.post(f"/tickets/{tid}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    client.post(f"/tickets/{tid}/start", headers={"X-Test-Clock": "2026-10-14T10:10:00Z"})
    client.post(f"/tickets/{tid}/resolve", headers={"X-Test-Clock": "2026-10-14T12:00:00Z"})
    client.post(f"/tickets/{tid}/close", headers={"X-Test-Clock": "2026-10-14T13:00:00Z"})

    resp = client.post(f"/tickets/{tid}/reopen", headers={"X-Test-Clock": "2026-10-15T13:00:00Z"})
    assert resp.status_code == 409


def test_reopen_new_ticket_is_409(client):
    ticket = _create(client)
    resp = client.post(f"/tickets/{ticket['id']}/reopen", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"})
    assert resp.status_code == 409
