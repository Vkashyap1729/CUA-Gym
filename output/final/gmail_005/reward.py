#!/usr/bin/env python3
"""Reward for: Apply the 'Travel' label to the flight confirmation from SkyJet.

Task-introduced change (and ONLY change scored):
  - email_2 (from SkyJet Airlines, "Your flight to Denver is confirmed")
    gains the Travel label (id 'l3'): labels [] -> ['l3'].

Distractors that MUST stay unchanged (over-action penalty):
  - email_1 keeps ['l1'] (Work)
  - email_3 (hotel "Reservation reminder", travel-ish but NOT the flight) stays []
  - email_4 stays []
  - no other email gains the Travel label

Scoring (pure exact-state check, no LLM judge):
  The reward is anchored entirely on the task-introduced action. On the
  initial (not-done) state the target has no Travel label, so score = 0.0.
  Distractor preservation is NOT independent credit (that would give the
  untouched initial state free points) -- it is a gate/penalty that only
  applies once the core action is present.

    core action (email_2 gets Travel label)      -> up to 0.7
    correct preservation of named distractors     -> +0.3 (only if core done)
    over-action on the target (extra labels)       -> partial core credit only
"""

import urllib.request
import json

BASE_URL = "https://cua-gym-gmail.xlang.ai"
TRAVEL_LABEL = "l3"
TARGET_ID = "email_2"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    out = {}
    for e in state.get("emails", []):
        out[e.get("id")] = e
    return out


def main():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    emails = _emails_by_id(current)

    score = 0.0

    target = emails.get(TARGET_ID)
    if target is None:
        # Target email missing entirely -> cannot have completed the task.
        print("Target email %s not found" % TARGET_ID)
        print("REWARD: 0.0")
        return

    target_labels = list(target.get("labels") or [])
    has_travel = TRAVEL_LABEL in target_labels

    # --- Core action: SkyJet flight confirmation gets the Travel label (0.7) ---
    # This is the ONLY thing that separates initial (no l3) from golden (l3).
    if has_travel:
        if target_labels == [TRAVEL_LABEL]:
            score += 0.7  # exactly the intended single label
        else:
            # Travel applied, but extra labels also added to the target ->
            # partial credit (right action, some over-action on the target).
            score += 0.5
            print("Target has Travel label but also extra labels: %r" % target_labels)
    else:
        # Not done. Do NOT award distractor-preservation credit here, or the
        # untouched initial state would score > 0.0.
        print("Target email %s does not have Travel label; labels=%r" % (TARGET_ID, target_labels))
        print("REWARD: 0.0")
        return

    # --- Distractor preservation (0.3): named emails must be unchanged. ---
    # Only reachable once the core action is present (score already >= 0.5).
    distractor_ok = True

    e1 = emails.get("email_1")
    if e1 is not None and list(e1.get("labels") or []) != ["l1"]:
        distractor_ok = False
        print("email_1 labels changed (must stay ['l1']): %r" % (e1.get("labels")))

    e3 = emails.get("email_3")
    if e3 is not None and list(e3.get("labels") or []) != []:
        distractor_ok = False
        print("email_3 labels changed (must stay []): %r" % (e3.get("labels")))

    e4 = emails.get("email_4")
    if e4 is not None and list(e4.get("labels") or []) != []:
        distractor_ok = False
        print("email_4 labels changed (must stay []): %r" % (e4.get("labels")))

    # No other email should have gained the Travel label (mis-targeting).
    for eid, e in emails.items():
        if eid == TARGET_ID:
            continue
        if TRAVEL_LABEL in list(e.get("labels") or []):
            distractor_ok = False
            print("Travel label wrongly applied to %s" % eid)

    if distractor_ok:
        score += 0.3

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    main()
