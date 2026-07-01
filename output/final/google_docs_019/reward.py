#!/usr/bin/env python3
"""Reward for: Delete the spam comment Bob posted on the "Feedback Form" document.

Task-introduced change: comment-2 (Bob/user-3, "BUY CHEAP STUFF NOW", the spam) on
doc-1 must be removed. comment-1 (Alice/user-2, legitimate) must remain untouched.
Initial state -> 0.0 ; fully-completed state -> 1.0.
"""

import urllib.request
import json

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sid = read_sid()
    data = fetch_state(sid)
    current = data.get("current_state", {}) or {}
    comments = current.get("comments", []) or []

    # Index comments by id for inspection.
    by_id = {c.get("id"): c for c in comments if isinstance(c, dict)}

    spam_present = "comment-2" in by_id
    legit_present = "comment-1" in by_id

    score = 0.0

    # --- Gating criterion: the spam comment must be deleted (0.7) ---------------
    # If the spam comment is still there, the task is not done at all.
    if not spam_present:
        score += 0.7

        # --- Preservation: the legitimate comment must remain (0.2) ------------
        # Penalize over-action (deleting Alice's legitimate comment too).
        if legit_present:
            score += 0.2

        # --- Exactness: exactly one comment left on doc-1 (0.1) ----------------
        # Expected end state: comment-1 only. Guards against deleting/adding
        # extra comments on the document.
        doc1_comments = [c for c in comments if c.get("docId") == "doc-1"]
        if len(doc1_comments) == 1 and doc1_comments[0].get("id") == "comment-1":
            score += 0.1

    if score > 1.0:
        score = 1.0

    print("REWARD: " + str(round(score, 2)))


if __name__ == "__main__":
    main()
