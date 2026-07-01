"""Reward for: Make a copy of "Policy Handbook", then rename the copy to "Policy Handbook 2025".

Progressive scoring (0.0-1.0). 0.0 on the initial (not-done) state, 1.0 when a single new
document exists titled "Policy Handbook 2025" with the same content/owner as the original,
while the original and the distractor doc are left untouched.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _norm(s):
    return (s or "").strip()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_docs = initial.get("documents", {}) or {}
    cur_docs = current.get("documents", {}) or {}

    # Locate the original "Policy Handbook" in the initial state (source of truth for content).
    orig_id = None
    orig_doc = None
    for did, doc in init_docs.items():
        if _norm(doc.get("title")) == "Policy Handbook":
            orig_id, orig_doc = did, doc
            break
    if orig_doc is None:
        # Fall back to the documented id from the task context.
        orig_doc = init_docs.get("doc-1", {}) or {}
        orig_id = "doc-1"
    orig_content = orig_doc.get("content", "")

    # New document entries (ids present now that were absent initially).
    new_ids = [did for did in cur_docs if did not in init_docs]

    score = 0.0

    # --- Credit for the copy ---------------------------------------------------
    if new_ids:
        # Prefer the new doc that already carries the target title; else the first.
        candidate_id = None
        for did in new_ids:
            if _norm(cur_docs[did].get("title")) == "Policy Handbook 2025":
                candidate_id = did
                break
        if candidate_id is None:
            candidate_id = new_ids[0]
        cand = cur_docs[candidate_id]

        # A new entry exists at all.
        score += 0.25

        # Renamed to the exact target title.
        if _norm(cand.get("title")) == "Policy Handbook 2025":
            score += 0.30

        # Content carried over from the original (true copy, not a blank new doc).
        if cand.get("content", "") == orig_content and orig_content != "":
            score += 0.30

        # Owner is the acting user.
        if cand.get("ownerId") == orig_doc.get("ownerId", "user-1"):
            score += 0.15

    # --- Over-action penalties (distractors must be untouched) -----------------
    # Original "Policy Handbook" must remain, with its title and content unchanged.
    cur_orig = cur_docs.get(orig_id, {}) or {}
    orig_intact = (
        _norm(cur_orig.get("title")) == "Policy Handbook"
        and cur_orig.get("content", "") == orig_content
    )
    if not orig_intact:
        score *= 0.5

    # Distractor doc-2 "Org Chart" must be untouched (present, same title).
    init_d2 = init_docs.get("doc-2")
    if init_d2 is not None:
        cur_d2 = cur_docs.get("doc-2")
        if cur_d2 is None or _norm(cur_d2.get("title")) != _norm(init_d2.get("title")):
            score *= 0.5

    # Exactly one new entry expected; extra new docs are over-action.
    if len(new_ids) > 1:
        score *= 0.5

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 2)))


if __name__ == "__main__":
    main()
