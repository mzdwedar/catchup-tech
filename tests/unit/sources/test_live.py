"""Opt-in checks against the real services. Excluded by default; run with `-m live`.

These exist because every source here has already surprised us once: HN rejects an
unencoded `>`, and arXiv returns an empty body over plain http rather than an error.
Neither failure is visible from a recorded fixture, so something has to actually call.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from catchup.sources.arxiv import fetch_arxiv
from catchup.sources.config import load_sources
from catchup.sources.feeds import fetch_feeds
from catchup.sources.hn import fetch_hn
from catchup.sources.models import DateRange

pytestmark = pytest.mark.live


@pytest.fixture
def recent() -> DateRange:
    end = date.today()
    return DateRange(start=end - timedelta(days=7), end=end)


def test_configured_feeds_are_reachable(recent: DateRange) -> None:
    """A rotted feed URL should be found here, not in a thin digest."""
    sources = load_sources()

    items, failures = fetch_feeds(sources, recent)

    assert items, "no configured feed returned anything in the last week"
    assert not failures, f"unreachable: {[(f.source, f.reason) for f in failures]}"


def test_hacker_news_accepts_our_query(recent: DateRange) -> None:
    """The encoding regression would show up here as a 400."""
    assert fetch_hn(recent, queries=("AI",))


def test_arxiv_and_hugging_face_return_papers(recent: DateRange) -> None:
    """arXiv over plain http returns an empty body, so this asserts on content."""
    items = fetch_arxiv(recent)

    assert {i.source for i in items} == {"arXiv", "Hugging Face Papers"}
