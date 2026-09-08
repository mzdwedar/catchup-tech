# Spec: `sources` + `collect`

Module ids `sources` and `collect` in `CAPABILITY-MAP.md`. Project-wide stack, commands,
structure, code style, and global boundaries: `SPEC.md`.

They share a spec because they share the `Item` contract and are meaningless apart:
`sources` produces items, `collect` decides which survive.

## Objective

Turn a list of configured feeds and APIs into a **validated** set of AI-news items
published inside a window.

"Validated" is the whole job. Every source will happily hand back items that are stale,
duplicated, off-topic, or pointing at a dead page, and none of them look wrong on
inspection. This module's real responsibility is refusing to pass along what it cannot
stand behind.

## The `Item` contract

Every source emits the same shape. This is the contract `collect`, `/scrape`, and the
artifact all share — changing it is Ask-first.

```python
@dataclass(frozen=True, slots=True)
class Item:
    title: str
    url: str
    source: str            # "OpenAI Blog", "Hacker News", "arXiv cs.AI"
    published_date: date
    summary: str           # as the source gave it; may be empty
    origin: Origin         # FEED | HN | ARXIV | SEARCH — where it came from
    extra: Mapping[str, str]  # per-source detail: HN points, arXiv authors, …
```

`origin` exists so a run record can answer "how many published items came only from the
WebSearch pass" — one of `SPEC.md`'s open questions, and unanswerable without it.

`extra` is a deliberate escape hatch, so a new source never needs a change to `Item`.
Scoring may read it; the gates never do.

## Sources

Each source is a fetcher in `src/catchup/sources/` plus a thin CLI under
`.agents/skills/<name>/`, following ai-job-search's discovery contract:

```
<tool> search [--days N | --since DATE] [--query Q] [--format json|table|plain]
<tool> detail <url|id>            [--format json|table|plain]
```

`--format json` is the machine contract: a JSON array of `Item` objects with ISO dates.
`table` and `plain` are for driving the tool by hand.

| Tool | Source | Endpoint | Notes |
|---|---|---|---|
| `feed-search` | Everything in `02-sources.md` | Each feed URL | Generic RSS/Atom. The list is config |
| `hn-search` | Hacker News | `https://hn.algolia.com/api/v1/search_by_date` | **`numericFilters=created_at_i>N` must be URL-encoded** or the API returns 400. Verified 2026-09-08 |
| `arxiv-search` | arXiv, HF daily papers | `https://export.arxiv.org/api/query`, `https://huggingface.co/api/daily_papers` | arXiv **must** be https — plain http returns an empty body |

No source needs an API key. All were verified reachable on 2026-09-08.

**Anthropic publishes no first-party RSS** (`anthropic.com/rss.xml` and `/news/rss.xml`
both 404). A FeedBurner mirror answers 200 but is unowned, so it is not a default; the
WebSearch pass in `/scrape` covers Anthropic announcements instead.

### Failure policy

A source that errors, times out, or returns unparseable content is **logged and skipped**.
It never aborts the run. Losing one feed should cost you that feed's items, not the
digest. The run record names every source that was skipped and why, so a permanently dead
feed becomes visible rather than silently shrinking your coverage.

Requests carry a descriptive User-Agent and a 15-second timeout, and sources are fetched
concurrently with a cap.

### Date parsing

The riskiest part of the module, and the reason `feedparser` is a dependency: feeds report
dates as RFC-822, ISO-8601, and several things that are neither, in varying timezones.

**An item whose date cannot be parsed is dropped, never defaulted to today.** Defaulting
would quietly inject stale items into every digest and make G2 useless.

All dates normalize to a UTC `date` before any gate sees them.

## Validation gates

Run in order, after collection, before returning. Each gate either drops items or aborts.
Carried over from revision 2's `digest` module, where they were the best idea in the spec.

