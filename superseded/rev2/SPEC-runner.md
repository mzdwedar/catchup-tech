> **Pending revision.** Written under capability map revision 1. Under revision 2 the
> `delivery` module is replaced by `broadcast`: one publish instead of N sends, so the
> per-recipient counts, `already_sent` resume logic, and delivery failure matrix below no
> longer apply. Rewrite tracked as **T14** in `tasks/todo.md`. Everything below is
> revision-1 text.

# Spec: `runner`

Module id `runner` in `CAPABILITY-MAP.md`. Depends on all other modules. Project-wide
stack, commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Be the entry point and the safety layer: decide whether today is a run day, orchestrate
the other four modules in the right order, refuse to double-send, write an auditable run
record, and make sure a failed run reaches a human.

No business logic lives here. If it can be tested without a schedule or a filesystem, it
belongs in another module.

## Order of operations

```
1. Should we run today?      → biweekly check, exit 0 quietly if not
2. Load recipients           → subscribers.load_recipients()
3. Check idempotency         → refuse if this period already completed
4. Generate the digest       → digest.generate_digest()      ← first step that costs money
5. Send                      → delivery.send_digest()
6. Write the run record      → runs/<period_end>.json
7. Exit                      → 0 on success, 1 on abort
```

**Recipients load before the digest is generated, deliberately.** Loading is free and
fails fast on a typo'd roster; generation costs about a dollar. There is no reason to buy
a digest that has nobody to send to.

## The biweekly problem

**GitHub Actions cron cannot express "every two weeks."** Cron has no notion of alternating
weeks — it offers day-of-week, day-of-month, and month, none of which produce a stable
14-day cadence across month boundaries.

The workflow therefore runs **weekly** and the runner decides:

```python
def is_run_day(today: date, anchor: date) -> bool:
    """True on the anchor date and every 14th day after it."""
    return (today - anchor).days % 14 == 0
```

`CATCHUP_ANCHOR_DATE` is set once and never changed casually — changing it shifts the
cadence for everyone. On an off week the runner logs and exits **0**; a skipped week is
not a failure and must not page anyone.

GitHub cron runs in **UTC** and may fire late under load. Neither matters for a biweekly
digest, but the `is_run_day` check uses the UTC date so behavior is consistent.

## CLI

```
uv run python -m catchup.runner [options]

  --dry-run            Generate and render; write .eml files; send nothing.  DEFAULT
  --send               Really send. Also requires CATCHUP_ALLOW_SEND=1
  --period-end DATE    Override the window end (backfill, testing)
  --only EMAIL         Send to this address only, ignoring the roster
  --force              Run even if a completed record exists for this period
  --ignore-schedule    Run even on an off week
```

**`--dry-run` is the default and `--send` needs two independent signals** — the flag plus
the environment variable. A single mistyped flag on a developer machine should not be able
to mail real subscribers. `--only` is how run #1 goes to the operator alone.

## Idempotency and state

GitHub Actions is stateless, so run state lives in the repository. After a successful
send the workflow commits `runs/<period_end>.json` back to the default branch.

This gives idempotency and an audit log from one mechanism. `--send` refuses to proceed if
a record for the period exists with status `completed`, unless `--force` is passed.

Requires `contents: write` permission on the workflow. Dry runs write locally and commit
nothing.

**Run record:**

```json
{
  "run_id": "2026-09-15",
  "period_start": "2026-09-01",
  "period_end": "2026-09-15",
  "status": "completed",
  "generated_at": "2026-09-15T06:03:11Z",
  "item_count": 10,
  "usage": {"web_search_requests": 14, "input_tokens": 182043, "output_tokens": 2611},
  "estimated_cost_usd": 1.19,
  "recipients": {"active": 42, "sent": 41, "hard_bounce": 1, "transient": 0},
  "gate_failures": []
}
```

`status` is one of `completed`, `aborted`, `skipped`. `estimated_cost_usd` is computed
from recorded usage at $10 per 1,000 searches plus the model's token rates — so cost is
visible in the audit log rather than in a billing dashboard.

A resumed run reads the previous record's sent addresses and passes them as
`already_sent` to `delivery`.

## Failure handling and alerting

**Alerting is the exit code.** A non-zero exit fails the workflow, and GitHub emails the
repository owner. Zero infrastructure, and it works on the first run.

