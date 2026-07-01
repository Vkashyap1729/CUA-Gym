"""Reward for: Move the "1:1 with Manager" meeting from 9 AM to 4 PM on the same
day, keeping it one hour long.

Task-introduced change ONLY:
  evt_020 '1:1 with Manager'  start 2026-03-17 09:00 -> 16:00,  end 10:00 -> 17:00
  (date unchanged, duration preserved at 1 hour)

Distractor evt_021 'Lunch' must remain untouched (over-action penalty).

Scoring (progressive, 0.0 .. 1.0):
  +0.5  start moved to 16:00 on 2026-03-17
  +0.5  end at 17:00 on 2026-03-17 AND duration preserved at exactly 60 minutes
  x0.5  penalty applied to the total if the 'Lunch' distractor was modified
"""

import re
import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

EXPECTED_DATE = (2026, 3, 17)
EXPECTED_START_HM = (16, 0)
EXPECTED_END_HM = (17, 0)
EXPECTED_DURATION_MIN = 60

_DT_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})")


def parse_dt(s):
    """Extract (year, month, day, hour, minute) from an ISO-ish datetime string."""
    if not isinstance(s, str):
        return None
    m = _DT_RE.search(s)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def minutes_between(start, end):
    """Whole-minute duration between two parsed datetimes (same date assumed)."""
    if start is None or end is None:
        return None
    sd = (start[0], start[1], start[2])
    ed = (end[0], end[1], end[2])
    if sd != ed:
        # different calendar dates -> compute via simple ordinal day difference is
        # unnecessary here; the task keeps the same day, so flag as mismatch.
        return None
    return (end[3] * 60 + end[4]) - (start[3] * 60 + start[4])


def find_event(events, evt_id, title):
    by_id = None
    by_title = None
    for e in events or []:
        if e.get("id") == evt_id:
            by_id = e
        if (e.get("title") or "").strip().lower() == title.strip().lower():
            by_title = by_title or e
    return by_id or by_title


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}
    events = current.get("events") or []

    meeting = find_event(events, "evt_020", "1:1 with Manager")

    score = 0.0

    if meeting is not None:
        start = parse_dt(meeting.get("start"))
        end = parse_dt(meeting.get("end"))

        # +0.5 start moved to 16:00 on the correct (same) date
        if start is not None and start[:3] == EXPECTED_DATE and start[3:5] == EXPECTED_START_HM:
            score += 0.5

        # +0.5 end at 17:00 on the correct date AND duration preserved (1 hour)
        dur = minutes_between(start, end)
        if (
            end is not None
            and end[:3] == EXPECTED_DATE
            and end[3:5] == EXPECTED_END_HM
            and dur == EXPECTED_DURATION_MIN
        ):
            score += 0.5

    # Over-action penalty: the 'Lunch' distractor (evt_021) must be unchanged.
    init_lunch = find_event(initial.get("events") or [], "evt_021", "Lunch")
    cur_lunch = find_event(events, "evt_021", "Lunch")
    lunch_ok = True
    if init_lunch is None or cur_lunch is None:
        # missing/deleted distractor is itself over-action
        lunch_ok = (init_lunch is None and cur_lunch is None)
    else:
        for field in ("title", "start", "end", "calendarId"):
            if init_lunch.get(field) != cur_lunch.get(field):
                lunch_ok = False
                break

    if not lunch_ok:
        score *= 0.5

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    main()
