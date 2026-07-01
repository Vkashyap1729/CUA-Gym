#!/usr/bin/env python3
"""Reward for: Delete the "Lunch with Sarah" event from the calendar.

Task-introduced change: evt_002 ("Lunch with Sarah", c1) must be removed from
the events array. The two other events that share the day, evt_001
("Team Standup") and evt_003 ("Gym Session"), are distractors and MUST remain
untouched (over-action penalty).

Scoring (progressive, 0.0-1.0):
  - 0.70  the "Lunch with Sarah" event is gone from the events array (gating)
  - 0.15  distractor evt_001 still present and byte-for-byte unchanged
  - 0.15  distractor evt_003 still present and byte-for-byte unchanged

If the target event is NOT deleted the reward is 0.0 (the task has not been
done), so the not-done initial state scores 0.0 and the fully-completed golden
state scores 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_ID = "evt_002"
TARGET_TITLE = "lunch with sarah"
DISTRACTOR_IDS = ["evt_001", "evt_003"]


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _events_by_id(events):
    out = {}
    for ev in events or []:
        if isinstance(ev, dict) and ev.get("id"):
            out[ev["id"]] = ev
    return out


def _target_present(events):
    """True if the 'Lunch with Sarah' event is still in the events array.

    Match by id first, then fall back to a title match so a model that
    deleted-and-recreated, or whose event carries a different id, is still
    judged correctly.
    """
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        if ev.get("id") == TARGET_ID:
            return True
        if (ev.get("title") or "").strip().lower() == TARGET_TITLE:
            return True
    return False


def main():
    sid = _read_sid()
    data = _fetch_state(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_events = initial.get("events", []) or []
    cur_events = current.get("events", []) or []

    init_by_id = _events_by_id(init_events)
    cur_by_id = _events_by_id(cur_events)

    reward = 0.0

    # --- Gating: the target event must be removed -------------------------
    if _target_present(cur_events):
        # Task not done (this is the initial / not-done state).
        print("Target event 'Lunch with Sarah' still present -> task not done.")
        print(f"REWARD: {0.0:.1f}")
        return

    reward += 0.70
    print("PASS: 'Lunch with Sarah' (evt_002) removed from events (+0.70)")

    # --- Over-action: distractors must be untouched ----------------------
    per_distractor = 0.30 / len(DISTRACTOR_IDS)
    for did in DISTRACTOR_IDS:
        init_ev = init_by_id.get(did)
        cur_ev = cur_by_id.get(did)
        if cur_ev is None:
            print(f"PENALTY: distractor {did} was deleted (over-action).")
            continue
        if init_ev is not None and cur_ev == init_ev:
            reward += per_distractor
            print(f"PASS: distractor {did} unchanged (+{per_distractor:.2f})")
        else:
            print(f"PENALTY: distractor {did} was modified (over-action).")

    reward = max(0.0, min(1.0, reward))
    print(f"REWARD: {reward:.2f}")


if __name__ == "__main__":
    main()
