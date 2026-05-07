# Memex Source Registry. Shared reference

Conventions shared by `/memex:link-workspace`, `/memex:unlink-workspace`, and
`/memex:cross-search`. CLI surface lives in `memex/scripts/sources.py`
(read its module docstring for subcommand reference).

## Registry file

`~/.memex/sources.md`. Human-readable markdown, one `## <name>` block per
source with `path:`, `registered:`, `searchable:` fields. Local to the
machine. Never transmitted.

## Script path resolution

Skills resolve `sources.py` in this order:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/sources.py`
2. `${CLAUDE_SKILL_DIR}/../../scripts/sources.py`

Invoke with `python3 <path> <subcommand> ...`.

## Searchable / privacy semantics

- New sources default to `searchable: true`.
- `searchable: false` is total opt-out: cross-search skips that source.
- Toggle via `python3 sources.py set-searchable <name> true|false` or by
  editing `~/.memex/sources.md` directly.

## What cross-search reads

Per searchable source:

- `_MANIFEST.md` (top level)
- every `_CLOSETS.md` and `_CLOSETS-archive.md` under the workspace

It does not read individual content files. Closets are the index; content
is the body. Closets format spec: `memex/skills/session-end/references/closets-format.md`.
