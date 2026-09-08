"""Date parsing, and the rule that an unparseable date drops its item.

That rule is the reason this module exists as more than a one-liner: defaulting a
missing date to today would inject stale items into every digest and make the window
gate decorative.
"""

from __future__ import annotations

import time
from datetime import date
from typing import cast

import pytest

from catchup.sources.dates import from_epoch, from_iso, from_struct_time


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-09-08", date(2026, 9, 8)),
        ("2026-09-08T14:02:11Z", date(2026, 9, 8)),
        ("2026-09-08T14:02:11z", date(2026, 9, 8)),
        ("2026-09-08T14:02:11+00:00", date(2026, 9, 8)),
        ("  2026-09-08T00:00:00Z  ", date(2026, 9, 8)),
        ("2026-09-08T23:30:00-05:00", date(2026, 9, 9)),
    ],
)
def test_from_iso_parses_known_shapes(raw: str, expected: date) -> None:
    assert from_iso(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "   ", None, "not a date", "last Tuesday", "2026-13-45"]
)
def test_from_iso_returns_none_rather_than_guessing(raw: str | None) -> None:
    """The load-bearing case: unparseable means None, never today."""
    assert from_iso(raw) is None


def test_from_iso_normalizes_to_utc() -> None:
    """A late-evening US timestamp is already the next UTC day."""
    assert from_iso("2026-09-08T20:00:00-08:00") == date(2026, 9, 9)


def test_from_struct_time_treats_input_as_utc() -> None:
    """feedparser yields UTC struct_times, so local time must not be applied.

    Midday is chosen deliberately: a bug applying the local timezone would shift a
    midnight value across the date boundary in most of the world but not all of it.
    """
    parsed = time.struct_time((2026, 9, 8, 12, 0, 0, 0, 251, 0))
    assert from_struct_time(parsed) == date(2026, 9, 8)


def test_from_struct_time_handles_missing() -> None:
    assert from_struct_time(None) is None


def test_from_epoch_converts_utc_timestamps() -> None:
    assert from_epoch(1_757_289_600) == date(2025, 9, 8)


@pytest.mark.parametrize("raw", [None, "not a number", float("nan")])
def test_from_epoch_returns_none_on_garbage(raw: object) -> None:
    """Sources send what they like; a string where a number belongs is not a crash."""
    assert from_epoch(cast("float | None", raw)) is None
