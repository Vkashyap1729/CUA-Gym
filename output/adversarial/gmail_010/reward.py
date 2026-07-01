#!/usr/bin/env python3
"""Reward for gmail task gmail_010.

Task: Empty spam -- permanently delete every email currently sitting in the
spam folder (email_5 from 'Prize Notify' and email_6 from 'Crypto Alerts').

Task-introduced change: email_5 and email_6 must be PERMANENTLY deleted --
removed entirely from the `emails` array. Merely moving them to trash (they
would remain in `emails` with folder="trash") is NOT the requested action and
earns only partial credit. The three inbox distractors (email_1, email_2,
email_3) must remain fully untouched.

Scoring is exact-state only (no LLM judge needed). The gmail mock's state_diff
does NOT expose a `deletedEmails` list -- permanent deletion is detected by the
target being absent from the current `emails` array, while a trashed email is
still present with folder="trash". So we score directly off the emails array.

Progressive:
  +0.5  per spam target permanently deleted (absent from current emails array)
  +0.2  per spam target only moved to trash (present, folder == "trash")
  ->    forced to 0.0 on over-action: any distractor deleted/modified, or any
        non-target email deleted.

Initial state -> 0.0 (both targets still in spam).
Golden state  -> 1.0 (both targets gone from the emails array; distractors
                 untouched).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_IDS = ["email_5", "email_6"]                  # spam emails that must be deleted
DISTRACTOR_IDS = ["email_1", "email_2", "email_3"]   # inbox emails, must stay put

# Distractor fields whose change counts as over-action.
TRACKED_FIELDS = ("folder", "read", "starred", "important", "labels", "subject")


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    out = {}
    for e in (state or {}).get("emails", []) or []:
        eid = e.get("id")
        if eid is not None:
            out[eid] = e
    return out


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    initial_state = data.get("initial_state", {}) or {}
    current_state = data.get("current_state", {}) or {}

    initial_by_id = _emails_by_id(initial_state)
    current_by_id = _emails_by_id(current_state)

    # Any email present initially but absent now was permanently deleted.
    deleted_ids = set(initial_by_id) - set(current_by_id)

    score = 0.0

    # --- Reward permanent deletion of each spam target ------------------------
    for tid in TARGET_IDS:
        cur = current_by_id.get(tid)
        if tid not in current_by_id:
            # Absent from the emails array -> permanently deleted (requested).
            score += 0.5
        elif cur is not None and cur.get("folder") == "trash":
            # Only moved to trash, not permanently deleted -> partial progress.
            score += 0.2
        # otherwise still in spam / elsewhere -> 0.0 for this target

    # --- Over-action penalty: distractors must be untouched -------------------
    over_action = False
    for did in DISTRACTOR_IDS:
        cur = current_by_id.get(did)
        init = initial_by_id.get(did)
        if init is not None and cur is None:
            over_action = True  # a distractor was deleted
            break
        if cur is not None and init is not None:
            for field in TRACKED_FIELDS:
                if cur.get(field) != init.get(field):
                    over_action = True
                    break
        if over_action:
            break

    # Deleting anything other than the two spam targets is over-action too.
    if deleted_ids - set(TARGET_IDS):
        over_action = True

    if over_action:
        score = 0.0

    return round(max(0.0, min(1.0, score)), 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as exc:  # noqa: BLE001
        print("ERROR:", exc)
        reward = 0.0
    print("REWARD: {}".format(reward))
