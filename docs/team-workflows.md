# Team Workflows

Memex is designed for individual use, but it works for teams with a few adjustments.

## Shared Workspace

When multiple people work in the same Memex workspace:

### What to share
- **`CLAUDE.md`** - shared identity, voice, and conventions
- **`_MANIFEST.md`** - shared context routing
- **`memory/glossary.md`** - shared terminology
- **`memory/decisions.md`** - shared decision log
- **Domain folders** - shared domain files and hub indexes

### What to keep personal
- **`memory/status.md`** - each person has different priorities and blockers
- **`memory/session-log.md`** - each person's session history is different

### How to handle it

**Option A: Single shared workspace.** Everyone works in the same directory. The session log becomes a team log - entries are tagged with the author's name. Status.md reflects the team's state.

**Option B: Personal status overlays.** Keep personal variants: `memory/status-[name].md` and `memory/session-log-[name].md`.

Option A is simpler. Option B scales better past 3 people.

## Version Control

If the workspace is in a git repository:

```gitignore
# .gitignore additions for Memex

# Option 1: Track everything (recommended for teams)
# (no gitignore entries needed)

# Option 2: Track structure, not session state
memory/status.md
memory/session-log.md
scratch/ideas.md

# Option 3: Track nothing (Memex is local-only)
memory/
scratch/
_MANIFEST.md
```

## Onboarding a New Team Member

1. Clone the workspace (or share the directory)
2. Install the Memex plugin: `/plugin marketplace add Skyfox-io/Memex`
3. They open a new session - the session-start skill briefs them automatically
4. The glossary, decisions log, and hub files give them full context without a 30-minute onboarding call

## Conflict Resolution

If two people update the same file in the same session:

- **`decisions.md`** - append-only, so conflicts are rare. If they occur, keep both entries.
- **`status.md`** - last writer wins. This is fine because status is a snapshot, not a history.
- **Hub files** - merge both changes. Hub tables are additive.
- **`session-log.md`** - both entries go in. Tag with author name if using shared mode.
