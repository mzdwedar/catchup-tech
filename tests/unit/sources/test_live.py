"""Opt-in checks against the real services. Excluded by default; run with `-m live`.

These exist because every source here has already surprised us once: HN rejects an
unencoded `>`, and arXiv returns an empty body over plain http rather than an error.
Neither failure is visible from a recorded fixture, so something has to actually call.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from catchup.sources.arxiv import fetch_arxiv
from catchup.sources.config import load_sources, split_sources
from catchup.sources.feeds import fetch_feeds
from catchup.sources.hn import fetch_hn
from catchup.sources.models import DateRange

pytestmark = pytest.mark.live


@pytest.fixture
def recent() -> DateRange:
    end = date.today()
    return DateRange(start=end - timedelta(days=7), end=end)


# Transient by nature: rate limiting and server errors say nothing about whether a feed
# URL is still correct. This mirrors gate G3's rule that a 403/429 is bot protection
# rather than a dead link — a live test that fails on them is just flaky.
TRANSIENT = ("timeout", "http 429", "http 5", "connection error")


def test_configured_feeds_are_reachable(recent: DateRange) -> None:
    """A rotted feed URL should be found here, not in a thin digest."""
    feeds, _research = split_sources(load_sources())

    items, failures = fetch_feeds(feeds, recent)

    assert items, "no configured feed returned anything in the last week"
    broken = [f for f in failures if not f.reason.startswith(TRANSIENT)]
    assert not broken, f"unreachable: {[(f.source, f.reason) for f in broken]}"


def test_every_configured_feed_has_published_recently(recent: DateRange) -> None:
    """Catches the feed that answers 200 and is editorially dead.

    SemiAnalysis shipped exactly this failure at setup: `semianalysis.com/feed/` returns
    ten well-formed, correctly dated entries whose newest is a year old. Every automated
    check passes and the window gate silently drops the lot, so the source contributes
    nothing while looking healthy. Only a freshness assertion catches it.
    """
    feeds, _research = split_sources(load_sources())
    stale = DateRange(start=recent.start - timedelta(days=83), end=recent.end)

    items, failures = fetch_feeds(feeds, stale)

    transient = {f.source for f in failures}
    produced = {i.source for i in items}
    silent = [
        f.name for f in feeds if f.name not in produced and f.name not in transient
    ]

    assert not silent, f"200 but nothing published in 90 days: {silent}"


def test_hacker_news_accepts_our_query(recent: DateRange) -> None:
    """The encoding regression would show up here as a 400."""
    assert fetch_hn(recent, queries=("AI",))


def test_arxiv_and_hugging_face_return_papers(recent: DateRange) -> None:
    """arXiv over plain http returns an empty body, so this asserts on content."""
    items = fetch_arxiv(recent)

    assert {i.source for i in items} == {"arXiv", "Hugging Face Papers"}
