#!/usr/bin/env python3
"""Reward for google_calendar_031.

Task: De-duplicate the calendar. Two identical "Lunch with Sarah" events exist on
2026-03-20 12:00-13:00 (evt_210, evt_211). Exactly ONE of them must be deleted so a
single "Lunch with Sarah" remains. The unrelated "Afternoon Walk" (evt_212) on the same
day must be left untouched, and no extra events may be introduced.

Scoring is by exact state inspection (no subjective content), so no LLM judge is used.
  - 0.0 on the initial (still-duplicated) state.
  - 1.0 on the fully-completed state (one lunch removed, walk intact, nothing added).
  - Over-action (deleting/altering the walk, or adding stray events) is penalized.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_DATE = "2026-03-20"
LUNCH_TITLE = "Lunch with Sarah"
WALK_TITLE = "Afternoon Walk"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _norm(s):
    return (s or "").strip()


def _is_target_lunch(evt):
    """An identical 'Lunch with Sarah' on 2026-03-20 12:00-13:00."""
    if _norm(evt.get("title")) != LUNCH_TITLE:
        return False
    start = _norm(evt.get("start"))
    end = _norm(evt.get("end"))
    return start.startswith(TARGET_DATE + "T12:00") and end.startswith(TARGET_DATE + "T13:00")


def _is_walk(evt):
    """The unrelated 'Afternoon Walk' on 2026-03-20 15:00-15:30 (evt_212)."""
    if _norm(evt.get("title")) != WALK_TITLE:
        return False
    start = _norm(evt.get("start"))
    end = _norm(evt.get("end"))
    return start.startswith(TARGET_DATE + "T15:00") and end.startswith(TARGET_DATE + "T15:30")


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state") or {}
    events = current.get("events") or []

    lunch_events = [e for e in events if _is_target_lunch(e)]
    walk_events = [e for e in events if _is_walk(e)]

    lunch_count = len(lunch_events)
    walk_ok = len(walk_events) == 1

    # Anything that is neither a target lunch nor the expected walk is unexpected.
    unexpected = [e for e in events if not _is_target_lunch(e) and not _is_walk(e)]

    score = 0.0

    # --- Primary objective: exactly one "Lunch with Sarah" remains (0.8) ---
    # lunch_count == 2 -> not started (initial). 0 -> over-deleted (both gone).
    if lunch_count == 1:
        score += 0.8

        # --- Preserve the unrelated event (0.2) ---
        if walk_ok:
            score += 0.2

        # --- Over-action penalty: no stray/extra events should appear ---
        if unexpected:
            score = max(0.0, score - 0.3)

    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as exc:  # noqa: BLE001
        print("ERROR computing reward:", exc)
        reward = 0.0
    print("REWARD: %s" % reward)
