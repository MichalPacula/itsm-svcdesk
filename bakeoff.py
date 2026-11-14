# ai-generated: 90% - Claude Code implemented CI-SPEC.md section 3 (P-14..P-23); checked against the practice set's expected.json
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json

Standard library only (runs as `python3 -S -E bakeoff.py`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

CLASS_CWES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}
SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
CWE_RE = re.compile(r"(?<![A-Za-z0-9])CWE-([0-9]+)", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")


def _get(obj, key):
    """Member of a dict; null counts as absent."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _list(value):
    return value if isinstance(value, list) else []


def tool_id(run) -> str:
    name = _get(_get(run, "tool"), "driver")
    name = _get(name, "name")
    if not isinstance(name, str):
        return "unknown"
    n = name.strip().lower()
    if n in ("trivy", "grype", "osv-scanner", "gitleaks"):
        return n
    if n in SEMGREP_NAMES:
        return "semgrep"
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n or "unknown"


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def normalize_path(uri: str) -> str:
    p = unquote(uri)
    if p[:7].lower() == "file://":
        p = p[7:]
    if p.startswith("./"):
        p = p[2:]
    return p


def in_set(path: str, root: str):
    parts = path.split("/")
    idx = [i for i, c in enumerate(parts) if c == root]
    if not idx:
        return None
    return "/".join(parts[idx[-1]:])


def lines_of(result):
    loc = _list(result.get("locations"))
    region = _get(_get(loc[0], "physicalLocation"), "region") if loc else None
    start = _get(region, "startLine")
    if not (is_int(start) and start >= 1):
        return None
    end = _get(region, "endLine")
    if not is_int(end) or end < start:
        end = start
    return start, end


def cwe_numbers(tags) -> set:
    out = set()
    for t in tags:
        if isinstance(t, str):
            out.update(int(m) for m in CWE_RE.findall(t))
    return out


def result_classes(tid: str, result: dict, rule) -> set:
    props = _get(result, "properties")
    c = _get(props, "class")
    if isinstance(c, str) and c in CLASS_CWES:
        return {c}
    if tid == "gitleaks":
        return {"secret"}
    if tid in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    rule_tags = [t for t in _list(_get(_get(rule, "properties"), "tags")) if isinstance(t, str)]
    if tid == "trivy":
        got = set()
        lowered = {t.lower() for t in rule_tags}
        if "vulnerability" in lowered:
            got.add("vulnerable-dependency")
        if "secret" in lowered:
            got.add("secret")
        if "misconfiguration" in lowered:
            got.add("misconfiguration")
        if got:
            return got
    own_tags = [t for t in _list(_get(props, "tags")) if isinstance(t, str)]
    nums = cwe_numbers(own_tags + rule_tags)
    got = {cls for cls, cw in CLASS_CWES.items() if cw & nums}
    return got or {"other"}


def pep503(s: str) -> str:
    return re.sub(r"[-_.]+", "-", s.lower())


def names_package(text, package: str) -> bool:
    if not isinstance(text, str):
        return False
    want = pep503(package)
    for tok in TOKEN_RE.findall(text):
        tok = tok.strip("._-")
        if tok and pep503(tok) == want:
            return True
    return False


def matches(defect: dict, file: str, classes: set, lines, text) -> bool:
    if file != defect.get("file") or defect.get("class") not in classes:
        return False
    if defect["class"] == "vulnerable-dependency":
        return names_package(text, defect.get("package", ""))
    if lines is None:
        return False
    return lines[0] <= defect["end_line"] and defect["start_line"] <= lines[1]


def score(num, den):
    return None if den == 0 else round(num / den, 4)


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    root = labels["set"]
    defects = labels["defects"]
    # per tool: list of in-set results (file, classes, lines, text, ruleid)
    found: dict = {}
    for doc in sarif_documents:
        for run in _list(_get(doc, "runs")):
            if not isinstance(run, dict):
                continue
            tid = tool_id(run)
            bucket = found.setdefault(tid, [])
            rules = [r for r in _list(_get(_get(run, "tool") and _get(_get(run, "tool"), "driver"), "rules"))]
            for res in _list(run.get("results")):
                if not isinstance(res, dict):
                    continue
                kind = res.get("kind")
                if kind is not None and kind != "fail":
                    continue
                sup = res.get("suppressions")
                if sup is not None and sup not in ([], {}, False, 0, ""):
                    continue
                locs = _list(res.get("locations"))
                if not locs:
                    continue
                uri = _get(_get(_get(locs[0], "physicalLocation"), "artifactLocation"), "uri")
                if not isinstance(uri, str) or uri == "":
                    continue
                f = in_set(normalize_path(uri), root)
                if f is None:
                    continue
                rid = res.get("ruleId")
                rule = None
                if isinstance(rid, str):
                    for r in rules:
                        if isinstance(r, dict) and r.get("id") == rid:
                            rule = r
                            break
                msg = _get(res, "message")
                text = msg.get("text") if isinstance(msg, dict) else None
                bucket.append((f, result_classes(tid, res, rule), lines_of(res), text, rid if isinstance(rid, str) else None))
    tools = {}
    for tid, results in found.items():
        matched = [False] * len(defects)
        fps = set()
        for (f, classes, lines, text, rid) in results:
            hit = False
            for i, d in enumerate(defects):
                if matches(d, f, classes, lines, text):
                    matched[i] = True
                    hit = True
            if not hit:
                fps.add((rid, f, lines))
        tp = sum(matched)
        fn = len(defects) - tp
        fp = len(fps)
        tools[tid] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": score(tp, tp + fp),
            "recall": score(tp, tp + fn),
            "f1": score(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": labels["set"], "defects": len(defects), "tools": tools}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
