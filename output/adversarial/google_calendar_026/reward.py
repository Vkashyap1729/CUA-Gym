"""Reward for google_calendar_026.

Task: Move "Vendor Call" (evt_160) from Tuesday 2026-03-17 14:00-15:00 to
Wednesday 2026-03-18 at the SAME time (14:00-15:00), and add Eve
(eve@example.com) as a guest while keeping Frank (frank@example.com).
The distractor event evt_161 "Team Sync" must stay untouched.

Scoring (progressive, exact state checks only):
  - start moved to 2026-03-18 (same time-of-day preserved) : 0.25
  - end   moved to 2026-03-18 (same time-of-day preserved) : 0.25
  - eve@example.com added as guest                          : 0.30
  - frank@example.com retained (only credited once eve added): 0.20
  - distractor evt_161 changed -> hard penalty (cap to 0.0)
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"
TARGET_ID = "evt_160"
TARGET_TITLE = "Vendor Call"
DISTRACTOR_ID = "evt_161"
EVE = "eve@example.com"
FRANK = "frank@example.com"
NEW_DATE = "2026-03-18"


def parse_dt(iso):
    """Return (date_str 'YYYY-MM-DD', time_str 'HH:MM') from an ISO datetime."""
    if not iso or "T" not in iso:
        return None, None
    date_part, time_part = iso.split("T", 1)
    # strip timezone/fraction, keep HH:MM
    hhmm = time_part[:5]
    return date_part, hhmm


def find_event(events, ev_id, title=None):
    if not isinstance(events, list):
        return None
    for e in events:
        if isinstance(e, dict) and e.get("id") == ev_id:
            return e
    # fallback: a move done via delete+recreate keeps the title
    if title is not None:
        matches = [
            e for e in events
            if isinstance(e, dict) and e.get("title", "").strip().lower() == title.lower()
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}
    init_events = initial.get("events", []) or []
    cur_events = current.get("events", []) or []

    # --- reference time-of-day from the original event ---
    orig = find_event(init_events, TARGET_ID, TARGET_TITLE)
    orig_start_date, orig_start_time = parse_dt(orig.get("start")) if orig else (None, None)
    orig_end_date, orig_end_time = parse_dt(orig.get("end")) if orig else (None, None)
    # sensible fallbacks if initial_state was unavailable
    if orig_start_time is None:
        orig_start_time = "14:00"
    if orig_end_time is None:
        orig_end_time = "15:00"

    score = 0.0

    cur = find_event(cur_events, TARGET_ID, TARGET_TITLE)
    if cur is None:
        print("Vendor Call event not found in current state.")
        print("REWARD: 0.0")
        return

    cur_start_date, cur_start_time = parse_dt(cur.get("start"))
    cur_end_date, cur_end_time = parse_dt(cur.get("end"))

    # --- move: start ---
    if cur_start_date == NEW_DATE and cur_start_time == orig_start_time:
        score += 0.25
    else:
        print(f"start not correctly moved: {cur.get('start')} "
              f"(want date {NEW_DATE}, time {orig_start_time})")

    # --- move: end ---
    if cur_end_date == NEW_DATE and cur_end_time == orig_end_time:
        score += 0.25
    else:
        print(f"end not correctly moved: {cur.get('end')} "
              f"(want date {NEW_DATE}, time {orig_end_time})")

    # --- guests ---
    guests = cur.get("guests", []) or []
    guests = [g.strip().lower() for g in guests if isinstance(g, str)]
    eve_added = EVE in guests
    frank_kept = FRANK in guests
    if eve_added:
        score += 0.30
        # frank retention only credited alongside the eve addition so the
        # initial state (frank present, eve absent) scores exactly 0 here.
        if frank_kept:
            score += 0.20
        else:
            print("frank was dropped from guests (should be kept).")
    else:
        print("eve was not added as a guest.")

    # --- over-action penalty: distractor evt_161 must be unchanged ---
    init_distractor = find_event(init_events, DISTRACTOR_ID)
    cur_distractor = find_event(cur_events, DISTRACTOR_ID)
    if init_distractor is not None:
        if cur_distractor is None or cur_distractor != init_distractor:
            print(f"distractor {DISTRACTOR_ID} (Team Sync) was modified -> penalty.")
            score = 0.0

    score = round(max(0.0, min(1.0, score)), 2)
    print(f"REWARD: {score}")


main()
