"""
Generate Memex-style one-line summaries for every unique session in
LongMemEval-S using Claude Haiku. Caches by session_id to cache/haiku_summaries.json.

Approximate cost on full LongMemEval-S: ~$48 (19,829 unique sessions,
~3000 input tokens each, Haiku 4.5 pricing). Use --limit for a cheap pilot.

The summary prompt encodes the v2 Memex session-end rules: enumerate
distinct subjects, name entities, verbatim-always (don't paraphrase
user-stated facts).

Usage:
  ANTHROPIC_API_KEY=... python prepare_haiku.py [--limit N] [--retry-failed]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "haiku_summaries.json"
FAILED_FILE = CACHE_DIR / "haiku_summaries.failed.json"

# v2 Memex session-end summary rules, condensed for Haiku.
SYSTEM_PROMPT = """You are summarizing a chat session for a personal-memory index.

Your one-line summary will be scanned later when the user asks questions like
"what did I tell you about X?" — so it must capture every distinct subject
discussed, not just the opening topic.

Rules:
1. Enumerate every distinct subject discussed (people, projects, places,
   decisions, preferences, factual claims, plans).
2. Quote user-stated facts verbatim where possible. Do not paraphrase.
3. Include named entities (people, companies, products) by name.
4. Cap at 250 characters total.
5. No filler ("In this session...", "The user discussed..."). Just the subjects.
6. Format: comma-separated subjects, optionally with brief verbatim claims.

Example good summary:
  task management apps; allergic to coffee; brother-in-law named Mike; planning Lisbon trip in June; preferred timeline view over kanban

Example bad summary (too vague):
  user wanted help with productivity and shared some personal info"""


def session_to_text(session: list[dict], cap: int = 8000) -> str:
    """Render a session as alternating role-content turns, capped."""
    lines = []
    for t in session:
        role = t.get("role", "?")
        content = t.get("content", "")
        lines.append(f"[{role}] {content}")
    text = "\n".join(lines)
    if len(text) > cap:
        text = text[:cap] + "...[truncated]"
    return text


def summarize_one(client, session_id: str, session: list[dict]) -> tuple[str, str | None, str | None]:
    """Returns (session_id, summary, error)."""
    text = session_to_text(session)
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Session:\n{text}\n\nOne-line summary:"}],
        )
        out = resp.content[0].text.strip()
        # Strip "One-line summary:" prefix if Haiku echoes it
        for prefix in ("One-line summary:", "Summary:", "- "):
            if out.startswith(prefix):
                out = out[len(prefix):].strip()
        return (session_id, out, None)
    except Exception as e:
        return (session_id, None, str(e))


def collect_unique_sessions(data: list[dict]) -> dict[str, list[dict]]:
    """Build {session_id: session_turns}. First occurrence wins (they should be identical)."""
    out = {}
    for ex in data:
        for sid, sess in zip(ex["haystack_session_ids"], ex["haystack_sessions"]):
            if sid not in out:
                out[sid] = sess
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="cap unique sessions to summarize")
    parser.add_argument("--workers", type=int, default=8, help="concurrent API calls")
    parser.add_argument("--retry-failed", action="store_true", help="re-attempt failed sessions only")
    parser.add_argument("--dataset", choices=["s", "oracle"], default="oracle",
                        help="default oracle (~$2-4); s requires --confirm-cost (~$48)")
    parser.add_argument("--confirm-cost", action="store_true",
                        help="required to run against full LongMemEval-S (~$48)")
    args = parser.parse_args()
    if args.dataset == "s" and not args.confirm_cost:
        print(
            "ERROR: --dataset s costs ~$48. Pass --confirm-cost to proceed, or use "
            "--dataset oracle (default, ~$2-4).",
            file=sys.stderr,
        )
        sys.exit(2)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    import anthropic
    client = anthropic.Anthropic()

    fname = "longmemeval_s" if args.dataset == "s" else "longmemeval_oracle"
    data = json.loads((DATA_DIR / fname).read_text())
    print(f"Dataset: {fname}")
    sessions = collect_unique_sessions(data)
    print(f"Found {len(sessions)} unique sessions across {len(data)} questions.")

    cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    failed = json.loads(FAILED_FILE.read_text()) if FAILED_FILE.exists() else {}
    print(f"Cache: {len(cache)} hits, {len(failed)} previous failures.")

    if args.retry_failed:
        todo_ids = list(failed.keys())
        failed = {}
    else:
        todo_ids = [sid for sid in sessions if sid not in cache]

    if args.limit:
        todo_ids = todo_ids[: args.limit]

    if not todo_ids:
        print("Nothing to do.")
        return

    print(f"Summarizing {len(todo_ids)} sessions with {args.workers} workers...")

    save_every = 50
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(summarize_one, client, sid, sessions[sid]): sid
            for sid in todo_ids
        }
        done = 0
        with tqdm(total=len(futures)) as pbar:
            for fut in as_completed(futures):
                sid, summary, err = fut.result()
                if summary is not None:
                    cache[sid] = summary
                    failed.pop(sid, None)
                else:
                    failed[sid] = err
                done += 1
                pbar.update(1)
                if done % save_every == 0:
                    CACHE_FILE.write_text(json.dumps(cache))
                    FAILED_FILE.write_text(json.dumps(failed))

    CACHE_FILE.write_text(json.dumps(cache))
    FAILED_FILE.write_text(json.dumps(failed))
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s. Cache now {len(cache)} entries, failed {len(failed)}.")
    if cache:
        # show 3 random samples
        import random
        for sid in random.sample(list(cache), min(3, len(cache))):
            print(f"  [{sid}] {cache[sid]}")


if __name__ == "__main__":
    main()
