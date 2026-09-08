"""Hacker News fetching, including the encoding bug that costs an afternoon.

Algolia's `numericFilters` uses a literal `>`. Sent raw in a hand-built URL, Google's
frontend rejects the request with a 400 before Algolia sees it — verified against the
live API on 2026-09-08. Passing filters as params is what guarantees the encoding, and
the test below is what stops someone "simplifying" that back into an f-string.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import httpx

from catchup.sources.hn import _params, fetch_hn, parse_hits
from catchup.sources.models import DateRange, Origin

WINDOW = DateRange(start=date(2026, 9, 1), end=date(2026, 9, 8))


def test_numeric_filters_are_url_encoded() -> None:
    """The regression guard: `>` must not reach the wire unescaped."""
    endpoint = "https://hn.algolia.com/api/v1/search_by_date"
    request = httpx.Request("GET", endpoint, params=_params("AI", WINDOW))

    assert ">" not in str(request.url)
    assert "%3E" in str(request.url)


def test_filters_bound_both_ends_of_the_window() -> None:
    filters = _params("AI", WINDOW)["numericFilters"]

    assert "created_at_i>=" in filters
    assert "created_at_i<" in filters
    assert "points>=" in filters


def test_parses_recorded_hits(feed_bytes: Callable[[str], bytes]) -> None:
    import json

    payload = json.loads(feed_bytes("hn_algolia.json"))
    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))

    items = parse_hits(payload, wide)

    assert items, "recorded HN fixture yielded nothing"
    assert all(i.origin is Origin.HN for i in items)
    assert all(i.source == "Hacker News" for i in items)
    thread = "https://news.ycombinator.com/"
    assert all(i.extra["discussion"].startswith(thread) for i in items)


def test_self_posts_link_to_the_discussion() -> None:
    """An Ask HN with no URL is still news; the thread is the artifact."""
    payload: dict[str, object] = {
        "hits": [
            {
                "title": "Ask HN: what changed",
                "objectID": "12345",
                "url": None,
                "created_at_i": 1_788_000_000,
                "points": 200,
            }
        ]
    }

    (item,) = parse_hits(payload, DateRange(date(2026, 8, 1), date(2026, 10, 1)))

    assert item.url == "https://news.ycombinator.com/item?id=12345"


def test_out_of_window_hits_are_dropped() -> None:
    hit = {"title": "Old", "objectID": "1", "created_at_i": 1_000_000_000}
    payload: dict[str, object] = {"hits": [hit]}

    assert parse_hits(payload, WINDOW) == ()


def test_a_malformed_payload_is_skipped_not_raised() -> None:
    """Server-side oddities must not crash a run that other sources can still fill."""
    wrong_shape: dict[str, object] = {"error": "rate limited"}
    wrong_hits: dict[str, object] = {"hits": ["not an object"]}

    assert parse_hits(wrong_shape, WINDOW) == ()
    assert parse_hits(wrong_hits, WINDOW) == ()


def test_each_query_is_searched(feed_bytes: Callable[[str], bytes]) -> None:
    import json

    payload = json.loads(feed_bytes("hn_algolia.json"))
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params)["query"])
        return httpx.Response(200, json=payload)

    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        fetch_hn(wide, queries=("AI", "LLM"), http=http)

    assert seen == ["AI", "LLM"]
