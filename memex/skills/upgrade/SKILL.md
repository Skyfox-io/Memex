---
name: upgrade
description: >
  Upgrade an existing Memex workspace to the current major version in one
  command. Use when the user says "upgrade memex", "migrate to v2", "bring
  this workspace up to date", or runs `/memex:upgrade` after pulling a new
  Memex release. Detects the workspace's current state (manifest marker,
  summary-format-version, closets coverage) and orchestrates the right
  subset of `/memex:resummarize`, `/memex:reindex`, and lint, without
  re-running steps that are already current.
argument-hint: "[--dry-run] [--force]"
disable-model-invocation: true
---

# Memex - Upgrade

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format.

Bring a workspace from any older Memex layout to the current one in a single, idempotent pass. The skill is a thin orchestrator over `/memex:resummarize` and `/memex:reindex`; it adds *state detection* (so re-runs are cheap) and *sequencing* (resummarize before reindex so closets entries inherit the v2 summary rules).

For the v1 → v2 upgrade specifically, see [`references/v1-to-v2.md`](references/v1-to-v2.md). For the v2.0 → v2.1 increment, see [`references/v2-to-v2_1.md`](references/v2-to-v2_1.md). Future major versions add their own playbooks under `references/`.

---

## Step 0: Detect workspace, parse arguments

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If the file is missing or has no `<!-- memex-managed` marker, tell the user "Memex isn't managing this workspace yet. Run `/memex:init` to set up." and stop.

Acquire `memory/.upgrade.lock` and check the 24-hour cooldown in `memory/.upgrade-runs.log`. Both follow the shared bulk-write convention. See [`../consolidate/references/locking.md`](../consolidate/references/locking.md).

Parse `$ARGUMENTS`:

- `--dry-run`. Detect state and print the upgrade plan, but do not execute. Skip the lock acquisition.
- `--force`. Re-run every step regardless of state. Useful after a closets format change, or to verify cleanliness.

---

## Step 1: Detect state

Read five signals from the workspace:

1. **Manifest version marker.** `<!-- memex-managed:N.N.N -->` from `_MANIFEST.md`. Compare to the current Memex VERSION. If older or missing, the workspace was scaffolded by an earlier Memex release.
2. **Summary format version.** `<!-- summary-format-version:N -->` from `_MANIFEST.md`. If missing or `< 2`, summaries follow pre-v2 conventions and need `/memex:resummarize`.
3. **Closets coverage.** For each row in the Hub Map, check whether `<hub>/_CLOSETS.md` exists. Count hubs with coverage vs hubs without.
4. **Closets format version.** For each existing `_CLOSETS.md`, read the `<!-- memex-closets:N.N -->` marker. If `< 1.1` *and* the hub has > 30 files, pagination needs to engage.
5. **Memory closets** (2.1+). Check whether `memory/_CLOSETS.md` exists. If missing on a manifest version `< 2.1.0`, this signals a v2.0 → v2.1 migration step.

Build a state report:

```
Memex Upgrade — workspace state

  Manifest version:        <found> (current: <CURRENT>)
  Summary format version:  <found> (current: 2)
  Closets coverage:        <K>/<N> hubs (<P>%)
  Closets format:          <oldest version found> (current: 1.1, paginates >30 files)
  Memory closets:          <present | missing>
```

---

## Step 2: Build the upgrade plan

For each detected state mismatch, queue the right step. Skip steps that are already current unless `--force` was passed.

| Detected state | Action |
|---|---|
| Summary format < 2 OR missing | `/memex:resummarize` (rewrites manifest + hub summaries to the 8-rule format) |
| Any hub missing `_CLOSETS.md` | `/memex:reindex` (backfills missing closets; skips current ones via mtime check) |
| Closets format < 1.1 AND any hub has > 30 files | `/memex:reindex --force` (pagination engages on rewrite) |
| Memory closets missing AND manifest < 2.1.0 | `/memex:reindex --hub memory` (creates `memory/_CLOSETS.md` and seeds entries for Tier 1 files) |
| Manifest version < current | bump the marker to the current version after other steps complete |

The order is fixed: **resummarize first, reindex second.** Reindex reads file content to populate closets entries, and the closets entries follow the same 8 retrieval-tuned summary rules as manifest summaries (see [`../session-end/references/summary-rules.md`](../session-end/references/summary-rules.md)). If summaries were rewritten in this run, closets need to be rewritten with those rules in primary context.

---

## Step 3: Show the plan and confirm (or proceed if `--dry-run`)

