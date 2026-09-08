"""arXiv and Hugging Face paper parsing, from recorded responses."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date

from catchup.sources.arxiv import parse_arxiv, parse_hf_papers
from catchup.sources.models import DateRange, Origin

WIDE = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))


def test_parses_recorded_arxiv(feed_bytes: Callable[[str], bytes]) -> None:
    items = parse_arxiv(feed_bytes("arxiv_query.xml"), WIDE)

    assert items, "recorded arXiv fixture yielded nothing"
    first = items[0]
    assert first.origin is Origin.ARXIV
    assert first.url.startswith("http")
    assert first.extra["authors"]
    assert "\n" not in first.title, "titles arrive wrapped and must be flattened"


def test_arxiv_respects_the_window(feed_bytes: Callable[[str], bytes]) -> None:
    narrow = DateRange(start=date(1990, 1, 1), end=date(1990, 2, 1))

    assert parse_arxiv(feed_bytes("arxiv_query.xml"), narrow) == ()


def test_malformed_arxiv_xml_yields_nothing() -> None:
    """A truncated response is a skipped source, not a crashed run."""
    assert parse_arxiv(b"<feed><entry>unclosed", WIDE) == ()


def test_parses_recorded_hf_papers(feed_bytes: Callable[[str], bytes]) -> None:
    payload = json.loads(feed_bytes("hf_papers.json"))

    items = parse_hf_papers(payload, WIDE)

    assert items, "recorded HF fixture yielded nothing"
    assert all(i.url.startswith("https://huggingface.co/papers/") for i in items)
    assert all(i.source == "Hugging Face Papers" for i in items)
    assert all("upvotes" in i.extra for i in items)


def test_hf_entries_without_an_id_are_dropped() -> None:
    payload = [{"paper": {"title": "No id"}, "publishedAt": "2026-09-01T00:00:00Z"}]

    assert parse_hf_papers(payload, WIDE) == ()


def test_unexpected_hf_shape_is_skipped() -> None:
    assert parse_hf_papers({"error": "nope"}, WIDE) == ()
