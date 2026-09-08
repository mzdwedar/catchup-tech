"""Reading the source list out of `02-sources.md`.

The source list is config, not code: adding a feed is a markdown edit, and `SPEC.md`
makes that a success criterion. That means the markdown is parsed rather than imported,
so this module is deliberately forgiving — it looks for table rows containing a URL and
ignores everything else in the file, including prose, headings, and hand-written notes.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = Path(".claude/skills/ai-news-tracker/02-sources.md")

_ROW = re.compile(r"^\s*\|(?P<cells>.+)\|\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_URL = re.compile(r"https?://\S+")
_SEPARATOR = re.compile(r"^[\s|:-]+$")
_TIERS = ("primary", "press", "community", "research")


@dataclass(frozen=True, slots=True)
class FeedSource:
    """One RSS/Atom feed from the config table."""

    name: str
    url: str
    tier: str = "press"


def _cells(line: str) -> list[str] | None:
    match = _ROW.match(line)
    if match is None or _SEPARATOR.match(line):
        return None
    return [c.strip() for c in match.group("cells").split("|")]


def parse_sources(text: str) -> tuple[FeedSource, ...]:
    """Extract feed sources from the markdown of `02-sources.md`.

    A row contributes a source when one of its cells contains a URL. The name is the
    first non-empty cell before it; the tier is any cell matching a known tier, so
    column order can change without breaking this.

    Rows inside a fenced code block are ignored — they are documentation showing what a
    row looks like, and treating them as live config would mean a file explaining how to
    re-enable a source had already re-enabled it.
    """
    found: list[FeedSource] = []
    seen: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        # A row inside a fenced block is an example, not a source. Without this, a file
        # documenting "to add arXiv back, paste this row" adds arXiv back.
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cells = _cells(line)
        if cells is None:
            continue
        url_match = next((_URL.search(c) for c in cells if _URL.search(c)), None)
        if url_match is None:
            continue
        url = url_match.group(0).rstrip(">)|,.")
        if url in seen:
            continue
        name = next(
            (c for c in cells if c and not _URL.search(c) and c.lower() not in _TIERS),
            url,
        )
        tier = next((c.lower() for c in cells if c.lower() in _TIERS), "press")
        seen.add(url)
        found.append(FeedSource(name=name.strip("*` "), url=url, tier=tier))
    return tuple(found)


RESEARCH_TIER = "research"

# Research sources are APIs, not RSS. They are configured as table rows like everything
# else so that enabling or disabling one stays a markdown edit, but they are fetched by
# `catchup.sources.arxiv` rather than by the feed parser, which would choke on JSON.
RESEARCH_HOSTS = {"arxiv.org": "arxiv", "huggingface.co": "papers"}


def split_sources(
    sources: Iterable[FeedSource],
) -> tuple[tuple[FeedSource, ...], tuple[FeedSource, ...]]:
    """Separate RSS/Atom feeds from research APIs.

    Handing a JSON endpoint to the feed parser yields nothing and looks like a quiet
    week, so the split happens before either fetcher runs.
    """
    listed = tuple(sources)
    feeds = tuple(s for s in listed if s.tier != RESEARCH_TIER)
    research = tuple(s for s in listed if s.tier == RESEARCH_TIER)
    return feeds, research


def research_kinds(research: Iterable[FeedSource]) -> frozenset[str]:
    """Which research services the config asks for: `arxiv`, `papers`, or neither.

    Dropping raw arXiv while keeping Hugging Face daily papers is a real editorial
    choice — arXiv has no relevance ranking of its own — so it has to be expressible
    without a code change. Deleting the row is how you make it.
    """
    kinds = {
        kind
        for source in research
        for host, kind in RESEARCH_HOSTS.items()
        if host in source.url
    }
    return frozenset(kinds)


def load_sources(path: Path = DEFAULT_SOURCES) -> tuple[FeedSource, ...]:
    """Load the configured feeds, or none if the file does not exist yet.

    A missing file means `/setup` has not run. That is not an error here — the caller
    reports it, because "run /setup first" is a better message than a traceback.
    """
    if not path.exists():
        logger.warning("no source config at %s; run /setup", path)
        return ()
    sources = parse_sources(path.read_text(encoding="utf-8"))
    logger.info("loaded sources", extra={"count": len(sources)})
    return sources
