"""`catchup-arxiv` — arXiv submissions and Hugging Face daily papers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from catchup.sources.arxiv import DEFAULT_CATEGORIES, fetch_arxiv
from catchup.sources.cli import run
from catchup.sources.models import DateRange, Item


def _fetch(window: DateRange, args: argparse.Namespace) -> Sequence[Item]:
    categories = tuple(args.query) if args.query else DEFAULT_CATEGORIES
    return fetch_arxiv(window, categories=categories)


def main(argv: Sequence[str] | None = None) -> int:
    return run("Search arXiv and Hugging Face daily papers", _fetch, argv)


if __name__ == "__main__":
    raise SystemExit(main())
