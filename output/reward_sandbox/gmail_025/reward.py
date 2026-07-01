#!/usr/bin/env python3
"""Reward for: Star the email from Alice Smith about the Q4 budget review.

Task-introduced change: email_1 (Alice Smith, 'Q4 Budget Review') -> starred:true.
Everything else must be untouched:
  - email_3 (Alice Smith, 'Team Lunch Friday') is a distractor -> must stay starred:false
  - no email is read, moved (folder change), or deleted
Progressive score 0.0..1.0. Exact state checks only (a boolean flag; no LLM judge).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_ID = "email_1"          # Alice Smith / Q4 Budget Review
DISTRACTOR_ID = "email_3"      # Alice Smith / Team Lunch Friday


def _read_sid():
    with open("/tmp/task_web_sid", "r") as f:
        return f.read().strip()


def _fetch(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    out = {}
    for e in (state or {}).get("emails", []) or []:
        if isinstance(e, dict) and "id" in e:
            out[e["id"]] = e
    return out


def compute_reward():
    sid = _read_sid()
    data = _fetch(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_emails = _emails_by_id(initial)
    cur_emails = _emails_by_id(current)

    # --- Primary objective gates all credit: target email must be starred. ---
    # The task change is a single boolean flag, so nothing is earned until it flips.
    # This guarantees 0.0 on the initial (not-done) state.
    target = cur_emails.get(TARGET_ID)
    if target is None or bool(target.get("starred")) is not True:
        return 0.0

    # Primary action done -> full credit, then subtract over-action penalties so the
    # fully-correct golden state scores exactly 1.0.
    score = 1.0

    # Penalty 1: distractor (same sender, different subject) must stay unstarred.
    distractor = cur_emails.get(DISTRACTOR_ID)
    if distractor is not None and bool(distractor.get("starred")) is True:
        score -= 0.3

    # Penalty 2: no OTHER email's starred flag changed vs. initial.
    for eid, cur_e in cur_emails.items():
        if eid in (TARGET_ID, DISTRACTOR_ID):
            continue
        init_e = init_emails.get(eid)
        init_star = bool(init_e.get("starred")) if init_e else False
        if bool(cur_e.get("starred")) != init_star:
            score -= 0.2
            break

    # Penalty 3: no email was read, moved (folder change), added, or deleted.
    side_effect = False
    if set(init_emails.keys()) != set(cur_emails.keys()):
        side_effect = True
    else:
        for eid, cur_e in cur_emails.items():
            init_e = init_emails.get(eid, {})
            if bool(cur_e.get("read")) != bool(init_e.get("read")):
                side_effect = True
                break
            if cur_e.get("folder") != init_e.get("folder"):
                side_effect = True
                break
    if side_effect:
        score -= 0.3

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("ERROR computing reward:", repr(e))
        reward = 0.0
    print("REWARD:", reward)
