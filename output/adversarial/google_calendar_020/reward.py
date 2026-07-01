"""Reward for google_calendar_020.

Task: Delete the recurring "Old Weekly Sync" event and create a new "Team Retro"
event on March 20 from 3 PM to 4 PM (2026-03-20 15:00-16:00).

Scoring (progressive, exact state checks only):
  - "Old Weekly Sync" deleted .................... 0.40
  - a "Team Retro" event exists ................. 0.20
  - its start is 2026-03-20 15:00 .............. 0.20
  - its end is 2026-03-20 16:00 ................ 0.20
Over-action penalty: the distractor "Team Standup" event must remain
untouched (same title / start / end). If it was deleted or modified the
reward is forced to 0.0.
"""

import json
import urllib.request
from datetime import datetime

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_dt(s):
    """Parse an ISO 8601 datetime string (tolerant of trailing 'Z')."""
    if not isinstance(s, str) or not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Fall back to date-only / loose parsing.
        try:
            return datetime.fromisoformat(s[:19])
        except ValueError:
            return None


def _norm_title(t):
    return (t or "").strip().lower()


def _matches_dt(dt, year, month, day, hour, minute):
    if dt is None:
        return False
    return (
        dt.year == year
        and dt.month == month
        and dt.day == day
        and dt.hour == hour
        and dt.minute == minute
    )


def main():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    events = current.get("events", []) or []

    score = 0.0

    # --- Over-action guard: the distractor "Team Standup" must be untouched ---
    # Original: evt_111 'Team Standup', start 2026-03-13 09:00, end 09:30, calendar c2.
    standup = None
    for e in events:
        if _norm_title(e.get("title")) == "team standup":
            standup = e
            break
    standup_ok = False
    if standup is not None:
        s = _parse_dt(standup.get("start"))
        en = _parse_dt(standup.get("end"))
        if _matches_dt(s, 2026, 3, 13, 9, 0) and _matches_dt(en, 2026, 3, 13, 9, 30):
            standup_ok = True

    # --- Criterion 1: "Old Weekly Sync" deleted (0.40) ---
    old_sync_present = any(
        _norm_title(e.get("title")) == "old weekly sync" for e in events
    )
    if not old_sync_present:
        score += 0.40

    # --- Criterion 2/3/4: "Team Retro" created at the correct time ---
    retro = None
    for e in events:
        if _norm_title(e.get("title")) == "team retro":
            retro = e
            break

    if retro is not None:
        score += 0.20  # event exists with correct title
        start = _parse_dt(retro.get("start"))
        end = _parse_dt(retro.get("end"))
        if _matches_dt(start, 2026, 3, 20, 15, 0):
            score += 0.20
        if _matches_dt(end, 2026, 3, 20, 16, 0):
            score += 0.20

    # Apply the over-action penalty last: tampering with the distractor zeroes it.
    if not standup_ok:
        score = 0.0

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
