"""Reward for: Move the 'Weekly Deals' promotional email to spam.

Task-introduced change: email_1 (from newsletter@shopmart.com, subject
'Weekly Deals - 50% off', category promotions) must move folder inbox -> spam.

Distractors that MUST stay in the inbox (over-action guard):
  - email_2: same sender, subject 'Your order shipped' (legitimate)
  - email_3: subject contains 'Deals' but is a real work email

Scoring (progressive, exact state checks only):
  0.7  email_1.folder == 'spam'   (the target action; 0 => nothing done)
  0.3  both distractors still in the inbox and unchanged
Over-action (moving/altering distractors, or moving other emails to spam)
zeroes out the 0.3 component. Initial state -> 0.0, golden state -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_ID = "email_1"
DISTRACTOR_IDS = ["email_2", "email_3"]


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    return {e.get("id"): e for e in (state or {}).get("emails", [])}


def compute_reward():
    data = _get_state()
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur = _emails_by_id(current)
    init = _emails_by_id(initial)

    score = 0.0

    # --- Primary action: target moved to spam (0.7) ---
    target = cur.get(TARGET_ID)
    if target is None:
        # target email should never be deleted for this task
        print("REWARD: 0.0")
        return
    if target.get("folder") == "spam":
        score += 0.7
    else:
        # nothing meaningful done to the target -> no credit at all
        print("REWARD: 0.0")
        return

    # --- Over-action guard: distractors must be untouched (0.3) ---
    distractors_ok = True
    for did in DISTRACTOR_IDS:
        cur_d = cur.get(did)
        init_d = init.get(did)
        if cur_d is None or init_d is None:
            distractors_ok = False
            break
        # must stay in inbox and not otherwise be moved/deleted
        if cur_d.get("folder") != "inbox":
            distractors_ok = False
            break
        # guard against other observable tampering on the distractors
        if cur_d.get("folder") != init_d.get("folder"):
            distractors_ok = False
            break

    # No unrelated email should have been dumped into spam either.
    other_moved_to_spam = False
    for eid, e in cur.items():
        if eid == TARGET_ID:
            continue
        init_e = init.get(eid)
        if e.get("folder") == "spam" and (init_e is None or init_e.get("folder") != "spam"):
            other_moved_to_spam = True
            break

    if distractors_ok and not other_moved_to_spam:
        score += 0.3

    score = max(0.0, min(1.0, score))
    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    compute_reward()
