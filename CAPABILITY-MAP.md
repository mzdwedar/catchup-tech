# Capability Map: Biweekly Tech Digest

**Revision 2**, approved 2026-09-01. Supersedes revision 1 (static CSV roster,
per-recipient sending) — see `superseded/README.md`.

This file is the index of what exists. Specs are selected by module id, never by guessing
filenames.

## Initiative

A service that gathers notable tech news from the trailing two weeks and emails a digest
to a self-serve subscriber list. Runs every two weeks, unattended.

## Division of responsibility

**The newsletter platform owns:** the subscriber list, the hosted signup page and
embeddable form, double opt-in confirmation, unsubscribe (link plus `List-Unsubscribe`
headers), bounce and complaint suppression, and the fan-out to subscribers.

**We own:** generating the digest, composing the email body, publishing one broadcast,
scheduling, and the safety gates that decide whether a run sends at all.

## Modules

| Module id | Responsibility | Depends on | Spec |
|---|---|---|---|
| `digest` | Claude + `web_search` over the trailing 14 days → validated structured digest. Owns the prompt file and the validation gates | — | `SPEC-digest.md` |
| `render` | Compose the digest into email body content **once**, not per recipient | `digest` | `SPEC-render.md` (pending revision) |
| `broadcast` | Publish one broadcast to the platform's list; preflight checks; read subscriber count for the run record | `render` | not yet written |
| `runner` | Entry point + GitHub Actions workflow: schedule gate, orchestration, idempotency, run record, alerting | all | `SPEC-runner.md` (pending revision) |

**Build order:** `digest` → `render` → `broadcast` → `runner`

Dependency arrows point one way; there are no cycles. Every module is independently
verifiable: `digest` prints to stdout with no email involved, `broadcast` publishes to a
test list of one.

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| News source | LLM + `web_search` server tool | User decision. Buys coverage of stories no curated feed list would know about |
| Model | Deferred | One config value. Defaults to `claude-opus-5` |
| Subscriber list | Hosted newsletter platform, self-serve signup **and** unsubscribe | No database, no web service, no signup surface to host |
| Platform | Buttondown-style newsletter product, **not** Resend | Resend owns the list but not the signup page — using it would reintroduce the web service this choice exists to avoid. **Unverified; confirmed by the T1 spike** |
| Hosting | GitHub Actions cron, biweekly | 26 runs/year does not justify infrastructure |
| Stack | Python, uv + pytest | Matches the toolchain the repo's installed skills assume |

## Consequences of the revision-2 architecture

| Change | Effect |
|---|---|
| Platform owns fan-out | `render` renders **once**; `Recipient` leaves its signature. Golden tests get simpler and stricter |
| Platform owns bounces | The async-bounce gap flagged in revision 1 is closed — it is the platform's job now |
| Platform owns the list | Real addresses never enter git. The repo-visibility privacy question dissolves |
| One broadcast, not N sends | No rate limiting, retry classification, circuit breaker, or per-recipient resume |
| **Cost:** no per-recipient visibility | We know "published to N subscribers", not who bounced. That lives in the platform dashboard |
| **Cost:** vendor holds the list | Mitigated by a periodic CSV export |

## Risks carried into planning

| Risk | Mitigation | Lives in |
|---|---|---|
| `page_age` is approximate, so out-of-window items slip in | Model returns explicit `published_date`; a gate drops items outside the window | `digest` |
| Search results vary run to run — tests non-deterministic and billed | Recorded API responses replayed in CI; live calls only in an opt-in manual run | `digest` |
| Thin or off-topic results still look confident | Gates on count, window, and URL liveness; the run **aborts and alerts rather than sends** | `digest`, `runner` |
| Structured outputs may not compose with web search citations | Spike before writing the module; documented two-pass fallback | `digest` |
| Platform capabilities assumed, not verified | Spike before writing `render` or `broadcast` | T1 |
