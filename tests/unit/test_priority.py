# ai-generated: 90% - Claude Code wrote this test module; reviewed and accepted as-is
"""Unit tests for the priority matrix and VIP floor (FR-004, FR-005; decision C3 = vip)."""

import pytest

from svcdesk.priority import compute_priority

MATRIX_CASES = [
    (1, 1, "P1"), (1, 2, "P2"), (1, 3, "P3"),
    (2, 1, "P2"), (2, 2, "P3"), (2, 3, "P4"),
    (3, 1, "P3"), (3, 2, "P4"), (3, 3, "P4"),
]


@pytest.mark.parametrize("impact,urgency,expected", MATRIX_CASES)
def test_matrix_non_vip(impact, urgency, expected):
    assert compute_priority(impact, urgency, vip=False) == expected


def test_vip_floor_raises_p4_to_p2():
    assert compute_priority(3, 3, vip=True) == "P2"


def test_vip_floor_raises_p3_to_p2():
    assert compute_priority(2, 3, vip=True) == "P2"


def test_vip_does_not_lower_existing_p1():
    assert compute_priority(1, 1, vip=True) == "P1"


def test_vip_does_not_change_existing_p2():
    assert compute_priority(2, 1, vip=True) == "P2"
