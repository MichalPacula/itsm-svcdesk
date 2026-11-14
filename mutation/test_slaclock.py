# ai-generated: 80% - Claude Code wrote boundary tests from the slaclock docstrings; I review them against mutants
from datetime import datetime, timedelta

import pytest

import slaclock as s

MON = datetime(2026, 11, 16)  # a Monday


def at(day_offset, h, m=0):
    return MON + timedelta(days=day_offset, hours=h, minutes=m)


def test_priority_matrix():
    exp = {(1, 1): "P1", (1, 2): "P2", (2, 1): "P2", (1, 3): "P3", (2, 2): "P3", (3, 1): "P3",
           (2, 3): "P4", (3, 2): "P4", (3, 3): "P4"}
    for (i, u), p in exp.items():
        assert s.priority_of(i, u) == p
    assert s.priority_of(2, 2, vip=False) == "P3"


def test_priority_vip():
    assert s.priority_of(1, 1, True) == "P1"
    assert s.priority_of(1, 2, True) == "P2"
    assert s.priority_of(2, 1, True) == "P2"
    for i, u in [(1, 3), (2, 2), (3, 1), (2, 3), (3, 2), (3, 3)]:
        assert s.priority_of(i, u, True) == "P2"


@pytest.mark.parametrize("i,u", [(0, 1), (1, 0), (4, 1), (1, 4), (2.0, 1), (1, 2.0), (True, 1), (1, True), ("1", 1), (1, "1"), (-1, 1)])
def test_priority_invalid(i, u):
    with pytest.raises(ValueError):
        s.priority_of(i, u)


def test_targets():
    assert s.targets("P1") == (15, 240)
    assert s.targets("P2") == (60, 480)
    assert s.targets("P3") == (240, 1440)
    assert s.targets("P4") == (480, 4320)
    for bad in ("p1", " P1", "P5", "", "P0"):
        with pytest.raises(ValueError):
            s.targets(bad)


def test_sla_state_boundaries():
    assert s.sla_state(0, 15) == "ok"
    assert s.sla_state(11, 15) == "ok"
    assert s.sla_state(12, 15) == "warning"
    assert s.sla_state(15, 15) == "warning"
    assert s.sla_state(16, 15) == "breached"
    assert s.sla_state(74, 100) == "ok"
    assert s.sla_state(75, 100) == "warning"
    assert s.sla_state(100, 100) == "warning"
    assert s.sla_state(101, 100) == "breached"
    assert s.sla_state(0, 1) == "ok"
    assert s.sla_state(1, 1) == "warning"
    assert s.sla_state(2, 1) == "breached"
    assert s.sla_state(2999, 4000) == "ok"
    assert s.sla_state(3000, 4000) == "warning"


def test_sla_state_invalid():
    with pytest.raises(ValueError):
        s.sla_state(-1, 10)
    with pytest.raises(ValueError):
        s.sla_state(1, 0)
    with pytest.raises(ValueError):
        s.sla_state(1, -5)
    with pytest.raises(ValueError):
        s.sla_state(0, 0)


def test_business_time():
    assert s.is_business_time(at(0, 8))
    assert not s.is_business_time(at(0, 7, 59))
    assert s.is_business_time(at(0, 15, 59))
    assert not s.is_business_time(at(0, 16))
    assert s.is_business_time(at(0, 12))
    assert not s.is_business_time(at(0, 0))
    assert not s.is_business_time(at(0, 23, 59))
    for d in range(5):
        assert s.is_business_time(at(d, 9, 30))
    assert not s.is_business_time(at(5, 10))
    assert not s.is_business_time(at(6, 10))
    assert s.is_business_time(at(4, 15, 59))
    assert s.is_business_time(at(0, 8, 1))
    assert s.is_business_time(at(0, 9, 0))


