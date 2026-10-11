"""ADR 0010's four rules, with no database. The loop that wrote one folder into a consultant's
own Telegram 70,565 times would have stopped at its fourth identical write."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.outside import Guard, Refused

T0 = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)


def guard(*, switched_on: bool = True, hourly_ceiling: int = 10) -> Guard:
    return Guard("telegram", switched_on=switched_on, hourly_ceiling=hourly_ceiling, repeat_limit=3)


def test_nothing_is_written_while_the_switch_is_off():
    with pytest.raises(Refused, match="switched off"):
        guard(switched_on=False).admit("folder:1", "a", now=T0)


def test_the_same_write_repeated_opens_the_breaker():
    g = guard()
    for _ in range(3):
        g.admit("folder:1", "same members", now=T0)
    with pytest.raises(Refused, match="not sticking"):
        g.admit("folder:1", "same members", now=T0)
    assert g.breaker_reason


def test_a_changed_write_is_not_a_repeat():
    g = guard()
    for i in range(6):
        g.admit("folder:1", f"members {i}", now=T0)
    assert g.breaker_reason is None


def test_more_writes_than_the_ceiling_in_an_hour_opens_the_breaker():
    g = guard(hourly_ceiling=5)
    for i in range(5):
        g.admit(f"folder:{i}", "x", now=T0)
    with pytest.raises(Refused, match="more than 5"):
        g.admit("folder:9", "x", now=T0)


def test_an_open_breaker_refuses_everything_even_next_hour():
    g = guard(hourly_ceiling=1)
    g.admit("a", "x", now=T0)
    with pytest.raises(Refused):
        g.admit("b", "x", now=T0)
    with pytest.raises(Refused, match="breaker open"):
        g.admit("c", "y", now=T0 + timedelta(hours=5))


def test_a_new_hour_starts_a_new_count():
    g = guard(hourly_ceiling=2)
    g.admit("a", "x", now=T0)
    g.admit("b", "x", now=T0)
    g.admit("c", "x", now=T0 + timedelta(hours=1))
    assert g.writes_in_window == 1
