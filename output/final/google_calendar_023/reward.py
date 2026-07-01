#!/usr/bin/env python3
"""Reward for: add a Google Meet link to the "Remote Standup" event.

Task-introduced change ONLY:
  - evt_130 'Remote Standup' .meetLink should become
    'https://meet.google.com/abc-defg-hij'
  - evt_131 'In-Person Standup' must keep an EMPTY meetLink (distractor;
    over-action is penalized).

Scoring is an exact state check (no subjective content), progressive 0.0-1.0:
  - 1.0  : Remote Standup meetLink exactly correct, In-Person Standup untouched
  - 0.5  : Remote Standup has SOME (non-empty) meetLink but not the exact value
  - 0.0  : Remote Standup meetLink still empty (not done)
  - over-action (In-Person Standup meetLink no longer empty) halves the score
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"
TARGET_LINK = "https://meet.google.com/abc-defg-hij"
REMOTE_ID = "evt_130"      # 'Remote Standup'  -> should get the meet link
INPERSON_ID = "evt_131"    # 'In-Person Standup' -> must stay empty (distractor)


def _read_sid():
    with open("/tmp/task_web_sid", "r") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_event(events, evt_id):
    for ev in events or []:
        if ev.get("id") == evt_id:
            return ev
    return None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    events = current.get("events", []) or []

    remote = _find_event(events, REMOTE_ID)
    inperson = _find_event(events, INPERSON_ID)

    if remote is None:
        print("Remote Standup event (evt_130) missing from current state.")
        return 0.0

    remote_link = (remote.get("meetLink") or "").strip()

    # --- core correctness: the meet link on Remote Standup ---
    if remote_link == TARGET_LINK:
        score = 1.0
        print("Remote Standup meetLink exactly correct.")
    elif remote_link:
        score = 0.5
        print(f"Remote Standup has a meetLink but it is not exact: {remote_link!r}")
    else:
        score = 0.0
        print("Remote Standup meetLink is still empty (task not done).")

    # --- over-action penalty: distractor must keep empty meetLink ---
    if inperson is not None:
        inperson_link = (inperson.get("meetLink") or "").strip()
        if inperson_link:
            print(
                "Over-action: In-Person Standup (evt_131) meetLink was modified "
                f"to {inperson_link!r}; it must stay empty."
            )
            score = score * 0.5
    else:
        print("In-Person Standup event (evt_131) missing — possible over-action.")
        score = score * 0.5

    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print(f"Error computing reward: {e}")
        reward = 0.0
    print(f"REWARD: {reward}")
