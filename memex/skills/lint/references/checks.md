# Lint Check Definitions

> Referenced from the main lint skill. Execute each category in order and collect findings.

---

## 1. Status Freshness

Read `status.md`. Parse the "Last updated: YYYY-MM-DD" line.

- Calculate the number of days between that date and today.
- **WARN** if more than 3 days old. Include the exact date and day count.
- **PASS** if 3 days or fewer.

If `status.md` doesn't have a "Last updated" line, **WARN** with: "status.md has no Last updated date."

---

## 2. Decision Consistency

Read `decisions.md` in full. Scan for entries where a later entry uses override language referencing an earlier entry. Look for these phrases in newer entries:

- "supersedes"
- "replaces"
- "dropped"
- "no longer"
- "instead of"
- "reverses"
- "overrides"

For each match, check whether the older entry being referenced is annotated with ~~strikethrough~~.

- **WARN** for each unannotated superseded entry. Include both the old and new entry text.
- **PASS** if no unannotated contradictions found.

Do not infer contradictions from topical similarity. Only flag entries where the override relationship is explicit in the text.

---

## 3. Orphan Files

For each domain in the Hub Map:

1. Read the hub index file listed in the Hub Map.
2. Parse the hub's file table to get the list of tracked files (extract filenames from `[[wikilinks]]` in the table).
3. List all `.md` files on disk in that domain's folder (excluding the hub index file itself).
4. Compare the two lists.

- **WARN** for each file on disk that isn't in the hub table. Include the filename and domain.
- **INFO** for each hub entry that points to a file not on disk. Include the wikilink and domain.
- **PASS** if all files match.

Skip the `memory/` and `scratch/` folders. These are Tier 1 and managed by the manifest, not hubs.

---

## 4. Stale Blockers

Read `status.md`. Parse the "## Blocked" section (or "## What's Blocked").

For each blocker item:

1. Read `session-log.md` (all entries, not just the latest).
2. Search for mentions of the blocker text (or close paraphrases) across session-log entries.
3. Count how many sessions mention this blocker without resolving it.

- **WARN** if a blocker appears unchanged across 3 or more session-log entries, or if the blocker has been present for more than 7 days based on session dates.
- **PASS** if no stale blockers found, or if the Blocked section is empty.

If there is no Blocked section or it says "None", **PASS**.

---

## 5. Manifest Consistency

Check structural integrity of `_MANIFEST.md`:

**Hub Map:**
- For each row in the Hub Map table, verify the hub file exists on disk.
- **WARN** for each hub file listed but not found.

**Tier 1 files:**
- For each row in the Tier 1 table, verify the file exists on disk.
- **WARN** for each Tier 1 file listed but not found.

**Tier 3 files:**
- For each row in the Tier 3 table, verify the file exists on disk.
- **INFO** for each Tier 3 file listed but not found (these are lower priority since they're archived).

- **PASS** if all referenced files exist.

---

## Output Format

Use this format for each check category:

```
[CATEGORY NAME]: PASS
```

or:

```
[CATEGORY NAME]: [N] issues
  [WARN] [description] -- fix: [suggested action]
  [INFO] [description] -- fix: [suggested action]
```

End with a summary line:

```
Summary: [N] warnings, [M] info across 5 checks
```
