"""Reward for google_calendar_022.

Task: Set Monday as the first day of the week in calendar settings.
  INITIAL: settings.weekStart 0 (Sunday), timeFormat '12h', defaultDuration 60.
  EXPECTED: settings.weekStart == 1 (Monday); all other settings keys unchanged.

Scoring (progressive, 0.0-1.0, exact state checks only):
  +1.0  settings.weekStart == 1 (the single task-introduced change)
  Over-action penalty: any OTHER settings key changed from its initial value
  caps the score. Initial state (weekStart still 0) -> 0.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

# The settings keys we expect to remain untouched by this task.
GUARDED_SETTINGS_KEYS = [
    "defaultDuration",
    "defaultView",
    "defaultReminder",
    "timeFormat",
    "showWeekNumbers",
    "showDeclinedEvents",
]


def _get_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_reward():
    sid = _get_sid()
    data = _fetch_state(sid)

    initial_state = data.get("initial_state", {}) or {}
    current_state = data.get("current_state", {}) or {}

    init_settings = initial_state.get("settings", {}) or {}
    cur_settings = current_state.get("settings", {}) or {}

    score = 0.0

    # --- Primary criterion: weekStart set to Monday (1) ---
    week_start = cur_settings.get("weekStart")
    # Accept numeric 1 (and tolerate the string "1" just in case the UI stores it as such).
    if week_start == 1 or week_start == "1":
        score = 1.0
        print("weekStart == 1 (Monday): +1.0")
    elif week_start == 0 or week_start == "0":
        print("weekStart still 0 (Sunday) -- task not done")
    else:
        print("weekStart is %r -- not Monday(1)" % (week_start,))

    # --- Over-action penalty: other settings keys must be unchanged ---
    changed_other = []
    for key in GUARDED_SETTINGS_KEYS:
        # Compare against the initial value; if the key existed initially it must match.
        init_val = init_settings.get(key)
        cur_val = cur_settings.get(key)
        if init_val != cur_val:
            changed_other.append(key)

    if changed_other:
        print("Over-action: other settings keys changed: %s" % ", ".join(changed_other))
        # Penalize: each unintended settings change halves the reward.
        score = score * (0.5 ** len(changed_other))

    score = max(0.0, min(1.0, round(score, 4)))
    return score


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("ERROR computing reward: %r" % (e,))
        reward = 0.0
    print("REWARD: %s" % reward)
