"""The three source tools, exercised through their real entry points.

`/scrape` calls these as subprocesses and parses stdout, so what is verified here is
the contract at that boundary: JSON on stdout, diagnostics on stderr, exit code 0 or 1.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import httpx
import pytest

from catchup.sources import config, feeds, hn
from catchup.sources.arxiv import fetch_arxiv
from catchup.sources.config import FeedSource
from catchup.sources.models import DateRange, Item, SourceFailure
from catchup.tools import arxiv_search, feed_search, hn_search

WINDOW = ["search", "--since", "2026-09-01", "--until", "2026-09-08"]
IN_WINDOW = date(2026, 9, 3)


def _items(n: int) -> tuple[Item, ...]:
    return tuple(
        Item(
            f"Headline about topic {chr(97 + i)}",
            f"https://example.com/{i}",
            "Example",
            IN_WINDOW,
        )
        for i in range(n)
    )


def test_feed_tool_emits_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        feed_search, "load_sources", lambda: (FeedSource("Example", "https://x/feed"),)
    )
    monkeypatch.setattr(feed_search, "fetch_feeds", lambda *_a, **_k: (_items(2), ()))

    assert feed_search.main(WINDOW) == 0

    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 2


def test_feed_tool_reports_skipped_sources_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Stdout stays parseable JSON; the warning goes where it cannot corrupt it."""
    monkeypatch.setattr(
        feed_search, "load_sources", lambda: (FeedSource("Example", "https://x/feed"),)
    )
    monkeypatch.setattr(
        feed_search,
        "fetch_feeds",
        lambda *_a, **_k: (_items(1), (SourceFailure("Dead Feed", "timeout"),)),
    )

    assert feed_search.main(WINDOW) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)
    assert "skipped Dead Feed: timeout" in captured.err


def test_feed_tool_says_to_run_setup_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(feed_search, "load_sources", lambda: ())

    assert feed_search.main(WINDOW) == 1
    assert "/setup" in capsys.readouterr().err


def test_hn_tool_passes_queries_through(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[tuple[str, ...]] = []

    def fake(window: DateRange, queries: tuple[str, ...] = (), **_k: object):
        seen.append(queries)
        return _items(1)

    monkeypatch.setattr(hn_search, "fetch_hn", fake)

    assert hn_search.main([*WINDOW, "--query", "agents", "--query", "eval"]) == 0
    assert seen == [("agents", "eval")]


def test_hn_tool_falls_back_to_default_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        hn_search,
        "fetch_hn",
        lambda w, queries=(), **_k: (seen.append(queries), _items(1))[1],
    )

    hn_search.main(WINDOW)

    assert seen[0] == hn.DEFAULT_QUERIES


def test_arxiv_tool_treats_query_as_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        arxiv_search,
        "fetch_arxiv",
        lambda w, categories=(), **_k: (seen.append(categories), _items(1))[1],
    )

    arxiv_search.main([*WINDOW, "--query", "cs.CV"])

    assert seen[0] == ("cs.CV",)


def test_arxiv_fetch_queries_both_services(feed_bytes: Callable[[str], bytes]) -> None:
    """One tool, two upstreams — a failure in either must not be silent."""
    called: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.host)
        if "arxiv" in request.url.host:
            return httpx.Response(200, content=feed_bytes("arxiv_query.xml"))
        return httpx.Response(200, content=feed_bytes("hf_papers.json"))

    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        items = fetch_arxiv(wide, http=http)

    assert called == ["export.arxiv.org", "huggingface.co"]
    assert {i.source for i in items} == {"arXiv", "Hugging Face Papers"}


def test_arxiv_fetch_skips_the_service_the_config_omits(
    feed_bytes: Callable[[str], bytes],
) -> None:
    """Dropping raw arXiv must actually stop the request, not just filter after it."""
    called: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.host)
        if "arxiv" in request.url.host:
            return httpx.Response(200, content=feed_bytes("arxiv_query.xml"))
        return httpx.Response(200, content=feed_bytes("hf_papers.json"))

    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        items = fetch_arxiv(wide, http=http, kinds=frozenset({"papers"}))

    assert called == ["huggingface.co"], "arXiv should not have been queried at all"
    assert {i.source for i in items} == {"Hugging Face Papers"}


def test_arxiv_fetch_with_no_kinds_makes_no_request() -> None:
    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no research source is configured")

    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
    with httpx.Client(transport=httpx.MockTransport(explode)) as http:
        assert fetch_arxiv(wide, http=http, kinds=frozenset()) == ()


def test_arxiv_fetch_raises_so_the_cli_can_report_it() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    wide = DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http,
        pytest.raises(httpx.HTTPStatusError),
    ):
        fetch_arxiv(wide, http=http)


def test_the_shipped_shims_point_at_the_package() -> None:
    """The discovery contract: /scrape finds tools by path, not by import."""
    root = Path(__file__).resolve().parents[3] / ".agents" / "skills"

    for folder, module in (
        ("feed-search", "feed_search"),
        ("hn-search", "hn_search"),
        ("arxiv-search", "arxiv_search"),
    ):
        script = root / folder / f"{module}.py"
        assert script.exists(), f"missing shim for {folder}"
        assert f"catchup.tools.{module}" in script.read_text()


def test_sources_config_default_path_is_inside_the_skill() -> None:
    assert config.DEFAULT_SOURCES.parts[:2] == (".claude", "skills")


def test_feeds_module_exposes_the_fetcher_the_tool_imports() -> None:
    assert callable(feeds.fetch_feeds)