def test_add_basic():
    assert s.add_business_minutes(at(0, 9), 30) == at(0, 9, 30)
    assert s.add_business_minutes(at(0, 9), 0) == at(0, 9)
    assert s.add_business_minutes(at(0, 8), 480) == at(0, 16)
    assert s.add_business_minutes(at(0, 8), 481) == at(1, 8, 1)
    assert s.add_business_minutes(at(0, 15), 60) == at(0, 16)
    assert s.add_business_minutes(at(0, 15), 61) == at(1, 8, 1)
    assert s.add_business_minutes(at(0, 15, 30), 45) == at(1, 8, 15)


def test_add_outside_hours():
    assert s.add_business_minutes(at(0, 6), 10) == at(0, 8, 10)
    assert s.add_business_minutes(at(0, 6), 0) == at(0, 8)
    assert s.add_business_minutes(at(0, 17), 10) == at(1, 8, 10)
    assert s.add_business_minutes(at(0, 17), 0) == at(1, 8)
    assert s.add_business_minutes(at(0, 16), 0) == at(1, 8)
    assert s.add_business_minutes(at(0, 7, 59), 1) == at(0, 8, 1)
    assert s.add_business_minutes(at(4, 15), 120) == at(7, 9)  # Fri 15:00 + 2h = Mon 09:00
    assert s.add_business_minutes(at(4, 17), 10) == at(7, 8, 10)
    assert s.add_business_minutes(at(5, 10), 10) == at(7, 8, 10)  # Saturday
    assert s.add_business_minutes(at(6, 10), 0) == at(7, 8)  # Sunday
    assert s.add_business_minutes(at(4, 16), 480) == at(7, 16)


def test_add_multi_day():
    assert s.add_business_minutes(at(0, 8), 960) == at(1, 16)
    assert s.add_business_minutes(at(0, 8), 961) == at(2, 8, 1)
    assert s.add_business_minutes(at(0, 8), 2400) == at(4, 16)
    assert s.add_business_minutes(at(0, 8), 2401) == at(7, 8, 1)
    assert s.add_business_minutes(at(0, 8, 0), 240) == at(0, 12)


def test_add_seconds_ignored():
    start = at(0, 9) + timedelta(seconds=45, microseconds=5)
    assert s.add_business_minutes(start, 10) == at(0, 9, 10)


def test_add_errors_and_limit():
    with pytest.raises(ValueError):
        s.add_business_minutes(at(0, 9), -1)
    # 366 days is allowed, 367 is not (start's date + MAX_DAYS)
    with pytest.raises(ValueError):
        s.add_business_minutes(MON, 8 * 60 * 400)
    # due on day 366 exactly: MON + 366 days is a Wednesday
    d = MON + timedelta(days=366)
    assert d.weekday() < 5
    assert s.add_business_minutes(MON, 0) == at(0, 8)
    # start at Mon 00:00; consume windows so due falls on day offset 366 (a Tuesday): 366 days = 52 weeks + 2 days
    minutes = 263 * 480  # 263 workdays in offsets 0..366: due Wed 16:00 on offset 366
    assert s.add_business_minutes(MON, minutes) == d.replace(hour=16)
    with pytest.raises(ValueError):
        s.add_business_minutes(MON, minutes + 1)


def test_between_basic():
    assert s.business_minutes_between(at(0, 9), at(0, 9)) == 0
    assert s.business_minutes_between(at(0, 9), at(0, 10)) == 60
    assert s.business_minutes_between(at(0, 8), at(0, 16)) == 480
    assert s.business_minutes_between(at(0, 8), at(0, 23)) == 480
    assert s.business_minutes_between(at(0, 0), at(0, 8)) == 0
    assert s.business_minutes_between(at(0, 7), at(0, 8, 1)) == 1
    assert s.business_minutes_between(at(0, 15, 59), at(0, 16, 1)) == 1
    assert s.business_minutes_between(at(0, 16), at(0, 20)) == 0
    assert s.business_minutes_between(at(0, 15), at(1, 9)) == 120
    assert s.business_minutes_between(at(0, 9), at(1, 9)) == 480
    assert s.business_minutes_between(at(4, 15), at(7, 9)) == 120
    assert s.business_minutes_between(at(5, 9), at(6, 12)) == 0
    assert s.business_minutes_between(at(0, 8), at(7, 8)) == 2400
    assert s.business_minutes_between(at(0, 0), at(1, 0)) == 480
    assert s.business_minutes_between(at(4, 12), at(5, 12)) == 240


