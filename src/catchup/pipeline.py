"""`catchup-collect` — fetch every source, run the gates, emit JSON.

This exists so `/scrape` never has to reimplement a gate. The command orchestrates and
judges; the filtering that decides what is even eligible is tested Python behind one
call, and a run that fails a gate fails here with a reason rather than in a model's
reasoning.

Two modes:

* default — fetch all sources, merge, gate.
* ``--no-fetch`` — gate only what arrives on stdin, so the WebSearch pass in `/scrape`
  goes through exactly the same window, dedupe, and liveness checks as everything else.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from catchup.collect import GateError, UrlChecker, default_checker, gate
from catchup.seen import DEFAULT_LEDGER, SeenLedger
from catchup.sources.arxiv import fetch_arxiv
from catchup.sources.cli import DEFAULT_DAYS, today_utc
from catchup.sources.config import load_sources
from catchup.sources.feeds import fetch_feeds
from catchup.sources.hn import fetch_hn
from catchup.sources.models import DateRange, Item, Origin, SourceFailure

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch all sources and run the gates")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--days", type=int, help=f"lookback (default {DEFAULT_DAYS})")
    window.add_argument("--since", type=date.fromisoformat, help="window start")
    parser.add_argument(
        "--until", type=date.fromisoformat, help="window end, exclusive"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="JSON array of extra items to merge; '-' reads stdin",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="gate only --input, skipping every source (used for the search pass)",
    )
    parser.add_argument(
        "--include-seen",
        action="store_true",
        help="do not drop items published by an earlier run",
    )
    parser.add_argument("--min-items", type=int, help="override the abort floor")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="truncate summaries — enough to rank by, a quarter of the bytes",
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--verbose", action="store_true")
    return parser


def _window(args: argparse.Namespace) -> DateRange:
    end = args.until or today_utc()
    if args.since:
        return DateRange(start=args.since, end=end)
    return DateRange(start=end - timedelta(days=args.days or DEFAULT_DAYS), end=end)


def item_from_json(raw: dict[str, object]) -> Item:
    """Rebuild an `Item` from a tool's JSON output.

    Deliberately strict about the date: a search result whose date could not be
    determined must not reach the gates with today's date standing in for the truth.
    """
    published = str(raw.get("published_date") or "")
    extra = raw.get("extra")
    carried = (
        {str(k): str(v) for k, v in extra.items()} if isinstance(extra, dict) else {}
    )
    return Item(
        title=str(raw["title"]),
        url=str(raw["url"]),
        source=str(raw.get("source") or "unknown"),
        published_date=date.fromisoformat(published),
        summary=str(raw.get("summary") or ""),
        origin=Origin(str(raw.get("origin") or "feed")),
        extra=carried,
    )


def read_items(path: Path) -> tuple[Item, ...]:
    """Load items from a JSON array file, or stdin when given `-`."""
    text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError("--input must be a JSON array of items")
    return tuple(item_from_json(entry) for entry in payload)


def fetch_all(window: DateRange) -> tuple[tuple[Item, ...], tuple[SourceFailure, ...]]:
    """Fetch every source, collecting failures rather than raising them.

    Each source is tried independently: one dead API must not cost the run the other
    two, which is the same policy `fetch_feeds` applies within the feed list.
    """
    items: list[Item] = []
    failures: list[SourceFailure] = []

    feed_items, feed_failures = fetch_feeds(load_sources(), window)
    items.extend(feed_items)
    failures.extend(feed_failures)

    for name, fetcher in (("Hacker News", fetch_hn), ("Research", fetch_arxiv)):
        try:
            items.extend(fetcher(window))
        except Exception as exc:
            logger.warning("source skipped", extra={"source": name})
            failures.append(SourceFailure(source=name, reason=type(exc).__name__))
    return tuple(items), tuple(failures)


def main(argv: Sequence[str] | None = None, check: UrlChecker | None = None) -> int:
    """Run the pipeline and print the result. Returns the process exit code.

    `check` is the liveness checker, injected for the same reason `collect.gate` takes
    one: without that seam the only way to test this boundary is to let it reach the
    real internet, which the suite forbids and which would make the tests flaky anyway.
    """
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    window = _window(args)

    items: tuple[Item, ...] = ()
    failures: tuple[SourceFailure, ...] = ()
    if not args.no_fetch:
        items, failures = fetch_all(window)
    if args.input:
        items = items + read_items(args.input)

    seen = None if args.include_seen else SeenLedger.load(args.ledger)
    http = None
    if check is None:
        check, http = default_checker()
    try:
        collection = gate(
            items,
            window,
            check,
            seen=seen,
            skipped_sources=failures,
            **({"min_items": args.min_items} if args.min_items else {}),
        )
    except GateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if http is not None:
            http.close()

    print(
        json.dumps(
            {
                "window": {
                    "start": window.start.isoformat(),
                    "end": window.end.isoformat(),
                },
                "collected": len(items),
                "items": [
                    item_to_json(i, compact=args.compact) for i in collection.items
                ],
                "skipped_sources": [
                    {"source": f.source, "reason": f.reason}
                    for f in collection.skipped_sources
                ],
                "gate_counts": {
                    name: {"before": c.before, "after": c.after}
                    for name, c in collection.gate_counts.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


COMPACT_SUMMARY_CHARS = 180


def item_to_json(item: Item, *, compact: bool = False) -> dict[str, object]:
    """Serialize an item, optionally trimmed for ranking.

    A fortnight of sources runs to roughly half a megabyte of JSON, most of it abstract
    text nobody reads before deciding what to keep. Compact output carries enough to
    rank by; the full summary is still in the run's raw output for the dozen items that
    survive.
    """
    summary = item.summary
    if compact and len(summary) > COMPACT_SUMMARY_CHARS:
        summary = summary[:COMPACT_SUMMARY_CHARS].rstrip() + "…"
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "published_date": item.published_date.isoformat(),
        "summary": summary,
        "origin": item.origin.value,
        "extra": {} if compact else dict(item.extra),
    }


if __name__ == "__main__":
    raise SystemExit(main())
