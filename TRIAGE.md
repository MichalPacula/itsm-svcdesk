---
lab5_triage:
  image: ghcr.io/michalpacula/itsm-svcdesk@sha256:388a26834c0f7f751b49ef2b60dc101e725e19d7256f989173aee22332002dfe
  sarif_receipt: 365
---
<!-- ai-generated: 70% - Claude Code drafted the rows from my receipted SARIF and matrix; I reviewed the decisions -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
`.trivyignore` and `.gitleaksignore` are empty: the gates went green by fixing, not by ignoring.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | image gate (fixable HIGH/CRITICAL) | fix | Dockerfile: base image pinned by digest, `apt-get upgrade -y` after FROM, and `pip uninstall -y pip` so pip's vendored packages are gone; the image job went green on main. |
| grype | GHSA-6w46-j5rx-g56g-pytest | accept | requirements-dev.txt pins pytest 8.4.1 (tmpdir handling, medium); dev-only, never installed in the image, so no runtime exposure. Bump pytest at the next dependency refresh. |
| osv-scanner | CVE-2025-71176 | accept | The same pytest 8.4.1 advisory in requirements-dev.txt; local test tooling only, not in the Docker image. Accepted until pytest is bumped. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | Dockerfile:36 runs uvicorn as root. The container is a course lab with a named volume at /data; adding a non-root user is planned after Lab 5. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | lab4/agent/prom_mcp.py:34 calls urlopen on URL from a fixed environment setting plus a fixed path, not on user input; it is a Lab 4 helper outside src/. |
| semgrep | python.lang.security.audit.formatted-sql-query.formatted-sql-query | false-positive | semgrep/rules.py:8 is my Stretch 3 test file; its f-string SQL is a deliberate test case for my own rule and never executed. |
| semgrep | python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query | false-positive | src/svcdesk/store.py:62 and :104 build SQL from fixed column names and bind all values as :name parameters; no SQLAlchemy is used (sqlite3), and semgrep/rules.py:8 is a test case. |

## Bake-off

On my canary set (9 defects) the matrix was: trivy TP 4, FP 0, FN 5 (precision 1.0, recall 0.4444, F1 0.6154); gitleaks 2/0/7 (1.0, 0.2222); grype and osv-scanner each 2/0/7 (1.0, 0.2222); semgrep 5/2/4 (precision 0.7143, recall 0.5556, F1 0.625). If I had to pick gates, I would keep Trivy and gitleaks as blocking gates: both had zero false positives, so a red build means something. Trivy found both vulnerable pins and two of the three hard-coded credentials, the most of any zero-FP tool. Semgrep has the highest recall because it alone sees the code defects (the command injection, the deserialization and the SQL injection), but two FPs out of seven reported lines make it a reviewer's report rather than a gate. Grype and osv-scanner added nothing over Trivy on the two pins, so they are redundant here. Surprises: gitleaks missed the credential in mailer.py (C05) and no tool found it, and no tool found the path traversal in attachment_read.py (A03). Both survivors look like ordinary code with no known signature, which scanners with rules cannot see. Every recall is an upper bound: the defects are seeded and written to look like textbook cases, and studies find detection rates on injected defects several times higher than on real ones.
