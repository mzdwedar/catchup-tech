"""The cross-run ledger of URLs already published.

Without it, two runs over overlapping windows repeat themselves — and overlapping
windows are the normal case, since `/scrape` defaults to "since the last run" but the
window is often widened by hand.

Written only after a successful publish. A dry run or an aborted run leaves it
untouched, so a failed attempt never burns an item.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from catchup.sources.models import Item
from catchup.sources.urls import normalize_url

logger = logging.getLogger(__name__)

DEFAULT_LEDGER = Path("data/seen.json")


@dataclass(frozen=True, slots=True)
class SeenLedger:
    """Normalized URL → the run id that published it."""

    entries: dict[str, str]

    @classmethod
    def empty(cls) -> SeenLedger:
        return cls(entries={})

    @classmethod
    def load(cls, path: Path = DEFAULT_LEDGER) -> SeenLedger:
        """Read the ledger, treating a missing or corrupt file as empty.

        A corrupt ledger must not block a run: the cost of losing it is a few repeated
        items, which is strictly better than refusing to produce a digest at all.
        """
        if not path.exists():
            return cls.empty()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("ledger unreadable (%s), starting empty", type(exc).__name__)
            return cls.empty()
        if not isinstance(raw, dict):
            logger.warning("ledger is not an object, starting empty")
            return cls.empty()
        return cls(entries={str(k): str(v) for k, v in raw.items()})

    def __contains__(self, url: str) -> bool:
        return normalize_url(url) in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def unseen(self, items: Iterable[Item]) -> tuple[Item, ...]:
        """Drop items whose URL has already been published."""
        return tuple(i for i in items if i.url not in self)

    def record(self, items: Iterable[Item], run_id: str) -> SeenLedger:
        """Return a new ledger including `items`. Pure — the caller decides to save."""
        merged = dict(self.entries)
        for item in items:
            merged.setdefault(normalize_url(item.url), run_id)
        return SeenLedger(entries=merged)

    def save(self, path: Path = DEFAULT_LEDGER) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        logger.info("ledger saved", extra={"entries": len(self.entries)})


def run_id_for(period_end: date) -> str:
    return period_end.isoformat()
