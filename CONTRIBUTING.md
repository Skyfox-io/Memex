# Contributing to Memex

Memex is open source under the MIT license. Contributions are welcome - new skills, bug fixes, documentation improvements, and example workspaces.

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

**1. Wikilink integrity (examples only):**
```bash
python3 memex/scripts/verify-wikilinks.py examples/nonprofit
python3 memex/scripts/verify-wikilinks.py examples/startup
```

**2. No placeholder text:**
```bash
grep -r '\[placeholder\]\|\[bracket\]\|{{.*}}' --include="*.md" examples/
```
Should return nothing (templates in `memex/skills/init/templates/` are expected to have `{{placeholders}}`).

**3. Valid JSON:**
```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"
python3 -c "import json; json.load(open('memex/.claude-plugin/plugin.json'))"
python3 -c "import json; json.load(open('memex/hooks/hooks.json'))"
```

---

## Contributing Skills

To modify an existing skill or add a new one:

1. Skills live in `memex/skills/[skill-name]/SKILL.md`
2. SKILL.md needs YAML frontmatter (`name`, `description`)
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

---

## Contributing Examples

Example workspaces show people what Memex looks like after setup. To add one:

1. Create a folder in `examples/` with a descriptive name
2. Include: `CLAUDE.md`, `_MANIFEST.md`, `memory/` files, domain hubs
3. Fill in realistic (fictional) content - no placeholders
4. Run wikilink verification to confirm zero broken links
5. Add a row to the Examples table in `README.md`

---

## Code Style

- Markdown files: no trailing whitespace, one blank line at end of file
- Python scripts: standard formatting, docstrings on modules and public functions
- Commit messages: imperative mood, one line, under 72 characters
- No em dashes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
