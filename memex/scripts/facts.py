#!/usr/bin/env python3
"""
Memex temporal facts sidecar.

Stores facts as (subject, predicate, object) triples with optional valid_from
and valid_to dates. Pure-Python stdlib only (sqlite3 is built into Python).

The DB lives at memory/.facts.db (workspace-local). It is regenerable from
memory/facts.md (the human-readable mirror), so it can be safely .gitignored.

Subcommands:
    init [WORKSPACE]            Create empty .facts.db
    add SUBJ PRED OBJ [...]     Insert a fact
    query SUBJ [PRED]           List currently-valid facts
    timeline SUBJ [PRED]        List all facts (current + superseded) chronologically
    contradictions              List subject+predicate pairs with multiple current objects
    supersede ID NEW_OBJ        Mark fact ID superseded; insert new fact with same subj+pred
    rebuild                     Rebuild .facts.db from memory/facts.md mirror
    export                      Write memory/facts.md from .facts.db
    stats                       Counts and summary

Frontmatter ingestion (called by session-end):
    ingest WORKSPACE            Parse decisions.md and frontmatter; auto-extract facts

Schema:
    facts(id, subject, predicate, object, source_file, source_line,
          valid_from, valid_to, confidence, superseded_by, created_at)

Standard predicates (suggested, not enforced):
    is, has, prefers, named, located_at, started, ended, decided, supersedes,
    blocks, blocked_by, works_at, attends, owns, allergic_to
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    source_file TEXT,
    source_line INTEGER,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    confidence REAL DEFAULT 1.0,
    superseded_by INTEGER REFERENCES facts(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subject_predicate ON facts(subject, predicate);
CREATE INDEX IF NOT EXISTS idx_valid_to ON facts(valid_to);
CREATE INDEX IF NOT EXISTS idx_superseded ON facts(superseded_by);
"""


def db_path(workspace: Path) -> Path:
    return workspace / "memory" / ".facts.db"


def mirror_path(workspace: Path) -> Path:
    return workspace / "memory" / "facts.md"


