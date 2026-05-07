---
name: add-domain
description: >
  Add a new domain folder with a hub index and wire it into _MANIFEST.md. Use when
  the user says "add a domain", "create a marketing/product/research folder", or runs
  /memex:add-domain. Also use when scan suggests an obvious new cluster of files
  the user wants split out of an existing domain.
argument-hint: "[domain-name]"
disable-model-invocation: true
---

# Memex - Add Domain

**Wikilink rule:** Use `[[filename]]` for every file reference in markdown.

Create a domain folder with a hub index and a closets file, optionally migrate matching files into it, and wire it into `_MANIFEST.md`.

## Step 1: Validate workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If missing: tell the user "No manifest found. Run `/memex:init` first." and stop.

## Step 2: Get the domain name

If `$ARGUMENTS` is set, use it. Otherwise ask. Convert to slug (lowercase, hyphens, no spaces).

## Step 3: Scan for files that belong in this domain

Scan the workspace for existing files about this topic (by content, not filename). If found, list them and ask whether to move them in. On confirmation, move and update `[[wikilinks]]` in other files that referenced the old paths.

## Step 4: Create the folder and closets file

Create `[domain-name]/` at the workspace root (or inside the established domains parent if existing Hub Map entries use one).

Create `[domain-name]/_CLOSETS.md`. Format and per-entry typed-field schema (`subjects`, `people`, `claims`, `decisions`, `dates`, `status`) are canonical at [`memex/skills/session-end/references/closets-format.md`](../session-end/references/closets-format.md). Per-entry summary fields follow the 8 rules at [`memex/skills/session-end/references/summary-rules.md`](../session-end/references/summary-rules.md). Use `templates/closets.md.tmpl` from the init skill for the file header.

If files were moved in Step 3, add a closets entry per file populated from its content.

### Optional: prose hub index

By default, domains are **closets-only** (the typed-field index handles retrieval). An optional prose `[domain-name]-index.md` can also be created for human-facing context: domain philosophy, "how we work here" preamble, ad-hoc notes that don't fit typed rows. Skipped by default.

If the user explicitly asks for a hub index, or the domain has prose context worth preserving (e.g., a long-form doc migrated from elsewhere), create `[domain-name]/[domain-name]-index.md`:

```markdown
# [Domain Name]

[One sentence describing what this folder contains.]

[Any prose context, philosophy, working agreements specific to this domain.]
```

Drop the file table entirely — the closets file is the source of truth for what's in the domain. Index files exist only for prose context closets can't capture.

## Step 5: Update _MANIFEST.md

Add under **Tier 2 - By Domain**:

```markdown
### [Domain Name]
Closets: [[<domain-name>/_CLOSETS]]
```

(If a prose hub index was also created, add `Hub: [[<domain-name>-index]]` on a second line.)

Add a row to the **Hub Map** with a one-line summary. The wikilink in the Hub column points at whichever file is the primary entry — closets for closets-only domains, the index for domains with prose:

```markdown
| [Domain Name] | [[<domain-name>/_CLOSETS]] | [one-line summary] |
```

If a prose hub index exists, the row format is the legacy `| [Domain Name] | [[<domain-name>-index]] | [...] |`. Both forms are valid; session-start handles either.

## Step 6: Verify wikilinks

Run wikilink verification. Fix any breaks before finishing.

## Step 7: Confirm

```
Domain added: [domain-name]
  Closets:  [domain-name]/_CLOSETS.md
  Hub:      [domain-name]/[domain-name]-index.md (only if created)
  Files moved: [count or "none"]
  Manifest: updated
  Wikilinks: CLEAN
```

---

## Gotchas

- **No manifest = no domain.** If `_MANIFEST.md` is missing, stop and route the user to `/memex:init`. Don't scaffold a half-wired domain.
- **Slugify the input.** "Marketing Strategy" → `marketing-strategy`. Spaces and uppercase break wikilinks and file resolution downstream.
- **Don't duplicate an existing domain.** Before creating, scan the Hub Map for similar slugs (`marketing` vs `marketing-strategy` vs `mkt`). Ask the user whether to merge into the existing domain instead of forking.
- **Domain root location follows existing convention.** If existing Hub Map entries put domains under `domains/<name>/` or `areas/<name>/`, mirror that. Don't drop a new domain at workspace root if siblings live in a parent folder.
- **Moved files keep their wikilinks alive.** Every move triggers a `[[old-name]]` → `[[new-name]]` rewrite across all `.md` files. Skipping this leaves the Obsidian graph broken even though tests pass.
- **Closets entry per moved file is required.** Every file in the domain folder needs a closets entry. Populate from file content, not filename. Closets are the source of truth; the optional prose hub index does not need a corresponding file table.

- **Closets-only by default; prose index only when there's prose to capture.** v2.1+ treats the per-domain `[domain]-index.md` as optional. Skip it unless the domain has working-agreement / philosophy / long-form context that doesn't fit typed rows.
- **Catch-all topics aren't domains.** "miscellaneous", "other", "stuff". Refuse politely and ask the user to name a real subject area.
