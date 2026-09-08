"""The shared vocabulary every source and every gate speaks.

`Item` is the contract: sources produce it, gates filter it, the artifact renders it.
Changing it is Ask-first in `SPEC.md` precisely because everything downstream assumes
its shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Origin(StrEnum):
    """Where an item came from.

    Kept on the item so a run record can answer whether the WebSearch pass earned its
    place — one of `SPEC.md`'s open questions, and unanswerable without this field.
    """

    FEED = "feed"
    HN = "hn"
    ARXIV = "arxiv"
    SEARCH = "search"


@dataclass(frozen=True, slots=True)
class DateRange:
    """A half-open window, `[start, end)`.

    Half-open because two consecutive windows must not both claim the boundary day.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError(f"empty window: {self.start} >= {self.end}")

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    def __str__(self) -> str:
        return f"{self.start.isoformat()} → {self.end.isoformat()}"


@dataclass(frozen=True, slots=True)
class Item:
    """One piece of news, normalized across every source."""

    title: str
    url: str
    source: str
    published_date: date
    summary: str = ""
    origin: Origin = Origin.FEED
    extra: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceFailure:
    """A source that could not be read.

    Recorded rather than raised: losing one feed should cost that feed's items, not the
    run. Surfacing it in the run record is what stops a permanently dead feed from
    silently shrinking coverage.
    """

    source: str
    reason: str
