"""Parsing the source list out of markdown.

`02-sources.md` is written for a human first. The parser must survive prose, headings,
extra columns, and reordered columns, because the alternative is that editing your own
config breaks the tool.
"""

from __future__ import annotations

from pathlib import Path

from catchup.sources.config import (
    load_sources,
    parse_sources,
    research_kinds,
    split_sources,
)

MARKDOWN = """
# Sources

Some prose that mentions https://example.com/not-a-row in passing.

| Source | Feed | Tier |
|---|---|---|
| OpenAI | https://openai.com/news/rss.xml | primary |
| The Verge AI | https://www.theverge.com/rss/index.xml | press |

## Community

| Feed | Name | Tier | Notes |
|---|---|---|---|
| https://simonwillison.net/atom/everything/ | Simon Willison | community | good |
"""


def test_extracts_rows_containing_urls() -> None:
    sources = parse_sources(MARKDOWN)

    assert [s.name for s in sources] == ["OpenAI", "The Verge AI", "Simon Willison"]


def test_tier_is_found_regardless_of_column_order() -> None:
    """The third table puts the URL first; the tier is still read correctly."""
    by_name = {s.name: s for s in parse_sources(MARKDOWN)}

    assert by_name["OpenAI"].tier == "primary"
    assert by_name["Simon Willison"].tier == "community"


def test_prose_urls_are_ignored() -> None:
    """Only table rows count, or a link in a footnote becomes a source."""
    assert all("not-a-row" not in s.url for s in parse_sources(MARKDOWN))


def test_separator_rows_are_not_sources() -> None:
    assert parse_sources("| --- | --- |\n|:---|---:|") == ()


def test_missing_tier_defaults_to_press() -> None:
    (source,) = parse_sources("| Blog | https://example.com/feed |")

    assert source.tier == "press"


def test_duplicate_urls_are_collapsed() -> None:
    text = "| A | https://example.com/f |\n| B | https://example.com/f |"

    assert len(parse_sources(text)) == 1


def test_a_missing_config_file_is_not_an_error(tmp_path: Path) -> None:
    """ "Run /setup first" is a better message than a traceback from the fetcher."""
    assert load_sources(tmp_path / "absent.md") == ()


def test_loads_the_projects_own_config() -> None:
    """The shipped `02-sources.md` must actually parse — it is the default config."""
    sources = load_sources()

    assert len(sources) >= 5
    assert any(s.tier == "primary" for s in sources)
    assert all(s.url.startswith("http") for s in sources)


# --- fenced examples are documentation, not config -------------------------------

FENCED = """
| Live | https://example.com/live | press |

To add arXiv back, paste this row:

```
| arXiv | https://export.arxiv.org/api/query | research |
```

| Also live | https://example.com/other | press |
"""


def test_rows_inside_a_code_fence_are_not_sources() -> None:
    """A file explaining how to re-enable a source must not have re-enabled it.

    This is not hypothetical: `02-sources.md` documents the arXiv row that setup
    removed, and before the fence check that example was parsed as a live source.
    """
    names = [s.name for s in parse_sources(FENCED)]

    assert names == ["Live", "Also live"]
    assert all("arxiv" not in s.url for s in parse_sources(FENCED))


def test_parsing_resumes_after_the_fence_closes() -> None:
    """An unbalanced fence would silently swallow the rest of the file."""
    assert len(parse_sources(FENCED)) == 2


def test_tilde_fences_count_too() -> None:
    text = "| A | https://example.com/a |\n~~~\n| B | https://example.com/b |\n~~~\n"

    assert [s.name for s in parse_sources(text)] == ["A"]


# --- research rows are APIs, not feeds -------------------------------------------

MIXED = """
| OpenAI | https://openai.com/news/rss.xml | primary |
| Hugging Face daily papers | https://huggingface.co/api/daily_papers | research |
"""


def test_research_rows_are_kept_out_of_the_feed_list() -> None:
    """Handing a JSON endpoint to the feed parser yields a silent zero, not an error."""
    feeds, research = split_sources(parse_sources(MIXED))

    assert [s.name for s in feeds] == ["OpenAI"]
    assert [s.name for s in research] == ["Hugging Face daily papers"]


def test_research_kinds_names_the_configured_services() -> None:
    _feeds, research = split_sources(parse_sources(MIXED))

    assert research_kinds(research) == frozenset({"papers"})


def test_dropping_the_arxiv_row_drops_arxiv() -> None:
    """The editorial choice made at setup, expressed as a deleted table row."""
    with_arxiv = MIXED + "| arXiv | https://export.arxiv.org/api/query | research |\n"

    _f, research = split_sources(parse_sources(with_arxiv))
    assert research_kinds(research) == frozenset({"arxiv", "papers"})

    _f2, without = split_sources(parse_sources(MIXED))
    assert research_kinds(without) == frozenset({"papers"})


def test_no_research_rows_means_no_research_fetch() -> None:
    assert research_kinds(()) == frozenset()


def test_the_shipped_config_drops_raw_arxiv() -> None:
    """Guards the actual decision recorded in `02-sources.md`."""
    feeds, research = split_sources(load_sources())

    assert research_kinds(research) == frozenset({"papers"})
    assert all("api/daily_papers" not in s.url for s in feeds)
    assert any(s.name == "Anthropic" for s in feeds), "Anthropic mirror missing"
