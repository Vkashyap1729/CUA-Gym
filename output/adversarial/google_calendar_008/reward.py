"""Reward for: Collapse the left sidebar so the calendar takes the full width.

Task-introduced change: sidebarOpen true -> false. No other fields should change.
Scoring is a single exact-state check (sidebarOpen == false) with an over-action
penalty: if the agent mutated unrelated state (events, view, calendars, settings,
user, currentDate), points are deducted.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


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
    initial = data.get("initial_state", {}) or {}

    score = 0.0

    # --- Primary criterion: sidebar collapsed (sidebarOpen == False) ---
    sidebar = current.get("sidebarOpen", True)
    if sidebar is False:
        score = 1.0
    else:
        # Not done. The initial (not-done) state has sidebarOpen == True -> 0.0.
        return 0.0

    # --- Over-action penalty: nothing else should have changed ---
    # Compare task-irrelevant fields against the initial state. Any divergence
    # means the agent did more than collapse the sidebar.
    guarded_keys = ["events", "view", "calendars", "settings", "user", "currentDate"]
    for key in guarded_keys:
        if json.dumps(initial.get(key), sort_keys=True) != json.dumps(
            current.get(key), sort_keys=True
        ):
            score -= 0.5
            break

    if score < 0.0:
        score = 0.0
    return score


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: " + str(round(reward, 1)))
