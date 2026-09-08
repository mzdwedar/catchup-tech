# Digest design

The shape of the published digest.

**The structure below is fixed.** `/setup` picks the topics, the sources, and the window;
it does not get to renegotiate the template. Whatever you end up following — AI, or
chips, or biotech — a digest opens with its conclusions and every item says what it
unblocked, why it matters, and what it connects to. Those parts are the product.

What *is* configurable: the category names and their order, the target item count
(`03-period.md`), and the voice notes at the bottom of this file.

## Structure

1. **TLDR** — the conclusions, as a list. See below; this is the part most likely to be
   done badly.
2. **Items, grouped by category** — in this order, omitting any category with nothing in
   it (an empty section is worse than no section):
   1. Models and releases
   2. Research
   3. Tooling and agents
   4. Industry and infrastructure
   5. Safety and policy
3. **Also noticed** — one-liners for items that scored just below the cutoff.
4. **Footer** — sources consulted, sources skipped, counts through each gate.

The footer is not decoration. "12 items from 11 sources, 2 skipped" is honest about the
digest's own coverage in a way a bare list is not.

## TLDR — conclusions, not headlines

Three to five bullets. Each one is a **claim about the period**, drawn from the items
together — something a reader could disagree with.

The failure mode is restating headlines with the specifics filed off. A bullet that
paraphrases exactly one item's title is not a conclusion; it is that item, moved.

| Not a conclusion | A conclusion |
|---|---|
| "OpenAI released GPT-6 Astra." | "Both frontier launches this period led on computer use and cybersecurity rather than reasoning scores — the pitch has moved from what a model answers to what it operates." |
| "Nvidia bought Hugging Face." | "The neutral distribution point for open models now belongs to the company selling the hardware they run on." |
| "There were several agent incidents." | "Agent containment failed three separate ways in two weeks, and in each case the gap was procedural rather than technical." |

A period with nothing to conclude gets fewer bullets, not padded ones. Two honest
conclusions beat five manufactured ones.

Write the TLDR **last**, from the items you kept. Writing it first turns it into a thesis
you then select evidence for.

## Per item

| Element | Rule |
|---|---|
| Title | Links to the original. **Never rewritten** into a headline the source did not write |
| Source and date | Both shown. The date is the item's own, not the run's |
| Summary | 2–3 sentences. Factual. No adjective the source did not earn |
| **The bottleneck** | What was blocking this, and what is now unblocked |
| **Why it matters** | The consequence — the value this adds over a feed reader |
| **The trend** | What this connects to, across items or across periods |

### The bottleneck, and when to skip it

For a genuine technical advance, this is the most informative line in the entry, because
it says what was *previously impossible or impractical* — the thing a title never tells
you. Name the concrete limit: a cost, a latency, a context length, a failure rate, a step
that needed a human.

**Not every item has one.** An IPO, a lawsuit, an acquisition, an outage — these are news
without being breakthroughs. Manufacturing a bottleneck for them produces exactly the
confident-sounding filler this digest exists to avoid.

So the rule is: **bottleneck and why-it-matters are an and/or pair, and at least one must
be present.**

- Genuine advance → lead with the bottleneck. Add why-it-matters only if it says something
  the bottleneck did not.
- Business, legal, or incident news → why-it-matters alone.
- Both, when each carries something distinct.

If you can write neither honestly, the item does not belong in the digest. Drop it and
take the next one up.

### The trend, and when to skip it

Connect the item to something larger: another item in the same digest, a direction visible
across recent periods, or a shift the item is evidence of.

**"If any" is load-bearing.** A trend asserted from a single data point is a guess wearing
a suit. Skip the line rather than reach — and prefer connections you can point at, ideally
to another item in this same digest, since those the reader can check.

Two items pointing the same way is a pattern worth naming. One is an anecdote.

## Voice

Plain and specific. Name the thing, say what changed, say why it matters, stop.

- Write "context window goes from 200K to 1M tokens", not "a major leap forward".
- No hype vocabulary: *revolutionary*, *game-changing*, *unprecedented*, *seismic*.
- No hedging filler: *it seems that*, *arguably*, *many are saying*.
- Attribute claims to whoever made them. A vendor's benchmark is a vendor's benchmark.
- Uncertainty is stated, not smoothed over: "no independent evaluation yet" is useful.

For an HN item, link the article and note the discussion separately. For a paper, link the
abstract, not the PDF.

## Artifact conventions

- Title `AI News <period_end>` — a name, not a summary. Stable across runs.
- One artifact per run. Never republish over a previous period's URL.
- Theme-aware: full light palette on bare `:root`, overrides under both
  `prefers-color-scheme: dark` and `[data-theme="dark"]`, explicit `body` background.
- Responsive; wide elements scroll inside their own container, never the page body.
- Everything inlined — no external script, stylesheet, or font beyond Google Fonts.
- Favicon set on the first publish of an artifact and never changed after.
