"""`catchup-feeds` — every RSS/Atom feed listed in `02-sources.md`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from catchup.sources.cli import run
from catchup.sources.config import load_sources
from catchup.sources.feeds import fetch_feeds
from catchup.sources.models import DateRange, Item


def _fetch(window: DateRange, args: argparse.Namespace) -> Sequence[Item]:
    sources = load_sources()
    if not sources:
        raise RuntimeError("no feeds configured in 02-sources.md — run /setup first")
    items, failures = fetch_feeds(sources, window)
    for failure in failures:
        print(f"skipped {failure.source}: {failure.reason}", file=sys.stderr)
    return items


def main(argv: Sequence[str] | None = None) -> int:
    return run("Search configured RSS/Atom feeds", _fetch, argv)


if __name__ == "__main__":
    raise SystemExit(main())