| Situation | Exit | Sends | Notify |
|---|---|---|---|
| Off week | 0 | none | no |
| Success | 0 | all active | no |
| Gate abort (`DigestGateError`) | 1 | **none** | yes |
| Roster error | 1 | none | yes |
| Delivery `FATAL` / circuit breaker | 1 | partial | yes |
| Some transient failures, most sent | 0 | most | summary only |
| Already completed, no `--force` | 1 | none | yes |

Every run writes a human-readable summary to `$GITHUB_STEP_SUMMARY`: item count, cost,
recipient counts, and any gate failures. That is what the operator reads first.

**A gate abort sends nothing at all.** Not a partial digest, not a "we found only 4
stories" email. Per `SPEC.md`, sending nothing is always acceptable and sending something
wrong never is.

## Workflows

`.github/workflows/digest.yml` — weekly cron plus `workflow_dispatch` (with `dry_run` and
`only` inputs, so a manual test run is possible from the Actions tab without a checkout).
Secrets: `ANTHROPIC_API_KEY`, the provider key. Permissions: `contents: write`.

`.github/workflows/ci.yml` — on push and PR: `ruff check`, `ruff format --check`,
`ty check`, `pytest --cov`. No secrets, no network; the `live` marker never runs here.

## Interface

```python
@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    period_start: date
    period_end: date
    status: RunStatus
    item_count: int
    usage: Usage
    estimated_cost_usd: float
    recipients: RecipientCounts
    gate_failures: tuple[str, ...]


def execute_run(opts: RunOptions, deps: Dependencies) -> RunRecord:
    """Orchestrate one run. Returns the record; never raises for an expected
    failure — those become status='aborted'."""


def is_run_day(today: date, anchor: date) -> bool: ...
```

`Dependencies` bundles the injected clock, provider, and Anthropic client, so the whole
orchestration is testable with no network and no real date.

## Testing Strategy

Every dependency is injected; the suite exercises orchestration and safety rules only,
with the four other modules faked.

| Test | Asserts |
|---|---|
| `is_run_day` | True on anchor, anchor+14, anchor+28; false on +1, +7, +13. Correct across a month boundary |
| Off week | Exits 0, generates nothing, sends nothing |
| Ordering | Roster error means `generate_digest` is **never called** — asserted with a call counter |
| Gate abort | Zero sends, exit 1, record `status='aborted'` |
| Idempotency | Second `--send` for a completed period refuses; `--force` proceeds |
| Resume | Previously sent addresses passed as `already_sent` |
| `--send` without `CATCHUP_ALLOW_SEND` | Refuses, exit 1, zero sends |
| `--dry-run` default | No flag at all → nothing sent |
| `--only` | Exactly one recipient, roster ignored |
| Cost arithmetic | Known usage produces the expected `estimated_cost_usd` |
| Record round-trip | Written JSON parses back to an equal `RunRecord` |

## Boundaries

**Always** — load recipients before generating; write a run record for every outcome
including aborts; exit non-zero on anything a human must see; inject the clock.

**Ask first** — changing `CATCHUP_ANCHOR_DATE` or the cadence; granting the workflow new
permissions; adding an alerting channel beyond the Actions notification.

**Never** — send on an off week without `--ignore-schedule`; send when a gate aborted;
default to `--send`; put business logic here; commit a run record containing a full email
address.

## Success Criteria

1. `is_run_day` produces exactly 26 run days across a year from any anchor.
2. A gate abort results in zero provider calls — asserted, not assumed.
3. Running `--send` twice for the same period sends once.
4. Every terminal outcome leaves a run record on disk.
5. `--send` is impossible without both the flag and the environment variable.
6. Full suite runs with sockets disabled, no real dates, no real API keys.
7. A failed run produces a GitHub notification and a readable step summary.

## Open Questions

1. **Anchor date** — needed before the first scheduled run. Suggest the date of the first
   successful manual `--send`.
2. **Committing run records to the default branch** puts a bot commit in history every two
   weeks. Alternative is the Actions cache (evicted after 7 days of inactivity — unusable
   at a 14-day cadence) or an external store (new infrastructure). Committing is the
   recommendation; flagging the noise so it is not a surprise.
3. **Opening a GitHub issue on abort**, in addition to the failure email. Nice-to-have,
   trivial to add later.
