---
description: Define what AI news to follow and over what period — writes the config /scrape reads
argument-hint: "[--section interests|sources|period|scoring|design]"
allowed-tools: Read, Write, Edit, Bash(uv run catchup-feeds:*), Bash(git diff:*), AskUserQuestion, Skill
---

# /setup

Record what you follow, so `/scrape` knows what to collect. Arguments: `$ARGUMENTS`

Load the `ai-news-tracker` skill first — it describes the files, their formats, and how
`02-sources.md` is machine-read.

## Before asking anything

Check what already exists in `.claude/skills/ai-news-tracker/`:

- **No config** (fresh clone): run the full interview below.
- **Config exists, no `--section`**: show a one-screen summary of the current settings and
  ask whether to amend a section, replace one, or start over. **Never overwrite silently**
  — someone hand-edited these files, and that edit is the whole point of them being files.
- **`--section <name>`**: skip to that section only. Touch no other file.

## The interview

One question at a time, using AskUserQuestion where the options are enumerable and plain
prose where they are not. **Write each answer to its file before asking the next
question**, so an interrupted interview leaves usable config rather than nothing.

Order matters — later answers depend on earlier ones.

### 1. Topics → `01-interests.md`

What do they want to hear about? Offer the shipped defaults (frontier models, agents,
tooling, research, open models, compute, safety, policy) as a multi-select, and let them
add their own. **Ask them to rank the top three** — scoring weights the order, so an
unranked list makes every item score the same.

### 2. Who to always follow → `01-interests.md`

Labs, companies, and people whose output should surface even when it scores below the
cutoff. Offer the defaults; ask for additions. Keep this list short — everything on it is
effectively exempt from ranking, so a long list is the same as no ranking at all.

### 3. Sources → `02-sources.md`

Show the shipped defaults grouped by tier and ask what to add or remove. For each addition:

1. Get the feed URL. If they give a site rather than a feed, try `/rss.xml`, `/feed`,
   `/atom.xml`, `/index.xml` before asking them to find it.
2. Verify it: `uv run catchup-feeds search --days 30 --format table` after adding the row.
3. If a site has no feed, say so plainly. It needs a fetcher in `src/catchup/sources/`,
   and anything requiring HTML scraping is Ask-first — check `robots.txt` first.

Add rows to the tables. The parser reads any table row containing a URL, so the format is
forgiving, but keep the columns consistent with what is there for the humans reading it.

### 4. Window and size → `03-period.md`

How far back should a default run look, and how many items make a digest worth reading?
Push back on a target above 18: past that it stops being a catch-up. Push back on a
minimum below 6 too — that is the floor that makes an abort meaningful.

### 5. What to exclude → `01-interests.md`

What they never want to see. Offer the shipped list (funding rounds, listicles,
speculation, reposts, vendor content marketing, personality drama) and ask for additions.
Exclusions **remove** rather than down-rank, so confirm each one is genuinely unwanted
rather than merely low-priority.

### 6. Offer, do not assume

`04-scoring.md` and `05-digest-design.md` ship with working defaults. Mention they exist
and are editable; only walk through them if asked, or if `--section scoring`/`--section
design` was passed.

## Writing the files

- Preserve the existing structure and prose. These files are documentation as much as
  config — replacing a curated table with a bare list loses the notes explaining why a
  source is there.
- Keep the explanatory text. If a section's rationale no longer matches what it holds,
  update the rationale rather than deleting it.
- Where a choice is unusual, write a one-line note saying why. Six months from now that
  note is the difference between an informed edit and a guess.

## Finishing

Show `git diff --stat` for the skill directory so they can see exactly what changed, then
suggest `/scrape --dry-run` as the next step — reading one digest is worth more than any
amount of further configuration.

With `--section`, the diff must show **one** file. If it shows more, something was
overwritten that should not have been.
