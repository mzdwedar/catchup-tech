# Sources

Feeds read by `catchup-feeds`. **Any table row containing a URL is a source** — add one by
adding a row, remove one by deleting the row. No code change, no test update.

Tier is read from any cell reading `primary`, `press`, `community`, or `research`, and
feeds scoring: a primary announcement outranks coverage of it. **`research` is special** —
those rows are APIs rather than RSS, so they are fetched by `catchup-arxiv` and skipped by
the feed parser, which would choke on JSON.

All URLs below were verified reachable on 2026-09-08, with no API key.

## Labs and vendors

| Source | Feed | Tier |
|---|---|---|
| OpenAI | https://openai.com/news/rss.xml | primary |
| Anthropic | https://feeds.feedburner.com/anthropic | primary |
| Google DeepMind | https://deepmind.google/blog/rss.xml | primary |
| Google AI | https://blog.google/technology/ai/rss/ | primary |
| Hugging Face | https://huggingface.co/blog/feed.xml | primary |

**The Anthropic row is a third-party mirror, not a first-party feed.** `anthropic.com/rss.xml`
and `/news/rss.xml` both 404 — Anthropic publishes no RSS. The URL above is an
[openrss.org](https://openrss.org) scrape of `anthropic.com/news` that answers 200 with ten
dated items, verified to include announcements the previous run could only reach by web
search. Two caveats worth remembering when it eventually breaks:

- It is unowned by Anthropic and can rot without notice. A dead feed is logged, skipped,
  and named in the digest footer — check there before assuming Anthropic went quiet.
- It carries only **ten items**. A fortnight with more than ten Anthropic posts loses the
  oldest, so the WebSearch pass still matters for long windows.

## Press

| Source | Feed | Tier |
|---|---|---|
| The Verge AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml | press |
| Ars Technica AI | https://arstechnica.com/ai/feed/ | press |
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/feed/ | press |

## Analysis and business

Added for the *AI inference*, *compute and infrastructure*, and *AI in business context*
topics, which the press feeds above cover only incidentally.

| Source | Feed | Tier |
|---|---|---|
| SemiAnalysis | https://newsletter.semianalysis.com/feed | press |
| Stratechery | https://stratechery.com/feed/ | press |

**Note the SemiAnalysis URL.** The obvious one — `semianalysis.com/feed/` — answers 200
with ten well-formed, correctly dated entries, and is a **year stale**: its newest post is
16 September 2025. SemiAnalysis moved to a Substack-backed newsletter and left the old feed
serving. A feed that is alive but abandoned is worse than a 404, because every automated
check passes and the window gate silently drops everything. The URL above is the live one;
if SemiAnalysis stops appearing, check the newest date in the feed before assuming a quiet
quarter.

**Requested but not added, because they do not work:**

| Source | Why not |
|---|---|
| Reuters | Every RSS path returns 401 or a JavaScript challenge — `reuters.com/technology/rss`, `/rssfeed/technology`, and the retired `feeds.reuters.com` were all tried. Reuters has withdrawn public RSS |
| The Information | `theinformation.com/feed` returns 403 to any client, browser user-agent included. Paywalled, and scraping it would be Ask-first anyway |

Both are covered indirectly: their stories are typically picked up by the press feeds
above and by Hacker News within a day, and the WebSearch pass can reach them by name.

## Community

| Source | Feed | Tier |
|---|---|---|
| Simon Willison | https://simonwillison.net/atom/everything/ | community |

Hacker News is fetched by `catchup-hn` rather than a feed, so it needs no row here — the
Algolia API supports the window and score filters that `news.ycombinator.com/rss` does not.

## Research

| Source | Endpoint | Tier |
|---|---|---|
| Hugging Face daily papers | https://huggingface.co/api/daily_papers | research |

**Raw arXiv was removed at setup on 2026-09-08.** In the first real run, arXiv contributed
100 of 477 collected items and *none* of the published ones. It has no relevance ranking of
its own, so a hundred recent `cs.AI` preprints arrive as undifferentiated volume for the
scoring pass to sort out. Hugging Face daily papers covers the same ground with a community
upvote signal attached, and supplied both papers that made the last cut.

To put arXiv back, add its row — nothing else changes:

```
| arXiv | https://export.arxiv.org/api/query | research |
```

Categories default to `cs.AI`, `cs.LG`, `cs.CL`; override with
`catchup-arxiv search --query cs.CV`. Note arXiv **must** be queried over https: plain http
returns an empty body rather than an error, which looks exactly like a quiet week.

## Adding a source

1. Add a row above with the feed URL and a tier.
2. Check it: `uv run catchup-feeds search --days 30 --format table`.
3. If a site has no feed, it needs a fetcher in `src/catchup/sources/` and a shim under
   `.agents/skills/`. Anything requiring HTML scraping is Ask-first — check `robots.txt`.

A feed that fails is logged, skipped, and named in the run record. It never aborts a run,
so a rotted URL degrades coverage quietly — check the footer of the digest.
