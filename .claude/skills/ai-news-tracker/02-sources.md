# Sources

Feeds read by `catchup-feeds`. **Any table row containing a URL is a source** — add one by
adding a row, remove one by deleting the row. No code change, no test update.

Tier is read from any cell reading `primary`, `press`, `community`, or `research`, and
feeds scoring: a primary announcement outranks coverage of it.

All URLs below were verified reachable on 2026-09-08, with no API key.

## Labs and vendors

| Source | Feed | Tier |
|---|---|---|
| OpenAI | https://openai.com/news/rss.xml | primary |
| Google DeepMind | https://deepmind.google/blog/rss.xml | primary |
| Google AI | https://blog.google/technology/ai/rss/ | primary |
| Hugging Face | https://huggingface.co/blog/feed.xml | primary |

**Anthropic has no first-party feed.** `anthropic.com/rss.xml` and `/news/rss.xml` both
return 404. A FeedBurner mirror answers, but it is unowned by Anthropic, so it is not a
default here — the WebSearch pass in `/scrape` covers Anthropic announcements instead.

## Press

| Source | Feed | Tier |
|---|---|---|
| The Verge AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml | press |
| Ars Technica AI | https://arstechnica.com/ai/feed/ | press |
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/feed/ | press |

## Community

| Source | Feed | Tier |
|---|---|---|
| Simon Willison | https://simonwillison.net/atom/everything/ | community |

Hacker News is fetched by `catchup-hn` rather than a feed, so it needs no row here — the
Algolia API supports the window and score filters that `news.ycombinator.com/rss` does not.

## Research

Fetched by `catchup-arxiv`, not from this table. Categories default to `cs.AI`, `cs.LG`,
`cs.CL`; override with `catchup-arxiv search --query cs.CV`. Hugging Face daily papers is
included automatically, and its upvote count is a useful relevance signal.

## Adding a source

1. Add a row above with the feed URL and a tier.
2. Check it: `uv run catchup-feeds search --days 14 --format table`.
3. If a source has no feed, it needs a fetcher in `src/catchup/sources/` and a shim under
   `.agents/skills/`. Anything requiring HTML scraping is Ask-first — check `robots.txt`.

A feed that fails is logged, skipped, and named in the run record. It never aborts a run,
so a rotted URL degrades coverage quietly — check the footer of the digest.
