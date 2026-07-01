#!/usr/bin/env python3
"""Reward for: Change the location of the "Project Kickoff" meeting to "Conference Room B".

Exact-state check (no LLM judge needed):
  - evt_010 'Project Kickoff' location must become 'Conference Room B'
  - evt_011 'Sprint Review' (distractor, also originally in 'Conference Room A')
    must keep its location 'Conference Room A'
Progressive: 0.0 on initial (not done), 1.0 on fully completed, partial credit
for changing the target while penalizing over-action on the distractor.
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_ID = "evt_010"
TARGET_TITLE = "Project Kickoff"
EXPECTED_LOCATION = "Conference Room B"

DISTRACTOR_ID = "evt_011"
DISTRACTOR_ORIGINAL_LOCATION = "Conference Room A"


def _norm(s):
    return (s or "").strip()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    events = current.get("events", []) or []

    by_id = {e.get("id"): e for e in events if isinstance(e, dict)}

    target = by_id.get(TARGET_ID)
    # Fall back to title match if the id ever changes.
    if target is None:
        for e in events:
            if isinstance(e, dict) and _norm(e.get("title")) == TARGET_TITLE:
                target = e
                break

    distractor = by_id.get(DISTRACTOR_ID)

    score = 0.0

    # --- Main criterion (0.8): target event location changed correctly ---
    if target is not None:
        loc = _norm(target.get("location"))
        if loc.lower() == EXPECTED_LOCATION.lower():
            score += 0.8
        # else: not yet changed (or wrong value) -> 0 for this portion

    # --- Over-action penalty / distractor preserved (0.2) ---
    # Only award this when the main change is done, so initial state stays 0.0.
    if score >= 0.8 and distractor is not None:
        d_loc = _norm(distractor.get("location"))
        if d_loc.lower() == DISTRACTOR_ORIGINAL_LOCATION.lower():
            score += 0.2
        # distractor was modified -> withhold the 0.2 (over-action)

    if score > 1.0:
        score = 1.0
    if score < 0.0:
        score = 0.0

    print("REWARD: " + str(round(score, 1)))


if __name__ == "__main__":
    main()