def connect(workspace: Path) -> sqlite3.Connection:
    p = db_path(workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.executescript(SCHEMA)
    return conn


def today_iso() -> str:
    return datetime.date.today().isoformat()


# --- Subcommands -----------------------------------------------------------

def cmd_init(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    conn.commit()
    conn.close()
    print(f"Initialized {db_path(ws).relative_to(ws)}")


def cmd_add(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    valid_from = args.date or today_iso()
    cur = conn.execute(
        """INSERT INTO facts (subject, predicate, object, source_file, source_line,
                              valid_from, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (args.subject, args.predicate, args.object,
         args.source_file, args.source_line, valid_from, args.confidence),
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    print(f"Inserted fact #{fid}: ({args.subject}) ({args.predicate}) ({args.object})")


def cmd_query(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    sql = "SELECT id, subject, predicate, object, valid_from, source_file FROM facts WHERE subject = ? AND valid_to IS NULL"
    params: list = [args.subject]
    if args.predicate:
        sql += " AND predicate = ?"
        params.append(args.predicate)
    sql += " ORDER BY valid_from DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if not rows:
        print(f"No current facts for ({args.subject})" + (f" ({args.predicate})" if args.predicate else ""))
        return
    for r in rows:
        fid, subj, pred, obj, vf, src = r
        src_str = f" — {src}" if src else ""
        print(f"  #{fid:4d}  ({subj}) ({pred}) ({obj})  valid_from={vf}{src_str}")


def cmd_timeline(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    sql = """SELECT id, subject, predicate, object, valid_from, valid_to, superseded_by, source_file
             FROM facts WHERE subject = ?"""
    params: list = [args.subject]
    if args.predicate:
        sql += " AND predicate = ?"
        params.append(args.predicate)
    sql += " ORDER BY valid_from"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if not rows:
        print(f"No facts for ({args.subject})")
        return
    for r in rows:
        fid, subj, pred, obj, vf, vt, sb, src = r
        marker = "✓" if vt is None else "✗"
        end = vt or "current"
        sb_str = f" (superseded by #{sb})" if sb else ""
        print(f"  {marker} #{fid:4d}  ({pred}) ({obj})  {vf} → {end}{sb_str}")


def cmd_contradictions(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    rows = conn.execute(
        """SELECT subject, predicate,
                  GROUP_CONCAT(id, ','),
                  GROUP_CONCAT(object, '||'),
                  COUNT(DISTINCT object) AS distinct_objects
           FROM facts
           WHERE valid_to IS NULL
           GROUP BY subject, predicate
           HAVING distinct_objects > 1"""
    ).fetchall()
    rows = [(s, p, ids, objs) for s, p, ids, objs, _ in rows]
    conn.close()
    if not rows:
        print("No contradictions — every (subject, predicate) has at most one current object.")
        return
    print(f"CONTRADICTIONS ({len(rows)} found):")
    for subj, pred, ids, objs in rows:
        id_list = ids.split(",")
        obj_list = objs.split("||")
        print(f"\n  ({subj}) ({pred}):")
        for fid, obj in zip(id_list, obj_list):
            print(f"    #{fid}: {obj}")
        print(f"  Resolve: keep one with `facts.py supersede <ID> '<NEW_OBJ>'` "
              f"or annotate explicitly in decisions.md.")


def cmd_supersede(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    row = conn.execute("SELECT subject, predicate, object FROM facts WHERE id = ?", (args.fact_id,)).fetchone()
    if not row:
        print(f"ERROR: no fact #{args.fact_id}", file=sys.stderr)
        sys.exit(2)
    subj, pred, old_obj = row
    today = today_iso()
    cur = conn.execute(
        """INSERT INTO facts (subject, predicate, object, valid_from)
           VALUES (?, ?, ?, ?)""",
        (subj, pred, args.new_object, today),
    )
    new_id = cur.lastrowid
    conn.execute(
        "UPDATE facts SET valid_to = ?, superseded_by = ? WHERE id = ?",
        (today, new_id, args.fact_id),
    )
    conn.commit()
    conn.close()
    print(f"Superseded #{args.fact_id} ({subj}) ({pred}) ({old_obj}) → #{new_id} ({args.new_object})")


def cmd_stats(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    current = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_to IS NULL").fetchone()[0]
    superseded = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_to IS NOT NULL").fetchone()[0]
    subjs = conn.execute("SELECT COUNT(DISTINCT subject) FROM facts").fetchone()[0]
    preds = conn.execute("SELECT predicate, COUNT(*) FROM facts GROUP BY predicate ORDER BY 2 DESC").fetchall()
    conn.close()
    print(f"Total facts:      {total}")
    print(f"  Current:        {current}")
    print(f"  Superseded:     {superseded}")
    print(f"Distinct subjects: {subjs}")
    if preds:
        print(f"Top predicates:")
        for p, c in preds[:10]:
            print(f"  {p:20s} {c}")


# --- Markdown mirror -------------------------------------------------------

def render_facts_md(rows: list) -> str:
    out = ["# Memex Facts\n",
           "<!-- auto-generated by facts.py — do not edit by hand -->\n",
           "<!-- memex-facts-version:1 -->\n",
           "\n> Temporal knowledge graph mirror. The source of truth is `.facts.db`.\n",
           "> Run `python3 memex/scripts/facts.py rebuild` to regenerate the DB from this file.\n",
           "\n## Current facts\n\n"]
    current = [r for r in rows if r["valid_to"] is None]
    superseded = [r for r in rows if r["valid_to"] is not None]
    if current:
        out.append("| ID | Subject | Predicate | Object | Since | Source |\n")
        out.append("|----|---------|-----------|--------|-------|--------|\n")
        for r in current:
            src = r["source_file"] or ""
            if src and r["source_line"]:
                src = f"{src}:{r['source_line']}"
            out.append(f"| {r['id']} | {r['subject']} | {r['predicate']} | {r['object']} | {r['valid_from']} | {src} |\n")
    else:
        out.append("_No current facts yet._\n")
    if superseded:
        out.append("\n## Superseded\n\n")
        out.append("| ID | Subject | Predicate | Object | Valid | Superseded by |\n")
        out.append("|----|---------|-----------|--------|-------|---------------|\n")
        for r in superseded:
            sb = f"#{r['superseded_by']}" if r["superseded_by"] else ""
            out.append(f"| {r['id']} | {r['subject']} | {r['predicate']} | {r['object']} | {r['valid_from']} → {r['valid_to']} | {sb} |\n")
    return "".join(out)


def cmd_export(args):
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM facts ORDER BY id").fetchall()
    conn.close()
    md = render_facts_md(rows)
    p = mirror_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(md)
    print(f"Wrote {p.relative_to(ws)} ({len(rows)} facts)")


MIRROR_ROW_RE = re.compile(
    r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([0-9-]+(?:\s*→\s*[0-9-]+)?)\s*\|"
)


def cmd_rebuild(args):
    """Wipe and rebuild .facts.db from memory/facts.md."""
    ws = Path(args.workspace).resolve()
    p = mirror_path(ws)
    if not p.exists():
        print(f"ERROR: {p} not found", file=sys.stderr)
        sys.exit(2)
    db = db_path(ws)
    if db.exists():
        db.unlink()
    conn = connect(ws)
    inserted = 0
    for line in p.read_text().splitlines():
        m = MIRROR_ROW_RE.match(line)
        if not m:
            continue
        fid, subj, pred, obj, valid = m.groups()
        if "→" in valid:
            vf, vt = [s.strip() for s in valid.split("→")]
        else:
            vf, vt = valid.strip(), None
        conn.execute(
            """INSERT INTO facts (id, subject, predicate, object, valid_from, valid_to)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (int(fid), subj, pred, obj, vf, vt),
        )
        inserted += 1
    conn.commit()
    conn.close()
    print(f"Rebuilt {db.relative_to(ws)} from {p.relative_to(ws)} — {inserted} facts")


# --- Auto-ingest from decisions.md / frontmatter ---------------------------

DECISION_RE = re.compile(r"\*\*(\d{4}-\d{2}-\d{2})\*\*\s*[-—]\s*(.+)")
SIMPLE_FACT_RE = re.compile(
    r"\b([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,2})\s+(is|has|prefers|owns|attends|works for|works at|named|named after|allergic to|located at|joined|left|started|ended)\s+([^.;]+)",
    re.IGNORECASE,
)


def auto_extract_facts(text: str, source_file: str) -> list[tuple]:
    """Heuristic: extract simple subject-predicate-object triples.

    Returns list of (subject, predicate, object, source_line) tuples.
    """
    out = []
    for line_num, line in enumerate(text.split("\n"), 1):
        for m in SIMPLE_FACT_RE.finditer(line):
            subj, pred, obj = m.groups()
            obj = obj.strip().rstrip(".,!?;:")
            pred = pred.lower().replace(" ", "_")
            if len(obj) > 100:
                continue
            out.append((subj.strip(), pred, obj, line_num))
    return out


def cmd_ingest(args):
    """Parse decisions.md and frontmatter for facts. Idempotent (skips duplicates)."""
    ws = Path(args.workspace).resolve()
    conn = connect(ws)
    # Track existing (subject, predicate, object, source_file, source_line) to dedup
    existing = set(conn.execute(
        "SELECT subject, predicate, object, source_file, source_line FROM facts"
    ).fetchall())

    candidates: list[tuple] = []

    decisions_path = ws / "memory" / "decisions.md"
    if decisions_path.exists():
        text = decisions_path.read_text()
        for m in DECISION_RE.finditer(text):
            date_str, claim = m.groups()
            for s, p, o, ln in auto_extract_facts(claim, "memory/decisions.md"):
                candidates.append((s, p, o, "memory/decisions.md", ln, date_str))

    inserted = 0
    skipped = 0
    for subj, pred, obj, src, ln, vf in candidates:
        key = (subj, pred, obj, src, ln)
        if key in existing:
            skipped += 1
            continue
        conn.execute(
            """INSERT INTO facts (subject, predicate, object, source_file, source_line, valid_from)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (subj, pred, obj, src, ln, vf),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Ingested {inserted} new facts, skipped {skipped} duplicates "
          f"({len(candidates)} candidates total).")


# --- main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="facts.py")
    parser.add_argument("--workspace", default=os.getcwd())
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p = sub.add_parser("add")
    p.add_argument("subject")
    p.add_argument("predicate")
    p.add_argument("object")
    p.add_argument("--date", default=None)
    p.add_argument("--source-file", default=None)
    p.add_argument("--source-line", type=int, default=None)
    p.add_argument("--confidence", type=float, default=1.0)

    p = sub.add_parser("query")
    p.add_argument("subject")
    p.add_argument("predicate", nargs="?", default=None)

    p = sub.add_parser("timeline")
    p.add_argument("subject")
    p.add_argument("predicate", nargs="?", default=None)

    sub.add_parser("contradictions")

    p = sub.add_parser("supersede")
    p.add_argument("fact_id", type=int)
    p.add_argument("new_object")

    sub.add_parser("stats")
    sub.add_parser("export")
    sub.add_parser("rebuild")
    sub.add_parser("ingest")

    args = parser.parse_args()
    cmd_map = {
        "init": cmd_init, "add": cmd_add, "query": cmd_query,
        "timeline": cmd_timeline, "contradictions": cmd_contradictions,
        "supersede": cmd_supersede, "stats": cmd_stats, "export": cmd_export,
        "rebuild": cmd_rebuild, "ingest": cmd_ingest,
    }
    cmd_map[args.cmd](args)


if __name__ == "__main__":
    main()
