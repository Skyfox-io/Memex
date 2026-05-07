#!/usr/bin/env python3
"""
Memex cross-workspace source registry.

Sources are independent Memex workspaces registered globally so the user can
search across them. The registry lives at ~/.memex/sources.md (file-based,
human-readable, no DB). Each source has a name, an absolute path, and a
flag indicating whether it is `cross-source-searchable`.

Search is grep-based across each source's `_MANIFEST.md` and `_CLOSETS.md`
files. With `--facts`, also queries each source's `memory/.facts.db`
(read-only). Results are grouped by source.

Subcommands:
    list                List all registered sources
    add NAME PATH       Register a workspace as a source
    remove NAME         Deregister a source
    set-searchable NAME true|false  Toggle cross-source-searchable flag
    search QUERY        Grep across registered sources' manifests + closets
                        --facts also queries each source's .facts.db
                        --no-facts disables fact queries (default: on)
    where               Show registry path

Privacy: sources opt in via `cross-source-searchable: true`. Sources marked
`false` are still listed but never searched.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REGISTRY_DIR = Path.home() / ".memex"
REGISTRY_FILE = REGISTRY_DIR / "sources.md"

REGISTRY_TEMPLATE = """# Memex Sources

> Cross-workspace registry. Each source is an independent Memex workspace.
> Sources marked `searchable: true` are included in `/memex:cross-search`.

<!-- memex-sources-version:1 -->

