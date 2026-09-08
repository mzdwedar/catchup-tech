"""The gates: everything the system refuses to pass along.

Sources will happily return items that are stale, duplicated, or pointing at a dead
page, and none of them look wrong on inspection. Collecting is easy; refusing is the
job. Carried over from the superseded `digest` module, where it was the best idea in
the spec.

Publishing nothing is always an acceptable outcome. Publishing something wrong is not.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import StrEnum

import httpx

from catchup.seen import SeenLedger
from catchup.sources.http import MAX_CONCURRENCY, client, in_parallel
from catchup.sources.models import DateRange, Item, SourceFailure
from catchup.sources.urls import normalize_url

logger = logging.getLogger(__name__)

MIN_ITEMS = 6
TITLE_SIMILARITY = 0.9
LIVENESS_TIMEOUT = 10.0

# A definitively missing page. Everything else — 403, 429, 500 — is the internet being
# the internet, not evidence that the link is dead.
DEAD_STATUSES = frozenset({404, 410})


class Gate(StrEnum):
    COUNT = "G1"
    WINDOW = "G2"
    LIVENESS = "G3"
    DUPLICATES = "G4"
    RECOUNT = "G5"


@dataclass(frozen=True, slots=True)
class GateCount:
    before: int
    after: int


class GateError(Exception):
    """Raised when a gate refuses to pass a collection along.

    Carries the gate and the counts so the message says *why* rather than just *no*.
    """

    def __init__(self, gate: Gate, count: int, required: int) -> None:
        self.gate = gate
        self.count = count
        self.required = required
        super().__init__(
            f"{gate.value} failed: {count} item(s), need at least {required}. "
            f"Publishing nothing."
        )


@dataclass(frozen=True, slots=True)
class Collection:
    """What survived the gates, plus the evidence of what did not."""

    window: DateRange
    items: tuple[Item, ...]
    skipped_sources: tuple[SourceFailure, ...] = ()
    gate_counts: Mapping[str, GateCount] = field(default_factory=dict)


UrlChecker = Callable[[str], bool]


def within_window(items: Sequence[Item], window: DateRange) -> tuple[Item, ...]:
    """G2 — drop items published outside the window. Pure: no clock, no network."""
    return tuple(i for i in items if window.contains(i.published_date))


_DIGITS = re.compile(r"\d+")


def _titles_match(a: str, b: str) -> bool:
    """Whether two titles are the same story told twice.

    Similarity alone is not enough. "Gemini 3 Pro released" and "Gemini 2 Pro released"
    score 0.95 and are entirely different news — in this domain a version number is
    often the only thing that distinguishes one announcement from the next. So titles
    whose numbers disagree are never merged, however similar the words around them.
    """
    if _DIGITS.findall(a) != _DIGITS.findall(b):
        return False
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio() > TITLE_SIMILARITY


def deduplicate(items: Sequence[Item]) -> tuple[Item, ...]:
    """G4 — drop repeat URLs and near-duplicate titles, keeping the first seen.

    URLs are normalized before comparison, so the same story reaching us from a feed and
    from Hacker News with a `utm_source` tag collapses into one item instead of two.
    """
    kept: list[Item] = []
    urls: set[str] = set()
    for item in items:
        url = normalize_url(item.url)
        if url in urls:
            continue
        if any(_titles_match(item.title, k.title) for k in kept):
            continue
        urls.add(url)
        kept.append(item)
    return tuple(kept)


def url_is_live(url: str, http: httpx.Client) -> bool:
    """Whether `url` resolves to something that is not definitively gone.

    HEAD first, falling back to GET: plenty of servers answer HEAD with 405 while
    serving the page fine. Only 404/410 or a connection failure counts as dead — a 403
    or 429 is bot protection, and treating it as a dead link would silently gut the
    digest of exactly the mainstream sources it should contain.
    """
    try:
        response = http.head(url)
        if response.status_code == 405 or response.status_code >= 500:
            response = http.get(url)
    except httpx.HTTPError as exc:
        logger.info(
            "liveness: unreachable", extra={"url": url, "err": type(exc).__name__}
        )
        return False
    if response.status_code in DEAD_STATUSES:
        logger.info(
            "liveness: dead", extra={"url": url, "status": response.status_code}
        )
        return False
    return True


def drop_dead_links(
    items: Sequence[Item], check: UrlChecker, max_workers: int = MAX_CONCURRENCY
) -> tuple[Item, ...]:
    """G3 — check every URL concurrently and keep the ones that resolve."""
    if not items:
        return ()
    alive = in_parallel([i.url for i in items], check, max_workers=max_workers)
    return tuple(item for item, ok in zip(items, alive, strict=True) if ok)


def default_checker() -> tuple[UrlChecker, httpx.Client]:
    """A liveness checker bound to a client the caller is responsible for closing."""
    http = client(timeout=LIVENESS_TIMEOUT)
    return (lambda url: url_is_live(url, http)), http


def gate(
    items: Iterable[Item],
    window: DateRange,
    check: UrlChecker,
    seen: SeenLedger | None = None,
    min_items: int = MIN_ITEMS,
    skipped_sources: tuple[SourceFailure, ...] = (),
) -> Collection:
    """Run G1-G5 in order and return what survived.

    Ordering is not incidental: the free, local gates (window, dedupe) run before the
    one that costs a network round trip per item, so a run that was never going to
    survive fails without making a hundred HEAD requests first.
    """
    collected = tuple(items)
    counts: dict[str, GateCount] = {}

    if len(collected) < min_items:
        raise GateError(Gate.COUNT, len(collected), min_items)
    counts[Gate.COUNT] = GateCount(len(collected), len(collected))

    windowed = within_window(collected, window)
    counts[Gate.WINDOW] = GateCount(len(collected), len(windowed))

    deduped = deduplicate(windowed)
    counts[Gate.DUPLICATES] = GateCount(len(windowed), len(deduped))

    if seen is not None:
        fresh = seen.unseen(deduped)
        logger.info(
            "ledger filter", extra={"before": len(deduped), "after": len(fresh)}
        )
        deduped = fresh

    live = drop_dead_links(deduped, check)
    counts[Gate.LIVENESS] = GateCount(len(deduped), len(live))

    if len(live) < min_items:
        raise GateError(Gate.RECOUNT, len(live), min_items)
    counts[Gate.RECOUNT] = GateCount(len(live), len(live))

    logger.info(
        "gates passed",
        extra={"collected": len(collected), "published": len(live)},
    )
    return Collection(
        window=window,
        items=live,
        skipped_sources=skipped_sources,
        gate_counts=counts,
    )
