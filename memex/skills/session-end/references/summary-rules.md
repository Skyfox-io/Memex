# Retrieval-Tuned Summary Writing Rules (v2)

Canonical reference for the 8 summary writing rules. Other skills link here.

These rules govern hub-table summaries, manifest-level summaries, and every typed field in [[closets-format|`_CLOSETS.md`]] entries.

These summaries are scanned by future Claude sessions when the user asks questions like "what did we decide about X?" or "what did I tell you about Y?". A summary that only describes the file's *topic* loses retrieval recall on questions about specific subjects discussed inside the file. So summaries must enumerate every distinct subject the file covers, not just the headline topic.

The semantic content of the 8 rules is **benchmark-validated** (90.1% R@5 on LongMemEval-S; see `benchmarks/longmemeval/`). Do not paraphrase the rule meanings.

---

## The 8 rules

Six original retrieval-tuned rules + two added from LongMemEval-S benchmark validation.

1. **Enumerate every distinct subject** discussed in the file: people, projects, places, decisions, preferences, claims, events, dates. Aim for breadth; the summary's job is to surface the file when *any* of those subjects is queried later. **Pull subjects from anywhere in the file**, not just opening lines. Quoted strings, list items, mid-paragraph mentions, and ALL-CAPS acronyms (e.g., "MoMA", "GPT-4", "PetPassport") are all high-recall anchors.

2. **Quote user-stated facts verbatim** where space allows. Do not paraphrase claims the user explicitly made. If the user said "I'm allergic to coffee," the summary contains "allergic to coffee," not "has dietary restrictions." This applies to **identity** ("I'm a teacher"), **location** ("I live in Lisbon"), **family/relations** ("my brother Mike"), **occupation** ("I work at Acme"), **numeric facts** ("3 kids", "5 years old"), and **negative facts** ("I can't eat dairy", "allergic to coffee").

3. **Name entities by name.** Always include named people, organizations, products, and places by their actual names. Names are the strongest retrieval signal.

4. **Cap at 250 characters.** Pack signal. No filler ("This file describes..."). Comma-separated subjects work well.

5. **No throat-clearing.** Skip "In this file..." or "The user discusses...". Lead with subjects.

6. **Update on meaningful change only.** If the file's subjects changed this session, refresh the summary. If only formatting or wording changed, leave it.

7. **Capture decision REVERSALS, not just decisions.** "Switched from Asana to Linear", "rejected Notion", "abandoned the kanban view", "stopped using ClickUp" are all retrieval gold. The user later asks "why did I leave Asana". The file must surface for that. Use verbs like *switched*, *rejected*, *abandoned*, *dropped*, *picked X over Y* explicitly when they apply.

8. **Always extract date and time mentions** when present: month names (April, September), years (2024), relative dates (yesterday, last weekend, two months ago), day names with context (next Tuesday, Friday morning), and absolute dates (3/15, 2024-09-12). Temporal-reasoning questions ("how many weeks ago did I meet my aunt") need date anchors in the file's closet entry to surface correctly.

---

## Examples

**Good:**

> task management apps; allergic to coffee; brother-in-law named Mike; Lisbon trip planned for June 2026; preferred timeline view over kanban; rejected Asana; switched to Linear last March

**Bad** (too vague. Would not surface for "what did I tell you about Mike?"):

> User discussed productivity tools and personal travel plans

---

## Where the rules apply

- **Hub-table summaries** in domain index files (e.g., `programs/programs-index.md`).
- **Manifest-level summaries**: the `_MANIFEST.md` Hub Map row for each domain enumerates the domain's main subjects. Tier 1 file rows follow the same rules. `status.md`'s summary names current active subjects; `decisions.md`'s summary names recent decisions by subject.
- **Closets typed fields**: every line in a [[closets-format|`_CLOSETS.md`]] entry (`subjects`, `claims`, `decisions`, `dates`) is governed by these rules. `people:` is a wikilink list, but still follow rule 3 (name entities by name).

---

## Self-check

Before finishing, re-read each summary you wrote or updated. For each, ask: *if the user asked a question about each subject named in the file, would this summary surface it in the top 5 manifest hits?* If a subject in the file is missing from the summary, add it.
