#!/usr/bin/env python3
"""Reward for gmail_008: mark the two unread newsletters as read AND archive them,
without touching the distractor emails.

Target changes (task-introduced):
  - email_2 (Weekly Tech Digest): read -> true, folder -> "archive"
  - email_4 (Marketing Weekly):   read -> true, folder -> "archive"

Distractors that must stay UNCHANGED:
  - email_1: read=false, folder="inbox"  (real work email)
  - email_3: read=true,  folder="inbox"
  - email_5: read=false, folder="inbox"

No star / label / trash / spam / send changes anywhere.

Scoring: 4 target criteria worth 0.25 each (progressive). Over-action (any change to a
distractor, or any starred/label/folder change beyond archive on any email) subtracts 0.25
per violation, floored at 0.0. Initial state -> 0.0, fully-completed golden -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

# Target newsletters -> desired end state
TARGETS = {
    "email_2": {"read": True, "folder": "archive"},
    "email_4": {"read": True, "folder": "archive"},
}
# Distractors -> must remain exactly at these values
DISTRACTORS = {
    "email_1": {"read": False, "folder": "inbox"},
    "email_3": {"read": True, "folder": "inbox"},
    "email_5": {"read": False, "folder": "inbox"},
}


def get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def main():
    data = get_state()
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = {e.get("id"): e for e in current.get("emails", []) if isinstance(e, dict)}

    score = 0.0

    # --- Positive credit: 0.25 per satisfied target criterion (read + folder) ---
    for eid, want in TARGETS.items():
        e = emails.get(eid, {})
        if e.get("read") is True:
            score += 0.25
        if e.get("folder") == want["folder"]:
            score += 0.25

    # --- Over-action penalty ---------------------------------------------------
    penalty = 0.0

    # 1) Distractors must be byte-for-byte unchanged in read/folder.
    for eid, expect in DISTRACTORS.items():
        e = emails.get(eid, {})
        if e.get("read") != expect["read"]:
            penalty += 0.25
        if e.get("folder") != expect["folder"]:
            penalty += 0.25

    # 2) No email may be starred/labeled/trashed/spammed, and no new sends/drafts.
    #    Use state_diff.modifiedEmails to catch any change outside the allowed set.
    allowed_fields = {"read", "folder"}
    modified = diff.get("modifiedEmails", {}) or {}
    for eid, changes in modified.items():
        if not isinstance(changes, dict):
            continue
        for field, delta in changes.items():
            # Any modification to a distractor is already penalized above via
            # current_state; here we catch forbidden FIELDS on any email.
            if field not in allowed_fields:
                penalty += 0.25
                continue
            if field == "folder" and eid in TARGETS:
                # target folder change is only legitimate if it lands on "archive"
                to_val = delta.get("to") if isinstance(delta, dict) else None
                if to_val not in ("archive", "inbox"):
                    penalty += 0.25

    # 3) No emails deleted or newly created (no permanent-delete / send / reply).
    if diff.get("deletedEmails"):
        penalty += 0.25
    if diff.get("newEmails"):
        penalty += 0.25

    final = max(0.0, min(1.0, score - penalty))
    print("REWARD: {:.1f}".format(final))


if __name__ == "__main__":
    main()
