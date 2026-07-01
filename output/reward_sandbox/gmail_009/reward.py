#!/usr/bin/env python3
"""Reward for gmail_009: flag the Legal contract email as important and star it.

Task: Flag the contract email from Legal (email_3, subject
'Signed vendor contract — please retain') as important AND star it.
All other emails must remain unchanged (important=false, starred=false,
same folder/labels/read). Distractor email_1 (also from Legal, 'Policy update
FYI') must NOT be flagged or starred.

Scoring (progressive, exact state checks only — no LLM judge needed):
  +0.5  email_3.important == True
  +0.5  email_3.starred  == True
  Over-action penalty: if any OTHER email had important or starred flipped to
  true, or the target's folder/labels/read were altered, the score is forced
  toward 0 (multiplicative penalty). Initial state (nothing done) -> 0.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"
TARGET_ID = "email_3"


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    emails = current.get("emails", []) or []
    by_id = {e.get("id"): e for e in emails}

    target = by_id.get(TARGET_ID)
    if target is None:
        print("Target email %s not found in current state." % TARGET_ID)
        print("REWARD: 0.0")
        return

    score = 0.0

    # --- Core task credit (exact boolean checks) ---
    important_ok = bool(target.get("important")) is True
    starred_ok = bool(target.get("starred")) is True
    if important_ok:
        score += 0.5
        print("[+0.5] %s.important == True" % TARGET_ID)
    else:
        print("[+0.0] %s.important is not True" % TARGET_ID)
    if starred_ok:
        score += 0.5
        print("[+0.5] %s.starred == True" % TARGET_ID)
    else:
        print("[+0.0] %s.starred is not True" % TARGET_ID)

    # --- Over-action detection on distractor / other emails ---
    # Any OTHER email flagged important or starred is a mistake.
    over_action = False
    for e in emails:
        if e.get("id") == TARGET_ID:
            continue
        if bool(e.get("important")) or bool(e.get("starred")):
            print(
                "[penalty] distractor email %s was flipped "
                "(important=%s, starred=%s)"
                % (e.get("id"), e.get("important"), e.get("starred"))
            )
            over_action = True

    # --- No collateral changes on the target itself ---
    # The task must not move the email, relabel it, or mark it read.
    if target.get("folder") != "inbox":
        print("[penalty] target folder changed to %r (should stay 'inbox')" % target.get("folder"))
        over_action = True
    if target.get("labels"):
        print("[penalty] target labels changed to %r (should stay empty)" % target.get("labels"))
        over_action = True

    if over_action:
        # Over-action collapses the reward: correct flags don't excuse
        # touching things the task did not ask to touch.
        score *= 0.5
        print("[penalty] over-action detected -> score halved")

    score = max(0.0, min(1.0, score))
    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    main()
