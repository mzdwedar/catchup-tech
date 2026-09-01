# Implementation Plan: Biweekly Tech Digest

Built against capability map **revision 2** (`CAPABILITY-MAP.md`), `SPEC.md`, and
`SPEC-digest.md`. Tasks live in `tasks/todo.md`.

## Overview

A Python job on a GitHub Actions cron that, every two weeks, asks Claude to find notable
tech news from the trailing 14 days using the `web_search` server tool, validates the
result against hard gates, composes it into an email body, and publishes a single
broadcast to a hosted newsletter platform. The platform owns the subscriber list, signup,
double opt-in, unsubscribe, bounces, and fan-out. We own generation, composition,
scheduling, and the gates that decide whether anything gets sent at all.

## Architecture Decisions

- **Gates over trust.** Search-based generation is non-deterministic and `page_age` is
  approximate, so the digest is validated after generation — item count, date window, URL
  liveness, duplicates — and a failing run publishes nothing. Sending nothing is always
  acceptable; sending something wrong never is.
- **Every dependency is injected.** The Anthropic client, the platform adapter, the URL
  checker, and the clock are all parameters. This is the single decision that makes a
  deterministic, offline, zero-cost test suite possible.
- **Recorded API responses, not live calls, drive CI.** `pytest-socket` enforces it.
  Live calls sit behind an opt-in marker.
- **The platform owns subscriber identity.** No database, no web service, no email
  addresses in this repository, in run records, or in logs.
- **Run state lives in the repo.** The workflow commits `runs/<period_end>.json` back to
  the default branch, giving idempotency and an audit log from one mechanism. The Actions
  cache cannot do this — it evicts after 7 days and the cadence is 14.
- **GitHub cron cannot express "every two weeks."** The workflow runs weekly and
  `is_run_day(today, anchor)` decides, exiting 0 quietly on off weeks.

## Sequencing

Two spikes come first because both can invalidate design work that would otherwise be
written on top of them:

```
T1 platform spike ─────┬──→ T8  rewrite SPEC-render.md ──→ T9,T10  render
                       └──→ T11 write SPEC-broadcast.md ──→ T12,T13 broadcast
T2 structured-output spike ──→ T4,T5,T6,T7 digest
T3 skeleton ───────────────→ everything
                                                    all ──→ T14…T18 runner ──→ T19,T20 launch
```

T1 and T2 are independent and can run in parallel. Everything after T3 follows the
`digest → render → broadcast → runner` build order.

Each phase is a vertical slice that leaves something observable: a digest you can read in
your terminal, an email body you can open in a browser, a broadcast that arrives in your
own inbox, then the same thing on a schedule.

## Task List

**Tasks are tracked in Linear**, project [Catch up AI](https://linear.app/mohamed-dwedar/project/catch-up-ai-75fb6337189f), team MOH. Phases are Linear project milestones. Dependencies are encoded as Linear "blocked by" relations, so the tracker itself shows what is startable.

This section is the ordered index; the tracker holds acceptance criteria and verification steps.

| # | Task | Linear | Milestone | Blocked by |
|---|---|---|---|---|
| T1 | Spike — newsletter platform capabilities | MOH-5 | Phase 0 | — |
| T2 | Spike — structured outputs alongside web_search | MOH-6 | Phase 0 | — |
| T3 | Project skeleton, tooling, and CI ✅ | MOH-7 | Phase 1 | — |
| T4 | Digest model, JSON schema, response parsing | MOH-8 | Phase 2 | T2, T3 |
| T5 | Validation gates G1–G5 | MOH-11 | Phase 2 | T4 |
| T6 | Generation orchestration and API edge cases | MOH-14 | Phase 2 | T5 |
| T7 | Prompt file and --print CLI | MOH-18 | Phase 2 | T6 |
| T8 | Rewrite SPEC-render.md for revision 2 | MOH-9 | Phase 3 | T1 |
| T9 | Render implementation and golden fixtures | MOH-12 | Phase 3 | T8 |
| T10 | Escaping and URL-scheme hardening | MOH-15 | Phase 3 | T9 |
| T11 | Write SPEC-broadcast.md | MOH-10 | Phase 4 | T1 |
| T12 | Platform port, adapter, and fake | MOH-16 | Phase 4 | T11, T9 |
| T13 | Preflight checks and dry-run publishing | MOH-19 | Phase 4 | T12 |
| T14 | Rewrite SPEC-runner.md for revision 2 | MOH-13 | Phase 5 | T11 |
| T15 | Schedule gate, CLI, and send guards | MOH-17 | Phase 5 | T14, T3 |
| T16 | Orchestration and run record | MOH-20 | Phase 5 | T15, T13, T7 |
| T17 | Idempotency and record persistence | MOH-21 | Phase 5 | T16 |
| T18 | GitHub Actions workflows | MOH-22 | Phase 5 | T17 |
| T19 | First real send and schedule enablement | MOH-23 | Phase 6 | T18 |
| T20 | README and operator runbook | MOH-24 | Phase 6 | T19 |

## Checkpoints

Linear milestones carry each phase's exit criteria in their descriptions. The two that are
human judgement rather than a green suite:

- **After Phase 2 (Digest):** a human reads a real digest and decides whether it is worth
  reading *before* any packaging work is built on top of it. If the content is poor, the
  remaining phases are packaging for something nobody wants — iterate on
  `prompts/digest.md` here, not later.
- **After Phase 3 (Render):** view the body in Gmail web, Gmail mobile, and Apple Mail.
  Cheap, and catches what no unit test will.

## Definition of Done

Every task also clears `.claude/references/definition-of-done.md`. Two items from it bite
hardest here and are worth restating: behavior is **verified at runtime**, not merely
typechecked, and **no gate threshold is weakened to make a run pass**.

## Parallelization

- **Parallel:** T1 and T2. Also T9/T10 (render) against T12/T13 (broadcast), once T8 and
  T11 have fixed their contracts.
- **Sequential:** everything inside `digest` — T4 → T5 → T6 → T7 is a dependency chain.
- **Needs coordination:** T8 and T11 define the contract between `render` and `broadcast`.
  Settle both before parallelizing the implementations.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Structured outputs reject `web_search` citations | High — reshapes `digest` | T2 spike before any digest code. Documented two-pass fallback at ~$2/run instead of ~$1 |
| Platform lacks a hosted signup page or takes only markdown | High — reshapes `render` | T1 spike before any render code. A markdown-only platform simplifies `render` substantially but costs design control |
| Model invents `published_date` | Medium — stale items ship | Gate G2 drops them; if it proves systematic, fall back to fetching page metadata |
| Search variance makes prompt iteration unmeasurable | Medium — slow tuning | Replay a fixed recording when iterating on wording, isolating prompt effect from search variance |
| Digest quality is simply poor | Medium — the product does not work | Checkpoint B is an explicit human quality review before any downstream work is built on it |
| Cost creeps as `max_uses` rises | Low | Cost recorded per run; raising the cap is Ask-first |
| Vendor holds the subscriber list | Low | Periodic CSV export, added in T20's runbook |

## Open Questions

- **Which platform**, verified rather than expected — closed by T1.
- **Anchor date** for the biweekly cadence — needed before T18. Suggest the date of the
  first successful manual send.
- **Editorial scope** of "tech news" — deliberately left to prompt iteration in T7.
