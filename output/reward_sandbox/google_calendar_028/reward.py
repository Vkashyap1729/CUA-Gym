"""Reward for google_calendar_028.

Task: Create three back-to-back 30-minute interview slots titled
"Interview - Candidate A/B/C" starting at 1 PM on March 26 on the Work calendar (c2).

Expected new events (all 2026-03-26, calendarId c2):
  - "Interview - Candidate A"  13:00-13:30
  - "Interview - Candidate B"  13:30-14:00
  - "Interview - Candidate C"  14:00-14:30

Distractor that must remain unchanged: evt_180 "Lunch" (c1, 12:00-13:00).

Scoring is an exact state check (no subjective content => no LLM judge needed).
"""

import re
import sys
import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def parse_components(s):
    """Extract (year, month, day, hour, minute) from an ISO 8601 datetime string.

    Events are stored in UTC ('...Z') consistently for both injected and
    user-created events, so comparing raw wall-clock components is robust.
    """
    if not isinstance(s, str):
        return None
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", s)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def norm_title(t):
    return re.sub(r"\s+", " ", (t or "").strip()).lower()


def main():
    try:
        with open("/tmp/task_web_sid") as f:
            sid = f.read().strip()
    except Exception as e:
        print("Could not read sid:", e)
        print("REWARD: 0.0")
        return

    try:
        url = BASE_URL + "/go?sid=" + sid
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("Could not fetch state:", e)
        print("REWARD: 0.0")
        return

    current = data.get("current_state") or {}
    events = current.get("events") or []

    # ---- Expected interview slots -------------------------------------------
    # (title, calendarId, start_components, end_components)
    DATE = (2026, 3, 26)
    expected = [
        ("Interview - Candidate A", "c2", DATE + (13, 0), DATE + (13, 30)),
        ("Interview - Candidate B", "c2", DATE + (13, 30), DATE + (14, 0)),
        ("Interview - Candidate C", "c2", DATE + (14, 0), DATE + (14, 30)),
    ]

    score = 0.0
    per_event = 1.0 / len(expected)  # ~0.3333 per slot

    used_ids = set()
    for title, cal, exp_start, exp_end in expected:
        wanted = norm_title(title)

        # find an as-yet-unused event whose title matches
        match = None
        for ev in events:
            if id(ev) in used_ids:
                continue
            if norm_title(ev.get("title")) == wanted:
                match = ev
                break
        if match is None:
            continue
        used_ids.add(id(match))

        # Sub-scores within this slot: title 0.4 / calendar 0.2 / start 0.2 / end 0.2
        sub = 0.4  # title matched (event identified)
        if match.get("calendarId") == cal:
            sub += 0.2
        if parse_components(match.get("start")) == exp_start:
            sub += 0.2
        if parse_components(match.get("end")) == exp_end:
            sub += 0.2

        score += per_event * sub

    # ---- Over-action penalty: the Lunch distractor must be untouched --------
    lunch = None
    for ev in events:
        if ev.get("id") == "evt_180":
            lunch = ev
            break

    lunch_ok = (
        lunch is not None
        and norm_title(lunch.get("title")) == "lunch"
        and lunch.get("calendarId") == "c1"
        and parse_components(lunch.get("start")) == (2026, 3, 26, 12, 0)
        and parse_components(lunch.get("end")) == (2026, 3, 26, 13, 0)
    )
    if not lunch_ok:
        score *= 0.5  # the protected event was altered/removed -> over-action

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 4)))


if __name__ == "__main__":
    main()
