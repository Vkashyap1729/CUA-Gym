#!/usr/bin/env python3
"""Reward for google_calendar_016.

Task: Reschedule the "Quarterly Planning" meeting to next Monday, March 23rd,
keeping the same start time and duration.

INITIAL: evt_070 'Quarterly Planning' (c2) 2026-03-16 13:00-15:00 (Monday).
EXPECTED: evt_070 start -> 2026-03-23T13:00, end -> 2026-03-23T15:00 (same 13:00
start, same 2h duration). evt_071 'Budget Review' untouched.

Scoring (progressive, 0.0 on initial, 1.0 on golden):
  - start moved to the correct new date (2026-03-23): 0.4
  - end   moved to the correct new date (2026-03-23): 0.4
  - times/duration preserved (start 13:00 AND end 15:00), gated on the move
    having happened so the unchanged-time initial state scores 0.0: 0.2
  - over-action penalty: the distractor event evt_071 ('Budget Review') and the
    rescheduled event's own non-temporal fields (title/calendar) must be intact.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

# --- expected values -------------------------------------------------------
TARGET_ID = "evt_070"
DISTRACTOR_ID = "evt_071"
EXPECTED_DATE = "2026-03-23"
EXPECTED_START_TIME = "13:00"
EXPECTED_END_TIME = "15:00"
EXPECTED_TITLE = "Quarterly Planning"


def _split_iso(value):
    """Return ('YYYY-MM-DD', 'HH:MM') from an ISO 8601 datetime string."""
    if not isinstance(value, str) or "T" not in value:
        return None, None
    date_part, _, time_part = value.partition("T")
    return date_part.strip(), time_part.strip()[:5]


def _find_event(events, evt_id):
    for ev in events or []:
        if isinstance(ev, dict) and ev.get("id") == evt_id:
            return ev
    return None


def main():
    with open("/tmp/task_web_sid") as fh:
        sid = fh.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}
    cur_events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    score = 0.0

    target = _find_event(cur_events, TARGET_ID)
    if target is None:
        # The event was deleted / lost -> task not accomplished.
        print("evt_070 not found in current state")
        print("REWARD: 0.0")
        return

    start_date, start_time = _split_iso(target.get("start"))
    end_date, end_time = _split_iso(target.get("end"))

    start_moved = start_date == EXPECTED_DATE
    end_moved = end_date == EXPECTED_DATE

    if start_moved:
        score += 0.4
    if end_moved:
        score += 0.4

    # Time/duration preservation only counts once the event has actually been
    # moved to the new date. This keeps the initial (unchanged-time) state at 0.
    if start_moved and end_moved:
        if start_time == EXPECTED_START_TIME and end_time == EXPECTED_END_TIME:
            score += 0.2

    print(
        f"evt_070 start={target.get('start')} end={target.get('end')} "
        f"(start_moved={start_moved}, end_moved={end_moved}, "
        f"start_time={start_time}, end_time={end_time})"
    )

    # --- over-action penalties --------------------------------------------
    penalty = 0.0

    # The rescheduled event's identity fields must be intact.
    if target.get("title") != EXPECTED_TITLE:
        penalty += 0.3
        print(f"PENALTY: evt_070 title changed -> {target.get('title')!r}")
    init_target = _find_event(init_events, TARGET_ID)
    if init_target is not None and target.get("calendarId") != init_target.get("calendarId"):
        penalty += 0.3
        print("PENALTY: evt_070 calendarId changed")

    # The distractor event must be completely unchanged.
    init_distractor = _find_event(init_events, DISTRACTOR_ID)
    cur_distractor = _find_event(cur_events, DISTRACTOR_ID)
    if cur_distractor is None:
        penalty += 0.5
        print("PENALTY: distractor evt_071 was deleted")
    elif init_distractor is not None and cur_distractor != init_distractor:
        penalty += 0.5
        print("PENALTY: distractor evt_071 was modified")

    final = max(0.0, score - penalty)
    final = round(min(1.0, final), 2)
    print(f"REWARD: {final}")


if __name__ == "__main__":
    main()
