"""The gates: everything the system refuses to pass along.

These carry a 95% coverage floor because they are pure logic and because they are the
only thing standing between a noisy source and a digest that looks confident while
being wrong.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import httpx
import pytest

from catchup.collect import (
    Collection,
    Gate,
    GateError,
    deduplicate,
    default_checker,
    drop_dead_links,
    gate,
    url_is_live,
    within_window,
)
from catchup.seen import SeenLedger
from catchup.sources.models import DateRange, Item, SourceFailure

WINDOW = DateRange(start=date(2026, 9, 1), end=date(2026, 9, 8))
ALIVE: Callable[[str], bool] = lambda _url: True  # noqa: E731


SUBJECTS = (
    "A lab shipped a model",
    "Someone benchmarked inference latency",
    "A paper on distillation appeared",
    "An agent framework changed its protocol",
    "Regulators published guidance",
    "An open-weights license was revised",
    "A datacenter deal was signed",
    "Interpretability researchers found a circuit",
    "A coding assistant grew a sandbox",
    "Quantization got cheaper on consumer cards",
)


def items(n: int, *, day: date = date(2026, 9, 3)) -> tuple[Item, ...]:
    """`n` distinct in-window items — the "everything is fine" baseline.

    Titles are genuinely unlike each other, not `f"Story {i}"`: numbered titles are
    ~0.93 similar and would be collapsed by G4, which would quietly make every count
    assertion below meaningless.
    """
    return tuple(
        Item(
            title=SUBJECTS[i % len(SUBJECTS)]
            + (f" (part {i})" if i >= len(SUBJECTS) else ""),
            url=f"https://example.com/{i}",
            source="Example",
            published_date=day,
        )
        for i in range(n)
    )


# --- G2: window ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "kept"),
    [
        (date(2026, 9, 1), True),  # start is inclusive
        (date(2026, 9, 4), True),
        (date(2026, 9, 7), True),
        (date(2026, 9, 8), False),  # end is exclusive
        (date(2026, 8, 31), False),
        (date(2025, 9, 4), False),
    ],
)
def test_window_bounds_are_half_open(day: date, kept: bool) -> None:
    """Half-open, so consecutive runs never both claim the boundary day."""
    result = within_window(items(1, day=day), WINDOW)

    assert bool(result) is kept


def test_window_gate_is_pure() -> None:
    """No clock: the same inputs give the same answer whenever it runs."""
    batch = items(3)

    assert within_window(batch, WINDOW) == within_window(batch, WINDOW)


# --- G4: duplicates --------------------------------------------------------------


def test_identical_urls_collapse() -> None:
    duplicated = (
        Item("First telling", "https://example.com/a", "Feed", date(2026, 9, 2)),
        Item("Totally other words", "https://example.com/a", "HN", date(2026, 9, 3)),
    )

    assert len(deduplicate(duplicated)) == 1


def test_tracking_parameters_do_not_defeat_dedupe() -> None:
    """The real case: a story arrives from a feed and again from HN with a utm tag."""
    pair = (
        Item("A release", "https://example.com/post", "Feed", date(2026, 9, 2)),
        Item(
            "Different headline entirely",
            "https://example.com/post?utm_source=hn",
            "HN",
            date(2026, 9, 2),
        ),
    )

    assert len(deduplicate(pair)) == 1


def test_near_duplicate_titles_collapse() -> None:
    """Two outlets covering one announcement is one item, not two."""
    pair = (
        Item(
            "OpenAI releases GPT-6 with a 1M context window",
            "https://a.example.com/1",
            "A",
            date(2026, 9, 2),
        ),
        Item(
            "OpenAI releases GPT-6 with a 1M context window.",
            "https://b.example.com/2",
            "B",
            date(2026, 9, 2),
        ),
    )

    assert len(deduplicate(pair)) == 1


def test_the_first_telling_survives() -> None:
    """Keeping the first preserves source ordering, so primary sources win."""
    pair = (
        Item("A release", "https://primary.example.com/x", "OpenAI", date(2026, 9, 2)),
        Item("A release", "https://press.example.com/y", "The Verge", date(2026, 9, 2)),
    )

    (survivor,) = deduplicate(pair)

    assert survivor.source == "OpenAI"


def test_genuinely_different_stories_both_survive() -> None:
    assert len(deduplicate(items(5))) == 5


def test_titles_differing_only_by_a_version_number_both_survive() -> None:
    """The domain's sharpest edge: the number is often the entire story."""
    pair = (
        Item(
            "Gemini 3 Pro is now available",
            "https://a.example.com/3",
            "G",
            date(2026, 9, 2),
        ),
        Item(
            "Gemini 2 Pro is now available",
            "https://a.example.com/2",
            "G",
            date(2026, 9, 2),
        ),
    )

    assert len(deduplicate(pair)) == 2


