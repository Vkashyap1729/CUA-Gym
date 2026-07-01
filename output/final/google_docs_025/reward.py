#!/usr/bin/env python3
"""Reward for google_docs_025.

Task: Clean up the "Archive" workspace: delete "Draft A" and "Draft B",
but keep "Draft C".

Initial state:
  - documents: doc-1 "Draft A", doc-2 "Draft B", doc-3 "Draft C", doc-4 "Master Index"
  - comments: comment-1 (on doc-1), comment-2 (on doc-3)

Expected end state:
  - doc-1 and doc-2 removed from documents
  - doc-3 ("Draft C", required keep) and doc-4 ("Master Index", distractor) remain
  - comment-1 removed (cascade with deleted doc-1); comment-2 remains

Scoring is progressive and entirely based on exact state checks (no LLM judge
needed for a pure delete/keep task).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _title_of(doc):
    if isinstance(doc, dict):
        return (doc.get("title") or "").strip().lower()
    return ""


def _find_doc_by_title(documents, title):
    """Return (doc_id, doc) for the first document whose title matches, else (None, None)."""
    target = title.strip().lower()
    if not isinstance(documents, dict):
        return None, None
    for doc_id, doc in documents.items():
        if _title_of(doc) == target:
            return doc_id, doc
    return None, None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state") or {}
    documents = current.get("documents") or {}
    comments = current.get("comments") or []

    # Resolve document presence by title (robust to any re-keying the UI does).
    draft_a_id, draft_a = _find_doc_by_title(documents, "Draft A")
    draft_b_id, draft_b = _find_doc_by_title(documents, "Draft B")
    draft_c_id, draft_c = _find_doc_by_title(documents, "Draft C")
    master_id, master = _find_doc_by_title(documents, "Master Index")

    draft_a_deleted = draft_a is None
    draft_b_deleted = draft_b is None
    draft_c_present = draft_c is not None
    master_present = master is not None

    # Comment presence: comment-1 lives on the deleted doc (Draft A), comment-2 on Draft C.
    comment_ids = {c.get("id") for c in comments if isinstance(c, dict)}
    comment1_present = "comment-1" in comment_ids
    comment2_present = "comment-2" in comment_ids

    score = 0.0

    # Core deletions (the task-introduced change). 0.45 each.
    if draft_a_deleted:
        score += 0.45
    if draft_b_deleted:
        score += 0.45

    # Cascade: deleting Draft A should drop its comment (comment-1).
    if not comment1_present:
        score += 0.10

    # --- Over-action penalties (distractors / required-keep must be untouched) ---

    # "Draft C" must be kept. Deleting it defeats the explicit instruction -> reward 0.
    if not draft_c_present:
        score = 0.0

    # "Master Index" is a distractor doc not mentioned in the task; deleting it is over-action.
    if not master_present:
        score = max(0.0, score - 0.40)

    # comment-2 belongs to the kept Draft C; removing it is over-action.
    if not comment2_present:
        score = max(0.0, score - 0.10)

    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print(f"REWARD: {reward}")
