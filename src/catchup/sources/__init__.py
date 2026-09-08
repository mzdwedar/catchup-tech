"""Fetching and normalizing news items from feeds and APIs.

Every fetcher in this package returns `Item`s in the same shape, so `collect` can gate
them without knowing where they came from.
"""

from __future__ import annotations

from catchup.sources.config import FeedSource, load_sources, parse_sources
from catchup.sources.models import DateRange, Item, Origin, SourceFailure

__all__ = [
    "DateRange",
    "FeedSource",
    "Item",
    "Origin",
    "SourceFailure",
    "load_sources",
    "parse_sources",
]
