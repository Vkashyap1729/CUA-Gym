"""Reward for google_docs_030.

Task: Reply "Done — updated in the latest version." to Alice's comment on
"Translation Strings" and then mark that comment as resolved.

Expected end state:
  - comment-1 (on doc-1, by user-2/Alice) gains exactly ONE reply by user-1
    whose content matches "Done — updated in the latest version."
  - comment-1.resolved becomes true.
  - No new top-level comment is created.

Scoring (progressive, 0.0-1.0):
  - 0.30  exactly one new reply by user-1 on comment-1 (no extra replies/comments)
  - 0.30  reply wording matches the requested text   (LLM judge, <=40% of score)
  - 0.40  comment-1.resolved == true
Over-action (extra top-level comments, or other comments mutated) caps/zeros score.
"""

import json
import urllib.request

from reward_judge import call_llm_judge

BASE_URL = "https://cua-gym-google-docs.xlang.ai"

TARGET_COMMENT_ID = "comment-1"
TARGET_DOC_ID = "doc-1"
REPLY_AUTHOR = "user-1"
EXPECTED_REPLY_TEXT = "Done — updated in the latest version."


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_comment(comments, cid):
    for c in comments or []:
        if c.get("id") == cid:
            return c
    return None


def compute_reward():
    data = _get_state()
    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_comments = initial.get("comments", []) or []
    cur_comments = current.get("comments", []) or []

    score = 0.0

    target = _find_comment(cur_comments, TARGET_COMMENT_ID)
    if target is None:
        # Target comment must still exist (deleting it is not the task).
        print("REWARD: 0.0")
        return

    init_target = _find_comment(init_comments, TARGET_COMMENT_ID)
    init_reply_ids = {r.get("id") for r in (init_target or {}).get("replies", []) or []}

    # --- Over-action guards ---------------------------------------------------
    # No new top-level comment should be created.
    if len(cur_comments) > len(init_comments):
        print("REWARD: 0.0")
        return

    # Other comments must be untouched (no spurious replies / resolves elsewhere).
    for ic in init_comments:
        cid = ic.get("id")
        if cid == TARGET_COMMENT_ID:
            continue
        cc = _find_comment(cur_comments, cid)
        if cc is None:
            print("REWARD: 0.0")
            return
        if cc.get("resolved") != ic.get("resolved"):
            print("REWARD: 0.0")
            return
        if len(cc.get("replies", []) or []) != len(ic.get("replies", []) or []):
            print("REWARD: 0.0")
            return

    # --- Criterion 1: exactly one new reply by user-1 on the target comment ---
    cur_replies = target.get("replies", []) or []
    new_replies = [r for r in cur_replies if r.get("id") not in init_reply_ids]
    new_user1_replies = [r for r in new_replies if r.get("userId") == REPLY_AUTHOR]

    one_clean_reply = len(new_replies) == 1 and len(new_user1_replies) == 1
    if one_clean_reply:
        score += 0.30

    # --- Criterion 2: reply wording matches the requested text ----------------
    reply_for_content = new_user1_replies[0] if new_user1_replies else None
    if reply_for_content is not None:
        reply_text = (reply_for_content.get("content") or "").strip()
        # Cheap exact/substring fast-path before paying for the judge.
        norm = reply_text.lower().replace("—", "-").replace("--", "-")
        expected_norm = EXPECTED_REPLY_TEXT.lower().replace("—", "-")
        if expected_norm in norm:
            score += 0.30
        elif reply_text:
            # JUSTIFICATION: the requested reply wording is short and subjective
            # (em-dash / phrasing variants), so an exact string match is too
            # brittle; use the LLM judge for semantic equivalence only. This
            # judged criterion is 0.30 of 1.0 = 30% <= 40% cap.
            verdict = call_llm_judge(
                prompt=(
                    "A user was asked to reply to a document comment with the "
                    'message: "Done — updated in the latest version."\n\n'
                    "Here is the reply they actually wrote:\n"
                    f'"{reply_text}"\n\n'
                    "Does the reply convey essentially the same message "
                    "(acknowledging it is done / updated in the latest version)? "
                    "Answer YES or NO."
                ),
            )
            if isinstance(verdict, str) and verdict.strip().upper().startswith("Y"):
                score += 0.30

    # --- Criterion 3: target comment is resolved ------------------------------
    if target.get("resolved") is True:
        score += 0.40

    print(f"REWARD: {round(score, 2)}")


if __name__ == "__main__":
    compute_reward()
