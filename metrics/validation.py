# ai-generated: 85% - Claude Code drafted this module from METRIC-SPEC.md sec 1; reviewed and accepted
"""Parsing and well-formedness validation for the DORA event log (METRIC-SPEC.md sec 1).

Deliberately independent of svcdesk.clock: this package has no dependency on the ticketing
service, so it repeats the small RFC 3339 "an instant, not a bare date/time" check rather than
importing it.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from .errors import MetricsError

_EVENT_TYPES = {"commit", "deployment", "incident"}
_OUTCOMES = {"success", "failure"}
_PHASES = {"opened", "resolved"}


def _parse_instant(value: Any, where: str) -> datetime:
    if not isinstance(value, str):
        raise MetricsError(f"{where}: 'at' must be a string")
    try:
        dt = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise MetricsError(f"{where}: 'at' is not an RFC 3339 instant: {value!r}") from exc
    if dt.tzinfo is None:
        raise MetricsError(f"{where}: 'at' has no offset: {value!r}")
    return dt.astimezone(timezone.utc)


def _require(obj: dict, key: str, types: tuple, where: str) -> Any:
    if key not in obj:
        raise MetricsError(f"{where}: missing '{key}'")
    value = obj[key]
    if not isinstance(value, types):
        raise MetricsError(f"{where}: '{key}' has the wrong type")
    return value


def _require_str_or_none(obj: dict, key: str, where: str) -> Optional[str]:
    if key not in obj:
        raise MetricsError(f"{where}: missing '{key}'")
    value = obj[key]
    if value is not None and not isinstance(value, str):
        raise MetricsError(f"{where}: '{key}' must be a string or null")
    return value


def _require_str_list(obj: dict, key: str, where: str) -> list:
    value = _require(obj, key, (list,), where)
    for item in value:
        if not isinstance(item, str):
            raise MetricsError(f"{where}: '{key}' must be a list of strings")
    return value


class ParsedLog:
    """Everything the engine needs, already validated, deduplicated (R-05) and normalized."""

    def __init__(self) -> None:
        # sha -> {"at": datetime, "branch": str, "change_id": str|None, "reverts": str|None}
        self.commits: dict[str, dict] = {}
        # [{"deployment_id","at","environment","outcome","commits","unplanned","caused_by"}]
        self.deployments: list[dict] = []
        # incident_id -> {"opened": datetime|None, "resolved": datetime|None, "deployments": set[str]}
        self.incidents: dict[str, dict] = {}


def parse_and_validate(raw_events: Any) -> ParsedLog:
    if not isinstance(raw_events, list):
        raise MetricsError("'events' must be an array")

    seen_event_ids: set = set()
    commit_events: list = []
    deployment_events: list = []
    incident_events: list = []

    for index, raw in enumerate(raw_events):
        where = f"events[{index}]"
        if not isinstance(raw, dict):
            raise MetricsError(f"{where}: not an object")

        event_id = _require(raw, "event_id", (str,), where)
        if not (1 <= len(event_id) <= 64):
            raise MetricsError(f"{where}: 'event_id' must be 1..64 characters")

        # R-05: a repeated event_id is counted once - the first occurrence wins, later ones are
        # ignored outright (not even validated further), and that is not itself an error.
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)

        event_type = _require(raw, "type", (str,), where)
        if event_type not in _EVENT_TYPES:
            raise MetricsError(f"{where}: unknown 'type' {event_type!r}")

        at = _parse_instant(raw.get("at"), where)

        if event_type == "commit":
            sha = _require(raw, "sha", (str,), where)
            branch = _require(raw, "branch", (str,), where)
            change_id = _require_str_or_none(raw, "change_id", where)
            reverts = _require_str_or_none(raw, "reverts", where)
            # "a commit carries a change_id exactly when reverts is null"
            if (change_id is None) == (reverts is None):
                raise MetricsError(f"{where}: exactly one of 'change_id'/'reverts' must be null")
            commit_events.append(
                {"event_id": event_id, "at": at, "sha": sha, "branch": branch,
                 "change_id": change_id, "reverts": reverts}
            )
        elif event_type == "deployment":
            deployment_id = _require(raw, "deployment_id", (str,), where)
            environment = _require(raw, "environment", (str,), where)
            outcome = _require(raw, "outcome", (str,), where)
            if outcome not in _OUTCOMES:
                raise MetricsError(f"{where}: 'outcome' must be 'success' or 'failure'")
            commits = _require_str_list(raw, "commits", where)
            unplanned = _require(raw, "unplanned", (bool,), where)
            caused_by = _require_str_or_none(raw, "caused_by", where)
            deployment_events.append(
                {"event_id": event_id, "at": at, "deployment_id": deployment_id,
                 "environment": environment, "outcome": outcome, "commits": commits,
                 "unplanned": unplanned, "caused_by": caused_by}
            )
        else:  # incident
            incident_id = _require(raw, "incident_id", (str,), where)
            phase = _require(raw, "phase", (str,), where)
            if phase not in _PHASES:
                raise MetricsError(f"{where}: 'phase' must be 'opened' or 'resolved'")
            deployments = _require_str_list(raw, "deployments", where)
            incident_events.append(
                {"event_id": event_id, "at": at, "incident_id": incident_id,
                 "phase": phase, "deployments": deployments}
            )

    log = ParsedLog()

    # "every sha is unique"
    shas = [c["sha"] for c in commit_events]
    if len(shas) != len(set(shas)):
        raise MetricsError("well-formedness: duplicate 'sha' across distinct commits")
    for c in commit_events:
        log.commits[c["sha"]] = c

    deployment_ids = {d["deployment_id"] for d in deployment_events}
    incident_ids = {i["incident_id"] for i in incident_events}

    # "every reverts ... names something present in the log"
    for c in commit_events:
        if c["reverts"] is not None and c["reverts"] not in log.commits:
            raise MetricsError(
                f"well-formedness: commit {c['event_id']} reverts unknown sha {c['reverts']!r}"
            )

    # "every entry of a deployment's commits ... names something present in the log"
    # "every caused_by ... names something present in the log"
    for d in deployment_events:
        for sha in d["commits"]:
            if sha not in log.commits:
                raise MetricsError(
                    f"well-formedness: deployment {d['event_id']} names unknown sha {sha!r}"
                )
        if d["caused_by"] is not None and d["caused_by"] not in incident_ids:
            raise MetricsError(
                f"well-formedness: deployment {d['event_id']} names unknown incident {d['caused_by']!r}"
            )
        log.deployments.append(d)

    # "every entry of an incident's deployments names something present in the log"
    # "the same incident_id carries at most one of each [phase]"
    # "every incident that resolved was also opened"
    for i in incident_events:
        for dep_id in i["deployments"]:
            if dep_id not in deployment_ids:
                raise MetricsError(
                    f"well-formedness: incident {i['event_id']} names unknown deployment {dep_id!r}"
                )
        rec = log.incidents.setdefault(
            i["incident_id"], {"opened": None, "resolved": None, "deployments": set()}
        )
        if rec[i["phase"]] is not None:
            raise MetricsError(
                f"well-formedness: incident {i['incident_id']} has more than one '{i['phase']}' event"
            )
        rec[i["phase"]] = i["at"]
        rec["deployments"].update(i["deployments"])

    for incident_id, rec in log.incidents.items():
        if rec["resolved"] is not None and rec["opened"] is None:
            raise MetricsError(
                f"well-formedness: incident {incident_id} resolved without ever being opened"
            )

    return log
