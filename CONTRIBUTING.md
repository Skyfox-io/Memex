# Contributing to Memex

Memex is open source under the MIT license. Contributions are welcome - new skills, bug fixes, documentation improvements, and example workspaces.

## The moat (read this before any change)

Every contribution must preserve six gates:

1. **No new runtime dependencies.** Only Python stdlib. No `pip install`. No `npm`.
2. **No server processes.** Nothing running in the background. No daemons.
3. **No cloud requirement.** Works fully offline. No API keys for core operation.
4. **Setup stays at 2 commands.** `/plugin marketplace add` + `/memex:init`.
5. **Markdown stays primary.** Files are human-readable, version-controllable, Obsidian-compatible.
6. **Backwards-compatible.** Existing workspaces upgrade silently.

If a proposed change violates any gate, it doesn't ship. The `benchmarks/` directory is the only exception — its tooling uses pip-installed packages but never runs on user machines.

**Why the gates matter:** Memex's edge over a "bigger, smarter memory" is that it works with zero infrastructure. A user who installs the plugin and runs `/memex:init` is productive in 30 seconds. Any gate violation moves Memex toward "yet another memory framework that needs setup, accounts, or trust" and away from "drop-in for any Cowork workspace". Backwards compat preserves user trust across upgrades; the v2 release retained every v1.x workspace shape and added v2 features purely additively.

## How to Contribute

### Reporting Issues
Open an issue on GitHub. Include:
- What you expected to happen
- What actually happened
- Your setup (Cowork or Claude Code, OS)

### Submitting Changes
1. Fork the repository
2. Create a feature branch (`git checkout -b my-feature`)
3. Make your changes
4. Run the verification pass (see below)
5. Submit a pull request

### Verification Pass

Before submitting, run these checks:

**1. Free script tests (all 10 must pass):**
```bash
python3 tests/test_scripts.py
```

These exercise `verify-wikilinks.py`, `extract-graph.py`, `facts.py`, and `sources.py` against fixture workspaces. No API keys needed, ~5 seconds. Driven on CI by `.github/workflows/scripts.yml`.

**2. Wikilink integrity (examples):**
```bash
python3 memex/scripts/verify-wikilinks.py examples/nonprofit
python3 memex/scripts/verify-wikilinks.py examples/startup
```

**3. Typed-edge graph integrity (examples):**
```bash
python3 memex/scripts/extract-graph.py examples/nonprofit --check
python3 memex/scripts/extract-graph.py examples/startup --check
```

**4. No placeholder text in examples:**
```bash
grep -r '\[placeholder\]\|\[bracket\]\|{{.*}}' --include="*.md" examples/
```
Should return nothing (templates in `memex/skills/init/templates/` are expected to have `{{placeholders}}`).

**5. Valid JSON:**
```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"
python3 -c "import json; json.load(open('memex/.claude-plugin/plugin.json'))"
python3 -c "import json; json.load(open('memex/hooks/hooks.json'))"
```

---

## Contributing Skills

To modify an existing skill or add a new one:

1. Skills live in `memex/skills/[skill-name]/SKILL.md`
2. SKILL.md needs YAML frontmatter (`name`, `description`, optionally `argument-hint`, `disable-model-invocation`)
3. Description should be short - a trigger condition, not a summary
4. If the skill has known failure modes, add a `## Gotchas` section at the bottom
5. If the skill has multiple independent paths, consider using `references/` sub-files for progressive disclosure
6. Use convention > config > search for path resolution
7. Update the Skills table in `README.md` and `memex/README.md`
8. Update `CHANGELOG.md`

### Skill Guidelines

- **Single responsibility.** One skill, one job.
- **Convention first.** Resolve paths by convention before falling back to Config or search.
- **Fail loudly.** If something is wrong, tell the user. Never silently pass.
- **Use `[[wikilinks]]`** when referencing files in output.
- **Don't duplicate logic in CLAUDE.md.** Session logic lives in skills, not in CLAUDE.md.
- **Document gotchas.** If a skill has known edge cases or failure modes, add a Gotchas section.

### Backwards compat

If you change a summary-writing rule or storage format:
- Bump the corresponding version marker (`<!-- memex-managed:1.x.y -->`, `<!-- summary-format-version:N -->`).
- Add a migration note in `init/references/migrations.md`.
- Make `/memex:lint` flag old-version workspaces so users can opt into the upgrade via `/memex:resummarize`.

---

## Contributing Scripts

The `memex/scripts/` directory holds the deterministic helpers (`verify-wikilinks.py`, `extract-graph.py`, `facts.py`, `sources.py`). Rules:

1. **Python stdlib only.** No `pip install`. No new runtime deps.
2. Add a `#!/usr/bin/env python3` shebang and `chmod +x`.
3. Use `argparse` subcommands for verbs.
4. Add a test in `tests/test_scripts.py` for any new behavior.
5. Document the flag surface in the docstring at the top of the file.

---

## Frontmatter schema

Optional. Files without frontmatter still work (purely additive). Recognized keys:

```yaml
---
type: decision | person | project | meeting | reference | other
people: [[Alice]], [[Bob]]
projects: [[campaign-2026]]
supersedes: [[old-decision]]
superseded-by: [[newer-decision]]
blocks: [[other-task]]
blocked-by: [[upstream-task]]
date: YYYY-MM-DD
status: active | superseded | archived | draft
---
```

`memex/scripts/extract-graph.py` parses these into `memory/.graph.md` at session-end.

---

## Benchmarks

`benchmarks/longmemeval/` is a self-contained retrieval benchmark on LongMemEval-S. The tooling there installs `numpy`, `rank_bm25`, `sentence-transformers`, etc. into a `.venv` — that's allowed because it's contributor-only and never runs on user machines.

To re-baseline:

```bash
cd benchmarks/longmemeval
.venv/bin/python run_bench.py --strategies content:bm25 summary:bm25 firstmsg:bm25 summary:embed firstmsg:embed --save-as baseline_$(date +%Y%m%d)
```

To diff:

```bash
.venv/bin/python compare.py results/<new>.json results/<old>.json --by-type
```

---

## Contributing Examples

Example workspaces show people what Memex looks like after setup. To add one:

1. Create a folder in `examples/` with a descriptive name
2. Include: `CLAUDE.md`, `_MANIFEST.md`, `memory/` files, domain hubs, `_CLOSETS.md` per hub
3. Fill in realistic (fictional) content - no placeholders
4. Run wikilink + graph verification to confirm clean state
5. Add a row to the Examples table in `README.md`

---

## Code Style

- Markdown files: no trailing whitespace, one blank line at end of file
- Python scripts: standard formatting, docstrings on modules and public functions, type annotations on public functions
- Commit messages: imperative mood, one line, under 72 characters
- No em dashes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
