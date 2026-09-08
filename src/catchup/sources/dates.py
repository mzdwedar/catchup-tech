"""Publication-date parsing, and the decision to drop rather than guess.

Feeds report dates as RFC-822, ISO-8601, and several things that are neither, in
whatever timezone they please. `feedparser` handles most of that zoo; this module adds
the ISO formats the APIs use and normalizes everything to a UTC calendar date.

The load-bearing rule: an unparseable date returns `None` and the caller drops the item.
Defaulting to today would inject stale items into every digest and make the window gate
decorative.
"""

from __future__ import annotations

import calendar
import logging
from datetime import UTC, date, datetime
from time import struct_time

logger = logging.getLogger(__name__)


def from_struct_time(parsed: struct_time | None) -> date | None:
    """Convert feedparser's `*_parsed` struct_time to a UTC date.

    feedparser always returns these in UTC, so `timegm` — not `mktime`, which would
    apply the local timezone and shift dates by a day near midnight.
    """
    if parsed is None:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC).date()
    except (ValueError, OverflowError, TypeError) as exc:
        logger.warning("unparseable struct_time: %s", type(exc).__name__)
        return None


def from_iso(raw: str | None) -> date | None:
    """Parse an ISO-8601 date or datetime, with or without a `Z` suffix.

    Naive values are treated as UTC: the sources using this format (arXiv, HN, Hugging
    Face) all publish in UTC, and a one-day drift matters more than the pedantry.
    """
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            logger.warning("unparseable date, dropping item: %r", raw[:40])
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def from_epoch(seconds: int | float | None) -> date | None:
    """Convert a Unix timestamp (Hacker News' `created_at_i`) to a UTC date."""
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(float(seconds), tz=UTC).date()
    except (ValueError, OverflowError, OSError, TypeError):
        logger.warning("unparseable epoch, dropping item: %r", seconds)
        return None
