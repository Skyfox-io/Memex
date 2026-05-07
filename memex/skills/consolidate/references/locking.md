# Bulk-write locking convention

Shared by `/memex:consolidate`, `/memex:reindex`, `/memex:resummarize`, and `/memex:upgrade`. These four skills do bulk writes across the workspace and can corrupt each other (or themselves) if two run concurrently. They follow the same lock + run-log semantics, with per-skill filenames.

## Filenames

| Skill | Lock | Run log |
| --- | --- | --- |
| consolidate | `memory/.consolidate.lock` | `memory/.consolidate-runs.log` |
| reindex | `memory/.reindex.lock` | `memory/.reindex-runs.log` |
| resummarize | `memory/.resummarize.lock` | `memory/.resummarize-runs.log` |
| upgrade | `memory/.upgrade.lock` | `memory/.upgrade-runs.log` |

These filenames are part of Memex's public surface. Never rename them.

## Lock semantics

At Step 0 (workspace detection), check the skill's lock file:

- **Exists, timestamp < 30 minutes old:** Abort with `"<Skill> already running (lock at <path>). Wait for the running pass or remove the lock if stale."`
- **Exists, timestamp ≥ 30 minutes old:** Treat as stale, overwrite with a fresh lock.
- **Absent:** Write a fresh lock.

Lock contents (one line):

```
2026-05-04T15:42:18  pid=<pid>  agent=<agent-name>
```

Clear the lock at the end of a successful run (Step "Record the run" or equivalent). On error paths, leave the lock. The 30-minute staleness rule will free it on the next attempt.

## Run-log semantics

Append one line per successful run. Format:

```
YYYY-MM-DDTHH:MM:SS  <skill-specific-counts>  status=<ok|partial>
```

Skill-specific counts:

- consolidate: `dedup=<N> contradictions=<M> orphans=<K>`
- reindex: `hubs=<N> files=<K> refreshed=<R> skipped=<S>`
- resummarize: `tier1=<N> hubmap=<M> hubinteriors=<K>`
- upgrade: `from=<old-version> to=<current-version> resummarize=<ok|skipped> reindex=<ok|skipped> hubs=<N> files=<K>`

At Step 0, read the run log. If the most recent successful run was within the last 24 hours AND `--force` was not passed, ask:

> `<Skill>` ran `<time-ago>`. Run again? (y/n)

If no, exit and clear the lock.

## `--force` flag

`--force` skips the 24-hour cooldown prompt. It does not bypass the active lock. That requires manual removal.

Each skill may also use `--force` for skill-specific behavior (e.g., reindex `--force` rebuilds entries even if mtime says they're current). Document those in the skill's own argument-hint and Gotchas.

## `--fix` flag

`--fix` is consolidate's flag for *applying* safe annotations during the read-mostly pass (e.g., auto-supersede a contradiction where one fact is clearly older). Reindex and resummarize don't use `--fix`. They're already write skills.
