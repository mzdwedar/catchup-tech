"""The shared vocabulary, and the invariants it refuses to be constructed without."""

from __future__ import annotations

from datetime import date

import pytest

from catchup.sources.models import DateRange, Item, Origin


def test_a_window_must_move_forward() -> None:
    """An inverted window would silently match nothing and look like a quiet week."""
    with pytest.raises(ValueError, match="empty window"):
        DateRange(start=date(2026, 9, 8), end=date(2026, 9, 1))


def test_a_zero_length_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty window"):
        DateRange(start=date(2026, 9, 8), end=date(2026, 9, 8))


def test_windows_render_as_explicit_dates() -> None:
    """Never "the past two weeks" — the model has no reliable sense of today."""
    window = DateRange(date(2026, 9, 1), date(2026, 9, 8))

    assert str(window) == "2026-09-01 → 2026-09-08"


def test_items_are_immutable() -> None:
    """Frozen because gates return new tuples rather than mutating in place."""
    item = Item("A release", "https://example.com/a", "Example", date(2026, 9, 1))

    # setattr, not `item.title = ...`: the typechecker rejects the direct form, and
    # this test is about the *runtime* guarantee that gates can share tuples safely.
    with pytest.raises(AttributeError):
        setattr(item, "title", "Changed")  # noqa: B010


def test_origin_serializes_as_its_own_name() -> None:
    """`--format json` writes this value; a repr change would break the contract."""
    assert Origin.SEARCH.value == "search"
    assert f"{Origin.FEED}" == "feed"
