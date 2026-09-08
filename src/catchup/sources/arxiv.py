"""Research sources: arXiv and Hugging Face daily papers.

Papers are their own kind of news — they rarely appear in a vendor feed and never in the
press within the window. Hugging Face's daily-papers list adds the community's own
filter, which is a better relevance signal than raw arXiv volume.
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree

import httpx

from catchup.sources.dates import from_iso
from catchup.sources.http import client
from catchup.sources.models import DateRange, Item, Origin

logger = logging.getLogger(__name__)

# https, not http: plain http returns an empty body rather than an error. Verified
# 2026-09-08, and the failure is silent, which is exactly the kind that wastes an hour.
ARXIV_ENDPOINT = "https://export.arxiv.org/api/query"
HF_ENDPOINT = "https://huggingface.co/api/daily_papers"

ATOM = "{http://www.w3.org/2005/Atom}"
DEFAULT_CATEGORIES = ("cs.AI", "cs.LG", "cs.CL")
MAX_RESULTS = 100


def parse_arxiv(raw: bytes, window: DateRange) -> tuple[Item, ...]:
    """Parse an arXiv Atom response into windowed items."""
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        logger.warning("arxiv response unparseable: %s", exc)
        return ()

    items: list[Item] = []
    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split()).strip()
        link = (entry.findtext(f"{ATOM}id") or "").strip()
        published = from_iso(entry.findtext(f"{ATOM}published"))
        if not title or not link or published is None:
            continue
        if not window.contains(published):
            continue
        authors = [
            name.strip()
            for author in entry.findall(f"{ATOM}author")
            if (name := author.findtext(f"{ATOM}name") or "")
        ]
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split()).strip()
        category = entry.find(f"{ATOM}category")
        term = category.get("term", "") if category is not None else ""
        items.append(
            Item(
                title=title,
                url=link,
                source="arXiv",
                published_date=published,
                summary=summary[:600],
                origin=Origin.ARXIV,
                extra={
                    "authors": ", ".join(authors[:5]),
                    "category": term or "",
                },
            )
        )
    return tuple(items)


def parse_hf_papers(payload: object, window: DateRange) -> tuple[Item, ...]:
    """Parse Hugging Face daily papers into windowed items."""
    if not isinstance(payload, list):
        logger.warning("unexpected HF payload shape; skipping")
        return ()
    items: list[Item] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        paper = entry.get("paper")
        paper = paper if isinstance(paper, dict) else {}
        title = " ".join(str(paper.get("title") or entry.get("title") or "").split())
        paper_id = str(paper.get("id") or "")
        raw_date = entry.get("publishedAt") or paper.get("publishedAt") or ""
        published = from_iso(str(raw_date))
        if not title or not paper_id or published is None:
            continue
        if not window.contains(published):
            continue
        items.append(
            Item(
                title=title.strip(),
                url=f"https://huggingface.co/papers/{paper_id}",
                source="Hugging Face Papers",
                published_date=published,
                summary=" ".join(str(paper.get("summary") or "").split())[:600],
                origin=Origin.ARXIV,
                extra={"upvotes": str(paper.get("upvotes") or 0), "arxiv_id": paper_id},
            )
        )
    return tuple(items)


def fetch_arxiv(
    window: DateRange,
    categories: tuple[str, ...] = DEFAULT_CATEGORIES,
    http: httpx.Client | None = None,
) -> tuple[Item, ...]:
    """Fetch recent arXiv submissions and Hugging Face daily papers.

    arXiv has no date filter in its query language, so this asks for the most recent
    submissions and lets the window filter do the work — which is why `MAX_RESULTS` is
    generous rather than tuned.
    """
    owned = http is None
    http = http or client()
    collected: list[Item] = []
    try:
        query = " OR ".join(f"cat:{c}" for c in categories)
        response = http.get(
            ARXIV_ENDPOINT,
            params={
                "search_query": query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": str(MAX_RESULTS),
            },
        )
        response.raise_for_status()
        collected.extend(parse_arxiv(response.content, window))

        hf = http.get(HF_ENDPOINT, params={"limit": "100"})
        hf.raise_for_status()
        collected.extend(parse_hf_papers(hf.json(), window))
    finally:
        if owned:
            http.close()
    logger.info("research fetched", extra={"items": len(collected)})
    return tuple(collected)
