"""
Memex retrieval benchmark on LongMemEval-S.

Strategies are <extractor>:<ranker> pairs. Extractors turn a session into the
text that gets indexed. Rankers score that text against a question.

Extractors:
  content   -- full session text (every turn concatenated)
  summary   -- heuristic 250-char summary (first user msg + first assistant)
  firstmsg  -- first user message only
  haiku     -- LLM-curated summary cached on disk (run prepare_haiku.py first)
  closets   -- closet pointer-line representation (run prepare_closets.py first)

Rankers:
  bm25      -- Okapi BM25 over tokens
  embed     -- cosine over sentence-transformer embeddings (all-MiniLM-L6-v2)

Strategy syntax: <extractor>:<ranker>, e.g. "content:bm25", "haiku:embed".

Usage:
  python run_bench.py                                    # defaults
  python run_bench.py --strategies content:bm25 haiku:embed
  python run_bench.py --limit 50 --dataset oracle        # cheap iteration
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable

import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
CACHE_DIR = Path(__file__).parent / "cache"
RESULTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STOP = set(
    "a an and are as at be by for from has have he her him his i in is it its "
    "me my of on or our she that the their them they this to was we were what "
    "when where which who will with you your".split()
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOP and len(t) > 1]


# --- Extractors -------------------------------------------------------------

def extract_content(session: list[dict], **kw) -> str:
    return "\n".join(t.get("content", "") for t in session)


def extract_summary(session: list[dict], cap: int = 250, **kw) -> str:
    user_msg = next((t["content"] for t in session if t.get("role") == "user"), "")
    asst_msg = next((t["content"] for t in session if t.get("role") == "assistant"), "")
    return user_msg[:cap] + " | " + asst_msg[:cap]


def extract_firstmsg(session: list[dict], **kw) -> str:
    return next((t["content"] for t in session if t.get("role") == "user"), "")


def extract_haiku(session: list[dict], session_id: str, haiku_cache: dict, **kw) -> str:
    s = haiku_cache.get(session_id)
    if s is None:
        raise RuntimeError(
            f"haiku cache miss for {session_id}. Run prepare_haiku.py first."
        )
    return s


def extract_closets(session: list[dict], session_id: str, closets_cache: dict, **kw) -> str:
    s = closets_cache.get(session_id)
    if s is None:
        raise RuntimeError(
            f"closets cache miss for {session_id}. Run prepare_closets.py first."
        )
    return s


EXTRACTORS: dict[str, Callable] = {
    "content": extract_content,
    "summary": extract_summary,
    "firstmsg": extract_firstmsg,
    "haiku": extract_haiku,
    "closets": extract_closets,
}


# --- Rankers ----------------------------------------------------------------

def rank_bm25(question: str, texts: list[str], **kw) -> np.ndarray:
    corpus_tokens = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(tokenize(question))
    return np.argsort(-scores)


_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def rank_embed(question: str, texts: list[str], **kw) -> np.ndarray:
    model = _get_embed_model()
    q_emb = model.encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
    doc_embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
    scores = doc_embs @ q_emb
    return np.argsort(-scores)


# Multi-vector retrieval over typed closet fields.
#
# Each closet entry is structured as "subjects: A; B; C | people: D, E | claims: F |
# decisions: G | dates: H". The single-vector embed ranker collapses this into one
# 384-dim vector — every field competes for the same semantic space, which dilutes
# fine-grained signal. Multi-vector splits each entry by " | ", embeds each typed
# field independently, and scores a session as max(cosine(question, field_i)).
#
# This solves the saturation observed in the benchmark: temporal-reasoning regresses
# under single-vector embed when dates are added (date tokens dilute topical match),
# but recovers under multi-vector because the topical and date vectors are scored
# separately and a max() picks the dominant signal per question.
FIELD_SPLIT = re.compile(r"\s+\|\s+")


def parse_closet_fields(text: str) -> list[str]:
    """Split a closet entry into its typed field strings. Falls back to [text]
    for non-closet inputs (e.g., the haiku/summary/firstmsg/content extractors)
    so this ranker stays usable across all extractors.
    """
    if not text:
        return [text or ""]
    parts = [p.strip() for p in FIELD_SPLIT.split(text) if p.strip()]
    return parts if parts else [text]


def _mvembed_field_sims(question: str, texts: list[str]) -> tuple[np.ndarray, list[int], np.ndarray]:
    """Encode question + every (session, field) pair. Return (similarities array,
    flat session-index per field, dimensionless-rank-of-questions).
    """
    model = _get_embed_model()
    q_emb = model.encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
    flat_idx: list[int] = []
    flat_texts: list[str] = []
    for i, t in enumerate(texts):
        for field in parse_closet_fields(t):
            flat_idx.append(i)
            flat_texts.append(field)
    if not flat_texts:
        return np.zeros(0), [], q_emb
    field_embs = model.encode(
        flat_texts, normalize_embeddings=True, show_progress_bar=False, batch_size=64
    )
    sims = field_embs @ q_emb
    return sims, flat_idx, q_emb


def rank_mvembed(question: str, texts: list[str], **kw) -> np.ndarray:
    """Multi-vector with MAX pool. Caveat: max-pool is sensitive to noisy
    short-input embeddings (e.g., a 2-token "people:" field). On this dataset
    it underperforms single-vector embed. Kept for ablation."""
    sims, flat_idx, _ = _mvembed_field_sims(question, texts)
    if len(sims) == 0:
        return np.arange(len(texts))
    n = len(texts)
    scores = np.full(n, -np.inf, dtype=np.float32)
    for sid, sim in zip(flat_idx, sims):
        if sim > scores[sid]:
            scores[sid] = sim
    return np.argsort(-scores)


def rank_mvmean(question: str, texts: list[str], **kw) -> np.ndarray:
    """Multi-vector with MEAN pool over session fields. Recovers compositional
    signal (multiple matching fields = stronger evidence) that MAX discards."""
    sims, flat_idx, _ = _mvembed_field_sims(question, texts)
    if len(sims) == 0:
        return np.arange(len(texts))
    n = len(texts)
    sums = np.zeros(n, dtype=np.float32)
    counts = np.zeros(n, dtype=np.int64)
    for sid, sim in zip(flat_idx, sims):
        sums[sid] += float(sim)
        counts[sid] += 1
    scores = np.where(counts > 0, sums / np.maximum(counts, 1), -np.inf)
    return np.argsort(-scores)


def rank_emax(question: str, texts: list[str], **kw) -> np.ndarray:
    """Ensemble: single-vector embed + max-field-vector, equally weighted by
    score. Recovers the MAX signal as a tiebreaker without dropping the strong
    whole-entry baseline."""
    model = _get_embed_model()
    q_emb = model.encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
    doc_embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
    whole_sims = doc_embs @ q_emb

    sims, flat_idx, _ = _mvembed_field_sims(question, texts)
    n = len(texts)
    max_sims = np.full(n, -np.inf, dtype=np.float32)
    if len(sims):
        for sid, sim in zip(flat_idx, sims):
            if sim > max_sims[sid]:
                max_sims[sid] = float(sim)
        # Replace -inf (no fields) with the whole-entry sim so they don't disqualify
        no_field = ~np.isfinite(max_sims)
        max_sims[no_field] = whole_sims[no_field]
    else:
        max_sims = whole_sims.copy()

    # Both signals are cosine in [-1, 1]; simple sum is fine since the relative
    # scale matches.
    ensemble = whole_sims + max_sims
    return np.argsort(-ensemble)


# Hybrid retrieval via Reciprocal Rank Fusion (RRF).
#
# BM25 captures lexical overlap (named entities, exact tokens, dates) that
# embeddings smooth over. all-MiniLM-L6-v2 captures semantic similarity that
# BM25 misses ("kitchen knives" ~ "chef's blade"). Each is partially right;
# fusion lets the two signals vote without one dominating.
#
# RRF score per doc d, given rankers r_1..r_n:
#   RRF(d) = sum_i 1 / (K + rank_i(d))
# K = 60 is the standard tuning constant from Cormack et al. 2009; high enough
# that the top-1 dominates moderately but not absolutely.
RRF_K = 60


def _rank_positions(order: np.ndarray, n: int) -> np.ndarray:
    pos = np.empty(n, dtype=np.int64)
    pos[order] = np.arange(n)
    return pos


def rank_hybrid(question: str, texts: list[str], **kw) -> np.ndarray:
    """Symmetric RRF fusion of BM25 and embed (1:1 weight). The naive starting
    point — useful as a diagnostic, but on this dataset embed is meaningfully
    stronger than BM25, so symmetric voting drags relevant embed-found docs out
    of top-5 when BM25 disagrees. See `rank_hybrid2` for the weighted variant.
    """
    n = len(texts)
    bm25_pos = _rank_positions(rank_bm25(question, texts), n)
    embed_pos = _rank_positions(rank_embed(question, texts), n)
    rrf = 1.0 / (RRF_K + bm25_pos) + 1.0 / (RRF_K + embed_pos)
    return np.argsort(-rrf)


def rank_hybrid2(question: str, texts: list[str], **kw) -> np.ndarray:
    """Weighted RRF: embed gets 2x weight vs BM25. Picks the right asymmetry
    when one ranker is reliably stronger than the other."""
    n = len(texts)
    bm25_pos = _rank_positions(rank_bm25(question, texts), n)
    embed_pos = _rank_positions(rank_embed(question, texts), n)
    rrf = 2.0 / (RRF_K + embed_pos) + 1.0 / (RRF_K + bm25_pos)
    return np.argsort(-rrf)


def rank_rerank(question: str, texts: list[str], top_k: int = 20, **kw) -> np.ndarray:
    """BM25 reranks within embed's top-K. Embed picks the candidate set (so we
    never lose embed-recall outside top-K), then BM25 votes inside that set to
    promote exact lexical matches. Output: BM25-reranked top-K, then embed's
    tail unchanged.
    """
    n = len(texts)
    embed_order = rank_embed(question, texts)
    if n <= 1:
        return embed_order

    head_idxs = embed_order[:top_k].tolist()
    head_texts = [texts[i] for i in head_idxs]

    # BM25 inside the top-K candidate set only
    head_order_local = rank_bm25(question, head_texts)
    bm25_pos_local = _rank_positions(head_order_local, len(head_idxs))
    embed_pos_local = np.arange(len(head_idxs))

    # Symmetric RRF inside the candidate set — embed already filtered, so
    # BM25 only contributes ordering signal here.
    rrf = 1.0 / (RRF_K + bm25_pos_local) + 1.0 / (RRF_K + embed_pos_local)
    head_reranked = np.argsort(-rrf)
    head_global = [head_idxs[i] for i in head_reranked]
    tail_global = embed_order[top_k:].tolist()
    return np.array(head_global + tail_global, dtype=np.int64)


def rank_emax_hybrid(question: str, texts: list[str], **kw) -> np.ndarray:
    """RRF fusion: emax (whole + max-field, weight 2) + BM25 (weight 1).
    Embed remains the dominant signal; BM25 adds lexical-exact tiebreaking
    for tokens (dates, names) the embedder smooths over.
    """
    n = len(texts)
    emax_pos = _rank_positions(rank_emax(question, texts), n)
    bm25_pos = _rank_positions(rank_bm25(question, texts), n)
    rrf = 2.0 / (RRF_K + emax_pos) + 1.0 / (RRF_K + bm25_pos)
    return np.argsort(-rrf)


RANKERS: dict[str, Callable] = {
    "bm25": rank_bm25,
    "embed": rank_embed,
    "mvembed": rank_mvembed,
    "mvmean": rank_mvmean,
    "emax": rank_emax,
    "emaxhyb": rank_emax_hybrid,
    "hybrid": rank_hybrid,
    "hybrid2": rank_hybrid2,
    "rerank": rank_rerank,
}


# --- Metrics ----------------------------------------------------------------

def recall_at_k(ranked_ids: list[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    return len(set(ranked_ids[:k]) & gold) / len(gold)


def hit_at_k(ranked_ids: list[str], gold: set[str], k: int) -> float:
    return 1.0 if (set(ranked_ids[:k]) & gold) else 0.0


def reciprocal_rank(ranked_ids: list[str], gold: set[str]) -> float:
    for i, sid in enumerate(ranked_ids, 1):
        if sid in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: list[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    dcg = sum(
        (1.0 / math.log2(i + 2)) for i, sid in enumerate(ranked_ids[:k]) if sid in gold
    )
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / ideal if ideal > 0 else 0.0


# --- Eval loop --------------------------------------------------------------

def load_cache(name: str) -> dict:
    path = CACHE_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def evaluate(
    dataset: list[dict],
    extractor_name: str,
    ranker_name: str,
    haiku_cache: dict | None = None,
    closets_cache: dict | None = None,
    limit: int | None = None,
) -> dict:
    extractor = EXTRACTORS[extractor_name]
    ranker = RANKERS[ranker_name]
    if limit:
        dataset = dataset[:limit]

    per_q = []
    by_type: dict[str, list[dict]] = defaultdict(list)
    skipped_no_gold = 0
    skipped_cache_miss = 0

    label = f"{extractor_name}:{ranker_name}"
    for ex in tqdm(dataset, desc=label):
        sids = ex["haystack_session_ids"]
        sessions = ex["haystack_sessions"]
        gold = set(ex["answer_session_ids"])
        gold_in_haystack = gold & set(sids)
        if not gold_in_haystack:
            skipped_no_gold += 1
            continue

        try:
            texts = [
                extractor(
                    s,
                    session_id=sid,
                    haiku_cache=haiku_cache or {},
                    closets_cache=closets_cache or {},
                )
                for sid, s in zip(sids, sessions)
            ]
        except RuntimeError:
            skipped_cache_miss += 1
            continue

        order = ranker(ex["question"], texts)
        ranked_sids = [sids[i] for i in order]

        m = {
            "qid": ex["question_id"],
            "qtype": ex["question_type"],
            "n_gold": len(gold_in_haystack),
            "n_haystack": len(sids),
            "hit@1": hit_at_k(ranked_sids, gold_in_haystack, 1),
            "hit@5": hit_at_k(ranked_sids, gold_in_haystack, 5),
            "hit@10": hit_at_k(ranked_sids, gold_in_haystack, 10),
            "r@5": recall_at_k(ranked_sids, gold_in_haystack, 5),
            "r@10": recall_at_k(ranked_sids, gold_in_haystack, 10),
            "mrr": reciprocal_rank(ranked_sids, gold_in_haystack),
            "ndcg@10": ndcg_at_k(ranked_sids, gold_in_haystack, 10),
        }
        per_q.append(m)
        by_type[ex["question_type"]].append(m)

    def avg(rows: list[dict], key: str) -> float:
        return sum(r[key] for r in rows) / len(rows) if rows else 0.0

    summary = {
        "strategy": label,
        "extractor": extractor_name,
        "ranker": ranker_name,
        "n_questions": len(per_q),
        "n_skipped_no_gold_in_haystack": skipped_no_gold,
        "n_skipped_cache_miss": skipped_cache_miss,
        "overall": {
            k: avg(per_q, k)
            for k in ("hit@1", "hit@5", "hit@10", "r@5", "r@10", "mrr", "ndcg@10")
        },
        "by_type": {
            qt: {
                "n": len(rows),
                **{k: avg(rows, k) for k in ("hit@5", "r@5", "r@10", "mrr", "ndcg@10")},
            }
            for qt, rows in by_type.items()
        },
        "per_q": per_q,
    }
    return summary


def fmt_pct(x: float) -> str:
    return f"{x*100:5.1f}%"


def print_summary(s: dict) -> None:
    print(f"\n=== {s['strategy']} ===")
    print(
        f"Questions: {s['n_questions']}  "
        f"(skipped no-gold: {s['n_skipped_no_gold_in_haystack']}, "
        f"cache-miss: {s['n_skipped_cache_miss']})"
    )
    o = s["overall"]
    print(
        f"Overall  Hit@1 {fmt_pct(o['hit@1'])}  Hit@5 {fmt_pct(o['hit@5'])}  "
        f"R@5 {fmt_pct(o['r@5'])}  R@10 {fmt_pct(o['r@10'])}  "
        f"MRR {o['mrr']:.3f}  NDCG@10 {o['ndcg@10']:.3f}"
    )
    print("By question type:")
    for qt, m in sorted(s["by_type"].items()):
        print(
            f"  {qt:30s} n={m['n']:3d}  Hit@5 {fmt_pct(m['hit@5'])}  "
            f"R@5 {fmt_pct(m['r@5'])}  MRR {m['mrr']:.3f}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dataset", choices=["s", "oracle"], default="s")
    parser.add_argument(
        "--strategies", nargs="+",
        default=["content:bm25", "summary:bm25", "firstmsg:bm25"],
        help="strategy strings <extractor>:<ranker>, e.g. content:bm25 haiku:embed",
    )
    parser.add_argument(
        "--save-as", default=None,
        help="results filename suffix (default: <dataset>)",
    )
    args = parser.parse_args()

    fname = "longmemeval_s" if args.dataset == "s" else "longmemeval_oracle"
    path = DATA_DIR / fname
    if not path.exists():
        print(f"ERROR: {path} not found. Run download.py first.", file=sys.stderr)
        sys.exit(2)

    print(f"Loading {fname}...")
    data = json.loads(path.read_text())
    print(f"Loaded {len(data)} questions.")

    haiku_cache = load_cache("haiku_summaries")
    closets_cache = load_cache("closets")
    if any("haiku" in s for s in args.strategies):
        print(f"Haiku cache loaded: {len(haiku_cache)} entries")
    if any("closets" in s for s in args.strategies):
        print(f"Closets cache loaded: {len(closets_cache)} entries")

    suffix = args.save_as or args.dataset

    all_overall = {}
    t0 = time.time()
    for strat in args.strategies:
        try:
            ext, rnk = strat.split(":")
        except ValueError:
            print(f"ERROR: bad strategy '{strat}', expected <extractor>:<ranker>")
            sys.exit(2)
        if ext not in EXTRACTORS:
            print(f"ERROR: unknown extractor '{ext}'. Have: {list(EXTRACTORS)}")
            sys.exit(2)
        if rnk not in RANKERS:
            print(f"ERROR: unknown ranker '{rnk}'. Have: {list(RANKERS)}")
            sys.exit(2)
        s = evaluate(
            data, ext, rnk,
            haiku_cache=haiku_cache, closets_cache=closets_cache,
            limit=args.limit,
        )
        print_summary(s)
        out = RESULTS_DIR / f"{ext}_{rnk}_{suffix}.json"
        out.write_text(json.dumps(s, indent=2))
        print(f"  -> wrote {out}")
        all_overall[strat] = s["overall"]

    print(f"\nTotal wallclock: {time.time()-t0:.1f}s")
    print("\nHeadline (R@5 / R@10 / MRR):")
    for strat, o in all_overall.items():
        print(f"  {strat:20s}  R@5 {fmt_pct(o['r@5'])}  R@10 {fmt_pct(o['r@10'])}  MRR {o['mrr']:.3f}")


if __name__ == "__main__":
    main()
