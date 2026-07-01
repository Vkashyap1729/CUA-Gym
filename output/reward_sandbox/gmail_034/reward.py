#!/usr/bin/env python3
"""Reward for gmail_034.

Task: Reorganize the two flagged project emails: remove the 'Personal' label
(l2) from both, add the 'Work' label (l1) to both, and star the one from the
project lead (email_1, from lead@company.com).

Scoring is entirely exact state checks over current_state:
  - email_1 (project lead): l2 removed, l1 added, starred == true
  - email_2 (dev):          l2 removed, l1 added, starred stays false
  - email_3 (distractor):   must stay unchanged (labels ['l2'], not starred)

No LLM judge needed — all criteria are deterministic state comparisons.
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


def _email_by_id(emails, eid):
    for e in emails:
        if e.get("id") == eid:
            return e
    return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    emails = current.get("emails", []) or []

    e1 = _email_by_id(emails, "email_1")  # project lead -> l1, starred
    e2 = _email_by_id(emails, "email_2")  # dev          -> l1, not starred
    e3 = _email_by_id(emails, "email_3")  # distractor    -> unchanged

    # Guard: emails must not be moved/deleted.
    if e1 is None or e2 is None or e3 is None:
        print("Missing one of the required emails (moved/deleted).")
        print("REWARD: 0.0")
        return

    def labels_of(e):
        return set(e.get("labels", []) or [])

    score = 0.0

    # --- email_1: 3 sub-criteria (0.2 each) ---
    l1_labels = labels_of(e1)
    if "l2" not in l1_labels:
        score += 0.2  # Personal removed
    if "l1" in l1_labels:
        score += 0.2  # Work added
    if e1.get("starred") is True:
        score += 0.2  # starred (from project lead)

    # --- email_2: 2 sub-criteria (0.2 each) ---
    l2_labels = labels_of(e2)
    if "l2" not in l2_labels:
        score += 0.2  # Personal removed
    if "l1" in l2_labels:
        score += 0.2  # Work added

    # --- Over-action penalties ---
    # email_2 must NOT be starred (only the lead's email is starred).
    if e2.get("starred") is True:
        score -= 0.3

    # email_3 (distractor) must be completely unchanged.
    if labels_of(e3) != {"l2"}:
        score -= 0.3
    if e3.get("starred") is True:
        score -= 0.3

    # email_1 must not gain extra labels beyond exactly {l1}.
    if l1_labels - {"l1", "l2"}:
        score -= 0.2
    # email_2 must not gain extra labels beyond exactly {l1}.
    if l2_labels - {"l1", "l2"}:
        score -= 0.2

    # No emails should be added/deleted (over-action).
    diff = data.get("state_diff", {}) or {}
    if diff.get("newEmails") or diff.get("deletedEmails"):
        score -= 0.3

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 1)))


if __name__ == "__main__":
    main()
