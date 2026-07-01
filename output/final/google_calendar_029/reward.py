"""Reward for: Reschedule the "Board Meeting" to start one hour earlier, move it to
the Family calendar, and change its color to grape purple.

Task-introduced changes scored (event evt_190 "Board Meeting"):
  1. start/end shifted exactly 1 hour earlier, duration (90 min) preserved   (0.34)
  2. calendarId moved to the Family calendar 'c3'                            (0.33)
  3. color changed to grape purple '#8E24AA'                                 (0.33)

Over-action penalty: the distractor event evt_191 "Prep Notes" must be unchanged.

Scores 0.0 on the initial (not-done) state and 1.0 on the fully-completed state.
"""

import json
import urllib.request
from datetime import datetime

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

GRAPE_PURPLE = "#8e24aa"
FAMILY_CAL = "c3"
TARGET_ID = "evt_190"
DISTRACTOR_ID = "evt_191"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_go(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_dt(s):
    """Parse an ISO 8601 datetime string, tolerating a trailing 'Z' and milliseconds."""
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Fallback: strip fractional seconds / tz if fromisoformat is unhappy
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    return None


def find_event(events, eid):
    for e in events or []:
        if e.get("id") == eid:
            return e
    return None


def main():
    sid = read_sid()
    data = fetch_go(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_events = initial.get("events", []) or []
    cur_events = current.get("events", []) or []

    init_evt = find_event(init_events, TARGET_ID)
    cur_evt = find_event(cur_events, TARGET_ID)

    score = 0.0

    if cur_evt is None:
        # Target event missing entirely -> nothing to credit.
        print("Board Meeting (evt_190) not found in current state.")
        print("REWARD: 0.0")
        return

    # --- Reference times: prefer the actual initial state; fall back to ground truth. ---
    if init_evt is not None:
        init_start = parse_dt(init_evt.get("start"))
        init_end = parse_dt(init_evt.get("end"))
    else:
        init_start = parse_dt("2026-03-24T15:00:00.000Z")
        init_end = parse_dt("2026-03-24T16:30:00.000Z")

    cur_start = parse_dt(cur_evt.get("start"))
    cur_end = parse_dt(cur_evt.get("end"))

    # --- Criterion 1: shifted exactly one hour earlier, duration preserved (0.34) ---
    if cur_start and cur_end and init_start and init_end:
        start_shift = (cur_start - init_start).total_seconds()
        end_shift = (cur_end - init_end).total_seconds()
        init_dur = (init_end - init_start).total_seconds()
        cur_dur = (cur_end - cur_start).total_seconds()

        start_ok = abs(start_shift + 3600) <= 60          # 1h earlier (±1 min tol)
        dur_ok = abs(cur_dur - init_dur) <= 60            # duration preserved
        end_ok = abs(end_shift + 3600) <= 60              # end also 1h earlier

        if start_ok and dur_ok and end_ok:
            score += 0.34
        elif start_ok and dur_ok:
            # Start correct & duration preserved but end slightly off -> partial.
            score += 0.20
        elif start_ok:
            # Started one hour earlier but duration changed.
            score += 0.10
    print(f"start: init={init_evt.get('start') if init_evt else 'n/a'} -> cur={cur_evt.get('start')}")

    # --- Criterion 2: moved to the Family calendar 'c3' (0.33) ---
    if cur_evt.get("calendarId") == FAMILY_CAL:
        score += 0.33
    print(f"calendarId: cur={cur_evt.get('calendarId')} (want {FAMILY_CAL})")

    # --- Criterion 3: color changed to grape purple '#8E24AA' (0.33) ---
    cur_color = str(cur_evt.get("color", "")).strip().lower()
    if cur_color == GRAPE_PURPLE:
        score += 0.33
    print(f"color: cur={cur_evt.get('color')} (want {GRAPE_PURPLE})")

    # --- Over-action penalty: distractor evt_191 must be unchanged ---
    init_distractor = find_event(init_events, DISTRACTOR_ID)
    cur_distractor = find_event(cur_events, DISTRACTOR_ID)
    distractor_changed = False
    if cur_distractor is None and init_distractor is not None:
        distractor_changed = True
    elif init_distractor is not None and cur_distractor is not None:
        fields = ["calendarId", "title", "color", "location", "description"]
        for fld in fields:
            if init_distractor.get(fld) != cur_distractor.get(fld):
                distractor_changed = True
                break
        if not distractor_changed:
            if parse_dt(init_distractor.get("start")) != parse_dt(cur_distractor.get("start")):
                distractor_changed = True
            if parse_dt(init_distractor.get("end")) != parse_dt(cur_distractor.get("end")):
                distractor_changed = True

    if distractor_changed:
        print("Over-action: distractor evt_191 'Prep Notes' was modified -> penalized.")
        score *= 0.5

    score = max(0.0, min(1.0, round(score, 2)))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
