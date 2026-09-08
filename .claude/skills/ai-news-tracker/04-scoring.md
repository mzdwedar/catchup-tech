# Scoring

How `/scrape` ranks what survived the gates. Expect this file to churn — it is a first
draft, and the honest test is whether the digests it produces are worth reading.

## Rubric

Score each item 0–10. Sum the dimensions, then apply the exclusions.

| Dimension | Max | What earns it |
|---|---|---|
| **Topic match** | 4 | 4 for a top-three topic in `01-interests.md`; 2 for anything lower in the list; 0 for adjacent-but-not-listed |
| **Notability** | 3 | 3 for a capability, release, or result; 2 for a substantive technical writeup; 1 for informed analysis; 0 for commentary on commentary |
| **Source tier** | 2 | 2 for `primary` (the org announcing its own work); 1 for `press` or `research`; 1 for `community` with technical depth |
| **Corroboration** | 1 | 1 if the same story reached us from more than one source, or from HN above 100 points |

**Always-surface override:** anything from a lab or person in `01-interests.md`'s
always-surface list floors at 6, so a genuine announcement cannot fall below the cutoff on
topic wording alone.

**Exclusions remove, they do not subtract.** An item matching the exclude list is dropped
regardless of score.

## Cutoff

Take the highest-scoring items down to the target in `03-period.md` (12), never below the
minimum (6) and never above the maximum (18).

Ties break toward: primary source, then earlier publication date, then shorter path to the
underlying artifact (the paper over the writeup about it).

Items scoring 5 or above that miss the cutoff go into **Also noticed** as one-liners —
they are the honest signal that the period had more in it than the digest shows.

## Recording

Every item's score, its dimension breakdown, and the reason it was kept or dropped go to
`data/runs/<period_end>/items.json`. This is what makes a digest you disagree with
diagnosable: you can see what lost and why, rather than guessing at the model's taste.

## Calibration

After a run that reads wrong, change this file — not the gates in `catchup.collect`.
Weakening a gate to make a run pass is explicitly forbidden; changing what counts as
notable is exactly what this file is for.