| Gate | Rule | On failure |
|---|---|---|
| **G1 – count** | ≥ `MIN_ITEMS` (default 6) collected | Abort |
| **G2 – window** | `published_date` inside `[start, end)` | Drop the item |
| **G3 – liveness** | `HEAD` (falling back to `GET`) each URL, 10s timeout, ≤5 concurrent | Drop **only** on `404`/`410` or connection failure |
| **G4 – duplicates** | No repeated URL; no two titles with >0.9 similarity | Drop the later item |
| **G5 – recount** | After G2–G4, count still ≥ `MIN_ITEMS` | Abort |

**G3 deserves its explicit rule.** A `403` or `429` is bot protection, not evidence that
the page is missing — Cloudflare-fronted sites return them routinely to a `HEAD`.
Dropping on `403` would silently gut the digest of exactly the mainstream sources it
should contain.

**G4's URL comparison is normalized** before matching: scheme and host lowercased,
trailing slash stripped, and tracking parameters (`utm_*`, `ref`, `source`) removed. The
same story reaching you from a feed and from HN otherwise survives as two items.

Aborts raise `GateError`, which carries the gate id and the item counts before and after
each stage, so the failure message says *why* rather than just *no*.

## The seen ledger

`data/seen.json` maps a normalized URL to the run that published it. `/scrape` drops
anything already there unless `--include-seen`, so consecutive runs over overlapping
windows do not repeat themselves.

Written only after a successful publish — a dry run or an aborted run leaves it untouched,
so a failed attempt never burns an item.

## Interface

```python
def collect(
    sources: Sequence[Fetcher],
    window: DateRange,
    seen: SeenLedger,
    cfg: CollectConfig,
    check_url: UrlChecker,
) -> Collection:
    """Fetch, merge, gate. Raises GateError if G1 or G5 aborts."""


@dataclass(frozen=True, slots=True)
class Collection:
    window: DateRange
    items: tuple[Item, ...]
    skipped_sources: tuple[SourceFailure, ...]
    gate_counts: Mapping[str, GateCount]   # per gate: before, after
```

`check_url` is injected rather than constructed here — that injection point is what makes
an offline test suite possible.

## Testing Strategy

The default suite makes **zero** network calls.

- **Recorded responses.** One real response per source captured into
  `tests/fixtures/feeds/`, then replayed. Parsing and normalization are tested against
  them deterministically.
- **Hand-built fixtures for gate edges.** Out-of-window dates, a 403 URL, a 404 URL,
  near-duplicate titles, tracking-parameter twins, an unparseable date, and a thin
  five-item result are constructed directly rather than hunted for in a recording.
- **`@pytest.mark.live`.** One test per source that really fetches. Excluded from CI.

| Test | Asserts |
|---|---|
| Out-of-window item | Dropped by G2 |
| Unparseable date | Dropped, **not** defaulted to today |
| Thin result (5 items) | Raises `GateError`, does not return a short collection |
| URL returning 403 | **Kept** — bot protection is not a dead link |
| URL returning 404 | Dropped |
| Same story via feed and HN | One survives G4 |
| URLs differing only by `?utm_source=` | One survives G4 |
| A source raising / timing out | Logged, skipped, recorded in `skipped_sources`; run continues |
| Item already in the ledger | Dropped, unless `--include-seen` |
| HN filter encoding | `created_at_i>N` is URL-encoded in the request |

Coverage floor for the gates: **95%**.

## Boundaries

**Always** — normalize URLs before comparing; drop an unparseable date; log and skip a
failing source; send a descriptive User-Agent.

**Ask first** — changing `Item`; lowering `MIN_ITEMS`; adding an HTML-scraped source
(check `robots.txt` first); raising the concurrency cap.

**Never** — default a missing date to today; drop on 403/429; abort the run because one
source failed; write the seen ledger on a dry or aborted run.

## Success Criteria

1. `collect()` over recorded fixtures returns identical output across runs.
2. No returned item has a `published_date` outside the window — verified by a property
   test over generated dates, not a single example.
3. A thin result raises `GateError` and returns nothing.
4. The full module suite runs with sockets disabled.
5. Every source tool returns real items when run by hand with `--format json`.
6. Adding a feed to `02-sources.md` requires no Python change.
