# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""Priority matrix and VIP floor (FR-004, FR-005; decision C3 = vip, DECISIONS.md)."""

MATRIX: dict[tuple[int, int], str] = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    base = MATRIX[(impact, urgency)]
    if vip and base in ("P3", "P4"):
        return "P2"
    return base
