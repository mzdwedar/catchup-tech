# catchup-tech

Catch up on AI news on demand. You say what to follow; two commands go and get it and hand
you back a readable digest as a Claude Artifact.

```
/setup      # what do you follow, and over what period?
/scrape     # go get it → an artifact URL
```

No newsletter, no subscribers, no schedule. It runs when you type it.

## How it works

**Deterministic tools** fetch from RSS/Atom feeds, Hacker News, arXiv, and Hugging Face
papers; normalize everything to one shape; parse publication dates; filter to the window;
deduplicate; and check that links resolve. Free, offline-testable, no API keys.

**Claude** does the judgement: ranking against your interests, writing each summary and
its *why it matters* line, and composing the artifact — plus a web-search pass for stories
no configured feed carries.

Anything a tool can decide is never left to the model.

### The gates

Sources return items that are stale, duplicated, or pointing at a dead page, and none of
them look wrong on inspection. Collecting is easy; refusing is the job.

| Gate | Rule |
|---|---|
| G1 | At least 6 items collected, or abort |
| G2 | Published inside the window, or drop the item |
| G3 | URL resolves — drop only on 404/410, never on 403/429 |
| G4 | No duplicate URL (normalized) and no near-duplicate title |
| G5 | Still at least 6 after G2–G4, or abort |

**Publishing nothing is always an acceptable outcome. Publishing something wrong is not.**
A quiet fortnight ends with a message naming the gate that stopped the run, not with a
thin digest that looks as confident as a good one.

## Getting started

```bash
uv sync --all-extras
uv run pytest                # offline, no network, no keys
```

Then in Claude Code:

```
/setup                       # walk the interview
/scrape --dry-run            # read a digest before publishing one
/scrape                      # publish it
```

`--dry-run` first is worth the extra step: if the digest isn't worth reading, the fix is
in `01-interests.md` and `04-scoring.md`, and it is much cheaper to find that out before
you have a URL.

## Configuring it

Everything you'd want to change is markdown in `.claude/skills/ai-news-tracker/`:

| File | Holds |
|---|---|
| `01-interests.md` | Topics, who to always follow, what to exclude |
| `02-sources.md` | The feed list |
| `03-period.md` | Default window and digest size |
| `04-scoring.md` | The notability rubric |
| `05-digest-design.md` | Layout and voice |

Adding a source is adding a table row — any row with a URL in it becomes a source. Then:

```bash
uv run catchup-feeds search --days 14 --format table
```

Scope is config, not code: nothing in the Python assumes AI specifically, so widening to
broader tech is an edit to `01-interests.md`.

## The tools, run directly

```bash
uv run catchup-collect --days 14 --compact       # everything, gated
uv run catchup-feeds  search --days 14 --format table
uv run catchup-hn     search --days 14 --format json
uv run catchup-arxiv  search --days 14 --query cs.CV
```

Each takes `--days N` or `--since DATE --until DATE`, and prints `json`, `table`, or
`plain`. This is how you find out why a digest looked thin.

## Notes on the sources

All defaults are reachable with no API key. Two things worth knowing, both found the hard
way and both now covered by tests:

- **Anthropic publishes no RSS feed.** `anthropic.com/rss.xml` 404s. Anthropic news is
  covered by `/scrape`'s web-search pass instead.
- **arXiv must be queried over https** — plain http returns an empty body rather than an
  error, which looks exactly like a quiet week.

## Layout

```
.claude/commands/          /setup and /scrape
.claude/skills/            configuration
.agents/skills/            source tools, discovered by path
src/catchup/               fetchers, gates, the pipeline CLI
artifacts/INDEX.md         published digests, newest last
data/                      run records and the seen ledger (gitignored)
```

Design decisions and their reasoning are in `SPEC.md` and the per-module specs;
`superseded/` keeps the earlier email-newsletter design and explains what changed.
