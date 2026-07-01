#!/usr/bin/env python3
"""Reward for gmail_023.

Task: file every message from a company.com colleague under the Work label (l1),
marking each as read; leave external-sender emails alone.

Target emails (company.com colleagues): email_1, email_2, email_3
  -> each must have 'l1' in labels AND read == True
Distractor emails (must stay untouched): email_4 (vendor@outside.io),
  email_5 (noreply@company-news.com) -> read == False, labels == []
No folder/star changes anywhere.

Scoring is a pure exact-state check (no LLM judge needed): the outcome is fully
observable in the mock state. Progressive over the 6 target sub-conditions, with a
hard penalty for over-action on the named distractors (and for folder/star drift).
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGETS = ["email_1", "email_2", "email_3"]
DISTRACTORS = ["email_4", "email_5"]
WORK_LABEL = "l1"


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    data = _get_state()
    current = data.get("current_state", {}) or {}
    emails = {e.get("id"): e for e in current.get("emails", []) if isinstance(e, dict)}

    # ----- Positive credit: 6 sub-conditions across the 3 target emails -----
    satisfied = 0
    total = len(TARGETS) * 2  # label + read per target
    for eid in TARGETS:
        e = emails.get(eid)
        if not e:
            continue
        labels = e.get("labels") or []
        if WORK_LABEL in labels:
            satisfied += 1
        if e.get("read") is True:
            satisfied += 1

    score = satisfied / total if total else 0.0

    # ----- Over-action penalty: named distractors must be pristine -----
    # email_4 / email_5 must remain read:false with labels [] (and not moved/starred).
    over_action = False
    for eid in DISTRACTORS:
        e = emails.get(eid)
        if not e:
            over_action = True  # deleted/missing counts as tampering
            continue
        if e.get("read") is True:
            over_action = True
        if e.get("labels"):
            over_action = True
        if e.get("folder") not in (None, "inbox"):
            over_action = True
        if e.get("starred") is True:
            over_action = True

    # ----- No folder/star changes on the target emails either -----
    target_side_effects = False
    for eid in TARGETS:
        e = emails.get(eid)
        if not e:
            continue
        if e.get("folder") not in (None, "inbox"):
            target_side_effects = True
        if e.get("starred") is True:
            target_side_effects = True

    if over_action:
        # Touching a distractor is a correctness failure -> cap hard.
        score = min(score, 0.25)
    if target_side_effects:
        # Unwanted mutation of a target (moved/starred) -> partial penalty.
        score = min(score, 0.75)

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(round(score, 1)))


if __name__ == "__main__":
    main()