"""


def ensure_registry() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.write_text(REGISTRY_TEMPLATE)


def parse_registry() -> list[dict]:
    """Parse sources.md into list of source dicts."""
    if not REGISTRY_FILE.exists():
        return []
    text = REGISTRY_FILE.read_text()
    sources: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(\S+)\s*$", line)
        if m:
            if current:
                sources.append(current)
            current = {"name": m.group(1), "path": "", "registered": "", "searchable": True}
            continue
        if current is None:
            continue
        m = re.match(r"^-\s+(\w+)\s*:\s*(.+)$", line.strip())
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key in ("path", "registered", "searchable"):
            if key == "searchable":
                current[key] = val.lower() in ("true", "yes", "1")
            else:
                current[key] = val
    if current:
        sources.append(current)
    return sources


def write_registry(sources: list[dict]) -> None:
    ensure_registry()
    out = [REGISTRY_TEMPLATE.rstrip(), ""]
    for s in sources:
        out.append(f"## {s['name']}")
        out.append(f"- path: {s['path']}")
        out.append(f"- registered: {s['registered']}")
        out.append(f"- searchable: {'true' if s.get('searchable', True) else 'false'}")
        out.append("")
    REGISTRY_FILE.write_text("\n".join(out) + "\n")


# --- Subcommands -----------------------------------------------------------

def cmd_list(args):
    sources = parse_registry()
    if not sources:
        print(f"No sources registered. Use `sources.py add NAME PATH` to register one.")
        print(f"Registry: {REGISTRY_FILE}")
        return
    for s in sources:
        flag = "✓" if s.get("searchable", True) else "✗"
        print(f"  {flag} {s['name']:24s} {s['path']}  (registered {s['registered']})")


def cmd_add(args):
    path = Path(args.path).resolve()
    if not path.is_dir():
        print(f"ERROR: {path} is not a directory", file=sys.stderr)
        sys.exit(2)
    if not (path / "_MANIFEST.md").exists():
        print(f"WARNING: {path}/_MANIFEST.md not found — is this a Memex workspace?", file=sys.stderr)
    sources = parse_registry()
    if any(s["name"] == args.name for s in sources):
        print(f"ERROR: source name '{args.name}' already registered", file=sys.stderr)
        sys.exit(2)
    sources.append({
        "name": args.name,
        "path": str(path),
        "registered": datetime.now().date().isoformat(),
        "searchable": True,
    })
    write_registry(sources)
    print(f"Registered '{args.name}' → {path}")


def cmd_remove(args):
    sources = parse_registry()
    before = len(sources)
    sources = [s for s in sources if s["name"] != args.name]
    if len(sources) == before:
        print(f"ERROR: no source named '{args.name}'", file=sys.stderr)
        sys.exit(2)
    write_registry(sources)
    print(f"Removed source '{args.name}'")


def cmd_set_searchable(args):
    val = args.value.lower() in ("true", "yes", "1")
    sources = parse_registry()
    found = False
    for s in sources:
        if s["name"] == args.name:
            s["searchable"] = val
            found = True
    if not found:
        print(f"ERROR: no source named '{args.name}'", file=sys.stderr)
        sys.exit(2)
    write_registry(sources)
    print(f"Source '{args.name}' searchable={val}")


def _search_facts_db(path: Path, query: str, limit: int = 20) -> list[str]:
    """Query a workspace's memory/.facts.db for current facts whose subject,
    predicate, or object matches the query (case-insensitive substring).

    Returns formatted hit lines. Empty list if the DB is missing, locked, or
    has no current matches.
    """
    db = path / "memory" / ".facts.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return []
    try:
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT id, subject, predicate, object, valid_from, source_file
               FROM facts
               WHERE valid_to IS NULL
                 AND (subject LIKE ? COLLATE NOCASE
                      OR predicate LIKE ? COLLATE NOCASE
                      OR object LIKE ? COLLATE NOCASE)
               ORDER BY valid_from DESC
               LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()
    out = []
    for fid, subj, pred, obj, vf, src in rows:
        src_str = f"  ({src})" if src else ""
        out.append(f"facts.db: #{fid} ({subj}) ({pred}) ({obj})  since {vf}{src_str}")
    return out


def cmd_search(args):
    sources = parse_registry()
    searchable = [s for s in sources if s.get("searchable", True)]
    if not searchable:
        print("No searchable sources registered.")
        return

    query = args.query
    include_facts = getattr(args, "facts", True)
    suffix = " (+ facts.db)" if include_facts else ""
    print(f"Searching {len(searchable)} source(s){suffix} for: {query}\n")

    total_hits = 0
    total_fact_hits = 0
    for s in searchable:
        path = Path(s["path"])
        if not path.is_dir():
            print(f"  [{s['name']}] (path missing: {path})\n")
            continue
        targets = [
            path / "_MANIFEST.md",
            *path.rglob("_CLOSETS.md"),
            *path.rglob("_CLOSETS-archive.md"),
        ]
        targets = [t for t in targets if t.exists()]
        grep_lines: list[str] = []
        if targets:
            cmd = ["grep", "-Hn", "-i", query] + [str(t) for t in targets]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                grep_lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
            except subprocess.TimeoutExpired:
                print(f"  [{s['name']}] grep timeout")

        fact_lines: list[str] = []
        if include_facts:
            fact_lines = _search_facts_db(path, query)

        if not grep_lines and not fact_lines:
            continue

        print(f"=== {s['name']} ({s['path']}) ===")
        for ln in grep_lines[:20]:
            print(f"  {ln}")
        if len(grep_lines) > 20:
            print(f"  ... and {len(grep_lines)-20} more grep matches")
        for ln in fact_lines:
            print(f"  {ln}")
        print()
        total_hits += len(grep_lines)
        total_fact_hits += len(fact_lines)

    summary = f"Total hits: {total_hits} grep across {len(searchable)} sources"
    if include_facts:
        summary += f" (+ {total_fact_hits} fact matches)"
    print(summary)


def cmd_where(args):
    print(REGISTRY_FILE)


# --- main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="sources.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    p = sub.add_parser("add")
    p.add_argument("name")
    p.add_argument("path")

    p = sub.add_parser("remove")
    p.add_argument("name")

    p = sub.add_parser("set-searchable")
    p.add_argument("name")
    p.add_argument("value", choices=["true", "false", "yes", "no", "1", "0"])

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--facts", dest="facts", action="store_true", default=True,
                   help="include facts.db queries (default: on)")
    p.add_argument("--no-facts", dest="facts", action="store_false",
                   help="skip facts.db queries (manifest+closets only)")

    sub.add_parser("where")

    args = parser.parse_args()
    cmd_map = {
        "list": cmd_list, "add": cmd_add, "remove": cmd_remove,
        "set-searchable": cmd_set_searchable, "search": cmd_search,
        "where": cmd_where,
    }
    cmd_map[args.cmd](args)


if __name__ == "__main__":
    main()
