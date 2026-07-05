#!/usr/bin/env python3
"""
Memex built-in similarity search over closets entries.

Grep (sources.py) is the primary retrieval path -- deterministic, zero
deps, always available. This script adds a second signal that catches
what a substring match can't: morphological variants, word-order
differences, and (when the environment permits) true paraphrases.

Two engines behind the same `query` subcommand, auto-selected:

  lexical     Pure stdlib BM25-style scoring over the same corpus, with
              fuzzy credit for prefix/near-miss token variants
              (fundraiser ~ fundraising). Always available -- this is
              the default, and the only engine a bare python3 sandbox
              (e.g. a cloud Cowork session) ever needs or gets.
  embeddings  `sentence-transformers` cosine similarity for true
              synonym/paraphrase matching. Used automatically when the
              package is already importable in this environment;
              never required, never suggested if it isn't.

Embedding-mode cache lives at `memory/.semantic-cache/` -- derived and
disposable, safe to delete, rebuilds on next query. Lexical mode writes
nothing to disk.

Subcommands:
    check                                   Report which engine is active.
    query QUERY --workspace PATH [--top N] [--engine lexical|embeddings|auto]
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBED_FLOOR = 0.30
LEXICAL_RELATIVE_FLOOR = 0.30
DEFAULT_TOP = 8
CACHE_DIR_NAME = ".semantic-cache"
HEADING_RE = re.compile(r"^##\s+\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]\s*$")

TOKEN_RE = re.compile(r"[a-z0-9]+")
MIN_TOKEN_LEN = 3
FUZZY_PREFIX_LEN = 6
FUZZY_RATIO = 0.85
FUZZY_WEIGHT = 0.7
BM25_K1 = 1.2

# Tiny stopword set -- just enough to keep BM25 from scoring on noise words.
STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
    "man", "new", "now", "old", "see",
}


def _model_name() -> str:
    return os.environ.get("MEMEX_EMBED_MODEL", DEFAULT_MODEL)


def _try_import():
    """Return (SentenceTransformer, numpy) or (None, None) if unavailable."""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer, np
    except ImportError:
        return None, None


def cmd_check(_args) -> int:
    SentenceTransformer, _np = _try_import()
    if SentenceTransformer is None:
        print("engine: lexical (stdlib, always available)")
    else:
        print(f"engine: embeddings (model: {_model_name()})")
    return 0


# --- corpus parsing ----------------------------------------------------------

def _closets_files(workspace: Path) -> list[Path]:
    """Every `_CLOSETS.md` / `_CLOSETS-archive.md` under the workspace,
    including `memory/_CLOSETS.md` (picked up by the same rglob)."""
    found = set(workspace.rglob("_CLOSETS.md")) | set(workspace.rglob("_CLOSETS-archive.md"))
    return sorted(found)


def parse_closets_entries(path: Path) -> list[tuple[str, str]]:
    """Parse `## [[stem]]` blocks from a closets file. Returns [(stem, entry_text)].

    Non-entry headings (e.g. "## Recently Archived") close the current
    entry without starting a new one.
    """
    try:
        content = path.read_text()
    except Exception:
        return []
    entries: list[tuple[str, str]] = []
    stem = None
    lines: list[str] = []

    def flush():
        if stem is not None:
            text = "\n".join(lines).strip()
            if text:
                entries.append((stem, text))

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        m = HEADING_RE.match(stripped)
        if m:
            flush()
            stem = m.group(1).strip()
            lines = [stripped]
            continue
        if stripped.startswith("## "):
            flush()
            stem = None
            lines = []
            continue
        if stem is not None:
            lines.append(raw_line)
    flush()
    return entries


def build_corpus(workspace: Path, closets_files: list[Path]) -> list[dict]:
    corpus = []
    for f in closets_files:
        rel = f.relative_to(workspace).as_posix()
        for stem, text in parse_closets_entries(f):
            corpus.append({"relpath": rel, "stem": stem, "text": text})
    return corpus


def _entry_key(e: dict) -> str:
    return f"{e['relpath']}::{e['stem']}"


def _first_field_line(text: str, limit: int = 120) -> str:
    """First subjects/people line of an entry, truncated. Falls back to the
    first non-empty field line if neither field is present."""
    body_lines = text.splitlines()[1:]  # skip the "## [[stem]]" heading
    field_line = None
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("- subjects:") or stripped.startswith("- people:"):
            field_line = stripped
            break
    if field_line is None:
        for line in body_lines:
            stripped = line.strip()
            if stripped:
                field_line = stripped
                break
    field_line = field_line or ""
    if len(field_line) > limit:
        field_line = field_line[: limit - 3] + "..."
    return field_line


# --- output formatting -------------------------------------------------------

def _print_results(results: list[tuple[float, dict]], label_fn, footer: str) -> None:
    if not results:
        print("No similarity matches above threshold.")
        return
    by_folder: dict[str, list[tuple[float, dict]]] = {}
    for score, entry in results:
        relpath = entry["relpath"]
        folder = str(Path(relpath).parent) if "/" in relpath else "."
        by_folder.setdefault(folder, []).append((score, entry))
    for folder in sorted(by_folder):
        print(f"=== {folder} ===")
        for score, entry in by_folder[folder]:
            snippet = _first_field_line(entry["text"])
            print(f"  {entry['relpath']}:[[{entry['stem']}]]  {label_fn(score)}  {snippet}")
        print()
    print(footer)


# --- lexical engine (stdlib, always available) ------------------------------

def _tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS]


def _idf(term: str, df: Counter, n: int) -> float:
    d = df.get(term, 0)
    return math.log((n - d + 0.5) / (d + 0.5) + 1)


def _fuzzy_match(term: str, entry_tokens) -> bool:
    """True if `term` shares a >=6-char prefix with any entry token, or is
    a >=0.85 difflib ratio match. Catches morphological variants
    (fundraiser/fundraising) -- not true synonyms."""
    for tok in entry_tokens:
        if (
            len(term) >= FUZZY_PREFIX_LEN
            and len(tok) >= FUZZY_PREFIX_LEN
            and term[:FUZZY_PREFIX_LEN] == tok[:FUZZY_PREFIX_LEN]
        ):
            return True
        if difflib.SequenceMatcher(None, term, tok).ratio() >= FUZZY_RATIO:
            return True
    return False


def lexical_scores(query: str, corpus: list[dict]) -> list[float]:
    query_tokens = _tokenize(query)
    if not query_tokens or not corpus:
        return [0.0] * len(corpus)

    doc_tokens = [Counter(_tokenize(e["text"])) for e in corpus]
    df: Counter = Counter()
    for tokens in doc_tokens:
        for tok in tokens:
            df[tok] += 1
    n = len(corpus)

    scores = []
    for tokens in doc_tokens:
        score = 0.0
        for term in query_tokens:
            idf = _idf(term, df, n)
            tf = tokens.get(term, 0)
            if tf > 0:
                score += idf * (tf / (tf + BM25_K1))
            elif _fuzzy_match(term, tokens.keys()):
                score += FUZZY_WEIGHT * idf * (1 / (1 + BM25_K1))
        scores.append(score)
    return scores


def _lexical_query(args, corpus: list[dict]) -> list[tuple[float, dict]]:
    scores = lexical_scores(args.query, corpus)
    if not scores or max(scores) <= 0:
        return []
    floor = LEXICAL_RELATIVE_FLOOR * max(scores)
    scored = [(s, e) for s, e in zip(scores, corpus) if s > 0 and s >= floor]
    scored.sort(key=lambda pair: -pair[0])
    top = args.top or DEFAULT_TOP
    return scored[:top]


# --- embedding engine (silent auto-upgrade, unchanged logic) ----------------

def _cache_dir(workspace: Path) -> Path:
    return workspace / "memory" / CACHE_DIR_NAME


def _source_stat(f: Path) -> dict:
    st = f.stat()
    return {"mtime": st.st_mtime, "size": st.st_size}


def _load_cache(cdir: Path, np):
    """Corrupt or unreadable cache -> (None, None), silently rebuilt by caller."""
    meta_path = cdir / "meta.json"
    emb_path = cdir / "embeddings.npy"
    if not meta_path.exists() or not emb_path.exists():
        return None, None
    try:
        meta = json.loads(meta_path.read_text())
        embeddings = np.load(emb_path)
        return meta, embeddings
    except Exception:
        return None, None


def _write_cache(np, cdir: Path, model_name: str, entry_keys: list[str], sources: dict, embeddings) -> None:
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        np.save(cdir / "embeddings.npy", embeddings)
        meta = {"model": model_name, "entries": entry_keys, "sources": sources}
        (cdir / "meta.json").write_text(json.dumps(meta))
    except Exception:
        pass  # cache is disposable; a failed write just means re-embedding next time


def _normalize(np, arr):
    arr = np.asarray(arr, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def _embedding_query(args, workspace: Path, closets_files: list[Path], corpus: list[dict], SentenceTransformer, np):
    model_name = _model_name()
    current_sources = {f.relative_to(workspace).as_posix(): _source_stat(f) for f in closets_files}
    entry_keys = [_entry_key(e) for e in corpus]

    cdir = _cache_dir(workspace)
    meta, embeddings = _load_cache(cdir, np)
    cache_ok = (
        meta is not None
        and embeddings is not None
        and meta.get("model") == model_name
        and meta.get("sources") == current_sources
        and meta.get("entries") == entry_keys
        and len(embeddings) == len(corpus)
    )

    model = SentenceTransformer(model_name)

    if not cache_ok:
        raw = model.encode([e["text"] for e in corpus], convert_to_numpy=True, show_progress_bar=False)
        embeddings = _normalize(np, raw)
        _write_cache(np, cdir, model_name, entry_keys, current_sources, embeddings)

    query_raw = model.encode([args.query], convert_to_numpy=True, show_progress_bar=False)
    query_emb = _normalize(np, query_raw)[0]

    scores = embeddings @ query_emb
    order = np.argsort(-scores)

    top = args.top or DEFAULT_TOP
    results = []
    for idx in order:
        score = float(scores[idx])
        if score < EMBED_FLOOR:
            break
        results.append((score, corpus[idx]))
        if len(results) >= top:
            break
    return results, model_name


# --- query -----------------------------------------------------------------

def _cmd_query_impl(args) -> int:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: {workspace} is not a directory", file=sys.stderr)
        return 2
    if not (workspace / "_MANIFEST.md").exists():
        print("ERROR: no _MANIFEST.md in current workspace. Run /memex:init first.", file=sys.stderr)
        return 2

    closets_files = _closets_files(workspace)
    corpus = build_corpus(workspace, closets_files)
    if not corpus:
        print("No similarity matches above threshold.")
        return 0

    SentenceTransformer, np = (None, None)
    if args.engine in ("embeddings", "auto"):
        SentenceTransformer, np = _try_import()

    # Forcing --engine embeddings without the package falls back to lexical
    # rather than erroring -- query always succeeds on a valid workspace.
    use_embeddings = SentenceTransformer is not None and args.engine in ("embeddings", "auto")

    if use_embeddings:
        results, model_name = _embedding_query(args, workspace, closets_files, corpus, SentenceTransformer, np)
        _print_results(
            results,
            lambda s: f"(semantic {s:.2f})",
            f"Similarity hits: {len(results)} (engine: embeddings, model: {model_name})",
        )
    else:
        results = _lexical_query(args, corpus)
        _print_results(
            results,
            lambda s: f"(lexical {s:.2f})",
            f"Similarity hits: {len(results)} (engine: lexical)",
        )
    return 0


def cmd_query(args) -> int:
    try:
        return _cmd_query_impl(args)
    except Exception as e:  # never traceback -- grep results are never blocked on this
        print(f"similarity query failed: {e}", file=sys.stderr)
        return 1


# --- main --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="semantic.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check")

    p = sub.add_parser("query")
    p.add_argument("query")
    p.add_argument("--workspace", default=os.getcwd(), help="workspace path (default: current directory)")
    p.add_argument("--top", type=int, default=DEFAULT_TOP, help="max results (default: 8)")
    p.add_argument(
        "--engine", choices=["lexical", "embeddings", "auto"], default="auto",
        help="force an engine (default: auto -- embeddings if sentence-transformers is importable, else lexical)",
    )

    args = parser.parse_args()
    if args.cmd == "check":
        sys.exit(cmd_check(args))
    else:
        sys.exit(cmd_query(args))


if __name__ == "__main__":
    main()
