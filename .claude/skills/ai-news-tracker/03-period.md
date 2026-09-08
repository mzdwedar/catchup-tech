# Period

Defaults for the window `/scrape` collects over. Override per run with `--days N` or
`--since YYYY-MM-DD`.

| Setting | Value | Notes |
|---|---|---|
| Default lookback | 7 days | Used when there is no previous run to continue from |
| Target items | **none** | No quota. Everything clearing the quality bar is published |
| Quality bar | score ≥ 6 of 10 | The cutoff, defined in `04-scoring.md`. **This is the number to tune** |
| Minimum items | 6 | `MIN_ITEMS`. Below this, G1/G5 abort and nothing is published |

## No item cap, deliberately

Set at setup: *"don't put a limit on the number of items — return all important news."*

That moves the cutoff from a **quota** to a **quality bar**, and the two behave
differently in a way worth knowing about:

- A top-N cutoff forces ranking to discriminate. There are twelve slots, so the twelfth
  item has to beat the thirteenth, every time.
- A quality bar does not. A generous week produces a long digest by design, and nothing
  stops the bar from drifting downward run over run except the bar itself.

So the bar is the thing to watch. If a digest starts feeling padded, **raise the threshold
in `04-scoring.md`** — do not reintroduce a cap, which would just hide the drift.

The two sixes in the table above are unrelated: `MIN_ITEMS` counts *items* and decides
whether a run publishes at all; the quality bar scores *an item* out of ten and decides
whether it appears. They collide only by coincidence.

## Window resolution

`/scrape` resolves the window in this order:

1. `--since` / `--days`, if given.
2. The end date of the last run in `artifacts/INDEX.md` → today.
3. `today - 7 days` → today.

The window is **half-open**, `[start, end)`, so two consecutive runs never both claim the
boundary day. Both bounds are passed to every tool and prompt as explicit ISO dates — the
phrase "the past two weeks" never appears, because the model has no reliable sense of
today's date.

## Cadence

There is no schedule. `/scrape` runs when you type it, and defaulting the window to
"since the last run" means an irregular rhythm loses nothing — a fortnight between runs
simply produces a fortnight's digest, since the window follows the gap rather than the
7-day default.

`src/catchup/runner/schedule.py` holds a biweekly gate from the superseded newsletter
design. It is unused, kept as the seed for optional scheduling later.
