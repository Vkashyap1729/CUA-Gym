#!/usr/bin/env python3
"""Reward for: downgrade Alice (user-2) on "Financial Model" (doc-1) from editor to viewer.

All criteria are structural — no LLM judge needed.

The task-introduced change is a single field flip: Alice's permission editor -> viewer.
The score is GATED on that change so the initial (not-done) state scores 0.0:
  - Alice (user-2) permission == "viewer"  ........ required, else 0.0
Given the change is done, the rest is over-action penalty (so golden == 1.0, and
clumsy edits that touch the distractor lose credit):
  - sharedWith still has exactly user-2 + user-3 (none added/removed)  (0.5 of remainder)
  - Bob (user-3) commenter entry unchanged ...........................  (0.5 of remainder)

Initial state (Alice=editor) -> 0.0 ; fully-completed state (Alice=viewer, Bob intact) -> 1.0.
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
DOC_ID = "doc-1"
ALICE_ID = "user-2"
BOB_ID = "user-3"


def get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def perm_of(share_list, user_id):
    for entry in share_list or []:
        if entry.get("userId") == user_id:
            return entry.get("permission")
    return None


def main():
    data = get_state()
    current = data.get("current_state", {}) or {}
    documents = current.get("documents", {}) or {}
    doc = documents.get(DOC_ID, {}) or {}
    shared = doc.get("sharedWith", []) or []

    # GATE: the task is only "done" once Alice is downgraded to viewer.
    # Initial state has Alice=editor -> this fails -> 0.0.
    if perm_of(shared, ALICE_ID) != "viewer":
        print("REWARD: 0.0")
        return

    # The downgrade is done. Award full credit, then penalize over-action so a
    # sloppy edit (entries added/removed, or the distractor Bob touched) loses points.
    score = 0.5

    # No entries added or removed: exactly the original two userIds remain.
    shared_ids = sorted(e.get("userId") for e in shared)
    if shared_ids == sorted([ALICE_ID, BOB_ID]):
        score += 0.25

    # Distractor: Bob (user-3) must stay a commenter, unchanged.
    if perm_of(shared, BOB_ID) == "commenter":
        score += 0.25

    score = round(min(score, 1.0), 2)
    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    main()
