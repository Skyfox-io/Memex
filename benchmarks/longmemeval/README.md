# Memex on LongMemEval-S

Reproducible retrieval-recall benchmark for Memex's hub-and-spoke retrieval, run against the 500-question [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval) subset (Wu et al., ICLR 2025, [arXiv:2410.10813](https://arxiv.org/abs/2410.10813)).

The point: get a real, comparable number for *"does Memex find the right session in its top K?"*, without spending money on judge models or end-to-end QA.

## Important: this is retrieval recall, not end-to-end QA accuracy

Recall@5 is a retrieval metric. It answers *"did the right session appear in the top 5 retrieved candidates?"* — nothing more. It does **not** measure whether the system answered the question correctly.

The published [LongMemEval leaderboard](https://github.com/xiaowu0162/LongMemEval) uses an end-to-end retrieve-then-generate pipeline scored by a GPT-4o judge. That's a different, harder evaluation that costs money to run. The numbers reported in this README are not directly comparable to leaderboard QA-accuracy numbers; they live one step earlier in the pipeline.

Why we report retrieval recall: closets affect retrieval. The benchmark isolates the stage Memex actually changes. End-to-end QA accuracy depends on the answering model and prompting, which Memex doesn't own. Reporting retrieval cleanly separates the contribution.

What the comparison to BM25 means: the standard `content:bm25` baseline indexes the entire raw session text and lands at ~90.6% R@5 on this dataset. The closets-format index gets within 0.5pp of that at roughly 1/10th the size. The story is **competitive recall at a much smaller index**, not "we beat keyword search." Anyone who claims either against a different evaluation class (e.g., systems indexing with ChromaDB and dense embeddings) is comparing different cost structures.

End-to-end QA accuracy on LongMemEval-S is on the roadmap. It would close the gap with leaderboard numbers but adds API cost and judge-model dependency. Not a v2.x deliverable.

## Headline

| Strategy | R@5 | R@10 | MRR | NDCG@10 | Hit@5 |
|---|---|---|---|---|---|
| **`closets:emax`** (production v2 proxy, multi-vector ensemble) | **90.1%** | **94.6%** | **0.880** | **0.871** | **96.4%** |
| `closets:embed` (single-vector baseline) | 87.9% | 92.9% | 0.858 | — | 95.0% |
| `content:bm25` (full-text upper bound) | 90.6% | 94.6% | 0.905 | 0.892 | 96.8% |

500 questions. ~3-5 minutes wallclock for `emax`. **$0.** No API keys, all local.

### What that means

`closets:emax` lands at 90.1% R@5, within 0.5pp of the upper bound represented by `content:bm25`, which indexes the entire raw session text. The closets representation achieves nearly the same retrieval quality at roughly **1/10th the size**, with each field (`subjects`, `people`, `claims`, `decisions`, `dates`) explicitly typed so an LLM's attention can zoom to the right line for a question.

### What we ship to get here

- **No hosted services, no API keys at retrieval time.** The benchmark runs offline.
- **No learned vector index.** No FAISS, no HNSW, no ChromaDB. Cosine over a small in-memory matrix.
- **No proprietary database.** No SQLite schemas, no Postgres, no pgvector. The closets file IS the index: plain markdown, ~30 entries × ~1 KB.
- **Lightweight Python deps:** `numpy`, `rank_bm25`, `sentence-transformers` (with `all-MiniLM-L6-v2`, ~90 MB on first run). No GPU required.

Production Memex performs LLM-mediated retrieval over the same closets at session-start, so this benchmark is a deterministic proxy for how well Memex actually retrieves on a real workspace, without a judge model or end-to-end QA cost.

## What the benchmark measures

A LongMemEval-S question gives the system a *haystack* of ~54 conversation sessions plus a question that can only be answered by retrieving the right session(s). The benchmark scores how well a retriever ranks the correct sessions in its top K.

Memex retrieves by scanning *closets*: per-hub `_CLOSETS.md` files that enumerate every file's distinct subjects, named entities, verbatim claims, decisions, dates, and status. To score this deterministically without running a real LLM, the harness builds a synthetic closets entry for each session via deterministic regex extraction (`prepare_closets.py`), then ranks via BM25 or embedding cosine. The heuristic is a floor; the LLM-mediated production version writes richer closets and is expected to perform at least as well.

Strategy syntax is `<extractor>:<ranker>`:

| Extractor | What it indexes |
|---|---|
| `content` | Full session text — every turn concatenated. The "what if Claude could read everything" upper bound. |
| `summary` | Heuristic summary (first user msg + first assistant reply, 250 chars). |
| `firstmsg` | Just the first user message. |
| `closets` | Closets-format entry: typed fields (subjects, people, claims, decisions, dates), ~800 chars avg. |
| `haiku` | Haiku-written summary (cached on disk; see `prepare_haiku.py`). |

| Ranker | Method |
|---|---|
| `bm25` | Okapi BM25 over tokens. |
| `embed` | Cosine over `all-MiniLM-L6-v2` sentence-transformer embeddings (single vector per entry). |
| `mvembed` | Multi-vector with MAX pool over typed fields. Worse than `embed` (regresses -2.6pp R@5) — kept for ablation. |
| `mvmean` | Multi-vector with MEAN pool. Worse than `embed` (-1.0pp R@5) — kept for ablation. |
| `emax` | **Headline ranker.** Sum of (whole-entry single-vector similarity) + (max field-vector similarity). Compositional + specific-entity signals stack. |
| `hybrid` / `hybrid2` | RRF fusion of BM25 + embed (1:1 and 2:1 weight). On this dataset BM25's noise hurts R@5 — kept for ablation only. |
| `rerank` | BM25 reranking inside embed's top-20 candidate set. Kept for ablation. |

`closets:emax` is the production proxy. It models how an LLM's attention combines two signals: holistic semantic match across the entire closets entry (the compositional signal) and specific-field match (when a question targets a single entity, decision, or date, attention zooms to the matching typed line).

## Per-category breakdown (R@5)

LongMemEval-S has six question categories. `closets:emax` performance vs the
prior `closets:embed` baseline:

| Category | n | `closets:embed` (baseline) | `closets:emax` (current) | Δ |
|---|---|---|---|---|
| single-session-assistant | 56 | 100.0% | 100.0% | — |
| single-session-preference | 30 | 96.7% | 96.7% | — |
| knowledge-update | 78 | 90.4% | 95.5% | +5.1pp |
| single-session-user | 70 | 90.0% | 94.3% | +4.3pp |
| multi-session | 133 | 81.9% | 85.0% | +3.1pp |
| temporal-reasoning | 133 | 83.4% | 84.1% | +0.7pp |
| **overall** | 500 | **87.7%** | **90.1%** | **+2.4pp** |

Robustly positive across every category, no regressions. The biggest wins are
on knowledge-updates and multi-session, exactly the cases where structured
typed-field retrieval disambiguates better than a single squashed embedding.

## Cost discipline

LongMemEval-S (500 q × ~54 sessions = ~25,000 session instances, ~20,000 unique) is the **default target for free strategies** (BM25, local embeddings).

LongMemEval-Oracle (500 q × 3 sessions = 1,500 instances, ~1,000 unique) is the **default target for any LLM-backed strategy** (haiku-summary, future GPT-judge). Same diagnostic signal at <10% of the cost.

Full Haiku-summary on LongMemEval-S would cost ~$48 and is gated behind `--dataset s --confirm-cost` in `prepare_haiku.py`. The default Oracle pass costs ~$2-4 and gives the same diagnostic signal.

## Reproduce

```bash
cd benchmarks/longmemeval
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
    datasets rank_bm25 numpy tqdm huggingface_hub sentence-transformers anthropic
.venv/bin/python download.py
.venv/bin/python run_bench.py \
    --strategies closets:emax closets:embed closets:bm25 content:bm25 summary:embed summary:bm25
```

Per-strategy results land in `results/<extractor>_<ranker>_<dataset>.json` with full per-question metrics.

For statistical comparison between strategies:

```bash
.venv/bin/python compare.py \
    results/closets_embed_s.json \
    results/summary_embed_s.json \
    --by-type
```

Outputs paired-bootstrap 95% CIs and significance markers, computed on the same 500-question set.

## Files

| File | Purpose |
|---|---|
| `download.py` | Fetches LongMemEval-S + Oracle from HuggingFace |
| `run_bench.py` | Strategy registration, retrieval, R@K / MRR / NDCG@10 scoring |
| `compare.py` | Paired-bootstrap CI between any two strategy result files |
| `prepare_haiku.py` | Generates Haiku-written session summaries (Oracle by default; `--confirm-cost` for full S) |
| `prepare_closets.py` | Generates heuristic closets entries from raw sessions |
| `data/` | gitignored; the 280 MB LongMemEval-S JSON |
| `cache/` | gitignored; LLM summary cache by session_id |
| `results/` | gitignored; per-strategy result JSON |

## Limitations

- **Retrieval-only.** R@K is not QA accuracy (see top-of-file note). Closing retrieval doesn't guarantee Claude answers correctly with the retrieved context.
- **Not directly comparable to the LongMemEval leaderboard.** The leaderboard measures end-to-end QA accuracy with a GPT-4o judge. This harness measures retrieval recall, one stage earlier. Numbers from the two are in different units.
- **BM25 baseline is strong.** A `content:bm25` baseline that indexes raw session text hits ~90.6% R@5 on this dataset, ~0.5pp above closets. The closets argument is **size**, not raw recall: same retrieval at ~10× smaller index. Don't read the closets number as "we beat keyword search"; read it as "structured markdown + 1/10th the bytes is within noise of full-content keyword search."
- **Sessions vs files.** LongMemEval indexes by session; production Memex indexes by file. The mapping is 1:1 in this harness; a real Memex workspace splits content across hub files, so retrieval shape differs slightly at scale.
- **Deterministic closets.** The `closets:emax` 90.1% number uses `prepare_closets.py`'s regex-based extraction. That's the number we report.

## Roadmap

End-to-end QA accuracy (retrieve → generate → GPT-4o judge) is the right next benchmark. It would produce numbers directly comparable to the LongMemEval leaderboard at the cost of API spend and judge-model dependency. Not in v2.x. Tracked in the project's open work list.

## Source

- LongMemEval paper: [arXiv:2410.10813](https://arxiv.org/abs/2410.10813)
- LongMemEval repo: [xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval)
- Dataset (legacy, used by `download.py` for reproducibility of the 90.1% R@5 number): [HuggingFace xiaowu0162/longmemeval](https://huggingface.co/datasets/xiaowu0162/longmemeval)
- Dataset (cleaned variant the authors now recommend for new work): [HuggingFace xiaowu0162/longmemeval-cleaned](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned)
