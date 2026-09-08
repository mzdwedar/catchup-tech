# Published digests

One row per published run, newest last. `/scrape` appends to this file **and reads it**:
step 1 takes the newest `Period` end as the start of the next window, so a run picks up
where the last one left off.

That makes this file load-bearing rather than a record. Deleting a row does not unpublish
the artifact — it makes the next run re-cover that period.

| Period | Items | Published | Link |
|---|---|---|---|

*No runs yet. `/scrape --dry-run` to see what a digest would contain.*
