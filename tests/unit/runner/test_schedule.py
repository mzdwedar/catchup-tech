"""Tests for the biweekly schedule gate.

GitHub Actions cron cannot express "every two weeks" — it offers day-of-week,
day-of-month, and month, none of which produce a stable 14-day cadence across month
boundaries. The workflow therefore runs weekly and `is_run_day` decides.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from catchup.runner.schedule import is_run_day

ANCHOR = date(2026, 9, 1)


def test_anchor_date_is_a_run_day() -> None:
    assert is_run_day(ANCHOR, ANCHOR)


@pytest.mark.parametrize("offset", [14, 28, 42, 364])
def test_multiples_of_fourteen_days_after_anchor_are_run_days(offset: int) -> None:
    assert is_run_day(ANCHOR + timedelta(days=offset), ANCHOR)


@pytest.mark.parametrize("offset", [1, 7, 13, 15, 27, 29])
def test_other_offsets_are_not_run_days(offset: int) -> None:
    assert not is_run_day(ANCHOR + timedelta(days=offset), ANCHOR)


@pytest.mark.parametrize("offset", [-1, -7, -13, -14, -28])
def test_dates_before_the_anchor_are_never_run_days(offset: int) -> None:
    """The schedule must not fire before it was enabled.

    A naive `(today - anchor).days % 14 == 0` returns True at -14 and -28, because
    Python's modulo is non-negative for negative operands. That would let a backfill
    run with `--period-end` before the anchor publish a digest.
    """
    assert not is_run_day(ANCHOR + timedelta(days=offset), ANCHOR)


def test_cadence_holds_across_a_month_boundary() -> None:
    anchor = date(2026, 12, 25)
    assert is_run_day(date(2027, 1, 8), anchor)
    assert not is_run_day(date(2027, 1, 1), anchor)


def test_cadence_holds_across_a_leap_day() -> None:
    """2028 is a leap year: 20 Feb + 14 days lands on 5 March, not 6 March."""
    anchor = date(2028, 2, 20)
    assert is_run_day(date(2028, 3, 5), anchor)
    assert not is_run_day(date(2028, 3, 6), anchor)


def test_run_days_in_a_year_window() -> None:
    """A 365-day window starting on the anchor contains 27 run days.

    365 / 14 = 26.07, so a year holds 26 or 27 run days depending on alignment --
    starting exactly on the anchor gives offsets 0, 14, ... 364, which is 27.
    """
    run_days = [
        day for day in range(365) if is_run_day(ANCHOR + timedelta(days=day), ANCHOR)
    ]
    assert len(run_days) == 27
    assert run_days[0] == 0
    assert run_days[-1] == 364