def test_matching_numbers_still_collapse() -> None:
    """The guard is about disagreeing numbers, not about disabling title matching."""
    pair = (
        Item(
            "GPT-6 ships with a 1M context window",
            "https://a.example.com/x",
            "A",
            date(2026, 9, 2),
        ),
        Item(
            "GPT-6 ships with a 1M context window.",
            "https://b.example.com/y",
            "B",
            date(2026, 9, 2),
        ),
    )

    assert len(deduplicate(pair)) == 1


# --- G3: liveness ----------------------------------------------------------------


def _checker(status: int | None) -> Callable[[str], bool]:
    def handler(request: httpx.Request) -> httpx.Response:
        if status is None:
            raise httpx.ConnectError("no route", request=request)
        return httpx.Response(status)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return lambda url: url_is_live(url, http)


@pytest.mark.parametrize("status", [200, 301, 401, 403, 429])
def test_bot_protection_is_not_a_dead_link(status: int) -> None:
    """A 403 from Cloudflare would otherwise gut the digest of mainstream sources."""
    assert _checker(status)("https://example.com/post") is True


@pytest.mark.parametrize("status", [404, 410])
def test_definitively_missing_pages_are_dropped(status: int) -> None:
    assert _checker(status)("https://example.com/post") is False


def test_a_connection_failure_drops_the_item() -> None:
    assert _checker(None)("https://example.com/post") is False


def test_head_falls_back_to_get() -> None:
    """Plenty of servers reject HEAD with 405 while serving the page fine."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(405) if request.method == "HEAD" else httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        assert url_is_live("https://example.com/post", http) is True

    assert calls == ["HEAD", "GET"]


def test_liveness_preserves_order() -> None:
    """Results are zipped back onto items, so a shuffle would mislabel them."""
    batch = items(6)
    dead = {batch[1].url, batch[4].url}

    kept = drop_dead_links(batch, lambda url: url not in dead)

    assert [i.url for i in kept] == [b.url for b in batch if b.url not in dead]


def test_liveness_on_an_empty_batch_makes_no_requests() -> None:
    def explode(_url: str) -> bool:
        raise AssertionError("should not be called")

    assert drop_dead_links((), explode) == ()


def test_default_checker_is_wired_to_a_client() -> None:
    check, http = default_checker()
    try:
        assert callable(check)
        assert http.timeout.connect == pytest.approx(10.0)
    finally:
        http.close()


# --- G1 / G5: counts -------------------------------------------------------------


def test_too_few_collected_aborts_before_any_network_call() -> None:
    """G1 runs first so a doomed run costs nothing."""

    def explode(_url: str) -> bool:
        raise AssertionError("liveness should not run when G1 fails")

    with pytest.raises(GateError) as caught:
        gate(items(5), WINDOW, explode, min_items=6)

    assert caught.value.gate is Gate.COUNT
    assert caught.value.count == 5


def test_a_collection_gutted_by_filtering_aborts() -> None:
    """Passing G1 is not enough — G5 recounts what actually survived."""
    stale = items(4, day=date(2020, 1, 1)) + items(4)

    with pytest.raises(GateError) as caught:
        gate(stale, WINDOW, ALIVE, min_items=6)

    assert caught.value.gate is Gate.RECOUNT


def test_the_error_says_why() -> None:
    with pytest.raises(GateError, match=r"G1 failed: 2 item.*need at least 6"):
        gate(items(2), WINDOW, ALIVE, min_items=6)


def test_a_healthy_collection_passes() -> None:
    result = gate(items(8), WINDOW, ALIVE, min_items=6)

    assert isinstance(result, Collection)
    assert len(result.items) == 8
    assert result.window == WINDOW


def test_gate_counts_record_each_stage() -> None:
    """The run record's audit trail: what each gate saw and what it kept."""
    mixed = items(6) + items(3, day=date(2020, 1, 1))

    result = gate(mixed, WINDOW, ALIVE, min_items=6)

    assert result.gate_counts[Gate.WINDOW].before == 9
    assert result.gate_counts[Gate.WINDOW].after == 6
    assert result.gate_counts[Gate.LIVENESS].after == 6


def test_skipped_sources_are_carried_through() -> None:
    failures = (SourceFailure("TechCrunch AI", "timeout"),)

    result = gate(items(6), WINDOW, ALIVE, skipped_sources=failures)

    assert result.skipped_sources == failures


def test_already_published_items_are_dropped() -> None:
    batch = items(8)
    ledger = SeenLedger.empty().record(batch[:2], run_id="2026-09-01")

    result = gate(batch, WINDOW, ALIVE, seen=ledger, min_items=6)

    assert len(result.items) == 6


def test_the_ledger_can_starve_a_run() -> None:
    """Nothing new since last time is a legitimate abort, not a thin digest."""
    batch = items(8)
    ledger = SeenLedger.empty().record(batch, run_id="2026-09-01")

    with pytest.raises(GateError) as caught:
        gate(batch, WINDOW, ALIVE, seen=ledger, min_items=6)

    assert caught.value.gate is Gate.RECOUNT
