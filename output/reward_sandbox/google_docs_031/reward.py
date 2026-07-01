#!/usr/bin/env python3
"""Reward for: create a new meeting-notes document titled "All-Hands 2025-06"
and share it with both Alice (user-2) and Bob (user-3) as viewers.

Scoring (progressive, 0.0-1.0):
  - 0.30  exactly one new document was created (current docs = initial docs + 1)
  - 0.20  the new document's title equals "All-Hands 2025-06"
  - 0.10  the new document is owned by user-1
  - 0.20  the new document is shared with user-2 (Alice) as viewer
  - 0.20  the new document is shared with user-3 (Bob) as viewer
Over-action guard: the pre-existing document doc-1 ("Last All-Hands") must be
untouched (title, ownerId, sharedWith). Any modification to it zeroes the score.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
TARGET_TITLE = "All-Hands 2025-06"
OWNER_ID = "user-1"
EXPECTED_VIEWERS = {"user-2", "user-3"}


def _norm(s):
    return (s or "").strip().lower()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    initial_state = data.get("initial_state") or {}
    current_state = data.get("current_state") or {}

    initial_docs = initial_state.get("documents") or {}
    current_docs = current_state.get("documents") or {}

    score = 0.0

    # --- Over-action guard: doc-1 must be untouched ---------------------------
    init_doc1 = initial_docs.get("doc-1")
    cur_doc1 = current_docs.get("doc-1")
    if init_doc1 is not None:
        if cur_doc1 is None:
            print("doc-1 was deleted -> over-action")
            print("REWARD: 0.0")
            return
        for field in ("title", "ownerId", "content"):
            if init_doc1.get(field) != cur_doc1.get(field):
                print(f"doc-1 field '{field}' modified -> over-action")
                print("REWARD: 0.0")
                return
        if (init_doc1.get("sharedWith") or []) != (cur_doc1.get("sharedWith") or []):
            print("doc-1 sharedWith modified -> over-action")
            print("REWARD: 0.0")
            return

    # --- Identify newly created documents -------------------------------------
    new_ids = [doc_id for doc_id in current_docs if doc_id not in initial_docs]

    if not new_ids:
        print("No new document created yet.")
        print("REWARD: 0.0")
        return

    if len(new_ids) > 1:
        # Over-action: created more than one document. Only credit if exactly one
        # of them is the genuine target; otherwise treat as over-action.
        print(f"Warning: {len(new_ids)} new documents created (expected 1).")

    # Choose the candidate that best matches the target title; fall back to first.
    def title_match(doc_id):
        return _norm(current_docs[doc_id].get("title")) == _norm(TARGET_TITLE)

    matching = [d for d in new_ids if title_match(d)]
    if matching:
        new_doc = current_docs[matching[0]]
    else:
        new_doc = current_docs[new_ids[0]]

    # Penalize if extra (non-target) documents were created.
    over_creation = len(new_ids) > 1
    creation_credit = 0.30 if not over_creation else 0.15
    score += creation_credit

    # --- Title -----------------------------------------------------------------
    if _norm(new_doc.get("title")) == _norm(TARGET_TITLE):
        score += 0.20
    else:
        print(f"Title mismatch: got {new_doc.get('title')!r}")

    # --- Owner -----------------------------------------------------------------
    if new_doc.get("ownerId") == OWNER_ID:
        score += 0.10
    else:
        print(f"Owner mismatch: got {new_doc.get('ownerId')!r}")

    # --- Sharing ---------------------------------------------------------------
    shared = new_doc.get("sharedWith") or []
    viewer_ids = {
        e.get("userId")
        for e in shared
        if isinstance(e, dict) and e.get("permission") == "viewer"
    }
    if "user-2" in viewer_ids:
        score += 0.20
    else:
        print("Alice (user-2) not shared as viewer.")
    if "user-3" in viewer_ids:
        score += 0.20
    else:
        print("Bob (user-3) not shared as viewer.")

    score = max(0.0, min(1.0, round(score, 4)))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
