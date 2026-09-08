"""`catchup-hn` — Hacker News stories via the Algolia API."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from catchup.sources.cli import run
from catchup.sources.hn import DEFAULT_QUERIES, fetch_hn
from catchup.sources.models import DateRange, Item


def _fetch(window: DateRange, args: argparse.Namespace) -> Sequence[Item]:
    queries = tuple(args.query) if args.query else DEFAULT_QUERIES
    return fetch_hn(window, queries=queries)


def main(argv: Sequence[str] | None = None) -> int:
    return run("Search Hacker News for stories in a window", _fetch, argv)


if __name__ == "__main__":
    raise SystemExit(main())
