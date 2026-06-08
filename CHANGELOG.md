# Changelog

## [2.1.3] - 2026-06-08

Bug fix: wikilink targets containing dots are no longer reported as broken.

### Fixed

- `verify-wikilinks.py` resolved link stems with `os.path.splitext`, which truncated dotted names (`[[v1.2.3]]` → `v1.2`) and falsely flagged them as broken — in both the broken-link and closets checks. Stems now strip only a trailing `.md`, so filenames with internal dots resolve correctly.

## [2.1.2] - 2026-05-07

Skill architecture change: scripts now live in their consuming skill folders.

### Changed

- Each skill that invokes a deterministic helper (`verify-wikilinks.py`, `extract-graph.py`, `sources.py`) ships its own copy at `<skill>/scripts/<script>.py`. Skills resolve scripts via `${CLAUDE_SKILL_DIR}/scripts/<script>.py` — self-contained, no plugin-root traversal. The top-level `memex/scripts/` directory has been removed; tests, CI, and docs reference the owner-skill copies (`wikilinks/`, `lint/`, `cross-search/`). A drift check in `tests/test_scripts.py` keeps mirrors byte-identical.

## [2.1.1] - 2026-05-06

Two changes: drop the unpopulated facts.db sidecar, reframe the benchmark headline.

### Removed

- **`memory/.facts.db` and `/memex:facts`.** The temporal-facts SQLite sidecar shipped in v2.0.0 but never auto-initialized — `/memex:init` and `/memex:upgrade` never bootstrapped the DB, and nothing in the session lifecycle wrote to it. Closets already capture verbatim user-stated facts (`claims:`), decisions (`decisions:`), and dates (`dates:`) on every refresh, and `decisions.md` already records supersession with stronger guarantees (always loaded, always dated, lint-checkable). The unique value the DB layer was supposed to add — contradiction detection — is duplicated by the keyword-explicit decision-supersession check already in `/memex:lint` and `/memex:consolidate`. Result: the feature was theater. Removed:
  - `memex/scripts/facts.py`
  - `memex/skills/facts/`
  - `_search_facts_db()` and the `--facts`/`--no-facts` flags from `sources.py`
  - All facts.db / facts.md / temporal-facts references in `ARCHITECTURE.md`, `README.md`, `memex/README.md`, `CONTRIBUTING.md`, the cross-search/idea/unlink skills, and the v1→v2 upgrade playbook
  - The contradictions-via-facts.py step in `/memex:consolidate`, replaced with a decision-text contradiction sweep that mirrors `/memex:lint --fix`
  - The facts subtests in `tests/test_scripts.py`, replaced with a `search-local` folder-grouping test

  Migration: workspaces with no `.facts.db` are unaffected (most workspaces, since the bootstrap never ran). Workspaces that manually populated facts via `/memex:facts add ...` lose the DB but keep their `memory/facts.md` markdown mirror; no automated export step ships in v2.1.1 because manual users had to write to `facts.md` themselves anyway.

### Changed

- **README headline reframed.** Drops the leaderboard-comparable "90.1% Recall@5 on LongMemEval-S" pull-quote in favor of the actual differentiator: "closets-format index in pure markdown matches full-content keyword search on retrieval recall at roughly 1/10th the size, with zero external dependencies." The 90.1% number stays in `benchmarks/longmemeval/README.md` with full context — what R@5 measures, what the BM25 baseline does, the size argument, and an explicit note that retrieval recall ≠ end-to-end QA accuracy. Anyone who knows the LongMemEval space recognized that the leaderboard measures end-to-end QA with a GPT-4o judge and that R@5 is one stage earlier; the new framing stops conflating the two.
- **`benchmarks/longmemeval/README.md` adds a top-of-file disclaimer.** Explicit on what R@5 is (retrieval), what it isn't (QA accuracy), how the closets-vs-BM25 comparison actually reads ("competitive recall at much smaller index, not 'we beat keyword search'"), and that end-to-end QA accuracy with judge is the right next benchmark.
- **`/memex:consolidate` Step 2 rewritten.** Now scans `decisions.md` for explicit override language (the same keyword set `/memex:lint` uses) and proposes annotating unannotated supersessions with `~~strikethrough~~` + `(superseded YYYY-MM-DD)`. `--fix` applies. Same keyword-explicit detection — no inferential contradictions from topical similarity.
- **`/memex:lint` typed-edge footer no longer routes to `/memex:facts`.** Now suggests `/memex:reindex` to regenerate `memory/.graph.md`.
- **`/memex:idea`, `/memex:unlink-workspace`, `/memex:cross-search`, `/memex:search` descriptions and gotchas** updated to drop facts.db references.
- **`/memex:upgrade` v1→v2 playbook** drops the `memory/.facts.db` row from the state-signals table. v2.0→v2.1 playbook is unchanged.

