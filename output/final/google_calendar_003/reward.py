"""Reward for: Switch my calendar to Month view.

Scores ONLY the task-introduced change: the calendar `view` field must change
from its initial value ('week') to 'month'. Everything else (currentDate,
events, calendars, settings, user, sidebarOpen) must remain unchanged
(over-action penalty).

Scoring (progressive, 0.0 - 1.0):
  +0.8  view == 'month'  (the core, required change)
  +0.2  no over-action: all other top-level state fields unchanged

initial state (view == 'week', nothing else touched) -> 0.0
golden  state (view == 'month', nothing else touched) -> 1.0
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state():
    sid = _read_sid()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_reward():
    data = _get_state()
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    score = 0.0

    # --- Core change: view switched to 'month' (0.8) ---
    view = current.get("view")
    if view == "month":
        score += 0.8
    else:
        # Not done (still 'week' or some other view) -> no core credit.
        print(f"view is {view!r}, expected 'month'")

    # --- Over-action penalty: every OTHER top-level field must be unchanged (0.2) ---
    # We compare current vs initial for all keys except the intended 'view'.
    keys = set(initial.keys()) | set(current.keys())
    keys.discard("view")

    unchanged = True
    for k in keys:
        if current.get(k) != initial.get(k):
            unchanged = False
            print(f"over-action: field {k!r} was modified (should be unchanged)")

    if unchanged:
        score += 0.2

    # Only award the over-action bonus meaningfully once the core change exists;
    # but on the pristine initial state nothing has changed AND view != 'month',
    # so score would be 0.2 with the bonus alone. Guard: require the core change
    # before granting any reward, so the not-done initial state scores 0.0.
    if view != "month":
        score = 0.0

    return max(0.0, min(1.0, score))


if __name__ == "__main__":
    reward = compute_reward()
    print(f"REWARD: {reward}")