Print the plan:

```
Upgrade plan for <workspace>:

  1. /memex:resummarize    — refresh <K> manifest + hub summaries to v2 format
  2. /memex:reindex        — backfill <H> hubs (<F> files) with _CLOSETS.md
  3. Update manifest marker — <old> → <current>

Estimated time: <T> seconds. Proceed? (y/n)
```

If `--dry-run`, stop after printing. Don't execute.

If the user says no, clear the lock and stop.

If yes (or no confirmation needed because `--force`), proceed to Step 4.

---

## Step 4: Execute the plan

For each queued step, invoke the constituent skill and surface its output:

- **resummarize**: invoke `/memex:resummarize`. If it asks "Manifest is already v2-format. Resummarize anyway? (y/n)" because of `--force`, answer y.
- **reindex**: invoke `/memex:reindex` (or `/memex:reindex --force` if pagination needs to engage). Pass `--hub` only if the user limited the scope.
- **Manifest version bump**: edit `<!-- memex-managed:OLD -->` → `<!-- memex-managed:CURRENT -->` in `_MANIFEST.md`. The current version comes from `memex/.claude-plugin/plugin.json` if accessible, otherwise hardcode the value documented in `references/v1-to-v2.md`.

If any step fails, stop and surface the error. Do not roll back. The changes from earlier steps are valid on their own.

---

## Step 5: Verify

Run `/memex:lint` and capture its output. The expected post-upgrade state:

- **Manifest consistency**: PASS
- **Wikilinks**: CLEAN (or pre-existing issues unchanged)
- **Summary format version**: PASS at current version
- **Typed-edge graph integrity**: PASS or pre-existing issues unchanged
- **Stale status / blockers / decisions**: unchanged from before the upgrade

If lint surfaces issues that didn't exist before the upgrade, surface them prominently in the report. They're regressions caused by the upgrade and need user attention.

---

## Step 6: Record the run and report

Append to `memory/.upgrade-runs.log`:

```
YYYY-MM-DDTHH:MM:SS  from=<old-version> to=<current-version> resummarize=<ok|skipped> reindex=<ok|skipped> hubs=<N> files=<K>  status=<ok|partial>
```

Clear `memory/.upgrade.lock`. Output:

```
Memex Upgrade Complete

  From version:    <old> (or "fresh upgrade")
  To version:      <current>

  resummarize:     <ok / skipped — already v2>
  reindex:         <ok — H hubs, F files / skipped — full coverage>
  Manifest marker: <old> → <current>

  Lint:            <PASS / N issues>

Next session-start will load the upgraded workspace at full v2 retrieval quality.
```

If lint surfaced new issues, append:

```
⚠ Post-upgrade lint flagged issues that didn't exist before:
  <issue 1>
  <issue 2>
  ...

Resolve with /memex:lint --fix where applicable, or open the relevant files.
```

---

## Gotchas

- **Idempotent on re-run.** Without `--force`, this skill is a no-op on a workspace that's already current. The state detection in Step 1 catches that and Step 2's plan is empty. Cheap to run defensively after pulling a new Memex release.
- **Compatible mode is not full mode.** A workspace with a `_MANIFEST.md` but no `<!-- memex-managed` marker is in compatible mode (see `/memex:session-start`). Upgrade refuses to operate on those. The user should run `/memex:init` first to opt into full Memex management. This is intentional: silently rewriting summaries on a workspace the user hasn't explicitly opted in to could surprise them.
- **Resummarize → reindex order is load-bearing.** Reindex inherits the 8 summary rules from session-end. If you reindex first and then resummarize, the closets entries are written under the *old* rules and only the manifest summaries get the new rules. Don't reorder unless you also pass `--force` to reindex on a second pass.
- **Manifest marker bump is last.** If any step fails, the marker stays at the old version. A subsequent `/memex:upgrade` will re-detect the work-in-progress state and resume from where the previous run failed.
- **The lock file is shared with `--dry-run`.** Dry-run still acquires the lock (briefly) to prevent two concurrent dry-runs from reading inconsistent state. If a previous upgrade crashed, the lock is honored as stale after 30 minutes. See locking reference.
- **For partial scope, run the constituent skills directly.** This skill always operates on the full workspace. To upgrade just one hub, run `/memex:reindex --hub <name>` directly.
- **Future major versions:** When v3 ships, add a new playbook under `references/v2-to-v3.md` and extend the state detection in Step 1 with whatever signals v3 cares about. The skill's flow stays the same. Only the version-specific knowledge moves.
