#!/usr/bin/env python3
"""Reward for google_calendar_032.

Task: Create a new event "Mom's Birthday Dinner" on March 28 at 7 PM for 2 hours,
on the Family calendar (c3), with mom@example.com as a guest and a 1-day-before
(1440-minute) popup reminder. evt_220 ('Work Deadline') must remain unchanged.

Scores ONLY the task-introduced change (the newly appended event), is progressive
(0.0-1.0), and penalizes over-action on the pre-existing distractor event.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

# --- target spec ---------------------------------------------------------------
TARGET_TITLE = "mom's birthday dinner"
TARGET_CAL = "c3"  # Family
TARGET_START = (2026, 3, 28, 19, 0)  # March 28, 7 PM
TARGET_END = (2026, 3, 28, 21, 0)    # +2 hours
TARGET_GUEST = "mom@example.com"
TARGET_REMINDER = ("popup", 1440)    # 1-day-before popup


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_dt(s):
    """Return (y, m, d, H, M) from an ISO datetime string, ignoring tz."""
    if not isinstance(s, str) or not s:
        return None
    from datetime import datetime

    txt = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
        return (dt.year, dt.month, dt.day, dt.hour, dt.minute)
    except Exception:
        # Best-effort manual parse for "YYYY-MM-DDTHH:MM..."
        try:
            date_part, time_part = txt[:19].split("T")
            y, mo, d = (int(x) for x in date_part.split("-"))
            hh, mm = (int(x) for x in time_part.split(":")[:2])
            return (y, mo, d, hh, mm)
        except Exception:
            return None


def norm(s):
    return (s or "").strip().lower()


def find_event_by_id(events, eid):
    for e in events:
        if e.get("id") == eid:
            return e
    return None


def main():
    sid = read_sid()
    data = fetch_state(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_events = initial.get("events", []) or []
    cur_events = current.get("events", []) or []

    init_ids = {e.get("id") for e in init_events}

    # --- identify the task-introduced (newly appended) event ----------------
    # New = present in current but not in initial. Prefer one whose title matches.
    new_events = [e for e in cur_events if e.get("id") not in init_ids]
    target = None
    for e in new_events:
        if norm(e.get("title")) == TARGET_TITLE:
            target = e
            break
    if target is None and new_events:
        # title not exact but a new event exists; pick best title-ish match
        for e in new_events:
            if "birthday" in norm(e.get("title")) and "dinner" in norm(e.get("title")):
                target = e
                break

    score = 0.0
    breakdown = {}

    if target is None:
        # No new event created at all -> nothing introduced.
        print("DETAIL: no newly-created event found")
        print("REWARD: 0.0")
        return

    # 1) Correct title (0.2)
    title_ok = norm(target.get("title")) == TARGET_TITLE
    breakdown["title"] = 0.2 if title_ok else 0.0

    # 2) On the Family calendar c3 (0.2)
    cal_ok = target.get("calendarId") == TARGET_CAL
    breakdown["calendar"] = 0.2 if cal_ok else 0.0

    # 3) Correct start AND 2-hour span (0.2 -> 0.1 start, 0.1 end)
    start_ok = parse_dt(target.get("start")) == TARGET_START
    end_ok = parse_dt(target.get("end")) == TARGET_END
    breakdown["start"] = 0.1 if start_ok else 0.0
    breakdown["end"] = 0.1 if end_ok else 0.0

    # 4) Guest mom@example.com present (0.2)
    guests = target.get("guests", []) or []
    guests_norm = {norm(g) for g in guests if isinstance(g, str)}
    guest_ok = TARGET_GUEST in guests_norm
    breakdown["guest"] = 0.2 if guest_ok else 0.0

    # 5) 1-day-before popup reminder (0.2)
    reminders = target.get("reminders", []) or []
    rem_ok = any(
        isinstance(r, dict)
        and norm(r.get("type")) == TARGET_REMINDER[0]
        and r.get("minutes") == TARGET_REMINDER[1]
        for r in reminders
    )
    breakdown["reminder"] = 0.2 if rem_ok else 0.0

    score = sum(breakdown.values())

    # --- over-action penalty: distractor evt_220 must be untouched ----------
    init_220 = find_event_by_id(init_events, "evt_220")
    cur_220 = find_event_by_id(cur_events, "evt_220")
    penalty = 0.0
    if init_220 is not None:
        if cur_220 is None:
            # distractor deleted -> heavy penalty
            penalty = 0.5
            breakdown["evt_220_deleted"] = True
        else:
            unchanged = (
                cur_220.get("calendarId") == init_220.get("calendarId")
                and norm(cur_220.get("title")) == norm(init_220.get("title"))
                and parse_dt(cur_220.get("start")) == parse_dt(init_220.get("start"))
                and parse_dt(cur_220.get("end")) == parse_dt(init_220.get("end"))
            )
            if not unchanged:
                penalty = 0.5
                breakdown["evt_220_modified"] = True

    score = max(0.0, score - penalty)
    score = round(min(1.0, score), 4)

    print("DETAIL:", json.dumps(breakdown))
    print("REWARD:", score)


if __name__ == "__main__":
    main()
