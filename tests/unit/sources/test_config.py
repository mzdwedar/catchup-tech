"""Parsing the source list out of markdown.

`02-sources.md` is written for a human first. The parser must survive prose, headings,
extra columns, and reordered columns, because the alternative is that editing your own
config breaks the tool.
"""

from __future__ import annotations

from pathlib import Path

from catchup.sources.config import load_sources, parse_sources

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
