# Interests

What `/scrape` looks for and what it ignores. Edit freely — this file is the single
source of truth for scope, and nothing in the code assumes AI specifically.

Update interactively with `/setup --section interests`.

## Topics

Ordered by how much you care. Scoring uses the order, so the ranking is not decorative.

| # | Topic | Keywords |
|---|---|---|
| 1 | Breakthroughs in models and their applications | breakthrough, state of the art, first to, previously impossible, capability jump, new architecture, solves, milestone, outperforms |
| 2 | AI inference | inference, latency, throughput, tokens per second, cost per token, serving, batching, KV cache, quantization, distillation |
| 3 | Frontier models and releases | model release, context window, benchmark, multimodal, reasoning model, frontier |
| 4 | AI in business context | adoption, deployment, enterprise, revenue, market, acquisition, partnership, pricing, procurement, what it replaced |
| 5 | Compute and infrastructure | accelerator, GPU, datacenter, capacity, memory bandwidth, interconnect, supply |
| 6 | Open models | open weights, license, fine-tuning, local inference, self-hosted |
| 7 | Safety and alignment | alignment, red-team, jailbreak, incident, containment, model card, evaluation |
| 8 | Policy and regulation | AI act, export control, copyright ruling, standard, ruling, settlement |

**On the top three.** Both offered rankings were chosen at setup. They agreed on
breakthroughs first and inference in the top three, and split on whether frontier releases
or business context took the third slot — so inference, present in both, takes second and
the two contested topics follow. If a digest reads wrong, this order is the first thing to
change.

**Breakthroughs is the load-bearing topic**, named twice at setup, and it is what
`05-digest-design.md`'s bottleneck line exists to serve: an item earns its place by
clearing a limit that was real, not by being announced. Prefer the item that says what is
now possible over the item that says something shipped.

**Not followed, deliberately.** Agents and tool use, developer tooling, and research as a
category were all offered and declined. This does not mean an agent story never appears —
a genuine agent breakthrough scores under *breakthroughs*, and a containment failure
scores under *safety*. It means "an agent framework changed its API" is not news here.
Papers reach the digest as breakthroughs or not at all, which is also why raw arXiv was
dropped as a source.

**"Applications" is part of the topic, not a separate one.** A capability that only exists
in a benchmark is half a story; what it is being used for is the other half.

## Always surface

Anything from these, even if it scores below the cutoff on topic match alone.

**Frontier labs:** Anthropic, OpenAI, Google DeepMind, Meta AI, xAI

**Open-weights labs:** Qwen, DeepSeek, Mistral

**Silicon:** NVIDIA

**People:** Simon Willison

Trimmed from a longer list at setup. Everything here bypasses ranking, so length is the
enemy: a list of thirty is the same as no ranking at all. Hugging Face came off the
always-surface list — it is still a `primary` source and still supplies the daily-papers
feed, it just has to earn its place on score now.

The chipmaker and open-weights entries are here because *compute* and *open models* are
both followed topics, and those companies are frequently the primary source for their own
news rather than being covered by press.

## Exclude

Removed outright, not down-ranked.

- Funding rounds, valuations, and share-price commentary, unless the story is about what
  is being built rather than what it is worth
- Listicles: "top N tools", "N prompts that", "N ways AI will"
- Speculation with no artifact behind it — no paper, release, or announcement
- Reposts of an announcement already covered by its primary source this period
- Vendor content marketing dressed as research
- Personality and hiring drama with no technical substance

**On the funding rule and the business topic.** *AI in business context* is a followed
topic while funding rounds are excluded, which looks contradictory and was left standing
deliberately at setup. The caveat on that first rule is what reconciles them: a $3B raise
is excluded, what the money is being spent to build is not. If genuinely useful stories
start disappearing, loosen that caveat rather than deleting the rule — the rule is what
keeps a fortnight of valuation churn out of the digest.

**Vendor customer stories are deliberately *not* excluded.** They were offered as an
exclusion at setup and kept, because deployment stories are the *applications* half of the
first-ranked topic. "Vendor content marketing dressed as research" still goes — the
difference is whether it claims to be a finding.
