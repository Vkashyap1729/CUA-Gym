#!/usr/bin/env python3
"""Reward for: Make a copy of the "Contract Template" document.

Scores ONLY the task-introduced change: a single new document that is a copy of
the original "Contract Template" (doc-1) titled "Copy of Contract Template",
with the same content and the same owner (user-1). Original doc-1 must be
unchanged and the distractor doc-2 ("Invoice") must be untouched.

Progressive (0.0-1.0):
  0.30  exactly one new document was created (over-action penalized)
  0.25  the new document's content matches the original's content
  0.25  the new document's title == "Copy of Contract Template"
  0.10  the new document's ownerId == user-1
  0.10  originals untouched: doc-1 unchanged AND doc-2 unchanged
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _norm(s):
    """Normalize HTML-ish content for forgiving comparison."""
    if s is None:
        return ""
    return " ".join(str(s).split()).strip().lower()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_docs = initial.get("documents", {}) or {}
    cur_docs = current.get("documents", {}) or {}

    # Locate the original "Contract Template" in the initial state.
    orig = None
    orig_id = None
    for did, doc in init_docs.items():
        if (doc or {}).get("title") == "Contract Template":
            orig = doc
            orig_id = did
            break
    if orig is None:
        # Fallback: the ground-truth original is doc-1.
        orig_id = "doc-1"
        orig = init_docs.get("doc-1", {}) or {}

    orig_content = _norm(orig.get("content"))

    # New documents = IDs present now but not in the initial state.
    new_ids = [did for did in cur_docs if did not in init_docs]

    score = 0.0

    # --- 0.30: exactly one new document created (over-action penalized) ---
    if len(new_ids) == 1:
        score += 0.30
    elif len(new_ids) == 0:
        # Nothing created yet -> not done.
        print(f"REWARD: {round(score, 2)}")
        return
    else:
        # More than one new doc created -> over-action. Try to still find the
        # intended copy among them, but withhold the "exactly one" credit.
        pass

    # Choose the best candidate copy among new docs: prefer one whose content
    # matches the original AND title looks like a copy.
    def candidate_key(did):
        d = cur_docs.get(did, {}) or {}
        content_ok = _norm(d.get("content")) == orig_content and orig_content != ""
        title = d.get("title") or ""
        title_ok = title == "Copy of Contract Template"
        title_close = "contract template" in title.lower()
        return (content_ok, title_ok, title_close)

    candidate_id = None
    if new_ids:
        candidate_id = max(new_ids, key=candidate_key)
    cand = cur_docs.get(candidate_id, {}) or {}

    # --- 0.25: content matches the original ---
    if orig_content != "" and _norm(cand.get("content")) == orig_content:
        score += 0.25

    # --- 0.25: title is exactly "Copy of Contract Template" ---
    cand_title = cand.get("title") or ""
    if cand_title == "Copy of Contract Template":
        score += 0.25
    elif "contract template" in cand_title.lower() and cand_title != "Contract Template":
        # Partial credit for a copy-ish title that isn't exact.
        score += 0.10

    # --- 0.10: ownerId == user-1 ---
    if cand.get("ownerId") == "user-1":
        score += 0.10

    # --- 0.10: originals untouched (doc-1 unchanged AND doc-2 unchanged) ---
    originals_ok = True
    for did, idoc in init_docs.items():
        cdoc = cur_docs.get(did)
        if cdoc is None:
            originals_ok = False  # an original was deleted
            break
        if json.dumps(idoc, sort_keys=True) != json.dumps(cdoc, sort_keys=True):
            originals_ok = False  # an original was modified
            break
    if originals_ok:
        score += 0.10

    score = max(0.0, min(1.0, score))
    print(f"REWARD: {round(score, 2)}")


if __name__ == "__main__":
    main()
