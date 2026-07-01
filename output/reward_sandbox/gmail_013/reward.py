#!/usr/bin/env python3
"""Reward for: Star the email from Alice Smith about the Q4 roadmap.

Objective, exact-state scoring:
  - email_1 (from Alice Smith, "Q4 Project Roadmap Update") must become starred:true
  - Every other email must be untouched (distractor email_3 "Q3 roadmap retro notes"
    must stay starred:false; no folder/read/star changes anywhere else; no new/deleted).

No LLM judge is used: the entire criterion is a boolean state flag.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_ID = "email_1"


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def main():
    data = _get_state()
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = {e.get("id"): e for e in current.get("emails", []) if isinstance(e, dict)}

    target = emails.get(TARGET_ID)
    if not target:
        print("Target email_1 not found in current state.")
        print("REWARD: 0.0")
        return

    # --- Primary criterion: email_1 must be starred ---
    target_starred = bool(target.get("starred", False))
    if not target_starred:
        # Task not done at all (initial state has email_1.starred == false).
        print("email_1 is not starred yet.")
        print("REWARD: 0.0")
        return

    score = 1.0

    # --- Over-action penalties ---
    # Any modification other than email_1.starred false->true is unintended.
    modified = diff.get("modifiedEmails", {}) or {}
    new_emails = diff.get("newEmails", []) or []
    deleted = diff.get("deletedEmails", []) or []

    over_actions = []

    for eid, changes in modified.items():
        if not isinstance(changes, dict):
            continue
        if eid == TARGET_ID:
            # Only the "starred" field may have changed on the target.
            extra_fields = [f for f in changes.keys() if f != "starred"]
            for f in extra_fields:
                over_actions.append(f"{eid}.{f} changed unexpectedly")
        else:
            for f in changes.keys():
                over_actions.append(f"{eid}.{f} changed (distractor/other email touched)")

    for eid in new_emails:
        over_actions.append(f"new email created: {eid}")
    for eid in deleted:
        over_actions.append(f"email deleted: {eid}")

    # Defensive cross-check against current_state for the named distractor,
    # in case state_diff is incomplete.
    distractor = emails.get("email_3")
    if distractor is not None and bool(distractor.get("starred", False)):
        over_actions.append("email_3 (Q3 distractor) is starred")

    if over_actions:
        # Substantial deduction for collateral changes; the task requires that
        # only email_1 be affected.
        penalty = min(0.6, 0.3 * len(set(over_actions)))
        score = max(0.0, round(1.0 - penalty, 2))
        print("Over-actions detected:")
        for oa in sorted(set(over_actions)):
            print("  - " + oa)

    print(f"email_1.starred = {target_starred}; over_actions = {len(set(over_actions))}")
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
