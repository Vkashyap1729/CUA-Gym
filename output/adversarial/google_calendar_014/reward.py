#!/usr/bin/env python3
"""Reward for: Change the color of my "Birthday Party" event to tomato red.

Expected end state:
  - The "Birthday Party" event color is changed to tomato '#D50000'.
  - The "Dinner Reservation" distractor event keeps its original peacock '#039BE5'.

Scoring (progressive, 0.0-1.0):
  - 0.0 on the initial state (Birthday Party still peacock '#039BE5').
  - Main credit (0.8) for the Birthday Party color being changed to tomato.
    Partial credit (0.4) if it was recolored but to the wrong (non-tomato) color.
  - Over-action credit (0.2): the Dinner Reservation distractor must be unchanged.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

ORIGINAL_COLOR = "#039BE5"  # peacock
TOMATO = "#D50000"


def _norm(c):
    return (c or "").strip().upper()


def _find_event(events, title):
    for e in events:
        if (e.get("title") or "").strip().lower() == title.strip().lower():
            return e
    return None


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state") or {}
    events = current.get("events") or []

    birthday = _find_event(events, "Birthday Party")
    dinner = _find_event(events, "Dinner Reservation")

    score = 0.0

    # --- Main task: Birthday Party recolored to tomato (0.8) ---
    if birthday is not None:
        cur_color = _norm(birthday.get("color"))
        if cur_color == _norm(TOMATO):
            score += 0.8
        elif cur_color and cur_color != _norm(ORIGINAL_COLOR):
            # Recolored, but to the wrong color -> partial progress credit.
            score += 0.4

    # --- Over-action: Dinner Reservation distractor must stay peacock (0.2) ---
    if dinner is not None and _norm(dinner.get("color")) == _norm(ORIGINAL_COLOR):
        score += 0.2

    # Guard: only award the over-action credit if the main change shows progress,
    # so the untouched initial state still scores 0.0.
    if score == 0.2:
        score = 0.0

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD:", score)


if __name__ == "__main__":
    main()
