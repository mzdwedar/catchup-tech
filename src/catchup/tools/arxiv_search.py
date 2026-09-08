"""`catchup-arxiv` — arXiv submissions and Hugging Face daily papers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from catchup.sources.arxiv import ALL_KINDS, DEFAULT_CATEGORIES, fetch_arxiv
from catchup.sources.cli import run
from catchup.sources.config import load_sources, research_kinds, split_sources
from catchup.sources.models import DateRange, Item


def _fetch(window: DateRange, args: argparse.Namespace) -> Sequence[Item]:
    categories = tuple(args.query) if args.query else DEFAULT_CATEGORIES
    # Which research services are configured. Falls back to both when no config exists
    # yet, so the tool is still useful before /setup has run.
    _feeds, research = split_sources(load_sources())
    kinds = research_kinds(research) or ALL_KINDS
    return fetch_arxiv(window, categories=categories, kinds=kinds)


def main(argv: Sequence[str] | None = None) -> int:
    return run("Search arXiv and Hugging Face daily papers", _fetch, argv)


if __name__ == "__main__":
    raise SystemExit(main())
