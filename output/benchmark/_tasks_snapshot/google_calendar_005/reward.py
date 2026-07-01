"""Reward for: Hide all events from my "Work" calendar.

Task-introduced change: the "Work" calendar's `visible` flag must be flipped
from true -> false. Personal and Family calendars must keep their original
visibility, and no events may be deleted.

Scoring (progressive 0.0 - 1.0):
  - 0.0  if the Work calendar is still visible (task not done).
  - 1.0  if the Work calendar is hidden AND nothing else was over-touched.
  - Over-action penalties (only applied once Work is hidden) reduce the score:
      * another calendar that was visible is now hidden  -> -0.5 each
      * any event deleted                                -> -0.5
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_calendar(calendars, name):
    """Return the calendar dict whose name matches `name` (case-insensitive)."""
    for cal in calendars or []:
        if str(cal.get("name", "")).strip().lower() == name.lower():
            return cal
    return None


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_cals = current.get("calendars", []) or []
    init_cals = initial.get("calendars", []) or []

    work_cur = _find_calendar(cur_cals, "Work")
    if work_cur is None:
        # Work calendar must not be deleted; without it the task cannot be scored.
        print("Work calendar not found in current state.")
        print("REWARD: 0.0")
        return

    # Primary criterion: Work calendar is hidden.
    work_visible = bool(work_cur.get("visible", True))
    if work_visible:
        print("Work calendar still visible -> task not done.")
        print("REWARD: 0.0")
        return

    score = 1.0

    # Over-action: any OTHER calendar that was visible initially must stay visible.
    init_visible_by_id = {
        c.get("id"): bool(c.get("visible", True)) for c in init_cals
    }
    work_id = work_cur.get("id")
    for cal in cur_cals:
        cid = cal.get("id")
        if cid == work_id:
            continue
        was_visible = init_visible_by_id.get(cid, True)
        now_visible = bool(cal.get("visible", True))
        if was_visible and not now_visible:
            print(f"Over-action: calendar {cal.get('name')} ({cid}) was hidden too.")
            score -= 0.5

    # Over-action: no events may be deleted.
    init_events = initial.get("events", []) or []
    cur_events = current.get("events", []) or []
    init_ids = {e.get("id") for e in init_events}
    cur_ids = {e.get("id") for e in cur_events}
    deleted = init_ids - cur_ids
    if deleted:
        print(f"Over-action: {len(deleted)} event(s) deleted: {sorted(deleted)}")
        score -= 0.5

    score = max(0.0, min(1.0, score))
    print(f"Work calendar hidden correctly. Final score after penalties: {score}")
    print(f"REWARD: {score}")


if __name__ == "__main__":
    compute_reward()
