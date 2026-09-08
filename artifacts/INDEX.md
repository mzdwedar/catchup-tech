# Published digests

One row per published run, newest last. `/scrape` appends to this file **and reads it**:
step 1 takes the newest `Period` end as the start of the next window, so a run picks up
where the last one left off.

That makes this file load-bearing rather than a record. Deleting a row does not unpublish
the artifact — it makes the next run re-cover that period.

| Period | Items | Published | Link |
|---|---|---|---|
| 2026-08-25 → 2026-09-08 | 12 | 2026-09-08 | https://claude.ai/code/artifact/e858e58d-7996-4cf4-9fea-c2fff7de74db |
