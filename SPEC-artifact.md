# Spec: `artifact`

Module id `artifact` in `CAPABILITY-MAP.md`. Depends on `scrape`. Project-wide stack,
commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Turn a scored, gated collection into a digest page that is genuinely pleasant to read,
publish it as a Claude Artifact, and leave a local trail linking to it.

This is the only part of the system the user actually looks at. Everything upstream exists
to make sure what lands here is worth reading.

## Composition

Written to `artifacts/<period_end>-ai-news.html`, then published. **Load the
`artifact-design` skill before writing the file** — it calibrates the design work — and
`artifact-diagramming` only if a run genuinely warrants a diagram.

Structure, in order:

1. **Header** — the window as explicit dates, item count, generated timestamp.
2. **TLDR** — three to five bullets, each a claim about the period drawn from the items
   together. Written last, from the items, never from a template.
3. **Items, grouped by category** — models and releases, research, tooling, industry,
   policy. An empty category is omitted, not shown empty.
4. **Also noticed** — one-line mentions of items that scored just below the cutoff.
5. **Footer** — sources consulted, sources skipped, item counts through the gates.

Per item:

| Element | Rule |
|---|---|
| Title | Links to the original. Never rewritten into a headline the source did not write |
| Source and date | Both shown. The date is the item's, not the run's |
| Summary | 2–3 sentences, factual, no adjectives the source did not earn |
| The bottleneck | What was blocking this, and what is now unblocked. A concrete limit |
| Why it matters | The consequence — the value the digest adds over a feed reader |
| The trend | What this connects to, across items or across periods |

**This structure is fixed and does not vary with the topics chosen at `/setup`.** Topics,
sources, and window are configuration; the TLDR and the three per-item lines are the
product.

Two rules keep it honest:

- **Bottleneck and why-it-matters are an and/or pair; at least one must be present.** A
  technical advance leads with the bottleneck, because that names what was previously
  impractical. An IPO, a lawsuit, or an outage is news without being a breakthrough and
  gets why-it-matters alone — manufacturing a bottleneck for it produces exactly the
  confident filler the gates exist to keep out.
- **The trend line is skippable.** A trend asserted from one data point is a guess. Prefer
  connections the reader can check, ideally to another item in the same digest.

The footer is not decoration. A digest that says "12 items from 11 sources, 2 sources
skipped" is honest about its own coverage in a way an unqualified list is not.

`05-digest-design.md` holds the category names, their order, and the voice notes, so
changing how the digest *reads* is a config edit. Changing what every entry must *answer*
is a spec change, which is this file.

## Publishing

- **One artifact per run**, titled `AI News <period_end>` — a name, not a summary.
- Favicon set on first publish and never changed thereafter.
- A one-sentence `description` for the gallery card.
- Theme-aware: the full light palette on bare `:root`, overrides under both
  `prefers-color-scheme: dark` and `[data-theme="dark"]`, explicit `body` background.
- Responsive; any wide element scrolls inside its own container, never the page body.
- No external resources. Everything inlined.

After publishing, append to `artifacts/INDEX.md`:

```markdown
| Period | Items | Published | Link |
|---|---|---|---|
| 2026-08-25 → 2026-09-08 | 11 | 2026-09-08 | https://claude.ai/... |
```

`INDEX.md` is also what step 1 of `/scrape` reads to find the last run, so it is
load-bearing, not just a record.

## Boundaries

**Always** — load `artifact-design` before writing; link every item to its source; show
the window as explicit dates; define colours for both themes; write the TLDR last, from
the items.

**Ask first** — changing the artifact title format (it is how you find runs in the
gallery); switching to a single living artifact.

**Never** — publish on `--dry-run`; publish a collection that failed a gate; rewrite a
title into something the source did not say; invent a bottleneck for an item that
overcame none; assert a trend from a single data point; write a TLDR bullet that
paraphrases one item's title; change an existing artifact's favicon; load an external
script, stylesheet, or font file.

## Success Criteria

1. The published URL renders correctly in light mode, dark mode, and at phone width.
2. Every item title links to a URL that resolved during G3.
3. The footer's counts match the run record.
4. `INDEX.md` has one row per published run, newest last.
5. Changing category order needs only an edit to `05-digest-design.md`.
6. Every item carries a bottleneck line, a why-it-matters line, or both — and no item
   carries a bottleneck line that names no actual prior limit.
