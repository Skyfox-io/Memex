# Legacy Hub-Table Updates

Read when a touched hub has a prose `[domain]-index.md` file with a file table (i.e. it is not a closets-only hub).

For each such hub, update the table:

- Add new files with `[[filename]]` wikilinks, a retrieval-tuned summary, and status.
- Update the status of existing entries.
- Every file in a hub table must have a `[[wikilink]]`.

Closets-only hubs (v2.1+ default) skip this step entirely — closets are the source of truth, and new files land in `_CLOSETS.md` via Step 5c.
