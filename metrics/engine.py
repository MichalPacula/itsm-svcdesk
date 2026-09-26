# ai-generated: 85% - Claude Code drafted this module from METRIC-SPEC.md sec 2-5; reviewed and accepted
"""The five DORA metrics, the six edge-case rules, and ground truth (METRIC-SPEC.md sec 2-5)."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from .validation import ParsedLog

_DAY_SECONDS = 86400


def _round_seconds(raw: float) -> int:
    """R-03: whole seconds, rounded half-up."""
    return int(Decimal(repr(raw)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _round_rate(raw: float) -> float:
    """R-03: ratios and rates to six decimal places, rounded half-up."""
    return float(Decimal(repr(raw)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _clamp(raw_seconds: float) -> tuple:
    """R-03: a negative duration is clamped to zero. Returns (value, was_negative)."""
    if raw_seconds < 0:
        return 0.0, True
    return raw_seconds, False


def _median(values: list) -> Optional[int]:
    """R-04 (odd: middle value; even: mean of the two middle values), rounded by R-03."""
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    raw = ordered[mid] if n % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2
    return _round_seconds(raw)


def _resolve_all_changes(commits: dict) -> dict:
    """R-06: resolve every commit's sha to its change_id, following 'reverts' transitively so a
    revert of a revert collapses to the original change rather than three separate changes."""
    memo: dict = {}

    def resolve(sha: str, chain: list) -> str:
        if sha in memo:
            return memo[sha]
        commit = commits[sha]
        if commit["reverts"] is None:
            result = commit["change_id"]
        else:
            if commit["reverts"] in chain:
                raise ValueError(f"'reverts' cycle detected at sha {sha!r}")
            result = resolve(commit["reverts"], chain + [sha])
        memo[sha] = result
        return result

    return {sha: resolve(sha, []) for sha in commits}


def compute(log: ParsedLog, window_from: datetime, window_to: datetime) -> dict:
    commits = log.commits
    window_days = (window_to - window_from).total_seconds() / _DAY_SECONDS

    # R-01: only production deployments are in scope, at all.
    production = [d for d in log.deployments if d["environment"] == "production"]
    # R-02: half-open window, deployments only; commits and incidents are never window-filtered.
    in_window = [d for d in production if window_from <= d["at"] < window_to]
    successful = [d for d in in_window if d["outcome"] == "success"]
    failed = [d for d in in_window if d["outcome"] == "failure"]

    # --- R-08 change_lead_time_seconds_p50, with E1 (clock skew) and E4 (no commits) ---
    # "for every sha ... form one pair at that commit's first such [successful] deployment"
    first_deploy_at: dict = {}
    for d in successful:
        for sha in d["commits"]:
            at = d["at"]
            if sha not in first_deploy_at or at < first_deploy_at[sha]:
                first_deploy_at[sha] = at

    lead_time_pairs: list = []
    negative_lead_time_pairs = 0
    for sha, deploy_at in first_deploy_at.items():
        raw = (deploy_at - commits[sha]["at"]).total_seconds()
        value, was_negative = _clamp(raw)  # E1: clamped to zero and counted, never discarded
        if was_negative:
            negative_lead_time_pairs += 1
        lead_time_pairs.append(value)

    change_lead_time_seconds_p50 = _median(lead_time_pairs)

    # E4: a deployment with no commits contributes no pair but is dropped from nothing else.
    deployments_without_commits = sum(1 for d in in_window if not d["commits"])

    # --- E3: commits that reached production off `main` (R-09: branch never filters R-08) ---
    off_main_shas: set = set()
    for d in in_window:  # successful or failed, any production deployment in the window
        for sha in d["commits"]:
            if commits[sha]["branch"] != "main":
                off_main_shas.add(sha)
    commits_never_on_main = len(off_main_shas)

    # --- R-11 deployment_frequency_per_day ---
    deployment_frequency_per_day = _round_rate(len(in_window) / window_days)

    # --- incidents: covering-incident lookup for R-12, and intervals for E6 ---
    incidents = log.incidents
    covering_candidates: dict = {}
    for incident_id, rec in incidents.items():
        if rec["opened"] is None:
            continue
        for dep_id in rec["deployments"]:
            covering_candidates.setdefault(dep_id, []).append((rec["opened"], incident_id))

    def covering_incident(deployment_id: str) -> Optional[str]:
        candidates = covering_candidates.get(deployment_id)
        if not candidates:
            return None
        # "the incident whose deployments contains that deployment_id and whose opened instant
        # is earliest (ties: the lowest incident_id by byte order)"
        return sorted(candidates, key=lambda pair: (pair[0], pair[1]))[0][1]

    # --- R-12 failed_deployment_recovery_time_seconds_p50, with E5 (never recovered) ---
    recovered: list = []
    open_failures = 0
    for d in failed:
        incident_id = covering_incident(d["deployment_id"])
        resolved_at = incidents[incident_id]["resolved"] if incident_id is not None else None
        if incident_id is None or resolved_at is None:
            open_failures += 1  # E5: no covering incident, or one that never resolved
            continue
        raw = (resolved_at - d["at"]).total_seconds()
        value, _ = _clamp(raw)
        recovered.append(value)

    failed_deployment_recovery_time_seconds_p50 = _median(recovered)

    # --- E6: overlapping incident pairs (per failed deployment, never merged/summed) ---
    intervals = []
    for rec in incidents.values():
        if rec["opened"] is None:
            continue
        end = rec["resolved"] if rec["resolved"] is not None else window_to
        intervals.append((rec["opened"], end))
    overlapping_incident_pairs = 0
    for i in range(len(intervals)):
        a_start, a_end = intervals[i]
        for j in range(i + 1, len(intervals)):
            b_start, b_end = intervals[j]
            if a_start < b_end and b_start < a_end:
                overlapping_incident_pairs += 1

    # --- R-14 change_fail_rate, R-15 deployment_rework_rate ---
    denom = len(in_window)
    change_fail_rate = _round_rate(len(failed) / denom) if denom else None
    rework_deployments = sum(1 for d in in_window if d["unplanned"] and d["caused_by"] is not None)
    deployment_rework_rate = _round_rate(rework_deployments / denom) if denom else None

    # --- R-06/R-07: changes, over the whole log, window or not ---
    change_of_sha = _resolve_all_changes(commits)
    first_commit_instant: dict = {}
    for sha, change_id in change_of_sha.items():
        at = commits[sha]["at"]
        if change_id not in first_commit_instant or at < first_commit_instant[change_id]:
            first_commit_instant[change_id] = at
    changes = len(first_commit_instant)
    # E2: commits whose reverts is non-null contributed no change of their own under R-06.
    revert_chains_collapsed = sum(1 for c in commits.values() if c["reverts"] is not None)

    # --- R-16/R-17: ground truth ---
    first_successful_delivery: dict = {}
    for d in successful:
        for sha in d["commits"]:
            change_id = change_of_sha[sha]
            at = d["at"]
            if change_id not in first_successful_delivery or at < first_successful_delivery[change_id]:
                first_successful_delivery[change_id] = at
    changes_delivered = len(first_successful_delivery)

    true_lead_times: list = []
    for change_id, delivered_at in first_successful_delivery.items():
        raw = (delivered_at - first_commit_instant[change_id]).total_seconds()
        value, _ = _clamp(raw)
        true_lead_times.append(value)
    true_change_lead_time_seconds_p50 = _median(true_lead_times)

    return {
        "deployment_frequency_per_day": deployment_frequency_per_day,
        "change_lead_time_seconds_p50": change_lead_time_seconds_p50,
        "failed_deployment_recovery_time_seconds_p50": failed_deployment_recovery_time_seconds_p50,
        "change_fail_rate": change_fail_rate,
        "deployment_rework_rate": deployment_rework_rate,
        "counts": {
            "deployments": len(in_window),
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovered),
            "open_failures": open_failures,
            "rework_deployments": rework_deployments,
            "lead_time_pairs": len(lead_time_pairs),
            "changes": changes,
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_time_pairs,
            "deployments_without_commits": deployments_without_commits,
            "commits_never_on_main": commits_never_on_main,
            "revert_chains_collapsed": revert_chains_collapsed,
            "overlapping_incident_pairs": overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered": changes_delivered,
            "true_change_lead_time_seconds_p50": true_change_lead_time_seconds_p50,
        },
    }
