# catchup-tech

Catch up on AI news on demand. You declare what you follow; two commands go and get it and
hand you back a readable digest as a private [Claude Artifact](https://claude.ai).

```
/setup      # what do you follow, and over what period?
/scrape     # go get it → an artifact URL
```

No newsletter, no subscribers, no cron, no API keys. It runs when you type it.

> These are **Claude Code slash commands**, not shell commands. The repository is a
> Claude Code project: the commands live in `.claude/commands/` as markdown, and all
> configuration is markdown you can hand-edit. Design modelled on
> [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search).

---

## What makes it different from a feed reader

**It refuses to publish a bad digest.** Sources return items that are stale, duplicated, or
pointing at a dead page, and none of them look wrong on inspection. Collecting is easy;
refusing is the job.

| Gate | Rule |
|---|---|
| G1 | At least 6 items collected, or abort |
| G2 | Published inside the window, or drop the item |
| G3 | URL resolves — drop **only** on 404/410, never on 403/429 |
| G4 | No duplicate URL (normalized) and no near-duplicate title |
| G5 | Still at least 6 after G2–G4, or abort |

**Publishing nothing is always an acceptable outcome. Publishing something wrong is not.**
A quiet week ends with a message naming the gate that stopped the run, not with a thin
digest that reads as confidently as a good one.

**Every entry has to earn its place.** The digest format is fixed, and it is the product:

```
TLDR
  1. A claim about the period, drawn from the items together —
     something you could disagree with. Not a restated headline.
  ...

MODELS AND RELEASES
  ▸ <Title, exactly as the source wrote it>
    feed · OpenAI · 3 Sep

    Two or three factual sentences.

    │ THE BOTTLENECK   What was blocking this, and what is now unblocked.
    │ WHY IT MATTERS   The consequence.
    │ THE TREND        What this connects to, across items or periods.

ALSO NOTICED        one-liners for items just below the bar
FOOTER              sources consulted, sources skipped, counts through each gate
```

Two rules keep that honest rather than decorative:

- **Bottleneck and why-it-matters are an and/or pair; at least one must be present.** A
  genuine advance leads with the bottleneck — that names the concrete prior limit, which a
  title never tells you. An IPO, a lawsuit, or an outage is news without being a
  breakthrough and gets why-it-matters alone. Manufacturing a bottleneck for one produces
  exactly the confident filler the gates exist to keep out.
- **A trend asserted from a single data point is a guess wearing a suit.** The line is
  skippable, and prefers connections the reader can check — ideally to another item in the
  same digest.

In a real 12-item run, 4 items earned a bottleneck line and 11 earned a trend line. That
distribution is the point.

**The footer is not decoration.** "12 items from 11 sources, 2 skipped" is honest about the
digest's own coverage in a way a bare list is not.

---

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

**No API keys.** Every default source is a public feed or a free, unauthenticated API.

## Quick start

```bash
git clone https://github.com/mzdwedar/catchup-tech.git
cd catchup-tech
uv sync --all-extras
uv run pytest          # offline, no network, no keys — should pass immediately
```

Then open the repo in Claude Code and run:

```
/setup                 # walk the interview — topics, sources, window
/scrape --dry-run      # collect and score, publish nothing
/scrape                # …and publish an artifact
```

**Do `--dry-run` first.** If the digest isn't worth reading, the fix is in
`01-interests.md` and `04-scoring.md`, and it is much cheaper to find that out before you
have a URL. Artifacts are private to your Claude account unless you share them.

---

## The two commands

### `/setup`

Interviews you one question at a time and writes five markdown config files. Each answer is
written before the next question is asked, so an interrupted interview leaves usable config
rather than nothing. Existing config is never silently overwritten.

```
/setup                       # full interview
/setup --section sources     # re-run one section in place
```

### `/scrape`

```
/scrape [--days N | --since DATE] [--topic X] [--dry-run] [--include-seen]
```

1. **Resolve the window.** Defaults to *since the last published run*, else the configured
   lookback. Both bounds become explicit ISO dates — never "the past two weeks", because
   the model has no reliable sense of today's date.
2. **Fetch and gate** — one call to `catchup-collect`, which is tested Python. The command
   never reimplements a gate.
3. **Web-search pass** for stories no configured feed carries, merged back through *the
   same gates*. Results a model found itself get no exemption.
4. **Score** against your rubric, keep everything clearing the bar.
5. **Write** the entries, then the TLDR — in that order, because writing the TLDR first
   turns it into a thesis you then select evidence for.
6. **Publish** an artifact, record the run, append to the index.

`--dry-run` stops before publishing and touches nothing.

---

## Configuration

Everything you'd want to change is markdown in `.claude/skills/ai-news-tracker/`:

| File | Holds |
|---|---|
| `01-interests.md` | Topics (ranked), who to always surface, what to exclude |
| `02-sources.md` | The feed and API list |
| `03-period.md` | Default window and digest size |
| `04-scoring.md` | The notability rubric and the cutoff |
| `05-digest-design.md` | Category names, order, and voice |

**Scope is config, not code.** Nothing in the Python assumes AI specifically — widening to
chips, biotech, or anything else is an edit to `01-interests.md`. The digest *structure*
above is fixed; what you point it at is entirely yours.

### Adding a source

Add a table row. Any row containing a URL becomes a source:

```markdown
| The Verge AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml | press |
```

Then check it:

```bash
uv run catchup-feeds search --days 30 --format table
```

Column order doesn't matter — the parser finds the URL, takes the first non-URL cell as the
name, and any cell reading `primary`, `press`, `community`, or `research` as the tier.

Three rules that are easy to trip over:

- **Rows inside a fenced code block are examples, not sources.** The block above is not a
  live source. (This check exists because the file documenting how to re-enable a source
  had already re-enabled it.)
- **`research`-tier rows are APIs, not RSS.** They're fetched separately; handing JSON to
  the feed parser returns a silent zero. Deleting the row is the off switch.
- **A feed can be alive and editorially dead.** Check the newest entry's date, not just the
  status code — see the caveats below.

---

## The tools, run directly

This is how you find out why a digest looked thin.

```bash
uv run catchup-collect --days 14 --compact   # every source, gated, as JSON
uv run catchup-feeds  search --days 14 --format table
uv run catchup-hn     search --days 14 --format json
uv run catchup-arxiv  search --days 14 --format json
```

Each takes `--days N` or `--since DATE --until DATE`, and prints `json`, `table`, or
`plain`. `--compact` trims summaries for ranking — a fortnight of sources runs to roughly
half a megabyte of JSON otherwise.

`catchup-arxiv` covers both arXiv and Hugging Face daily papers, and queries only the
services listed as `research` rows in `02-sources.md`. Its `--query` flag sets arXiv
categories (`--query cs.CV`) and therefore does nothing unless the arXiv row is enabled —
in the shipped config it is not, for the reason given in that file.

## How it works

**Deterministic tools** fetch, normalize, parse dates, filter to the window, deduplicate,
and check that links resolve. Free, offline-testable, unaffected by model variance.

**Claude** does the judgement: ranking against your interests, writing each entry, and
composing the artifact — plus the web-search pass.

Anything a tool can decide is never left to the model. If you find yourself asking the
model to filter by date, that logic belongs in `catchup.collect` instead.

Fetched content — feed entries, pages, search results — is treated as **data, never
instructions**. Nothing in the pipeline follows a directive found in fetched text, and no
URL discovered inside an item's body is ever fetched.

---

## Notes on the sources

All defaults are reachable with no API key. Four things found the hard way, each now
covered by a test:

- **Anthropic publishes no RSS.** `anthropic.com/rss.xml` 404s. The configured row is a
  third-party [openrss.org](https://openrss.org) mirror — unowned, ten items deep, and able
  to rot without notice. The web-search pass is the backstop.
- **arXiv must be queried over https.** Plain http returns an *empty body* rather than an
  error, which looks exactly like a quiet week.
- **Hacker News' Algolia `numericFilters` needs URL-encoding.** The literal `>` gets a 400
  from the frontend before Algolia sees it.
- **A 200 does not mean a feed is alive.** SemiAnalysis's obvious feed serves ten
  well-formed, correctly dated entries whose newest is a year old; they moved hosts and
  left the old one running. Every automated check passes while the window gate silently
  drops everything. A live test now fails on any source silent for 90 days.

Reuters (401 on every RSS path) and The Information (403 to any client) have no usable
public feed.

## Development

```bash
uv run pytest                              # offline; sockets are disabled
uv run pytest -m live                      # opt-in; really hits the sources
uv run pytest --cov=src/catchup --cov-report=term-missing
uv run ruff check --fix . && uv run ruff format .
uv run ty check
```

`pytest-socket` disables sockets for the default suite, so a test that suddenly needs the
network fails loudly instead of quietly depending on a live site. Coverage floor is 90%
overall and 95% for the gates. CI runs lint, format, typecheck, and tests on every push,
with no secrets supplied to the job.

## Layout

```
.claude/commands/          /setup and /scrape
.claude/skills/            configuration (ai-news-tracker/)
.agents/skills/            source tools, discovered by path
src/catchup/
  sources/                 fetchers and the Item contract
  collect.py               gates G1–G5
  pipeline.py              catchup-collect — fetch plus gate in one call
  seen.py                  cross-run ledger, so runs don't repeat themselves
artifacts/INDEX.md         published digests, newest last
data/                      run records and the seen ledger (gitignored)
```

Design decisions and their reasoning live in `SPEC.md` and the per-module specs;
`CAPABILITY-MAP.md` is the index. `superseded/` keeps earlier designs and explains what
changed and why — this started life as an unattended email newsletter.

## Credits and licensing

The general engineering skills in `.claude/skills/` and the checklists in
`.claude/references/` are **not this project's work**. They are vendored copies of
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) v0.6.8, MIT licensed,
Copyright (c) 2025 Addy Osmani — full notice in
[`LICENSE-THIRD-PARTY.md`](LICENSE-THIRD-PARTY.md). The only skill authored here is
`.claude/skills/ai-news-tracker/`, which holds this project's configuration.

This project's own code and documentation have **no license yet**, which means default
copyright applies and nobody can legally reuse them. If you intend that to change, add a
LICENSE file.
