"""The generic RSS/Atom fetcher, driven entirely by `02-sources.md`.

One fetcher covers every feed in the config, which is what makes "add a source" a
markdown edit rather than a code change.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date

import feedparser
import httpx

from catchup.sources.config import FeedSource
from catchup.sources.dates import from_struct_time
from catchup.sources.http import client, describe_error, fetch_bytes, in_parallel
from catchup.sources.models import DateRange, Item, Origin, SourceFailure

logger = logging.getLogger(__name__)

_TAG = re.compile(r"<[^>]+>")


def strip_html(raw: str) -> str:
    """Flatten a feed's HTML summary to plain text.

    Feeds put markup in summaries, and it reaches the artifact as text. Tags are
    removed before entities are unescaped, so an escaped `&lt;script&gt;` in the source
    text cannot become a real tag on the way through.
    """
    return " ".join(html.unescape(_TAG.sub(" ", raw)).split()).strip()


def _entry_date(entry: feedparser.FeedParserDict) -> date | None:
    """Prefer the publication date; fall back to the update date.

    Some feeds (Atom in particular) carry only `updated`. Using it is a small
    imprecision; dropping the entry outright would be a large one.
    """
    return from_struct_time(
        entry.get("published_parsed") or entry.get("updated_parsed")
    )


def _summary(entry: feedparser.FeedParserDict) -> str:
    """The entry's own summary, tags stripped and truncated.

    Deliberately *not* rewritten here: this is the raw material `/scrape` summarizes
    from, and paraphrasing it twice compounds the drift from what the source said.
    """
    raw = entry.get("summary") or entry.get("description") or ""
    return strip_html(raw)[:600]


def parse_feed(raw: bytes, source: FeedSource, window: DateRange) -> tuple[Item, ...]:
    """Parse feed bytes into windowed items.

    Entries whose date cannot be parsed are dropped, never dated to today — see
    `dates.py` for why that rule is load-bearing.
    """
    parsed = feedparser.parse(raw)
    items: list[Item] = []
    undated = 0
    for entry in parsed.entries:
        link = (entry.get("link") or "").strip()
        title = " ".join((entry.get("title") or "").split()).strip()
        if not link or not title:
            continue
        published = _entry_date(entry)
        if published is None:
            undated += 1
            continue
        if not window.contains(published):
            continue
        items.append(
            Item(
                title=title,
                url=link,
                source=source.name,
                published_date=published,
                summary=_summary(entry),
                origin=Origin.FEED,
                extra={"tier": source.tier},
            )
        )
    if undated:
        logger.info(
            "dropped undated entries",
            extra={"source": source.name, "n": undated},
        )
    return tuple(items)


def fetch_feeds(
    sources: tuple[FeedSource, ...],
    window: DateRange,
    http: httpx.Client | None = None,
) -> tuple[tuple[Item, ...], tuple[SourceFailure, ...]]:
    """Fetch every configured feed concurrently.

    Returns what succeeded and what did not. A failing feed is reported, never raised:
    losing one source should cost that source's items, not the run.
    """
    if not sources:
        return (), ()
    owned = http is None
    http = http or client()
    try:

        def one(source: FeedSource) -> tuple[tuple[Item, ...], SourceFailure | None]:
            try:
                return parse_feed(fetch_bytes(source.url, http), source, window), None
            except (httpx.HTTPError, ValueError) as exc:
                reason = describe_error(exc)
                logger.warning(
                    "source skipped",
                    extra={"source": source.name, "reason": reason},
                )
                return (), SourceFailure(source=source.name, reason=reason)

        results = in_parallel(sources, one)
    finally:
        if owned:
            http.close()

    items = tuple(i for got, _ in results for i in got)
    failures = tuple(f for _, f in results if f is not None)
    logger.info("feeds fetched", extra={"items": len(items), "failed": len(failures)})
    return items, failures
