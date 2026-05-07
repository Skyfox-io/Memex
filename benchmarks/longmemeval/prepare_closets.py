"""
Generate heuristic closets-style entries for every unique session in the
LongMemEval datasets and cache them to cache/closets.json.

A closets entry simulates what /memex:session-end writes per file: an
enumeration of distinct subjects, named entities, decisions, and verbatim
user claims, capped at ~1500 chars. Heuristic version (no LLM) extracts:

  - subjects: noun phrases / sentence openers from user turns
  - people: capitalized 2-word patterns ("Alice Smith", "Mike")
  - claims: sentences starting with "I am", "I have", "I prefer", "I'm",
            "my <noun>", or containing "called X" / "named X"
  - decisions: assistant lines containing decision-language

This is a deterministic floor for the closets retrieval strategy. The
LLM-curated version (Haiku, run separately) is the production-faithful upper
bound.

Usage:
  python prepare_closets.py [--dataset s|oracle] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "closets.json"

CAP_PER_ENTRY = 1500
CAPITALIZED = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
CLAIM_PATTERNS = [
    # Identity / state
    re.compile(r"\bI\s+(?:am|'m)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\bI\s+(?:have|'ve)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\bI\s+(?:was|wasn't|used to)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Preferences / desires (the existing pattern, kept)
    re.compile(r"\bI\s+(?:prefer|like|want|need|love|hate|enjoy|dislike|adore|miss)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Possessives + copula ("my brother is X", "my dog's name was Y")
    re.compile(r"\bmy\s+\w+(?:'s\s+\w+)?\s+(?:is|are|was|were|isn't|aren't|wasn't|weren't)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Activity / occupation / location
    re.compile(r"\bI\s+(?:work|live|grew up|came from|moved|study|train|practice)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\bI\s+(?:went|got|bought|made|tried|visited|saw|met|joined|started|stopped|quit)\s+[^.?!]{2,80}", re.IGNORECASE),
    # "I'm a X", "I'm an X" — narrower than the generic "I'm" pattern but more retrievable
    re.compile(r"\bI'?m\s+(?:a|an)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Naming / introductions
    re.compile(r"\b(?:named|called|name is|nicknamed)\s+[A-Z]\w+(?:\s+[A-Z]\w+)?", re.IGNORECASE),
    # Allergies / health / dietary
    re.compile(r"\ballergic\s+to\s+[\w\s]{2,40}", re.IGNORECASE),
    re.compile(r"\bI\s+can'?t\s+(?:eat|drink|have|stand|stomach|tolerate)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Numeric facts: "3 kids", "two cats", "$50/month", "5 years old"
    re.compile(r"\b\d+(?:\.\d+)?\s+(?:kids?|children|cats?|dogs?|years?\s+old|months?\s+old|siblings?|brothers?|sisters?|hours?|miles?|pounds?|kg|lbs)\b", re.IGNORECASE),
]
DECISION_PATTERNS = [
    # Active decision verbs
    re.compile(r"\bI\s+(?:decided|chose|picked|went with|opted)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Plans / intentions
    re.compile(r"\b(?:going|planning|plan)\s+(?:to|with)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\bI'?ll\s+(?:go|try|use|switch|stick|stay|start|stop)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Switches / reversals
    re.compile(r"\b(?:switched|switching|moving|migrated)\s+(?:to|from)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\b(?:rejected|abandoned|gave up on|dropped|ditched|removed)\s+[^.?!]{2,80}", re.IGNORECASE),
    re.compile(r"\b(?:trying|testing|evaluating)\s+[A-Z]\w+\b[^.?!]{0,40}"),  # only with capitalized following thing — proper noun product/service
    # Negative decisions
    re.compile(r"\b(?:won'?t|will not|don'?t want to|not going to)\s+[^.?!]{2,80}", re.IGNORECASE),
    # Preference choices ("X over Y")
    re.compile(r"\b\w+\s+over\s+\w+(?:\s+\w+){0,3}", re.IGNORECASE),
]
# Date/time patterns. Temporal-reasoning questions (LongMemEval-S category, n=133)
# need to retrieve sessions by the dates they mention. Without these, the closet
# entry has no temporal signal — the embedder can match topical similarity but
# cannot disambiguate "what did I plan for September" from "what did I plan for March."
DATE_PATTERNS = [
    # Months EXCEPT May. May is split into a case-sensitive pattern below to avoid
    # the modal-verb collision ("may help", "may ask"). Other months don't have
    # this ambiguity; we keep them case-insensitive for things like "march" at
    # sentence start lowercased.
    re.compile(
        r"\b(?:January|February|March|April|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b[^.,!?\n;:]{0,30}",
        re.IGNORECASE,
    ),
    # May — case-sensitive ONLY to avoid catching the modal verb. "May 15", "May 2024",
    # "next May", "by May" all preserve capitalization in normal usage.
    re.compile(r"\bMay\b[^.,!?\n;:]{0,30}"),
    # Standalone years (1990-2099) — temporal anchors
    re.compile(r"\b(?:19[89]\d|20[0-9]\d)\b"),
    # Day names with up to ~20 chars of context ("next Tuesday", "Monday morning")
    re.compile(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b[^.,!?\n;:]{0,20}",
        re.IGNORECASE,
    ),
    # Relative time expressions
    re.compile(
        r"\b(?:yesterday|tomorrow|today|tonight|this morning|this afternoon|this evening|"
        r"last night|next week|last week|this week|next month|last month|this month|"
        r"next year|last year|this year|next weekend|last weekend|this weekend)\b",
        re.IGNORECASE,
    ),
    # "N days/weeks/months/years ago/from now/later"
    re.compile(
        r"\b\d+\s+(?:days?|weeks?|months?|years?|hours?|minutes?)\s+"
        r"(?:ago|from\s+now|later|before|after)\b",
        re.IGNORECASE,
    ),
    # Numeric dates: M/D, M/D/YY, M/D/YYYY, ISO YYYY-MM-DD
    re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    # Times: 12-hour (3pm, 3:30pm) and 24-hour (15:30)
    re.compile(r"\b(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:am|pm|AM|PM)\b"),
    re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"),
]
COMMON_NAMES_BLOCK = {
    "I", "We", "You", "They", "He", "She", "It",
    "My", "Your", "Our", "Their", "His", "Her",
    "And", "Or", "But", "So", "Then", "Now", "Today", "Yesterday", "Tomorrow",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "If", "When", "Where", "What", "Why", "How", "The",
}


RELATION_INTRO_PATTERN = re.compile(
    r"\bmy\s+(?:brother|sister|cousin|friend|coworker|colleague|manager|boss|partner|husband|wife|"
    r"boyfriend|girlfriend|son|daughter|mom|dad|mother|father|uncle|aunt|nephew|niece|grandma|"
    r"grandpa|grandmother|grandfather|roommate|neighbor|teammate|classmate|teacher|doctor|"
    r"therapist|trainer|coach|landlord)\s+(?:named\s+|called\s+)?([A-Z][a-z]{2,15}|[a-z]{3,15})\b",
    re.IGNORECASE,
)
NAMED_INTRO_PATTERN = re.compile(
    r"\b(?:named|called)\s+([A-Z][a-z]{2,15}(?:\s+[A-Z][a-z]{2,15})?)",
    re.IGNORECASE,
)


def extract_people(text: str, top_n: int = 8) -> list[str]:
    """Combine three signals:

    1. Capitalized 1-3-word patterns, frequency-ranked (existing). Catches names
       written normally in prose: "Mike came over", "Lisa Johnson called".
    2. Lowercase introductions via relation words: "my brother mike", "my friend
       named lisa". The lowercase form is what people actually type in chat.
    3. Explicit naming patterns: "named Alice", "called Bob". These are
       high-precision signals.

    Common false positives (sentence-start words, day names, months) are blocked.
    Single-word lowercase candidates are only kept if they came from an explicit
    introduction pattern, never from raw capitalization.
    """
    counter = Counter()

    # Signal 1: capitalized phrases (existing logic)
    for m in CAPITALIZED.findall(text):
        if m.split()[0] in COMMON_NAMES_BLOCK:
            continue
        if len(m) < 3:
            continue
        counter[m] += 2  # weight capitalized matches higher

    # Signal 2: relation-introduced names (covers lowercase chat-style)
    for m in RELATION_INTRO_PATTERN.findall(text):
        name = m.strip().title()  # normalize "mike" -> "Mike"
        if not name or name in COMMON_NAMES_BLOCK:
            continue
        if len(name) < 3:
            continue
        counter[name] += 3  # high-confidence pattern

    # Signal 3: explicit "named X" / "called X" patterns
    for m in NAMED_INTRO_PATTERN.findall(text):
        name = m.strip().title()
        if not name or name in COMMON_NAMES_BLOCK:
            continue
        counter[name] += 3

    return [name for name, _ in counter.most_common(top_n)]


def extract_claims(text: str, max_n: int = 6) -> list[str]:
    out = []
    seen = set()
    for pat in CLAIM_PATTERNS:
        for m in pat.findall(text):
            phrase = m.strip().rstrip(".,!?")
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(phrase)
            if len(out) >= max_n:
                return out
    return out


def extract_decisions(text: str, max_n: int = 4) -> list[str]:
    out = []
    seen = set()
    for pat in DECISION_PATTERNS:
        for m in pat.findall(text):
            phrase = m.strip().rstrip(".,!?")
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(phrase)
            if len(out) >= max_n:
                return out
    return out


def extract_dates(text: str, max_n: int = 10) -> list[str]:
    """Extract distinct date/time mentions. Phrases are normalized (whitespace
    collapsed, trailing punctuation stripped) and case-folded for dedup so that
    'Tuesday' and 'tuesday' don't both appear.
    """
    out = []
    seen = set()
    for pat in DATE_PATTERNS:
        for m in pat.findall(text):
            phrase = re.sub(r"\s+", " ", m.strip().rstrip(".,!?;:"))
            if len(phrase) < 3:
                continue
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(phrase)
            if len(out) >= max_n:
                return out
    return out


QUOTED_STRING_PATTERN = re.compile(r'"([^"\n]{4,80})"')
LIST_ITEM_PATTERN = re.compile(r"(?m)^\s*(?:[-*]|\d+\.)\s+(.{4,100})$")
HEADING_PATTERN = re.compile(r"(?m)^\s*#{1,4}\s+(.{3,80})$")
ALLCAPS_TOKEN_PATTERN = re.compile(r"\b[A-Z]{2,15}(?:[-_][A-Z]{1,15})?\b")


def extract_subjects(session: list[dict], max_n: int = 12) -> list[str]:
    """Multi-signal topical extraction. Earlier version only took the first
    sentence of each user turn, which missed mid-message topics, list items,
    and quoted facts. This version layers in:

    1. First sentence of each user turn (existing baseline — captures opening topic).
    2. Quoted strings ("the user wrote 'X'" — verbatim recall is the highest-value
       signal for retrieval; questions often reference the user's exact words).
    3. List items / bullet points — sessions where the user enumerates options.
    4. Markdown headings — explicit topic markers in agent or user messages.
    5. ALLCAPS tokens (acronyms, project names like "MoMA", "API", "GPT-4") — these
       are strong proper-noun-shaped retrieval anchors.

    Dedup is case-folded; first occurrence wins on ordering.
    """
    out: list[str] = []
    seen: set[str] = set()

    def add(phrase: str) -> bool:
        phrase = phrase.strip().rstrip(".,!?;:")
        if len(phrase) < 4:
            return False
        key = phrase.lower()
        if key in seen:
            return False
        seen.add(key)
        out.append(phrase)
        return len(out) >= max_n

    # Signal 1: first sentence of each user turn (preserves earlier behavior)
    for t in session:
        if t.get("role") != "user":
            continue
        content = t.get("content", "").strip()
        if not content:
            continue
        first_sentence = SENTENCE_SPLIT.split(content)[0]
        if add(first_sentence[:120]):
            return out

    # Signal 2: quoted strings (across all turns — assistant may quote user back)
    full_text = "\n".join(t.get("content", "") for t in session)
    for q in QUOTED_STRING_PATTERN.findall(full_text):
        if add(q):
            return out

    # Signal 3: list items
    for li in LIST_ITEM_PATTERN.findall(full_text):
        if add(li):
            return out

    # Signal 4: markdown headings
    for h in HEADING_PATTERN.findall(full_text):
        if add(h):
            return out

    # Signal 5: ALLCAPS tokens (acronyms, project names). Limit to top frequency.
    caps_counter = Counter(ALLCAPS_TOKEN_PATTERN.findall(full_text))
    # Filter common pronoun/word artifacts that happen to be all-caps short
    caps_block = {"I", "AM", "PM", "OK", "TO", "OF", "AT", "IS", "AS", "BY", "OR", "AND", "THE", "A", "AN"}
    for tok, _ in caps_counter.most_common(8):
        if tok in caps_block:
            continue
        if add(tok):
            return out

    return out


def session_to_closet_entry(session: list[dict]) -> str:
    """Render a heuristic closets-style entry."""
    user_text = "\n".join(t.get("content", "") for t in session if t.get("role") == "user")
    asst_text = "\n".join(t.get("content", "") for t in session if t.get("role") == "assistant")
    full = user_text + "\n" + asst_text

    subjects = extract_subjects(session)
    people = extract_people(full)
    claims = extract_claims(user_text)
    decisions = extract_decisions(asst_text + "\n" + user_text)
    dates = extract_dates(full)

    parts = []
    if subjects:
        parts.append("subjects: " + "; ".join(subjects))
    if people:
        parts.append("people: " + ", ".join(people))
    if claims:
        parts.append("claims: " + "; ".join(claims))
    if decisions:
        parts.append("decisions: " + "; ".join(decisions))
    if dates:
        parts.append("dates: " + "; ".join(dates))

    out = " | ".join(parts)
    if len(out) > CAP_PER_ENTRY:
        out = out[:CAP_PER_ENTRY] + "..."
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["s", "oracle"], default="s")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    fname = "longmemeval_s" if args.dataset == "s" else "longmemeval_oracle"
    path = DATA_DIR / fname
    if not path.exists():
        print(f"ERROR: {path} not found. Run download.py first.", file=sys.stderr)
        sys.exit(2)

    data = json.loads(path.read_text())

    cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    print(f"Cache loaded: {len(cache)} entries.")

    seen = set()
    todo = []
    for ex in data:
        for sid, sess in zip(ex["haystack_session_ids"], ex["haystack_sessions"]):
            if sid in seen:
                continue
            seen.add(sid)
            if sid not in cache:
                todo.append((sid, sess))

    if args.limit:
        todo = todo[: args.limit]

    print(f"Generating closets for {len(todo)} sessions...")
    for i, (sid, sess) in enumerate(todo):
        cache[sid] = session_to_closet_entry(sess)
        if i % 1000 == 999:
            CACHE_FILE.write_text(json.dumps(cache))

    CACHE_FILE.write_text(json.dumps(cache))
    print(f"Done. Cache now {len(cache)} entries.")
    if cache:
        import random
        for sid in random.sample(list(cache), min(2, len(cache))):
            print(f"\n[{sid}]")
            print(f"  {cache[sid][:300]}")


if __name__ == "__main__":
    main()
