"""
Compare two strategy result files via paired bootstrap CI.

For two strategies A and B evaluated on the same 500 questions, computes
the 95% CI of (A-B) on R@5, MRR, and NDCG@10 by resampling questions with
replacement N=10000 times. If the CI does not contain 0, the difference
is significant at p < 0.05.

Usage:
  python compare.py results/summary_bm25_s.json results/summary_embed_s.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


def paired_bootstrap_ci(
    a_per_q: list[dict],
    b_per_q: list[dict],
    metric: str,
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    """Returns (mean_diff, ci_low, ci_high, p_two_sided)."""
    a_by_qid = {r["qid"]: r[metric] for r in a_per_q}
    b_by_qid = {r["qid"]: r[metric] for r in b_per_q}
    common = sorted(set(a_by_qid) & set(b_by_qid))
    diffs = [a_by_qid[q] - b_by_qid[q] for q in common]
    n = len(diffs)
    if n == 0:
        return (0.0, 0.0, 0.0, 1.0)

    rng = random.Random(seed)
    boot_means = []
    for _ in range(n_resamples):
        # paired resample: draw indices with replacement
        idxs = [rng.randint(0, n - 1) for _ in range(n)]
        boot_means.append(sum(diffs[i] for i in idxs) / n)
    boot_means.sort()

    mean = sum(diffs) / n
    lo = boot_means[int(n_resamples * alpha / 2)]
    hi = boot_means[int(n_resamples * (1 - alpha / 2))]

    # two-sided p: fraction of bootstrap means with opposite sign of mean
    if mean >= 0:
        p = sum(1 for m in boot_means if m <= 0) / n_resamples
    else:
        p = sum(1 for m in boot_means if m >= 0) / n_resamples
    p = min(p * 2, 1.0)  # two-sided

    return (mean, lo, hi, p)


def fmt_pct(x: float) -> str:
    return f"{x*100:+5.2f}pp"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("a", help="results JSON A (the candidate)")
    parser.add_argument("b", help="results JSON B (the baseline)")
    parser.add_argument("--metrics", nargs="+",
                        default=["r@5", "r@10", "mrr", "ndcg@10", "hit@5"])
    parser.add_argument("--by-type", action="store_true",
                        help="break down by question_type")
    args = parser.parse_args()

    a = json.loads(Path(args.a).read_text())
    b = json.loads(Path(args.b).read_text())

    print(f"\nA: {a['strategy']}  ({a['n_questions']} questions)")
    print(f"B: {b['strategy']}  ({b['n_questions']} questions)")
    print(f"Diff = A - B (positive = A wins)\n")

    print(f"{'metric':10s}  {'A':>7s}   {'B':>7s}   {'Δ':>9s}   {'95% CI':>20s}   {'p':>6s}   sig")
    print("-" * 80)
    for m in args.metrics:
        mean, lo, hi, p = paired_bootstrap_ci(a["per_q"], b["per_q"], m)
        a_overall = a["overall"][m]
        b_overall = b["overall"][m]
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        ci_str = f"[{lo*100:+5.2f}, {hi*100:+5.2f}]"
        print(
            f"{m:10s}  {a_overall*100:6.2f}%  {b_overall*100:6.2f}%   "
            f"{fmt_pct(mean)}   {ci_str:>20s}   {p:6.3f}   {sig}"
        )

    if args.by_type:
        # group per-q rows by qtype, then bootstrap within each
        from collections import defaultdict
        a_by_t = defaultdict(list)
        b_by_t = defaultdict(list)
        for r in a["per_q"]:
            a_by_t[r["qtype"]].append(r)
        for r in b["per_q"]:
            b_by_t[r["qtype"]].append(r)

        print("\nBy question type (R@5):")
        for qt in sorted(set(a_by_t) | set(b_by_t)):
            mean, lo, hi, p = paired_bootstrap_ci(a_by_t[qt], b_by_t[qt], "r@5")
            a_v = sum(r["r@5"] for r in a_by_t[qt]) / max(len(a_by_t[qt]), 1)
            b_v = sum(r["r@5"] for r in b_by_t[qt]) / max(len(b_by_t[qt]), 1)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(
                f"  {qt:30s} A={a_v*100:5.1f}%  B={b_v*100:5.1f}%  "
                f"Δ={mean*100:+5.2f}pp  p={p:.3f}  {sig}"
            )


if __name__ == "__main__":
    main()
