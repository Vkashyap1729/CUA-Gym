"""Reward for google_docs task google_docs_014.

Task: Reply to Alice's comment on the "Release Notes" doc saying
      "Thanks, I'll fix this in the next pass."

Expected end state: comment-1 (on doc-1, authored by user-2/Alice, unresolved)
gains EXACTLY ONE reply authored by user-1 whose content matches the wording.
comment-1.resolved stays false. No new top-level comment is created.

Scoring (progressive, 0.0-1.0):
  +0.30  a reply authored by user-1 was added to comment-1
  +0.30  exactly one user-1 reply was added AND no over-action
         (comment-1 still unresolved, no new top-level comments)
  +0.40  the new reply's wording matches the requested message (LLM judge)
"""

import json
import urllib.request

from reward_judge import call_llm_judge

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
TARGET_COMMENT_ID = "comment-1"
TARGET_DOC_ID = "doc-1"
REPLY_AUTHOR = "user-1"
EXPECTED_MESSAGE = "Thanks, I'll fix this in the next pass."


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_comment(comments, comment_id):
    for c in comments or []:
        if c.get("id") == comment_id:
            return c
    return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)
    initial_state = data.get("initial_state", {}) or {}
    current_state = data.get("current_state", {}) or {}

    init_comments = initial_state.get("comments", []) or []
    cur_comments = current_state.get("comments", []) or []

    init_c1 = _find_comment(init_comments, TARGET_COMMENT_ID)
    cur_c1 = _find_comment(cur_comments, TARGET_COMMENT_ID)

    score = 0.0

    if cur_c1 is None:
        # Target comment vanished -> task not done / broken.
        print("REWARD: 0.0")
        return

    init_replies = (init_c1.get("replies", []) if init_c1 else []) or []
    cur_replies = cur_c1.get("replies", []) or []

    # Replies authored by user-1 (the active user) on comment-1.
    init_user1_replies = [r for r in init_replies if r.get("userId") == REPLY_AUTHOR]
    cur_user1_replies = [r for r in cur_replies if r.get("userId") == REPLY_AUTHOR]
    added_count = len(cur_user1_replies) - len(init_user1_replies)

    # ---- Criterion 1: a user-1 reply was added to comment-1 (0.30) ----
    if added_count >= 1:
        score += 0.30

    # ---- Criterion 2: exactly one added, no over-action (0.30) ----
    # comment-1 must stay unresolved; no new top-level comment created.
    resolved_ok = cur_c1.get("resolved", False) is False
    init_count = len(init_comments)
    cur_count = len(cur_comments)
    no_new_top_level = cur_count <= init_count

    if added_count == 1 and resolved_ok and no_new_top_level:
        score += 0.30

    # ---- Criterion 3: wording of the new reply matches (0.40, LLM judge) ----
    # Identify the newly added user-1 reply (by id if possible, else the last one).
    new_reply = None
    if cur_user1_replies:
        init_ids = {r.get("id") for r in init_user1_replies if r.get("id")}
        fresh = [r for r in cur_user1_replies if r.get("id") not in init_ids]
        new_reply = fresh[-1] if fresh else cur_user1_replies[-1]

    if new_reply is not None:
        reply_text = (new_reply.get("content") or "").strip()
        if reply_text:
            # JUSTIFICATION: The reply wording is free-text the agent typed; an exact
            # string match is too brittle (punctuation/casing/paraphrase), so an LLM
            # judge checks semantic equivalence to the requested message. Bounded to
            # 40% of total score; all structural facts above are exact state checks.
            success_criteria = (
                "The posted reply must convey the same message as: "
                f'"{EXPECTED_MESSAGE}" — i.e. it acknowledges thanks and commits '
                "to fixing the issue in the next pass. Score 1.0 if it clearly is "
                "the same intended message (minor punctuation/casing differences "
                "are fine), otherwise score 0.0."
            )
            state_excerpt = f'The reply the user posted is:\n"{reply_text}"'
            judge_score = call_llm_judge(
                "Reply to a comment with the requested acknowledgement message.",
                success_criteria,
                state_excerpt,
            )
            score += 0.40 * max(0.0, min(1.0, float(judge_score)))

    score = max(0.0, min(1.0, score))
    print(f"REWARD: {round(score, 2)}")


if __name__ == "__main__":
    main()
