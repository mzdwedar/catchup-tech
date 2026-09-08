"""The `catchup-collect` boundary that `/scrape` drives.

This is the seam where a tested gate meets an untested model. What matters here is that
the contract holds in both directions: valid JSON out on success, a named gate and a
non-zero exit on abort, and no silent date-guessing on the way in.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from catchup import pipeline
from catchup.pipeline import item_from_json, item_to_json, main, read_items
from catchup.sources.models import DateRange, Item, Origin

WINDOW = ["--since", "2026-09-01", "--until", "2026-09-08"]

SUBJECTS = (
    "A lab shipped a model",
    "Someone benchmarked inference latency",
    "A paper on distillation appeared",
    "An agent framework changed its protocol",
    "Regulators published guidance",
    "An open-weights license was revised",
    "A datacenter deal was signed",
)


def payload(n: int) -> list[dict[str, object]]:
    return [
        {
            "title": SUBJECTS[i],
            "url": f"https://example.com/{i}",
            "source": "Example",
            "published_date": "2026-09-03",
            "summary": "A summary. " * 40,
            "origin": "search",
        }
        for i in range(n)
    ]


def write(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    path = tmp_path / "items.json"
    path.write_text(json.dumps(entries))
    return path


ALIVE: Callable[[str], bool] = lambda _url: True  # noqa: E731


def run(argv: list[str], tmp_path: Path) -> int:
    """Drive `main` with liveness stubbed — G3 has its own tests in `test_collect`."""
    return main([*argv, "--ledger", str(tmp_path / "seen.json")], check=ALIVE)


def test_gated_items_come_back_as_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, payload(7))

    code = run(["--no-fetch", "--input", str(path), *WINDOW], tmp_path)

    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert len(result["items"]) == 7
    assert result["window"] == {"start": "2026-09-01", "end": "2026-09-08"}
    assert result["gate_counts"]["G2"]["after"] == 7


def test_an_abort_names_the_gate_and_prints_no_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`/scrape` reads stderr to tell the user why nothing was published."""
    path = write(tmp_path, payload(3))

    code = run(["--no-fetch", "--input", str(path), *WINDOW], tmp_path)

    captured = capsys.readouterr()
    assert code == 1
    assert "G1 failed" in captured.err
    assert "Publishing nothing" in captured.err
    assert captured.out == ""


def test_out_of_window_search_results_are_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The search pass gets no exemption from G2."""
    entries = payload(7)
    entries[0]["published_date"] = "2020-01-01"
    path = write(tmp_path, entries)

    run(["--no-fetch", "--input", str(path), *WINDOW, "--min-items", "1"], tmp_path)

    result = json.loads(capsys.readouterr().out)
    assert len(result["items"]) == 6


def test_compact_output_is_substantially_smaller(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Measured on a real 7-day fetch: 258KB becomes 150KB, a ~40% saving.

    The threshold is loose on purpose. The exact ratio depends on how verbose the
    period's sources happened to be, and pinning it tighter would make this a test of
    the fixture rather than of the flag.
    """
    path = write(tmp_path, payload(7))

    run(["--no-fetch", "--input", str(path), *WINDOW], tmp_path)
    full = len(capsys.readouterr().out)
    run(["--no-fetch", "--input", str(path), *WINDOW, "--compact"], tmp_path)
    compact = len(capsys.readouterr().out)

    assert compact < full * 0.8


def test_compact_output_keeps_what_ranking_needs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, payload(7))

    run(["--no-fetch", "--input", str(path), *WINDOW, "--compact"], tmp_path)

    item = json.loads(capsys.readouterr().out)["items"][0]
    assert item["title"] and item["url"] and item["source"]
    assert item["published_date"] == "2026-09-03"
    assert item["summary"].endswith("…")


def test_an_undated_item_is_refused_not_guessed(tmp_path: Path) -> None:
    """The whole point of the date rule: no silent stand-in for today."""
    entries = payload(7)
    entries[0]["published_date"] = ""

    with pytest.raises(ValueError, match=r"fromisoformat|Invalid"):
        read_items(write(tmp_path, entries))


def test_input_must_be_an_array(tmp_path: Path) -> None:
    path = tmp_path / "items.json"
    path.write_text('{"items": []}')

    with pytest.raises(ValueError, match="JSON array"):
        read_items(path)


def test_item_json_round_trips() -> None:
    """Tool output feeds straight back in, so the two must agree exactly."""
    item = Item(
        title="A release",
        url="https://example.com/a",
        source="OpenAI",
        published_date=date(2026, 9, 3),
        summary="Something happened.",
        origin=Origin.HN,
        extra={"points": "120"},
    )

    assert item_from_json(item_to_json(item)) == item


def test_missing_optional_fields_get_defaults() -> None:
    rebuilt = item_from_json(
        {"title": "T", "url": "https://x/", "published_date": "2026-09-03"}
    )

    assert rebuilt.source == "unknown"
    assert rebuilt.origin is Origin.FEED
    assert rebuilt.extra == {}


