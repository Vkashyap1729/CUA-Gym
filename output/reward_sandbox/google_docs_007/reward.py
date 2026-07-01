"""Reward for: Resolve the comment Alice left on the "Design Spec" document.

Task-introduced change: comment-1 (on doc-1 "Design Spec", authored by user-2 / Alice Chen)
must become resolved=true. comment-2 (authored by user-3 / Bob Smith) is a distractor and
must remain resolved=false.

Scoring (exact state checks only, progressive 0.0-1.0):
  - 0.0 until Alice's comment is resolved (so the not-done initial state scores 0.0).
  - 0.8: Alice's comment (comment-1) is resolved (the required action).
  - +0.2: AND Bob's comment (comment-2) is left untouched (over-action penalty otherwise).
Initial state -> 0.0; fully-completed state -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_comment(comments, cid):
    for c in comments:
        if c.get("id") == cid:
            return c
    return None


def main():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    comments = current.get("comments", []) or []

    score = 0.0

    # --- Primary: Alice's comment (comment-1 on doc-1) resolved (0.8) ---
    alice_comment = _find_comment(comments, "comment-1")
    alice_resolved = False
    if alice_comment is not None:
        # Sanity: confirm it really is Alice's comment on the Design Spec doc.
        is_alice = (
            alice_comment.get("userId") == "user-2"
            and alice_comment.get("docId") == "doc-1"
        )
        if is_alice and alice_comment.get("resolved") is True:
            alice_resolved = True

    if alice_resolved:
        score += 0.8

        # --- Over-action guard: Bob's comment (comment-2) must stay unresolved (+0.2).
        # Credited only after the required action so the initial state stays at 0.0.
        bob_comment = _find_comment(comments, "comment-2")
        if bob_comment is not None and bob_comment.get("resolved") is False:
            score += 0.2

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
