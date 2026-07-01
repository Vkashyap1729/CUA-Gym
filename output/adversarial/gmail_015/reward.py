#!/usr/bin/env python3
"""Reward for gmail_015: move the crypto-lottery email to spam.

Task: move email_1 (from prize@crypto-lottery-win.biz, 'You WON 5 BTC') to spam.
Distractors email_2 (hr@company.com) and email_3 (billing@saas-tool.com) must
remain in inbox. No read/star changes on any email.

Progressive score (exact state checks only; no LLM judge needed):
  The reward is ZERO until the task-introduced change is present. Distractor
  integrity only earns credit once email_1 has actually been moved to spam,
  so the untouched initial state scores 0.0 (email_1 still in inbox).
  Once email_1.folder == 'spam':
    0.7  base credit for the move
    0.15 email_2 unchanged (folder still 'inbox', read/starred untouched)
    0.15 email_3 unchanged (folder still 'inbox', read/starred untouched)
Over-action (read/starred flipped on email_1, or a distractor moved out of
inbox) forfeits the corresponding credit.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _by_id(emails):
    out = {}
    for e in emails or []:
        eid = e.get("id")
        if eid is not None:
            out[eid] = e
    return out


def compute_reward():
    sid = _read_sid()
    data = _fetch(sid)

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur = _by_id(current.get("emails", []))
    init = _by_id(initial.get("emails", []))

    score = 0.0

    # --- Primary gate: email_1 must be moved to spam. ---
    # Nothing is scored until this task-introduced change is present, so the
    # untouched initial state (email_1 in inbox) scores exactly 0.0.
    e1 = cur.get("email_1")
    e1_init = init.get("email_1", {})
    if e1 is None or e1.get("folder") != "spam":
        return 0.0

    score += 0.7
    # Over-action guard: moving to spam must not touch read/starred.
    if e1.get("read") != e1_init.get("read") or e1.get("starred") != e1_init.get("starred"):
        score -= 0.1

    # --- Distractors must remain untouched in inbox (0.15 each) ---
    for did, weight in (("email_2", 0.15), ("email_3", 0.15)):
        ce = cur.get(did)
        ie = init.get(did, {})
        if ce is None:
            continue
        unchanged = (
            ce.get("folder") == "inbox"
            and ce.get("read") == ie.get("read")
            and ce.get("starred") == ie.get("starred")
        )
        if unchanged:
            score += weight

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: " + str(reward))
