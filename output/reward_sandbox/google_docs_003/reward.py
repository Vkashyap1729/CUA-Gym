#!/usr/bin/env python3
"""Reward for google_docs_003: delete the document "Old Draft v1".

Task: Delete the document called "Old Draft v1".
Ground truth:
  INITIAL  -> documents: doc-1 "Old Draft v1", doc-2 "Old Draft v2", doc-3 "Final Report"
              comments:  comment-1 (on doc-1), comment-2 (on doc-2)
  EXPECTED -> doc-1 removed from documents; comment-1 removed from comments.
              doc-2, doc-3 and comment-2 must remain (distractors -> over-action penalty).

Scoring is progressive and scores ONLY the task-introduced change (deleting "Old Draft v1").
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
TARGET_TITLE = "Old Draft v1"


def _read_sid():
    with open("/tmp/task_web_sid", "r") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_doc_by_title(documents, title):
    """Return list of (doc_id, doc) whose title matches `title`."""
    matches = []
    for doc_id, doc in (documents or {}).items():
        if isinstance(doc, dict) and doc.get("title") == title:
            matches.append((doc_id, doc))
    return matches


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state", {}) or {}
    documents = current.get("documents", {}) or {}
    comments = current.get("comments", []) or []

    score = 0.0

    # --- Identify the target document ("Old Draft v1") in the CURRENT state. ---
    target_matches = _find_doc_by_title(documents, TARGET_TITLE)
    target_present = len(target_matches) > 0

    # Distractor documents that must REMAIN (over-action guards).
    has_v2 = len(_find_doc_by_title(documents, "Old Draft v2")) > 0
    has_final = len(_find_doc_by_title(documents, "Final Report")) > 0

    # comment-2 (the distractor comment on doc-2) must remain.
    comment2_present = any(
        isinstance(c, dict) and c.get("id") == "comment-2" for c in comments
    )
    # comment-1 (attached to the deleted doc) must be gone.
    comment1_present = any(
        isinstance(c, dict) and c.get("id") == "comment-1" for c in comments
    )

    # --- Main criterion: the target document is deleted (0.6). ---
    if not target_present:
        score += 0.6

    # --- Cascade: comment-1 (belonging to the deleted doc) removed (0.2). ---
    # Only meaningful once the doc itself is gone; reward the cascade either way
    # since deleting a doc should clear its comments.
    if not comment1_present:
        score += 0.2

    # --- Over-action guard: distractor docs / comment must be untouched (0.2). ---
    # Award only when the task work has actually started (target removed); on the
    # initial state these are all present but the task is not done, so the main
    # criterion keeps the total at 0.0 there.
    distractors_intact = has_v2 and has_final and comment2_present
    if distractors_intact and not target_present:
        score += 0.2

    # Hard over-action penalty: if a required distractor document was deleted,
    # cap the reward — we never reward destroying the wrong document.
    if not has_v2 or not has_final or not comment2_present:
        score = min(score, 0.4)

    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 1)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: {:.1f}".format(reward))
