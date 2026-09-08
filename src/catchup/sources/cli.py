"""The shared command-line surface every source tool exposes.

The contract is borrowed from ai-job-search's portal tools, so `/scrape` can discover a
new source by path and call it without being taught anything about it:

    <tool> search [--days N | --since DATE] [--query Q] [--format json|table|plain]

`--format json` is the machine contract: a JSON array of items with ISO dates. The other
two formats exist so a human can run the tool and see what a source is actually
returning, which is how most source bugs get found.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta

from catchup.sources.models import DateRange, Item

Fetcher = Callable[[DateRange, argparse.Namespace], Sequence[Item]]

DEFAULT_DAYS = 14


def today_utc() -> date:
    """The current UTC date.

    UTC rather than local time so a window means the same thing regardless of where the
    machine is, which matters because every source publishes in UTC.
    """
    return datetime.now(tz=UTC).date()


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="list items published in a window")
    window = search.add_mutually_exclusive_group()
    window.add_argument(
        "--days", type=int, help=f"lookback in days (default {DEFAULT_DAYS})"
    )
    window.add_argument(
        "--since", type=date.fromisoformat, help="window start, YYYY-MM-DD"
    )
    search.add_argument(
        "--until", type=date.fromisoformat, help="window end, exclusive"
    )
    search.add_argument("--query", action="append", help="repeatable, source-specific")
    search.add_argument(
        "--format", choices=("json", "table", "plain"), default="json", dest="fmt"
    )
    search.add_argument("--verbose", action="store_true", help="log to stderr")
    return parser


def resolve_window(args: argparse.Namespace) -> DateRange:
    """Turn the CLI's window flags into an explicit half-open range.

    Bounds are always concrete dates by the time anything downstream sees them, so no
    part of the system has to interpret a phrase like "the past two weeks".
    """
    end = args.until or today_utc()
    if args.since:
        return DateRange(start=args.since, end=end)
    return DateRange(start=end - timedelta(days=args.days or DEFAULT_DAYS), end=end)


def _as_dict(item: Item) -> dict[str, object]:
    data = dataclasses.asdict(item)
    data["published_date"] = item.published_date.isoformat()
    data["origin"] = item.origin.value
    return data


def render(items: Sequence[Item], fmt: str, window: DateRange) -> str:
    if fmt == "json":
        return json.dumps([_as_dict(i) for i in items], indent=2, ensure_ascii=False)
    if fmt == "plain":
        return "\n".join(f"{i.published_date}  {i.title}\n  {i.url}" for i in items)

    header = f"{len(items)} item(s)  {window}"
    rows = [f"{i.published_date}  {i.source[:18]:<18}  {i.title[:70]}" for i in items]
    return "\n".join([header, "-" * len(header), *rows])


def run(description: str, fetch: Fetcher, argv: Sequence[str] | None = None) -> int:
    """Parse arguments, fetch, print. Returns the process exit code.

    A source that fails prints the reason to stderr and exits 1; `/scrape` treats that
    as a skipped source rather than a failed run.
    """
    args = build_parser(description).parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    window = resolve_window(args)
    try:
        items = fetch(window, args)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    ordered = sorted(items, key=lambda i: (i.published_date, i.title), reverse=True)
    print(render(ordered, args.fmt, window))
    return 0
