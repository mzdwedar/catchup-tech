"""Feed parsing, driven by recorded RSS and Atom responses.

Both formats are represented on purpose: they disagree about where the date lives
(`published` vs `updated`) and how summaries are escaped, and that disagreement is the
whole reason this parser is not three lines.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import httpx
import pytest

from catchup.sources.config import FeedSource
from catchup.sources.feeds import fetch_feeds, parse_feed, strip_html
from catchup.sources.models import DateRange, Origin

SOURCE = FeedSource(name="Example", url="https://example.com/feed", tier="primary")


def test_parses_rss(feed_bytes: Callable[[str], bytes], wide_window: DateRange) -> None:
    items = parse_feed(feed_bytes("rss_deepmind.xml"), SOURCE, wide_window)

    assert items, "recorded RSS fixture yielded nothing"
    first = items[0]
    assert first.title and not first.title.startswith("<")
    assert first.url.startswith("http")
    assert first.source == "Example"
    assert first.origin is Origin.FEED
    assert first.extra["tier"] == "primary"


def test_parses_atom(
    feed_bytes: Callable[[str], bytes], wide_window: DateRange
) -> None:
    items = parse_feed(feed_bytes("atom_simonwillison.xml"), SOURCE, wide_window)

    assert items, "recorded Atom fixture yielded nothing"
    assert all(isinstance(i.published_date, date) for i in items)


def test_window_is_applied_during_parsing(feed_bytes: Callable[[str], bytes]) -> None:
    """Filtering at parse time keeps a decade-old feed from flooding the gates."""
    empty = DateRange(start=date(1990, 1, 1), end=date(1990, 2, 1))

    assert parse_feed(feed_bytes("rss_deepmind.xml"), SOURCE, empty) == ()


def test_entries_without_a_date_are_dropped(wide_window: DateRange) -> None:
    """No date means no item. Defaulting to today would fake freshness."""
    raw = b"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>Undated</title><link>https://example.com/a</link></item>
    <item><title>Dated</title><link>https://example.com/b</link>
      <pubDate>Mon, 08 Sep 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""

    items = parse_feed(raw, SOURCE, wide_window)

    assert [i.title for i in items] == ["Dated"]


def test_entries_without_a_link_or_title_are_dropped(wide_window: DateRange) -> None:
    raw = b"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>No link</title><pubDate>Mon, 08 Sep 2026 10:00:00 GMT</pubDate></item>
    <item><link>https://example.com/b</link>
      <pubDate>Mon, 08 Sep 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""

    assert parse_feed(raw, SOURCE, wide_window) == ()


def test_unparseable_bytes_yield_nothing(wide_window: DateRange) -> None:
    assert parse_feed(b"this is not a feed", SOURCE, wide_window) == ()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<p>Hello <b>world</b></p>", "Hello world"),
        ("Plain text", "Plain text"),
        ("&lt;script&gt;alert(1)&lt;/script&gt;", "<script>alert(1)</script>"),
        ("<p>line\n\nbreaks</p>", "line breaks"),
        ("", ""),
    ],
)
def test_strip_html(raw: str, expected: str) -> None:
    assert strip_html(raw) == expected


def test_escaped_markup_cannot_become_real_markup() -> None:
    """Tags are removed before entities are unescaped, never the other way round."""
    assert "<b>" in strip_html("&lt;b&gt;")
    assert strip_html("<b>bold</b>") == "bold"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_a_failing_feed_is_skipped_not_fatal(wide_window: DateRange) -> None:
    """Losing one source costs that source's items, never the run."""
    good = b"""<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>Fine</title><link>https://example.com/ok</link>
      <pubDate>Mon, 08 Sep 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        if "broken" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, content=good)

    sources = (
        FeedSource("Broken", "https://broken.example.com/feed"),
        FeedSource("Working", "https://example.com/feed"),
    )

    with _client(handler) as http:
        items, failures = fetch_feeds(sources, wide_window, http=http)

    assert [i.title for i in items] == ["Fine"]
    assert [(f.source, f.reason) for f in failures] == [("Broken", "http 500")]


def test_a_timeout_is_reported_as_such(wide_window: DateRange) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with _client(handler) as http:
        slow = (FeedSource("Slow", "https://slow.example.com/feed"),)
        items, failures = fetch_feeds(slow, wide_window, http=http)

    assert items == ()
    assert failures[0].reason == "timeout"


def test_no_sources_means_no_requests(wide_window: DateRange) -> None:
    assert fetch_feeds((), wide_window) == ((), ())
