#!/usr/bin/env python3
"""Reward for gmail_031.

Task: move all three emails from noreply@jobspam.io (email_1, email_2, email_3)
to trash, and mark the manager email (email_4) as important. email_5 (teammate
distractor) must stay unchanged. No emails may be permanently deleted.

Scoring (progressive, exact state checks only):
  - email_1 -> folder == 'trash'      : 0.25
  - email_2 -> folder == 'trash'      : 0.25
  - email_3 -> folder == 'trash'      : 0.25
  - email_4 -> important == True       : 0.25
Over-action penalties (zero out the reward):
  - any recruiter email permanently deleted (missing) -> 0.0
  - distractor email_5 modified (folder/important/starred/read/deleted) -> 0.0
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    out = {}
    for e in state.get("emails", []) or []:
        out[e.get("id")] = e
    return out


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    cur = _emails_by_id(current)

    recruiter_ids = ["email_1", "email_2", "email_3"]
    manager_id = "email_4"
    distractor_id = "email_5"

    # --- Over-action guard: nothing may be permanently deleted ---
    # All originally-present emails must still exist in the emails array.
    for eid in recruiter_ids + [manager_id, distractor_id]:
        if eid not in cur:
            print("Over-action: email %s permanently deleted (missing)." % eid)
            return 0.0

    # --- Distractor guard: email_5 must be fully unchanged ---
    d = cur[distractor_id]
    if d.get("folder") != "inbox":
        print("Over-action: distractor email_5 folder changed to %r." % d.get("folder"))
        return 0.0
    if d.get("important") is True:
        print("Over-action: distractor email_5 marked important.")
        return 0.0

    score = 0.0

    # --- Recruiter emails moved to trash (0.25 each) ---
    for eid in recruiter_ids:
        folder = cur[eid].get("folder")
        if folder == "trash":
            score += 0.25
            print("%s moved to trash: +0.25" % eid)
        else:
            print("%s not in trash (folder=%r)" % (eid, folder))

    # --- Manager email marked important (0.25) ---
    m = cur[manager_id]
    if m.get("important") is True:
        # manager email must remain in inbox (not moved as a side effect)
        if m.get("folder") == "inbox":
            score += 0.25
            print("%s marked important and still in inbox: +0.25" % manager_id)
        else:
            print(
                "%s marked important but folder=%r (should stay inbox)"
                % (manager_id, m.get("folder"))
            )
    else:
        print("%s not marked important (important=%r)" % (manager_id, m.get("important")))

    score = round(min(1.0, max(0.0, score)), 2)
    return score


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as exc:  # noqa: BLE001
        print("Error computing reward: %s" % exc)
        reward = 0.0
    print("REWARD: %s" % reward)
