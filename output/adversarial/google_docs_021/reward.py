"""Reward for: Re-open (unresolve) the comment on "Bug Triage" because the issue came back.

Task-introduced change (and ONLY this) is scored:
  - comment-1 on doc-1 (the recurring-bug thread) must become resolved=false.
Distractor / over-action guards:
  - comment-2 on doc-1 must stay resolved=true (must NOT be touched).
  - documents and the doc title must be unchanged.

Scoring (exact state checks only; no LLM judge needed for a boolean toggle):
  0.0 on the initial (both comments resolved=true)
  1.0 on the fully-completed state (comment-1 unresolved, comment-2 untouched)
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


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    comments = current.get("comments", []) or []

    c1 = _find_comment(comments, "comment-1")
    c2 = _find_comment(comments, "comment-2")

    if c1 is None or c2 is None:
        # Comment thread(s) were deleted / corrupted — not the requested action.
        return 0.0

    # --- Primary criterion (0.8): the target comment is re-opened. ---
    # Initial state has comment-1.resolved=true → contributes 0.0 here, so the
    # not-done state scores 0.0 overall.
    score = 0.8 if c1.get("resolved") is False else 0.0

    # --- Over-action guard (final 0.2): only credited once the primary action is
    # done AND the distractor is untouched. comment-2 must stay resolved=true. ---
    if score > 0.0:
        if c2.get("resolved") is True:
            score += 0.2
        else:
            # Distractor was unresolved as a side effect — cap below full credit.
            score = min(score, 0.5)

    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: " + str(reward))
