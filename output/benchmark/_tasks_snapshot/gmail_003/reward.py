"""Reward for gmail_003.

Task: "That promotional email from ShopMart is junk — move it to trash."

Target change (task-introduced): email_4 (from ShopMart Deals) moves from
folder 'inbox' -> 'trash'. Everything else must stay put.

Distractors that must remain unchanged (folder 'inbox', no other edits):
  - email_1: real colleague
  - email_2: bank statement notice
  - email_3: RetailPlus 'Your order shipped' (legit order confirmation)

Scoring (progressive, exact state checks only — no LLM judge needed):
  - email_4 correctly in 'trash'                 -> 1.0 base
  - email_4 moved out of inbox but wrong folder  -> 0.4 base (partial)
  - email_4 still in inbox                        -> 0.0 base
  - minus 0.25 for each over-action (a distractor changed, an email
    deleted, or a new email created)
Initial (not-done) state -> 0.0 ; fully-completed state -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_ID = "email_4"
DISTRACTOR_IDS = ["email_1", "email_2", "email_3"]


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    return {e.get("id"): e for e in (state.get("emails") or [])}


def compute_reward():
    data = _get_state()
    current = data.get("current_state") or {}
    diff = data.get("state_diff") or {}

    cur = _emails_by_id(current)

    # --- primary: did email_4 move to trash? ---
    target = cur.get(TARGET_ID)
    if target is None:
        # ShopMart email vanished entirely (permanent delete) — not what was asked.
        target_folder = None
    else:
        target_folder = target.get("folder")

    if target_folder == "trash":
        score = 1.0
    elif target_folder in ("spam", "archive"):
        score = 0.4  # moved out of inbox but to the wrong place
    else:
        score = 0.0  # still in inbox (initial state) or deleted

    # --- over-action penalty: distractors and the rest of the mailbox ---
    over_actions = 0

    # any distractor whose folder changed from 'inbox'
    for did in DISTRACTOR_IDS:
        e = cur.get(did)
        if e is None or e.get("folder") != "inbox":
            over_actions += 1

    # any distractor otherwise modified (read/starred/labels/etc.) per state_diff
    modified = diff.get("modifiedEmails") or {}
    for mid in modified:
        if mid in DISTRACTOR_IDS:
            over_actions += 1

    # emails created (e.g. a stray reply/compose) or permanently deleted
    over_actions += len(diff.get("newEmails") or [])
    over_actions += len(diff.get("deletedEmails") or [])

    score -= 0.25 * over_actions
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    return score


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: {:.1f}".format(reward))
