# Implementation Plan: AI News Catch-up

Built against capability map **revision 3** (`CAPABILITY-MAP.md`), `SPEC.md`,
`SPEC-collect.md`, `SPEC-scrape.md`, and `SPEC-artifact.md`. Tasks live in Linear — see
`tasks/todo.md`.

## Overview

Two Claude Code commands. `/setup` interviews you and writes five markdown config files;
`/scrape` resolves a window, collects from feeds and APIs, validates against hard gates,
ranks what survived against your interests, and publishes a digest as a Claude Artifact.

Nothing is scheduled and nothing is sent. You read the digest before it goes anywhere.

## Architecture Decisions

- **Gates over trust.** Sources return items that are stale, duplicated, or dead-linked,
  and none look wrong on inspection. Collection is validated after the fact — count,
  window, liveness, duplicates — and a failing run publishes nothing. Carried from
  revision 2, where it was the best idea in the spec.
- **Tools decide what can be decided; the model decides the rest.** Fetching,
  normalizing, date parsing, windowing, dedupe, and liveness are tested Python. Ranking,
  summarizing, and composition are the command's job. Anything a tool can settle is never
  left to the model.
- **One gate call, not two implementations.** `catchup-collect` runs G1-G5, and the
  WebSearch pass is piped back through it with `--no-fetch`. Results a model found itself
  get no exemption from the checks everything else passes.
- **Every dependency is injected.** The URL checker and the HTTP client are parameters —
  the seam that makes a deterministic, offline, zero-cost suite possible.
- **Config is markdown.** Scope, sources, window, rubric, and layout are all files you can
  hand-edit. Nothing in the Python assumes AI specifically.
- **Local state, gitignored.** `data/seen.json` and `data/runs/` are per-machine. The one
  exception is `artifacts/INDEX.md`, which is committed because the next run reads it to
  find where the last one ended.

## Sequencing

```
Phase A ── specs + sources + collect ──┐
                                       ├──→ Phase B ── /setup + /scrape ──→ quality checkpoint
                                       │                                          │
                                       └──────────────────────────────────────────┴──→ Phase C ── publish
```

Phases A and B are complete. The checkpoint between B and C is human judgement and is the
one gate a green suite cannot substitute for.

## Task List

**Tasks are tracked in Linear**, project [Catch up AI](https://linear.app/mohamed-dwedar/project/catch-up-ai-75fb6337189f), team MOH.

| # | Task | Linear | Milestone | Status |
|---|---|---|---|---|
| P1 | Rewrite the spec set for revision 3 | MOH-86 | Phase A | ✅ |
| P2 | Source fetchers, `Item` contract, gates | MOH-87 | Phase A | ✅ |
| P3 | `/setup`, `/scrape`, `catchup-collect` | MOH-88 | Phase B | ✅ |
| P4 | **Quality checkpoint** — read a real digest, tune the rubric | MOH-89 | Phase B | ← next |
| P5 | First published artifact | MOH-90 | Phase C | blocked by P4 |
| P6 | Does the WebSearch pass earn its place? | MOH-91 | Phase C | after ~5 runs |

Revision 2's task set (MOH-5 … MOH-24) is cancelled; each issue carries a note saying what
replaced it. MOH-7 (skeleton) and MOH-17 (schedule gate) remain done — the gate is unused
but kept as the seed for optional scheduling.

## Checkpoints

**P4 is the one that matters.** Read a real `/scrape --dry-run` as a reader rather than as
its author, and ask only whether you would want to read it. If the answer is no, the fix is
`01-interests.md` and `04-scoring.md` — never the gates, which decide eligibility rather
than merit.

Building the publish phase on top of a digest nobody wants to read just puts a URL on the
problem, which is why P5 is blocked by P4.

## Definition of Done

Every task also clears `.claude/references/definition-of-done.md`. Two items bite hardest
here: behavior is **verified at runtime**, not merely typechecked, and **no gate threshold
is weakened to make a run pass.**

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Digest quality is simply poor | High — the product does not work | P4 is an explicit human review before any publishing work is built on it |
| A feed rots (Anthropic already has none) | Medium — coverage shrinks quietly | Sources are config; a failure is logged, skipped, and named in the digest footer. WebSearch is the backstop |
| Dates arrive in inconsistent formats | Medium — stale items ship | `feedparser` plus explicit ISO handling; an unparseable date drops its item rather than defaulting to today |
| arXiv volume drowns the signal | Medium — ranking works harder than it should | ~160 items a week with no relevance filter of its own. HF daily papers is upvote-ranked and higher-signal; narrowing categories is a config edit |
| A source's payload gets large | Low | `--compact` for the ranking pass; full text only for the survivors |

## Open Questions

- **Scoring calibration** — the rubric is a first draft and expected to churn. Closed by P4.
- **Whether the WebSearch pass earns its cost** — measurable from `by_origin` in the run
  records. Closed by P6.
- **Scheduling** — `is_run_day` is kept but unused. Revisit once the on-demand flow has
  proved itself.
