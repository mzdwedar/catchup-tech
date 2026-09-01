"""The biweekly schedule gate.

GitHub Actions cron cannot express "every two weeks": it offers day-of-week,
day-of-month, and month, none of which produce a stable 14-day cadence across month
boundaries. The workflow runs weekly and this module decides whether today is a run
day, so an off week costs one cheap, silent job rather than a wrong send.

Pure and clock-free by design — the caller supplies the date, which is what makes the
cadence testable without freezing time.
"""

from __future__ import annotations

from datetime import date

CADENCE_DAYS = 14


def is_run_day(today: date, anchor: date) -> bool:
    """Whether `today` falls on the biweekly cadence starting at `anchor`.

    True on the anchor date and every 14th day after it. Dates before the anchor are
    never run days: the schedule must not fire before it was enabled. That guard is
    load-bearing — `(today - anchor).days % CADENCE_DAYS == 0` alone would accept
    -14 and -28, because Python's modulo is non-negative for negative operands.
    """
    elapsed = (today - anchor).days
    return elapsed >= 0 and elapsed % CADENCE_DAYS == 0
