"""The command-line contract every source tool shares.

`--format json` is what `/scrape` consumes, so its shape is a contract, not a
convenience.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

import pytest

from catchup.sources.cli import (
    DEFAULT_DAYS,
    build_parser,
    render,
    resolve_window,
    run,
    today_utc,
)
from catchup.sources.models import DateRange, Item, Origin

WINDOW = DateRange(start=date(2026, 9, 1), end=date(2026, 9, 8))
ITEMS = (
    Item("A release", "https://example.com/a", "OpenAI", date(2026, 9, 3), "Summary."),
    Item(
        "A paper",
        "https://example.com/b",
        "arXiv",
        date(2026, 9, 5),
        origin=Origin.ARXIV,
    ),
)


def parse(*argv: str) -> argparse.Namespace:
    return build_parser("test").parse_args(argv)


def test_days_produces_a_window_ending_today() -> None:
    window = resolve_window(parse("search", "--days", "7"))

    assert window.end == today_utc()
    assert window.days == 7


def test_since_and_until_are_explicit() -> None:
    args = parse("search", "--since", "2026-09-01", "--until", "2026-09-08")
    window = resolve_window(args)

    assert window == WINDOW


def test_the_default_window_is_the_documented_one() -> None:
    assert resolve_window(parse("search")).days == DEFAULT_DAYS


def test_days_and_since_are_mutually_exclusive() -> None:
    """Two ways to say where the window starts is one way to get it wrong."""
    with pytest.raises(SystemExit):
        parse("search", "--days", "7", "--since", "2026-09-01")


def test_json_output_is_the_machine_contract() -> None:
    payload = json.loads(render(ITEMS, "json", WINDOW))

    assert len(payload) == 2
    assert payload[0]["published_date"] == "2026-09-03"
    assert payload[0]["origin"] == "feed"
    assert payload[1]["origin"] == "arxiv"
    assert set(payload[0]) >= {"title", "url", "source", "published_date", "summary"}


def test_json_dates_are_iso_strings_not_objects() -> None:
    """`date` is not JSON-serializable; a regression here breaks every consumer."""
    assert json.dumps(json.loads(render(ITEMS, "json", WINDOW)))


def test_table_output_states_the_window() -> None:
    output = render(ITEMS, "table", WINDOW)

    assert "2 item(s)" in output
    assert "2026-09-01" in output and "2026-09-08" in output


def test_plain_output_pairs_titles_with_urls() -> None:
    output = render(ITEMS, "plain", WINDOW)

    assert "https://example.com/a" in output
    assert "A release" in output


def test_empty_results_render_without_crashing() -> None:
    for fmt in ("json", "table", "plain"):
        assert render((), fmt, WINDOW) is not None


def test_run_prints_newest_first(capsys: pytest.CaptureFixture[str]) -> None:
    code = run("test", lambda _w, _a: ITEMS, ["search", "--format", "plain"])

    assert code == 0
    printed = capsys.readouterr().out
    assert printed.index("A paper") < printed.index("A release")


def test_a_failing_source_exits_nonzero_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`/scrape` reads this as a skipped source, so the message must be short."""

    def boom(_w: DateRange, _a: argparse.Namespace) -> tuple[Item, ...]:
        raise RuntimeError("feed is down")

    code = run("test", boom, ["search"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.err.strip() == "RuntimeError: feed is down"
    assert captured.out == ""


def test_the_fetcher_receives_the_resolved_window() -> None:
    """Every tool gets concrete dates — never a phrase to interpret."""
    seen: list[DateRange] = []

    run("test", lambda w, _a: seen.append(w) or (), ["search", "--days", "3"])

    assert seen[0].days == 3
    assert seen[0].end - seen[0].start == timedelta(days=3)
