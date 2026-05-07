"""Print a markdown table row for a single benchmark result JSON.

Usage:  python print_summary_row.py results/closets_embed_oracle-haiku.json
"""
import json
import sys

d = json.loads(open(sys.argv[1]).read())
o = d["overall"]
print(
    f"| `{d['strategy']}` | "
    f"{o['r@5']*100:.1f}% | "
    f"{o['r@10']*100:.1f}% | "
    f"{o['mrr']:.3f} | "
    f"{o['hit@5']*100:.1f}% |"
)
