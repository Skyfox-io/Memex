"""Download LongMemEval-S subset from HuggingFace to data/."""
import json
import os
from pathlib import Path
from huggingface_hub import hf_hub_download

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REPO_ID = "xiaowu0162/longmemeval"
FILES = ["longmemeval_s", "longmemeval_oracle"]

for fname in FILES:
    print(f"Downloading {fname}...")
    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=fname,
        repo_type="dataset",
        local_dir=str(DATA_DIR),
    )
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  -> {path} ({size_mb:.1f} MB)")

print("\nDataset shapes:")
for fname in FILES:
    path = DATA_DIR / fname
    # files have no extension; try JSON first, fall back to JSONL
    raw = path.read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]
    print(f"  {fname}: {len(data)} questions")
    if data:
        ex = data[0]
        print(f"    keys: {list(ex.keys())}")
        if "haystack_sessions" in ex:
            print(f"    haystack_sessions: {len(ex['haystack_sessions'])} sessions")
        if "answer_session_ids" in ex:
            print(f"    answer_session_ids: {ex['answer_session_ids'][:5]}{'...' if len(ex['answer_session_ids'])>5 else ''}")
        if "question_type" in ex:
            print(f"    question_type: {ex['question_type']}")
