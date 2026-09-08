"""Hacker News via the Algolia search API.

HN is the corroboration source: a story that surfaces here as well as in a feed is more
likely to matter than one that only a vendor blog carried. It also catches announcements
from companies that publish no feed at all.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from catchup.sources.dates import from_epoch
from catchup.sources.http import client
from catchup.sources.models import DateRange, Item, Origin

logger = logging.getLogger(__name__)

ENDPOINT = "https://hn.algolia.com/api/v1/search_by_date"
DEFAULT_QUERIES = ("AI", "LLM", "machine learning")
MIN_POINTS = 20
HITS_PER_QUERY = 100


def _params(query: str, window: DateRange) -> dict[str, str]:
    """Build the Algolia query.

    `numericFilters` uses a literal `>` which **must** be URL-encoded — sending it raw
    gets a 400 from Google's frontend before Algolia ever sees it. Passing the filters
    as params (rather than in a hand-built URL) is what guarantees the encoding.
    """
    start = int(datetime.combine(window.start, datetime.min.time(), UTC).timestamp())
    end = int(datetime.combine(window.end, datetime.min.time(), UTC).timestamp())
    filters = f"created_at_i>={start},created_at_i<{end},points>={MIN_POINTS}"
    return {
        "query": query,
        "tags": "story",
        "numericFilters": filters,
        "hitsPerPage": str(HITS_PER_QUERY),
    }


def parse_hits(payload: dict[str, object], window: DateRange) -> tuple[Item, ...]:
    """Turn an Algolia response into windowed items.

    Stories with no `url` are Ask-HN style self-posts; they are linked back to the HN
    thread rather than dropped, since the discussion is the artifact in that case.
    """
    hits = payload.get("hits")
    if not isinstance(hits, list):
        logger.warning("unexpected HN payload shape; skipping")
        return ()
    items: list[Item] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        title = " ".join(str(hit.get("title") or "").split()).strip()
        object_id = str(hit.get("objectID") or "")
        thread = f"https://news.ycombinator.com/item?id={object_id}"
        url = str(hit.get("url") or "") or thread
        published = from_epoch(hit.get("created_at_i"))
        if not title or published is None or not window.contains(published):
            continue
        points = int(hit.get("points") or 0)
        items.append(
            Item(
                title=title,
                url=url,
                source="Hacker News",
                published_date=published,
                summary="",
                origin=Origin.HN,
                extra={
                    "points": str(points),
                    "comments": str(hit.get("num_comments") or 0),
                    "discussion": thread,
                },
            )
        )
    return tuple(items)


def fetch_hn(
    window: DateRange,
    queries: tuple[str, ...] = DEFAULT_QUERIES,
    http: httpx.Client | None = None,
) -> tuple[Item, ...]:
    """Search HN for each query across the window. Raises on a failed request."""
    owned = http is None
    http = http or client()
    try:
        collected: list[Item] = []
        for query in queries:
            response = http.get(ENDPOINT, params=_params(query, window))
            response.raise_for_status()
            collected.extend(parse_hits(response.json(), window))
    finally:
        if owned:
            http.close()
    logger.info("hn fetched", extra={"items": len(collected)})
    return tuple(collected)
