# Digest design

The shape of the published artifact. Changing how the digest reads should mean editing
this file, not the command.

## Structure

1. **Header** — the window as explicit dates, item count, generated timestamp.
2. **The lede** — two or three sentences on what actually mattered this period. Written
   last, from the items. Not a template, and not a restatement of the headlines.
3. **Items, grouped by category** — in this order, omitting any category with nothing in
   it (an empty section is worse than no section):
   1. Models and releases
   2. Research
   3. Tooling and agents
   4. Industry and infrastructure
   5. Safety and policy
4. **Also noticed** — one-liners for items that scored just below the cutoff.
5. **Footer** — sources consulted, sources skipped, counts through each gate.

The footer is not decoration. "11 items from 12 sources, 2 skipped" is honest about the
digest's own coverage in a way a bare list is not.

## Per item

| Element | Rule |
|---|---|
| Title | Links to the original. **Never rewritten** into a headline the source did not write |
| Source and date | Both shown. The date is the item's own, not the run's |
| Summary | 2–3 sentences. Factual. No adjective the source did not earn |
| Why it matters | One sentence — the value this adds over a feed reader. If you cannot write one honestly, the item does not belong in the digest |

For an HN item, link the article and note the discussion separately. For a paper, link the
abstract, not the PDF.

## Voice

Plain and specific. Name the thing, say what changed, say why it matters, stop.

- Write "context window goes from 200K to 1M tokens", not "a major leap forward".
- No hype vocabulary: *revolutionary*, *game-changing*, *unprecedented*, *seismic*.
- No hedging filler: *it seems that*, *arguably*, *many are saying*.
- Attribute claims to whoever made them. A vendor's benchmark is a vendor's benchmark.
- Uncertainty is stated, not smoothed over: "no independent evaluation yet" is useful.

## Artifact conventions

- Title `AI News <period_end>` — a name, not a summary. Stable across runs.
- One artifact per run. Never republish over a previous period's URL.
- Theme-aware: full light palette on bare `:root`, overrides under both
  `prefers-color-scheme: dark` and `[data-theme="dark"]`, explicit `body` background.
- Responsive; wide elements scroll inside their own container, never the page body.
- Everything inlined — no external script, stylesheet, or font.
- Favicon set on the first publish of an artifact and never changed after.
