# Superseded specs

Specs replaced by a later capability map revision. Kept rather than deleted: they record
decisions and the reasoning behind them, which a deletion would throw away.

## Revision 2 → revision 3 (2026-09-08)

`rev2/` holds the specs for the **unattended email newsletter**: a GitHub Actions cron
generated a biweekly digest with Claude + `web_search`, rendered an email body, and
published a broadcast to a hosted newsletter platform.

Revision 3 changes the product, not just the implementation. The digest is now built
**interactively from Claude Code** — `/setup` declares what to follow, `/scrape` goes and
gets it — and published as a **Claude Artifact**. There is no subscriber list, no
newsletter platform, and no unattended send, so the machinery that existed to make an
unattended send safe has nothing left to protect.

| File | Replaced by | Why |
|---|---|---|
| `rev2/CAPABILITY-MAP.md` | `CAPABILITY-MAP.md` rev 3 | `digest → render → broadcast → runner` became `sources → collect → scrape → artifact` |
| `rev2/SPEC.md` | `SPEC.md` rev 3 | Stack, code style, and testing strategy carried over; the objective and boundaries did not |
| `rev2/SPEC-digest.md` | `SPEC-collect.md` | One schema-constrained API call became deterministic source tools plus a WebSearch pass. **Gates G1–G5 survive close to unchanged** — they are the best idea in this file |
| `rev2/SPEC-render.md` | `SPEC-artifact.md` | Email-client compatibility, per-recipient rendering, and plain-text alternates are irrelevant to a web artifact |
| `rev2/SPEC-runner.md` | `SPEC-scrape.md` | The schedule gate, send guards, and double-send idempotency existed because nobody reviewed the output before it reached real inboxes. You now read it before it goes anywhere |

What carried forward verbatim: the toolchain (uv, pytest, ruff, ty), the code style, the
90% coverage floor, `pytest-socket` enforcing an offline suite, and
`src/catchup/runner/schedule.py` — which is unused today but is the seed for optional
scheduling later.

## Revision 1 → revision 2 (2026-09-01)

Approved under revision 1 (static CSV roster, per-recipient sending), replaced when the
initiative moved to a hosted newsletter platform.

| File | Replaced by | Why |
|---|---|---|
| `SPEC-subscribers.md` | the platform | The platform owns the list, signup, double opt-in, and unsubscribe. What remained on our side folded into `broadcast` |
| `SPEC-delivery.md` | `SPEC-broadcast.md` | The platform owns fan-out. Per-recipient sending, rate limiting, retry classification, the circuit breaker, and resume logic were all solving a problem we no longer have |

Both are themselves superseded by revision 3 — the whole delivery half of the initiative
is gone.
