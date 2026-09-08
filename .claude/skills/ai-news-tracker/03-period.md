# Period

Defaults for the window `/scrape` collects over. Override per run with `--days N` or
`--since YYYY-MM-DD`.

| Setting | Value | Notes |
|---|---|---|
| Default lookback | 14 days | Used when there is no previous run to continue from |
| Target items | 12 | The scoring cutoff aims here |
| Minimum items | 6 | `MIN_ITEMS`. Below this, G1/G5 abort and nothing is published |
| Maximum items | 18 | A digest longer than this stops being a catch-up |

## Window resolution

`/scrape` resolves the window in this order:

1. `--since` / `--days`, if given.
2. The end date of the last run in `artifacts/INDEX.md` → today.
3. `today - 14 days` → today.

The window is **half-open**, `[start, end)`, so two consecutive runs never both claim the
boundary day. Both bounds are passed to every tool and prompt as explicit ISO dates — the
phrase "the past two weeks" never appears, because the model has no reliable sense of
today's date.

## Cadence

There is no schedule. `/scrape` runs when you type it, and defaulting the window to
"since the last run" means an irregular rhythm loses nothing.

`src/catchup/runner/schedule.py` holds a biweekly gate from the superseded newsletter
design. It is unused, kept as the seed for optional scheduling later.
