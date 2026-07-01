"""Reward for google_calendar task:
Add a new event "Dentist Appointment" on March 18, 2026 from 2:00 PM to 3:00 PM
on the default Personal calendar (c1).

Scoring (progressive, exact state checks only):
  +0.30  a NEW event titled "Dentist Appointment" was appended
  +0.30  its start is 2026-03-18 at 14:00 (2:00 PM, wall-clock)
  +0.20  its end is 2026-03-18 at 15:00 (3:00 PM) -> 1h duration
  +0.20  it sits on the default Personal calendar (c1)
  gate:  the two pre-existing events (evt_001, evt_002) must be UNCHANGED;
         any modification to them zeroes the reward (over-action penalty).
"""

import json
import re
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_go(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_wallclock(s):
    """Return (year, month, day, hour, minute) from an ISO datetime string,
    using the wall-clock representation (no timezone conversion). The expected
    end state is 'local equivalent', so we compare the displayed components."""
    if not s or not isinstance(s, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", s)
    if not m:
        return None
    y, mo, d, h, mi = (int(g) for g in m.groups())
    return (y, mo, d, h, mi)


def norm_title(t):
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def event_key(e):
    """Stable comparable snapshot of an event for unchanged-check."""
    return json.dumps(e, sort_keys=True)


def main():
    sid = read_sid()
    data = fetch_go(sid)

    initial = data.get("initial_state") or {}
    current = data.get("current_state") or {}

    init_events = initial.get("events") or []
    cur_events = current.get("events") or []

    init_by_id = {e.get("id"): e for e in init_events}
    cur_by_id = {e.get("id"): e for e in cur_events}

    # --- Over-action gate: pre-existing events must be unchanged -------------
    for eid in ("evt_001", "evt_002"):
        before = init_by_id.get(eid)
        after = cur_by_id.get(eid)
        if before is None:
            # nothing to compare against; skip silently
            continue
        if after is None or event_key(before) != event_key(after):
            print("Pre-existing event %s was modified or removed -> over-action." % eid)
            print("REWARD: 0.0")
            return

    # --- Identify the newly added Dentist Appointment event -----------------
    init_ids = set(init_by_id.keys())
    new_events = [e for e in cur_events if e.get("id") not in init_ids]

    # Candidate = a new event whose title looks like "Dentist Appointment".
    candidates = [e for e in new_events if "dentist" in norm_title(e.get("title"))]

    score = 0.0

    if not candidates:
        # Maybe the agent reused an existing slot / didn't title it correctly but
        # added a new event. Give partial credit only if a brand-new event exists
        # that lands on the right date+time (handled below via best-match search).
        date_time_pool = new_events
    else:
        date_time_pool = candidates
        # +0.30 for a correctly-titled new event
        score += 0.30

    # Pick the best matching event from the pool (prefer exact start match).
    target_start = (2026, 3, 18, 14, 0)
    target_end = (2026, 3, 18, 15, 0)

    def match_score(e):
        s = 0
        if parse_wallclock(e.get("start")) == target_start:
            s += 2
        if parse_wallclock(e.get("end")) == target_end:
            s += 1
        return s

    chosen = None
    if date_time_pool:
        chosen = max(date_time_pool, key=match_score)

    if chosen is not None:
        # If we had no titled candidate but a new event matches date+time well,
        # we still don't award the title credit (already handled).
        cstart = parse_wallclock(chosen.get("start"))
        cend = parse_wallclock(chosen.get("end"))

        if cstart == target_start:
            score += 0.30
        elif cstart is not None and cstart[:3] == target_start[:3]:
            # right date, wrong time-of-day -> partial
            score += 0.10

        if cend == target_end:
            score += 0.20
        elif cstart == target_start and cend is not None and cend[:3] == (2026, 3, 18):
            # right start, end on same day but not exactly 3 PM -> partial
            score += 0.05

        # +0.20 for the default Personal calendar (c1)
        cal = chosen.get("calendarId")
        if cal == "c1":
            score += 0.20

    score = max(0.0, min(1.0, round(score, 2)))
    print("REWARD: %s" % score)


if __name__ == "__main__":
    main()
