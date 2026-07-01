#!/usr/bin/env python3
"""Reward for: Add a 30-minute popup reminder to the "Flight to Tokyo" event.

Scores ONLY the task-introduced change:
  - evt_060 ("Flight to Tokyo") must gain a popup reminder with minutes == 30.
  - evt_061 ("Hotel Check-in") existing reminder [{popup, 10}] must stay unchanged (over-action penalty).

Progressive:
  0.0  -> no reminder added to Flight to Tokyo (initial state)
  0.5  -> some reminder added, but not exactly a 30-minute popup
  1.0  -> a popup reminder with minutes == 30 present on Flight to Tokyo
  Then if Hotel Check-in's reminder was altered -> capped at 0.5 (over-action).
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


def _find_event(events, title):
    for ev in events or []:
        if (ev.get("title") or "").strip().lower() == title.strip().lower():
            return ev
    return None


def _as_int(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def _has_popup_minutes(reminders, minutes):
    for r in reminders or []:
        if not isinstance(r, dict):
            continue
        if (r.get("type") or "").lower() == "popup" and _as_int(r.get("minutes")) == minutes:
            return True
    return False


def main():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    events = current.get("events", []) or []

    flight = _find_event(events, "Flight to Tokyo")
    hotel = _find_event(events, "Hotel Check-in")

    score = 0.0

    if flight is None:
        print("Flight to Tokyo event not found — cannot score.")
        print("REWARD: 0.0")
        return

    flight_reminders = flight.get("reminders", []) or []

    # --- Main credit: the 30-minute popup reminder on Flight to Tokyo ---
    if _has_popup_minutes(flight_reminders, 30):
        score = 1.0
        print("PASS: Flight to Tokyo has a popup reminder with minutes == 30.")
    elif len(flight_reminders) > 0:
        # Some reminder added but not the exact target (wrong type or wrong minutes).
        score = 0.5
        print(
            "PARTIAL: a reminder was added to Flight to Tokyo but it is not a 30-min popup: "
            + json.dumps(flight_reminders)
        )
    else:
        score = 0.0
        print("Flight to Tokyo has no reminders (not-done state).")

    # --- Over-action penalty: Hotel Check-in's existing reminder must be unchanged ---
    expected_hotel = [{"type": "popup", "minutes": 10}]
    if hotel is not None:
        hotel_reminders = hotel.get("reminders", []) or []
        hotel_ok = (
            len(hotel_reminders) == 1
            and isinstance(hotel_reminders[0], dict)
            and (hotel_reminders[0].get("type") or "").lower() == "popup"
            and _as_int(hotel_reminders[0].get("minutes")) == 10
        )
        if not hotel_ok:
            score = min(score, 0.5)
            print(
                "OVER-ACTION: Hotel Check-in reminder changed (expected "
                + json.dumps(expected_hotel)
                + ", got "
                + json.dumps(hotel_reminders)
                + ") — capping score."
            )
    else:
        # Distractor event was removed entirely — definite over-action.
        score = min(score, 0.5)
        print("OVER-ACTION: Hotel Check-in event missing — capping score.")

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
