<!-- ai-generated: 85% - Claude Code drafted this policy; reviewed and accepted as-is -->
# Agent policy

The `reviewer` sub-agent (`.claude/agents/reviewer.md`) is read-only by construction, not by
convention: its `disallowedTools` list removes the specific actions below from its reach entirely,
so a reviewer that misjudges a diff cannot also act on that misjudgment. Each entry names an
action whose blast radius belongs to the person or agent that actually made the change, not to
the one commenting on it.

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, not the reviewer's to make on its own initiative.
- Bash(git push *): pushing shares a change with everyone else working from this repository, and that step is irreversible enough that only the author should trigger it.
- Bash(docker *): building or starting the service lets a review's verdict be quietly shaped by one specific local run instead of the diff and the published specs; the reviewer works from those, not from a container it started itself.
- WebFetch: this is a small, self-contained course lab with no external service the review needs to consult, so giving the reviewer a channel to fetch and read arbitrary remote content only adds a route for injected instructions to reach a report the author will trust.