def test_between_seconds_ignored():
    a = at(0, 9) + timedelta(seconds=59)
    b = at(0, 9, 10) + timedelta(seconds=1)
    assert s.business_minutes_between(a, b) == 10


def test_between_errors():
    with pytest.raises(ValueError):
        s.business_minutes_between(at(0, 10), at(0, 9))
    with pytest.raises(ValueError):
        s.business_minutes_between(MON, MON + timedelta(days=367))
    assert s.business_minutes_between(MON, MON + timedelta(days=366)) == 262 * 480
    with pytest.raises(ValueError):
        s.business_minutes_between(at(0, 23), at(0, 22))


def test_roundtrip():
    for start in (at(0, 9), at(0, 6), at(0, 17), at(4, 15, 30), at(5, 12), at(2, 8), at(3, 15, 59)):
        for m in (0, 1, 59, 480, 481, 1000, 5000):
            assert s.business_minutes_between(start, s.add_business_minutes(start, m)) == m


def test_escalation_matrix():
    for p, base in (("P1", 1), ("P2", 1), ("P3", 0), ("P4", 0)):
        assert s.escalation_tier(p, False, 0) == base
        assert s.escalation_tier(p, False, 1) == base
    assert s.escalation_tier("P1", True, 0) == 3
    assert s.escalation_tier("P2", True, 0) == 2
    assert s.escalation_tier("P3", True, 0) == 1
    assert s.escalation_tier("P4", True, 0) == 1
    assert s.escalation_tier("P1", False, 2) == 2
    assert s.escalation_tier("P2", False, 2) == 2
    assert s.escalation_tier("P3", False, 2) == 1
    assert s.escalation_tier("P4", False, 5) == 1
    assert s.escalation_tier("P1", True, 2) == 3
    assert s.escalation_tier("P1", True, 9) == 3
    assert s.escalation_tier("P2", True, 2) == 3
    assert s.escalation_tier("P3", True, 2) == 2
    assert s.escalation_tier("P4", True, 1) == 1


def test_escalation_errors():
    with pytest.raises(ValueError):
        s.escalation_tier("P5", False, 0)
    with pytest.raises(ValueError):
        s.escalation_tier("p1", False, 0)
    with pytest.raises(ValueError):
        s.escalation_tier("P1", False, -1)


def test_parse_ok():
    assert s.parse_duration("90m") == 90
    assert s.parse_duration("4h") == 240
    assert s.parse_duration("1h30m") == 90
    assert s.parse_duration("2d") == 2880
    assert s.parse_duration("1d4h") == 1680
    assert s.parse_duration("1d0h5m") == 1445
    assert s.parse_duration("1h59m") == 119
    assert s.parse_duration("60m") == 60
    assert s.parse_duration("0h60m") == 60
    assert s.parse_duration("  5m  ") == 5
    assert s.parse_duration("1m") == 1
    assert s.parse_duration("1d") == 1440
    assert s.parse_duration("1h") == 60
    assert s.parse_duration("1d1m") == 1441
    assert s.parse_duration("3d2h1m") == 3 * 1440 + 120 + 1
    assert s.parse_duration("0d1m") == 1
    assert s.parse_duration("120m") == 120
    assert s.parse_duration("10d") == 14400
    assert s.parse_duration("12h") == 720
    assert s.parse_duration("\t2h\n") == 120


@pytest.mark.parametrize("bad", ["", "0m", "0d", "0h", "0d0h0m", "1.5h", "30m1h", "-5m", "1 h", "1H", "1h60m", "1d60m",
                                 "1d99m", "h", "m", "1", "1x", "1h1h", "1m1m", "  ", "1d 2h", "2h30", "1h-5m", "1dh"])
def test_parse_bad(bad):
    with pytest.raises(ValueError):
        s.parse_duration(bad)
