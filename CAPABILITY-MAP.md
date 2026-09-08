# Capability Map: AI News Catch-up

**Revision 3**, approved 2026-09-08. Supersedes revision 2 (unattended email newsletter)
— see `superseded/README.md`.

This file is the index of what exists. Specs are selected by module id, never by guessing
filenames.

## Initiative

A local, interactive system for catching up on AI news. You declare what to follow with
`/setup`, and `/scrape` collects everything published in a window, validates it, and
publishes a readable digest as a Claude Artifact.

Two commands, run when you want them. Nothing is sent to anyone.

## Division of responsibility

**Deterministic tools own:** fetching from feeds and APIs, normalizing to one item shape,
parsing publication dates, filtering to the window, deduplicating, and checking that
links resolve. All free, offline-testable, and unaffected by model variance.

**Claude owns:** judgement. Scoring items against your interests, writing the summary and
the *why it matters* line, grouping, and composing the artifact. Plus a WebSearch pass to
catch stories no configured feed carries.

The split is deliberate: anything a tool can decide is never left to the model.

## Modules

| Module id | Responsibility | Depends on | Spec |
|---|---|---|---|
| `sources` | Fetch from feeds and APIs; normalize to `Item`; parse dates. One thin CLI per source under `.agents/skills/` | — | `SPEC-collect.md` |
| `collect` | Merge source output, apply gates G1–G5, maintain the cross-run seen ledger | `sources` | `SPEC-collect.md` |
| `scrape` | The `/scrape` command: window resolution, parallel fetch, WebSearch pass, scoring, run record | `collect` | `SPEC-scrape.md` |
| `artifact` | Compose and publish the digest artifact; maintain the local index | `scrape` | `SPEC-artifact.md` |
| `setup` | The `/setup` command: interview → the five config files | — | `SPEC-scrape.md` (§ Configuration) |

**Build order:** `sources` → `collect` → `setup` → `scrape` → `artifact`

`setup` depends on nothing and could be built first; it sits after `collect` only because
the config it writes is easier to get right once the fetchers exist to consume it.

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Interface | Claude Code slash commands, config as markdown | Modelled on `MadsLorentzen/ai-job-search`. Every knob is a file you can hand-edit; scope is config, not code |
| Fetching | Source CLI tools **and** a WebSearch pass | Tools give reproducibility and cost nothing; WebSearch covers what no feed carries (Anthropic publishes no RSS) |
| Output | A new Claude Artifact per run, dated | Browsable history in the gallery; a local `INDEX.md` links them |
| Scope | AI-focused, user-configurable | Ships AI defaults; widening to broader tech is a config edit, not a rewrite |
| Cadence | On demand | You read the output before it goes anywhere, so nothing needs to be safe unattended |
| Stack | Python 3.12, uv + pytest | Unchanged from revision 2; the toolchain and CI already exist |
| Source auth | None | Every default source is verified reachable with no API key |

## Consequences of the revision-3 architecture

| Change | Effect |
|---|---|
| A human reads every digest before it is published | The elaborate send-safety machinery disappears: no send guards, no double-send idempotency, no alerting |
| Deterministic tools replace one big API call | The default suite tests real fetch/parse/gate logic offline, instead of replaying recorded model output |
| Config lives in markdown, not Python | Changing what you follow needs no code change and no test update |
| Per-run artifacts | History is browsable, and a bad run is discarded by simply not linking it |
| **Cost:** feeds must be maintained | A feed URL can rot. A dead feed is logged and skipped, never fatal; WebSearch is the safety net |
| **Cost:** coverage is bounded by the source list | Mitigated by the WebSearch pass, which is not bounded by it |

## Risks carried into planning

| Risk | Mitigation | Lives in |
|---|---|---|
| Feeds report dates in inconsistent formats | Tolerant parser with a fixture per source; an unparseable date drops the item rather than defaulting to today | `sources` |
| A source goes away (Anthropic already has no feed) | Sources are config; failures are logged and skipped, never fatal | `sources` |
| Bot protection looks like a dead link | G3 drops only on 404/410 or connection failure — never on 403/429 | `collect` |
| Thin or off-topic results still look confident | G1/G5 abort the run rather than publish a thin digest | `collect` |
| Scoring drifts run to run | The rubric is a reviewable file; `data/runs/` keeps raw and scored items so a bad run is diagnosable | `scrape` |
