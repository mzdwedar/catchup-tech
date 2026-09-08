# Scoring

How `/scrape` ranks what survived the gates. Expect this file to churn — it is a first
draft, and the honest test is whether the digests it produces are worth reading.

## Rubric

Score each item 0–10. Sum the dimensions, then apply the exclusions.

| Dimension | Max | What earns it |
|---|---|---|
| **Topic match** | 4 | 4 for a top-three topic in `01-interests.md`; 2 for anything lower in the list; 0 for adjacent-but-not-listed |
| **Notability** | 3 | 3 for a **cleared limit** — something now possible, cheaper, or faster that was not; 2 for a release or result with no limit named; 1 for informed analysis; 0 for commentary on commentary |
| **Source tier** | 2 | 2 for `primary` (the org announcing its own work); 1 for `press` or `research`; 1 for `community` with technical depth |
| **Corroboration** | 1 | 1 if the same story reached us from more than one source, or from HN above 100 points |

**Notability rewards the bottleneck.** Top marks go to an item you can write
`05-digest-design.md`'s bottleneck line for — one that names a real prior limit. That is
deliberate: *breakthroughs* is the first-ranked topic, and an item that merely shipped is
not the same as an item that unblocked something. If you cannot name what it clears, it
scores 2, not 3.

**Always-surface override:** anything from a lab or company in `01-interests.md`'s
always-surface list floors at 6, so a genuine announcement cannot fall below the bar on
topic wording alone. Note this floors them **exactly at** the bar — they get in, but they
do not outrank anything.

**Exclusions remove, they do not subtract.** An item matching the exclude list is dropped
regardless of score.

## Cutoff — a bar, not a quota

**Publish everything scoring 6 or above. There is no item cap** (`03-period.md`).

A big week gets a big digest; a quiet week gets a short one. That is the intended
behaviour, and it is why the bar has to hold: with no quota forcing the twelfth item to
beat the thirteenth, nothing stops the threshold drifting downward except attention to it.

| Score | Outcome |
|---|---|
| 6–10 | Published |
| 5 | **Also noticed** — a one-liner. The honest signal that the period held more |
| 0–4 | Dropped, with the reason recorded |

Ordering within a section breaks toward: primary source, then earlier publication date,
then shorter path to the underlying artifact (the paper over the writeup about it).

**If a digest feels padded, raise this number — do not reintroduce a cap.** A cap would
hide the drift rather than fix it, and would start discarding items that genuinely cleared
the bar.

## Recording

Every item's score, its dimension breakdown, and the reason it was kept or dropped go to
`data/runs/<period_end>/items.json`. This is what makes a digest you disagree with
diagnosable: you can see what lost and why, rather than guessing at the model's taste.

## Calibration

After a run that reads wrong, change this file — not the gates in `catchup.collect`.
Weakening a gate to make a run pass is explicitly forbidden; changing what counts as
notable is exactly what this file is for.

Two dials, in the order to reach for them:

1. **The bar (6).** Digest too long or padded → raise it. Too thin while good items sat in
   *Also noticed* → lower it.
2. **The topic order in `01-interests.md`.** Right length, wrong items → the weighting is
   off, not the threshold.
