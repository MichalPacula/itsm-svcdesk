<!-- ai-generated: 85% - Claude Code drafted this file describing its own working conventions for this repo; reviewed and accepted as-is -->
# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository.

## What this repository is

`svcdesk`: a small HTTP/JSON service-desk ticketing API, built for the ITSM course's Lab 1. The
authoritative sources, in order of precedence when they disagree: `specs/API.md` (exact HTTP
contract) > `specs/REQUIREMENTS.md` (why) > `specs/001-svcdesk-ticketing/spec.md` (the spec-kit
restatement used to plan and build this). `DECISIONS.md` records how the three deliberately
contradictory requirement pairs (C1, C2, C3) were resolved; the running service's behavior must
always match it exactly (`L1-CORE-4`).

## Build, run, test

- Local dev tests (not shipped in the image): `pip install -r requirements-dev.txt && pytest`.
- Run the service: `docker compose up --build --wait svcdesk`, then `curl localhost:8080/health`.
- Full conformance: `./itsmlab.sh verify 1` (needs Docker; pulls the course checker image).
- Optional own-tests profile: `docker compose --profile tests run --rm --build tests`.

## Rules that apply to any change here

- **Specs before code**: `L1-CORE-5` requires the `specs` receipt's commit to be an ancestor of
  every commit that adds a file under `src/` (other than `src/README.md`). Do not rewrite history
  before that commit, and do not add `src/` files in the same commit as new `specs/` content once
  the receipt exists.
- **No network at container run time**: dependencies install at build time only
  (`requirements.txt`, `Dockerfile`); nothing under `src/` may call out to the network.
- **No bind mounts** in `docker-compose.yml`; the named volume `svcdesk-data` is how tickets
  survive a restart (FR-023).
- **AI-disclosure header**: every file under `src/` and `specs/` with a checked extension
  (`.py .go .ts .js .java .cs .rb .rs .kt .md`), plus `DECISIONS.md`, needs
  `ai-generated: <0-100>% - <one line on how>` in its first ten lines.
- Timestamps are always RFC 3339 UTC with a `Z` suffix (FR-018); never emit a bare offset like
  `+00:00` from a new response field.

## Sub-agents

`.claude/agents/reviewer.md` is a read-only reviewer; see `AGENT-POLICY.md` for exactly what it
is barred from doing and why. Do not widen its tool access without updating that policy file to
match.