### For contributors

- `tests/test_scripts.py` drops the three `facts_*` tests and replaces the `sources_search_includes_facts` test with `sources_search_local_groups_by_folder`. Total still 10 tests, all green.
- The "Intentional Non-Features" list in `ARCHITECTURE.md` adds "no database" as a first-class non-feature, with a short note on why facts.db was removed in v2.1.1.

### Roadmap

End-to-end QA accuracy on LongMemEval-S (retrieve → generate → GPT-4o judge) is the right next benchmark. It would produce numbers directly comparable to the LongMemEval leaderboard at the cost of API spend. Not a v2.x deliverable.

## [2.1.0] - 2026-05-06

A lighter, more discoverable v2. Session lifecycle does less. Tier 1 gets typed retrieval. Hub indexes become optional. Cross-hub search lands as its own skill. Decisions compression and graph rebuild move out of session-end and into the bulk-write skills where they belong.

All v2.0 workspaces are forward-compatible. No breaking changes. `/memex:upgrade` handles the v2.0 → v2.1 increment idempotently.

### Added
- **`memory/_CLOSETS.md`.** Typed-field index over Tier 1 files (status, session-log, decisions, glossary, plus user-added Tier 1 entries). Field-level retrieval ("who is X?", "what did the user say about Y?") now hits structured fields on Tier 1 just like hub closets do for Tier 2. Init scaffolds it; `/memex:reindex --hub memory` backfills existing workspaces. Same field semantics as hub closets; never paginates.
- **`/memex:search` skill.** Cross-hub search within a single workspace. Greps `_MANIFEST.md` plus every `_CLOSETS.md` and `_CLOSETS-archive.md` plus `memory/.facts.db`, grouped by folder. Companion to `/memex:cross-search` (which spans linked workspaces). Read-only; never opens content files. Uses the existing `sources.py search-local` plumbing extracted from cross-search.
- **Recently Archived section in primary `_CLOSETS.md`.** When pagination overflows into `_CLOSETS-archive.md`, the primary closets file now appends a list of the 5 most recently demoted file stems (one line each, with subjects fragment + last-touched date). Surfaces archive contents in the always-loaded layer without expanding retrieval surface area.
- **ORPHAN FOLDERS check in `/memex:lint`.** Flags top-level subdirectories with markdown files that aren't registered in the Hub Map. Suggests `/memex:add-domain <name>` per orphan. Skips known infrastructure paths and Memex-managed folders. Brings the orphan check from "files inside known hubs" up to "folders that should be hubs."
- **Decisions compression in `/memex:consolidate`.** Two concrete rules: drop redundant supersession pairs (collapse strikethrough'd entry + its superseder into one summary line) and collapse same-period clusters (≥3 entries in one ISO week with overlapping subjects merge into one entry with sub-bullets, every unique fact preserved). Read-only by default; `--fix` applies.
- **`v2-to-v2_1.md` upgrade playbook.** Documents what changes between v2.0 and v2.1 and the actions `/memex:upgrade` queues. Wired into the upgrade skill.

### Changed
- **Hub indexes are now optional.** `/memex:add-domain` is closets-only by default. The optional `[domain]-index.md` exists for prose context (philosophy, working agreements) that doesn't fit typed rows. Hub Map rows can point at `[[<domain>/_CLOSETS]]` directly. Existing workspaces with index files keep working unchanged; both forms coexist. Session-end skips the hub-table update step for closets-only domains.
- **Session-end is lighter.** Removed: typed-edge graph rebuild, session-lock writes, in-line decisions compression. Kept: status/log/closets updates proportional to touched files. Workspace-wide maintenance (graph rebuild, deep dedup, contradiction sweep, decisions compression) lives in `/memex:reindex` and `/memex:consolidate` and runs on its own cadence. Session-end is unconditional and idempotent.
- **Wikilink suggest at session-end is scoped to session-modified files.** Instead of running a workspace-wide suggest pass at every close, session-end runs `verify-wikilinks.py --suggest --files <touched>` against just the files modified this session. The `--files` flag is new on the script. Workspace-wide suggest stays available via `/memex:wikilinks`.
- **Session-start uses mtime for unclean-close detection.** Compares `status.md` mtime against the most recent workspace `.md` mtime; flags drift if any file is newer than `status.md` by more than 5 minutes. No lock file involved. The 5-minute window absorbs minor clock drift and avoids false positives from session-start's own writes.
- **Session lock removed.** `memory/.session.lock` is gone. Concurrent same-workspace sessions are not a real failure mode for Cowork users; the lock's stale-warning friction outweighed its concurrency value. Bulk-write skills (`/memex:reindex`, `/memex:consolidate`, `/memex:resummarize`, `/memex:upgrade`) keep their locks — those guard real multi-minute write operations.
- **Typed-edge graph refresh is lazy.** `memory/.graph.md` is rewritten by `/memex:reindex` (Step 5) and `/memex:consolidate` (Step 3b). Both are existing skills; the refresh just landed a new home. Session-end nudges the user to run one of them when frontmatter-bearing files change, but doesn't rebuild itself.
- **`/memex:lint` adds memory closets to the COVERAGE check.** Pre-2.1 workspaces are exempt; 2.1+ workspaces without `memory/_CLOSETS.md` get a WARN with the `/memex:reindex --hub memory` suggestion.
- **`/memex:reindex` covers `memory/` as a synthetic hub.** Walks Tier 1 entries from the manifest and writes typed-field entries into `memory/_CLOSETS.md`. The memory hub never paginates (small fixed set).
- **`/memex:reindex` rewrites `memory/.graph.md`.** Step 5 now runs `extract-graph.py` (without `--check`) after the verify pass. Reindex is the regular refresh point for the graph.
- **`/memex:consolidate` rewrites `memory/.graph.md`.** Step 3b runs `extract-graph.py` for both the dangling check and the file rewrite. Both refresh points are independent — running either keeps the graph current.
- **Hub Map column convention updated.** Manifest template now documents both forms (`[[<domain>-index]]` and `[[<domain>/_CLOSETS]]`). Existing rows in either form remain valid.

### Fixed
- **Decisions compression no longer happens at session-end or `/memex:update`.** Both skills are append-only for decisions and surface a one-line nudge if the file approaches the 100-line cap. Compression rules and the `--fix` action live in `/memex:consolidate` only. Closes a long-standing ambiguity where two skills had vague compression guidance and neither did it well.
- **`verify-wikilinks.py --suggest` accepts `--files <list>`.** Scopes the scan to a passed-in subset of files instead of the whole workspace. Used by session-end to keep its wikilink pass proportional to session size.

### For contributors
- The `/memex:upgrade` state detection grew a 5th signal (memory-closets presence) and a new playbook (`references/v2-to-v2_1.md`).
- `sources.py` gained a `search-local` subcommand. The cross-source `search` and within-workspace `search-local` share a `_search_workspace()` helper.

## [2.0.0] - 2026-05-05

**Validated retrieval quality.** Memex v2 hits **90.1% R@5 on [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval)** (Wu et al., ICLR 2025), the standard benchmark for long-term memory in chat assistants. That's within 0.5pp of indexing the entire raw session text, at roughly 1/10th the size, because closets are typed and structured, not raw transcripts. See [`benchmarks/longmemeval/`](benchmarks/longmemeval/) for the reproducer.

All v2 features ship with **zero new runtime dependencies.** Memex is still pure-Python stdlib plus markdown, and still installs in two commands. Benchmark tooling (numpy, sentence-transformers) is contributor-only and never runs on user machines.

### Added
- **Two-tier index (`_CLOSETS.md`).** Per-hub closets file enumerates subjects, named entities, decisions, and status for every file in the hub. Sessions scan closets to decide which files to open, without opening any of them.
- **Closets pagination (`_CLOSETS-archive.md`).** Primary closets cap is 30 entries (most-recently-modified files). Overflow spills to a sibling `_CLOSETS-archive.md` that session-start does not load eagerly; it's only consulted on a primary-closets miss. Bumps the in-file marker to `<!-- memex-closets:1.1 -->`. Hubs with ≤ 30 files keep the original single-file layout. Touching an archived file promotes it back to primary; the oldest primary entry demotes.
- **`/memex:upgrade` skill.** One-command orchestrator for v1→v2 migration. Detects workspace state (manifest version marker, summary-format-version, per-hub closets coverage), builds an idempotent upgrade plan, and runs the right subset of `/memex:resummarize` + `/memex:reindex` + lint. Re-runs are no-ops on a current workspace. Future major versions add their own playbooks under `references/`.
- **`/memex:reindex` skill.** Bulk-walks every hub in the manifest and generates or refreshes `_CLOSETS.md` from the underlying file content. Use after upgrading a v1 workspace (so closets are populated on session 1 instead of accumulating lazily over many session-ends), after a large bulk import, or any time first-pass v2 retrieval quality is needed immediately. Pairs with `/memex:resummarize` (which refreshes the *summary* layer); reindex covers the *closets* layer.
- **Cross-search reads facts.db too.** `/memex:cross-search` now queries each linked workspace's `memory/.facts.db` alongside the grep over manifests + closets. Default-on; pass `--no-facts` to skip. Read-only access; matches are limited to currently-valid facts (`valid_to IS NULL`). Closes a federation gap where temporal facts were invisible to cross-workspace queries.
- **Temporal facts SQLite sidecar.** `memory/.facts.db` stores `(subject, predicate, object)` triples with `valid_from`/`valid_to` dates. Stdlib `sqlite3` only. No new deps. `/memex:facts` skill for query/add/timeline/contradictions. Markdown mirror at `memory/facts.md` is the source of truth (the DB is regenerable via `facts.py rebuild`).
- **YAML frontmatter typed-edge graph.** Optional `supersedes`, `superseded-by`, `blocks`, `blocked-by`, `people`, `projects`, `type`, `status`, `date` keys auto-extracted into `memory/.graph.md` at session-end. Zero LLM calls; pure regex via `extract-graph.py`. Files without frontmatter are unaffected.
- **`/memex:consolidate` skill.** Runs dedup, contradiction sweep, and orphan check independently from session-end. Lock file (`memory/.consolidate.lock`) prevents concurrent runs.
- **`/memex:resummarize` skill.** Detects manifest and hub summaries written under older format rules and refreshes them to the current retrieval-tuned format.
- **`/memex:facts` skill.** Wraps `facts.py` for query, add, supersede, timeline, contradictions, export, and stats.
- **Cross-workspace federation.** `/memex:link-workspace`, `/memex:unlink-workspace`, `/memex:cross-search` plus `~/.memex/sources.md` global registry. Grep-based search across linked workspaces' manifests + closets, opt-in per source.
- **Session lock + crash recovery.** `memory/.session.lock` written at session-start, cleared at session-end. Session-start surfaces a warning if the previous session ended without closing.
- **Idempotent status writes.** Session-end skips the `status.md` write entirely when content hashes match, avoiding spurious timestamp churn from re-running session-end.
- **Self-test step at session-end.** Verifies each step's output landed (status, log, hubs, closets, manifest version, wikilinks). Surfaces any incomplete step in the close report instead of silently passing.
- **Free CI script tests.** `tests/test_scripts.py` exercises all four Python scripts (`verify-wikilinks`, `extract-graph`, `facts`, `sources`) against fixture workspaces. No API keys, ~5 seconds. Driven by `.github/workflows/scripts.yml`.
- **Reproducible LongMemEval-S benchmark.** `benchmarks/longmemeval/` with five extractors (content, summary, firstmsg, closets, haiku) × eight rankers (BM25, single-vector embed, multi-vector pools, RRF fusion variants, ensemble), `compare.py` for paired-bootstrap CIs, contributor-only deps in `.venv`. Headline strategy `closets:emax` lands at 90.1% R@5; ablation rankers documented in the benchmark README.

### Changed
- **Session-end summary writing rules (retrieval-tuned, 8 rules).** Summaries must enumerate every distinct subject (not just topic) including mid-file mentions and ALL-CAPS acronyms, name entities by name, quote user-stated facts verbatim across identity / location / family / occupation / numeric facts / negative facts, cap at 250 chars, no throat-clearing, plus capture decision **reversals** (switches, rejections, abandons) explicitly and always extract date/time mentions when present. The `_MANIFEST.md` and hub `_CLOSETS.md` summaries follow the same eight rules. New `<!-- summary-format-version:2 -->` marker tracks compliance; `/memex:lint` flags missing markers.
- **Closets file format adds `claims:` and `dates:` typed fields.** Each closet entry now has up to six typed lines (`subjects`, `people`, `claims`, `decisions`, `dates`, `status`), each independently retrievable by an LLM's attention. Existing entries are gradually migrated as files are touched. No migration script needed.
- **Session-end now refreshes the typed-edge graph and closets** when frontmatter-bearing files or hub-attached files change. Both are best-effort; graceful skip when scripts are unavailable.
- **`/memex:lint` adds two checks.** Typed-edge graph integrity (dangling references) and summary-format-version compliance.
- **Session-start loads `_CLOSETS.md`** for the active domain alongside `_MANIFEST.md`. Falls back to opening the hub index if no closets file exists (compatible-mode workspaces).
- **`/memex:add-domain` creates a closets file** alongside the new hub index, so new domains are v2-ready out of the box.
- **`/memex:init` scaffolds closets files** for every domain it creates during the scan-and-organize flow.

### Fixed
- `verify-wikilinks.py` no longer double-reports closet entries that point to missing files (closets-specific check owns those).

### Skill cohesion (engineering pass)

These changes follow a holistic audit of how all 17 skills wire together: fixing autonomous-invocation gaps that left v1 users stranded, gating dangerous bulk edits behind explicit invocation, inlining premature reference splits, and making lint actively suggest the right next-action skill instead of leaving the user to know.

- **session-start surfaces v1 → v2 upgrade prompt.** When the manifest marker is `<!-- memex-managed:1.x.x -->`, the briefing now appends `Memex upgrade available. Run /memex:upgrade to migrate to v2 retrieval.` Closes the gap where v1 workspaces silently ran in compatible mode forever unless the user already knew `/memex:upgrade` existed.
- **session-start surfaces missing-closets warning.** When any hub in the Hub Map lacks `_CLOSETS.md`, the briefing appends `Closets missing for [N] of [M] hubs. Run /memex:reindex to backfill.` Discoverability for the closets-coverage gap that previously degraded retrieval silently.
- **`/memex:lint` is now autonomously invokable.** Dropped `disable-model-invocation: true`. Lint is read-only by default; `--fix` is a separately-gated flag. The model can now suggest lint when status feels stale or after a long break, without requiring the user to remember the command.
- **`/memex:lint` adds CLOSETS COVERAGE check.** Reports hubs missing `_CLOSETS.md` so the gap surfaces in the per-check live report (not just session-start's summary).
- **`/memex:lint` adds Suggested next actions footer.** Below the report, lint now points the user at the right next skill (`/memex:resummarize`, `/memex:reindex`, `/memex:upgrade`, `/memex:consolidate`, `/memex:update`, `/memex:facts`) based on which checks failed. Closes the loop between read-only audit and bulk-write fix tools.
- **`/memex:facts` gated behind explicit invocation.** Added `disable-model-invocation: true`. Autonomous DB writes from model inference are a footgun. Misinterpreting "Alice probably works at X" as a fact would silently insert a false `(subject, predicate, object)` row. Reads still work via `/memex:cross-search` (read-only across all linked workspaces) or via `/memex:facts query` directly.
- **`/memex:wikilinks` gated behind explicit invocation.** Added `disable-model-invocation: true`. The conversion sweep is a workspace-wide bulk edit; auto-firing on a casual rename could propose hundreds of changes. Verification (`verify-wikilinks.py`) is still called from session-end.
- **session-end nags about consolidate cadence.** When `memory/.consolidate-runs.log` is missing or its last run is > 14 days old, the close report appends `Last /memex:consolidate: [N days ago | never]. Consider running it for a deeper drift sweep.` One-line nudge; never blocks close.
- **`/memex:lint` reference inlined.** The `references/checks.md` (171 lines) was an upside-down split. The reference *was* the skill. Inlined back into a single 238-line `SKILL.md` with all eight checks, the report layout, the suggested-next-actions footer, and the fix policy in one file.
- **`/memex:consolidate` `phases.md` inlined.** Same reasoning. The three-phase procedure belongs inline. `references/locking.md` stays (genuinely shared by `consolidate`, `reindex`, `resummarize`, `upgrade`).
- **`/memex:init` delegates v1→v2 to `/memex:upgrade`.** Init detects the old marker but no longer attempts to migrate in-place. The "Old version" row in init's state-detection table now routes to `/memex:upgrade` directly.

### Cohesion follow-ups (release pass)

A second-pass audit caught a handful of issues the first cohesion pass missed; all fixed before tagging.

- **Plugin metadata + manifest template now stamped `2.0.0`.** Without this the prior pass's v1-detection in `/memex:session-start` was dormant (compared 1.x.x against the 1.1.1 plugin version → never fired). `init/templates/_MANIFEST.md.tmpl` also moved from `1.1.0` to `2.0.0` so freshly-init'd workspaces don't immediately get a spurious upgrade nag.
- **`/memex:upgrade` added to the shared bulk-write locking convention.** `consolidate/references/locking.md` now lists upgrade alongside consolidate / reindex / resummarize, with its `from=<old> to=<new> resummarize=<…> reindex=<…>` run-log format.
- **session-start's missing-closets warning skips compatible mode.** Pre-v2 workspaces (no `<!-- memex-managed` marker) don't owe closets coverage; nagging about them was noise.
- **session-end's consolidate-cadence nag suppresses on new workspaces.** Skips the "Last consolidate: never" message when `_MANIFEST.md` mtime is < 14 days old. New workspaces have no drift to sweep yet.
- **Lint footer no longer cross-categorizes typed-edge failures as fact contradictions.** Typed edges (frontmatter `supersedes:`/`blocks:`) and facts (SQLite `(subject, predicate, object)`) are different systems. The footer now says so explicitly. Added a wikilinks footer entry too.
- **`/memex:idea` and `/memex:update` autonomous trigger descriptions tightened.** Both now require explicit user-stated capture/checkpoint intent rather than firing on vague "we should eventually..." or "context feels heavy" cues.
- **`/memex:archive` Step 4 now updates `_CLOSETS.md` status field.** The gotcha said the closets entry's `status:` field changes to `archived` on archive; the skill now actually does that instead of relying on session-end to re-derive it.
- **`/memex:facts` description rewritten to lead with explicit-invocation reality** instead of trigger-shaped language that was misleading after the gating change.
- **Skill-name cross-references standardized** to markdown-link form (`[session-end](../session-end/SKILL.md)`) instead of wikilink form (`[[session-end]]`) in `reindex` and `resummarize`. Wikilinks remain for actual file references.

### For contributors
- New `CONTRIBUTING.md` with the moat gates documented up front, expanded verification pass, and a frontmatter schema reference.
- Free script tests gate every push via the new CI workflow.
- Compare any retrieval-touching change with `benchmarks/longmemeval/compare.py results/<new>.json results/<reference>.json --by-type` (10,000-sample paired bootstrap CI).

## [1.1.1] - 2026-04-06

### Fixed
- Clean release tag for marketplace update detection (v1.1.0 tag was force-pushed, which can prevent marketplace git pull from updating cleanly).

## [1.1.0] - 2026-04-05

### Added
- New `/memex:lint` skill for workspace health audits: stale status, contradicted decisions, orphan files, broken hub references, stale blockers. Read-only by default, offers fixes with `--fix` flag.
- Gotchas sections in session-start, session-end, init, update, and wikilinks documenting known failure modes and edge cases.
- `$CLAUDE_PLUGIN_DATA` integration in session-end for tracking clean session closes.
- Progressive disclosure in init (health-check and migrations extracted to reference files) and lint (check definitions in reference file).

### Improved
- `/memex:update` auto-annotates superseded decisions with strikethrough and date pointers, keeping decisions.md self-consistent.
- Session-start warns when status.md is more than 3 days stale, catching drift from abandoned sessions.
- Skill descriptions rewritten as trigger conditions (when to use) across session-start, session-end, update, archive, and wikilinks.

### Fixed
- `.claude-plugin/marketplace.json` version now matches plugin.json (was stuck at 1.0.5).

## [1.0.6] - 2026-03-25

### Improved
- Session-start offers "Start session" or "Update first" prompt after briefing, so users can flag work done between sessions without extra friction.
- Session-end checks status sections in touched domain files (Step 5) and updates them if the session's work made them stale.

## [1.0.5] - 2026-03-22

### Improved
- README explains the hub-and-spoke architecture's purpose: full workspace awareness with minimal token cost.

## [1.0.4] - 2026-03-22

### Improved
- Init proposal step now shows the user exactly what will be added to CLAUDE.md before they confirm.
- Init completion output includes a skills table prioritizing session-active skills.
- Session start/end noted as automatic so users know they don't need to invoke them manually.

## [1.0.3] - 2026-03-22

### Improved
- Init distinguishes reference types: term definitions go to glossary, people/contacts/roles become their own Tier 1 file, quick refs stay separate.
- Init detects stale files (outdated, deprecated, superseded, version suffixes) and routes them to Tier 3 instead of active domains.
- Init surfaces conflicting files (same topic, different content) in the proposal step and asks which is authoritative before placing either.

## [1.0.2] - 2026-03-22

### Improved
- Init explains that `_MANIFEST.md` is the central routing file in the proposal step.
- Init recommends Obsidian as a visual layer after completion, with setup instructions.
- Init detects catch-all folders and recommends dissolving them instead of creating hubs.
- Install instructions updated with Cowork UI method alongside slash command.

## [1.0.1] - 2026-03-22

### Improved
- Session-start reads only the latest session-log entry instead of the full file. Stops at the first separator. Handles multiple sessions per day correctly.
- Manifest entries now include one-line content summaries. Session-start scans these to decide what to load without opening every file.
- Wikilink conversion split into two passes: exact filename matches apply automatically, semantic references are proposed to the user for confirmation.
- Init weaves lateral cross-links between files in different domains, enriching the Obsidian graph without affecting tiered loading.
- Session-end refreshes manifest summaries when file content changes.
- Hub Map entries include domain summaries.

## [1.0.0] - 2026-03-21

Initial public release as a Claude Cowork plugin.

### Core Features

- **Wikilinked knowledge base.** Converts workspaces into a connected `[[wikilink]]` graph. Init scans existing files and converts plain text references. All skills enforce wikilink format. Obsidian-compatible out of the box.
- **Tiered context loading.** Tier 1 (always load), Tier 2 (by domain), Tier 3 (archived). Claude only reads what it needs. Volatility markers (VOLATILE/STABLE) control freshness.
- **Two-track init.** Empty workspace: one question, 30-second scaffold. Existing files: content-aware scan, suggest domains, propose file moves, wire manifest. Zero file deletions.
- **Convention over configuration.** Standard paths (`memory/`, `scratch/`) work out of the box. Config optional for non-standard layouts. Path resolution: config > convention > search.
- **Three-tier workspace detection.** Memex-managed (full features), compatible (existing manifest without marker), none (prompt to init). Adopts existing workspaces without migration.
- **Session automation.** Hooks auto-trigger session-start and session-end. Single-line hook prompts, all logic in skills.
- **Content-aware scanning.** Session-start and session-end scan for untracked folders and loose files, suggest domain organization based on file content.

### Skills (8)

| Skill | Purpose |
|-------|---------|
| `init` | Set up, adopt, health-check, or upgrade a workspace |
| `session-start` | Session briefing with status, blockers, ideas, untracked content |
| `session-end` | Update memory, log decisions, verify wikilinks, detect domains |
| `update` | Mid-session memory flush without closing |
| `idea` | Quick-capture to ideas inbox (auto-creates if missing) |
| `add-domain` | Add domain folder with hub, scan for related files |
| `archive` | Move file from Tier 2 to Tier 3 |
| `wikilinks` | Check broken links and convert plain text to `[[wikilinks]]` |

### Plugin System

- Distributed via Claude plugin marketplace (`/plugin marketplace add Skyfox-io/Memex`)
- `SessionStart` and `SessionEnd` hooks for automatic session lifecycle
- `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` for portable path references
- Versioned manifest marker (`<!-- memex-managed:1.0.0 -->`) for upgrade detection
