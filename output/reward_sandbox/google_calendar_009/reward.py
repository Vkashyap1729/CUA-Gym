"""Reward for: Switch the calendar to use 24-hour time format.

Scores ONLY the task-introduced change: settings.timeFormat '12h' -> '24h'.
- 0.0 on the initial (not-done) state (timeFormat still '12h').
- 1.0 on the fully-completed state (timeFormat '24h', all other settings unchanged).
Over-action (changing other settings sub-keys) is penalized.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

# Expected baseline for the other settings sub-keys (from the task context).
EXPECTED_OTHER = {
    "weekStart": 0,
    "defaultDuration": 60,
    "defaultReminder": {"type": "popup", "minutes": 10},
}


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    settings = current.get("settings", {}) or {}

    score = 0.0

    # --- Primary criterion: timeFormat switched to 24h (0.8) ---
    time_format = settings.get("timeFormat")
    if time_format == "24h":
        score += 0.8
    elif time_format == "12h":
        score += 0.0  # not done
    else:
        # Some other/invalid value: partial credit for having moved away from 12h
        # but it isn't the requested target.
        score += 0.0

    # --- Over-action guard: other settings sub-keys must be unchanged (0.2) ---
    other_ok = all(settings.get(k) == v for k, v in EXPECTED_OTHER.items())
    if other_ok:
        score += 0.2
    # If primary not done, ensure initial state scores exactly 0.0 even though
    # the over-action guard would otherwise be satisfied.
    if time_format != "24h":
        score = 0.0

    score = max(0.0, min(1.0, score))
    return score


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("Error computing reward:", e)
        reward = 0.0
    print("REWARD: " + str(round(float(reward), 2)))