def test_the_ledger_filter_can_be_bypassed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, payload(7))
    ledger = tmp_path / "seen.json"
    ledger.write_text(
        json.dumps({f"https://example.com/{i}": "2026-09-01" for i in range(7)})
    )

    assert run(["--no-fetch", "--input", str(path), *WINDOW], tmp_path) == 1
    capsys.readouterr()

    code = main(
        [
            "--no-fetch",
            "--input",
            str(path),
            *WINDOW,
            "--include-seen",
            "--ledger",
            str(ledger),
        ],
        check=ALIVE,
    )

    assert code == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 7


# --- fetch_all honours the source config ----------------------------------------


def test_fetch_all_skips_research_when_the_config_lists_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wiring test.

    `research_kinds` returning nothing is worthless if `fetch_all` calls the research
    fetcher anyway. That exact break shipped once — an edit to this function silently
    failed to apply while every unit test still passed, and raw arXiv kept arriving.
    """
    from catchup.sources.config import FeedSource

    called: list[str] = []
    monkeypatch.setattr(
        pipeline,
        "load_sources",
        lambda: (FeedSource("Blog", "https://example.com/feed", "press"),),
    )
    monkeypatch.setattr(pipeline, "fetch_feeds", lambda *_a, **_k: ((), ()))
    monkeypatch.setattr(
        pipeline, "fetch_hn", lambda *_a, **_k: called.append("hn") or ()
    )
    monkeypatch.setattr(
        pipeline, "fetch_arxiv", lambda *_a, **_k: called.append("research") or ()
    )

    pipeline.fetch_all(DateRange(date(2026, 9, 1), date(2026, 9, 8)))

    assert called == ["hn"], "no research row configured, so none should be fetched"


def test_fetch_all_passes_the_configured_kinds_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catchup.sources.config import FeedSource

    seen: list[frozenset[str]] = []
    sources = (
        FeedSource("Blog", "https://example.com/feed", "press"),
        FeedSource("HF papers", "https://huggingface.co/api/daily_papers", "research"),
    )
    monkeypatch.setattr(pipeline, "load_sources", lambda: sources)
    monkeypatch.setattr(pipeline, "fetch_feeds", lambda *_a, **_k: ((), ()))
    monkeypatch.setattr(pipeline, "fetch_hn", lambda *_a, **_k: ())
    monkeypatch.setattr(
        pipeline, "fetch_arxiv", lambda _w, **kw: seen.append(kw["kinds"]) or ()
    )

    pipeline.fetch_all(DateRange(date(2026, 9, 1), date(2026, 9, 8)))

    assert seen == [frozenset({"papers"})], "raw arXiv must not be requested"


def test_fetch_all_keeps_research_rows_out_of_the_feed_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON endpoint handed to the feed parser returns a silent zero, not an error."""
    from catchup.sources.config import FeedSource

    handed: list[tuple[str, ...]] = []
    sources = (
        FeedSource("Blog", "https://example.com/feed", "press"),
        FeedSource("HF papers", "https://huggingface.co/api/daily_papers", "research"),
    )
    monkeypatch.setattr(pipeline, "load_sources", lambda: sources)
    monkeypatch.setattr(
        pipeline,
        "fetch_feeds",
        lambda got, *_a, **_k: (handed.append(tuple(s.name for s in got)), ((), ()))[1],
    )
    monkeypatch.setattr(pipeline, "fetch_hn", lambda *_a, **_k: ())
    monkeypatch.setattr(pipeline, "fetch_arxiv", lambda *_a, **_k: ())

    pipeline.fetch_all(DateRange(date(2026, 9, 1), date(2026, 9, 8)))

    assert handed == [("Blog",)]


def test_a_failing_source_does_not_end_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from catchup.sources.config import FeedSource

    sources = (
        FeedSource("HF papers", "https://huggingface.co/api/daily_papers", "research"),
    )
    monkeypatch.setattr(pipeline, "load_sources", lambda: sources)
    monkeypatch.setattr(pipeline, "fetch_feeds", lambda *_a, **_k: ((), ()))
    monkeypatch.setattr(pipeline, "fetch_hn", lambda *_a, **_k: _items(2))

    def boom(*_a: object, **_k: object) -> tuple[Item, ...]:
        raise TimeoutError("papers API down")

    monkeypatch.setattr(pipeline, "fetch_arxiv", boom)

    items, failures = pipeline.fetch_all(DateRange(date(2026, 9, 1), date(2026, 9, 8)))

    assert len(items) == 2, "Hacker News items survive a research outage"
    assert [(f.source, f.reason) for f in failures] == [("Research", "TimeoutError")]


def _items(n: int) -> tuple[Item, ...]:
    return tuple(
        Item(f"Story {chr(97 + i)}", f"https://example.com/{i}", "X", date(2026, 9, 3))
        for i in range(n)
    )
