"""Reward for: Extend the "Workshop" event so it ends at 5 PM instead of 3 PM.

Task-introduced change ONLY:
  - evt_120 'Workshop' (2026-03-24 13:00-15:00) -> end moved to 17:00 (5 PM).
  - start stays 13:00.
  - evt_121 'Wrap-up Call' (15:30-16:00) must remain untouched (do NOT shift it,
    even though the extended Workshop now overlaps it).

Scoring (exact state checks; no LLM judge needed):
  - End correctly extended to exactly 17:00 on the same date -> full credit.
  - End moved later than the original 15:00 but not exactly 17:00 -> partial.
  - Over-action penalties: shifting the Workshop start, or modifying the
    Wrap-up Call distractor, reduce the score.
Initial (not-done) state scores 0.0; fully-completed state scores 1.0.
"""

import json
import urllib.request
from datetime import datetime

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

WORKSHOP_ID = "evt_120"
WORKSHOP_TITLE = "Workshop"
DISTRACTOR_ID = "evt_121"  # 'Wrap-up Call' — must be unchanged

EXPECTED_END_HOUR = 17  # 5 PM
EXPECTED_END_MINUTE = 0
ORIGINAL_END_HOUR = 15  # 3 PM
EXPECTED_START_HOUR = 13
EXPECTED_DATE = "2026-03-24"


def _parse(dt_str):
    """Parse an ISO datetime to a naive datetime (wall-clock as written),
    ignoring any trailing 'Z' / timezone offset so we compare the literal time."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1]
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Fallback: strip an explicit offset like +00:00 then retry.
        try:
            dt = datetime.fromisoformat(s.split("+")[0])
        except ValueError:
            return None
    # Drop tzinfo to compare the literal wall-clock value.
    return dt.replace(tzinfo=None)


def _find_event(events, evt_id, title=None):
    if not isinstance(events, list):
        return None
    for ev in events:
        if isinstance(ev, dict) and ev.get("id") == evt_id:
            return ev
    if title:
        for ev in events:
            if isinstance(ev, dict) and (ev.get("title") or "").strip().lower() == title.lower():
                return ev
    return None


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.load(resp)

    initial_state = data.get("initial_state") or {}
    current_state = data.get("current_state") or {}
    init_events = initial_state.get("events") or []
    cur_events = current_state.get("events") or []

    workshop = _find_event(cur_events, WORKSHOP_ID, WORKSHOP_TITLE)
    init_workshop = _find_event(init_events, WORKSHOP_ID, WORKSHOP_TITLE)

    if workshop is None:
        print("Workshop event not found in current state.")
        print("REWARD: 0.0")
        return

    cur_start = _parse(workshop.get("start"))
    cur_end = _parse(workshop.get("end"))
    init_start = _parse(init_workshop.get("start")) if init_workshop else None
    init_end = _parse(init_workshop.get("end")) if init_workshop else None

    if cur_end is None:
        print("Workshop end time unparseable.")
        print("REWARD: 0.0")
        return

    # --- Primary signal: did the end move to 17:00 (or at least later)? ---
    end_correct = (
        cur_end.strftime("%Y-%m-%d") == EXPECTED_DATE
        and cur_end.hour == EXPECTED_END_HOUR
        and cur_end.minute == EXPECTED_END_MINUTE
    )

    end_extended = False  # moved later than the original 15:00, but not exactly right
    if init_end is not None:
        end_extended = cur_end > init_end
    else:
        end_extended = cur_end.hour > ORIGINAL_END_HOUR

    if end_correct:
        score = 1.0
        print("Workshop end correctly extended to 17:00.")
    elif end_extended:
        score = 0.4
        print(f"Workshop end moved later ({cur_end}) but not to 17:00 exactly.")
    else:
        print(f"Workshop end not extended (still {cur_end}).")
        print("REWARD: 0.0")
        return

    # --- Over-action penalty 1: the Workshop start must NOT have moved. ---
    start_ok = True
    if cur_start is not None:
        if init_start is not None:
            start_ok = cur_start == init_start
        else:
            start_ok = cur_start.hour == EXPECTED_START_HOUR and cur_start.minute == 0
    if not start_ok:
        score -= 0.4
        print(f"Penalty: Workshop start was shifted ({cur_start}); only the end should change.")

    # --- Over-action penalty 2: the 'Wrap-up Call' distractor must be untouched. ---
    cur_distractor = _find_event(cur_events, DISTRACTOR_ID)
    init_distractor = _find_event(init_events, DISTRACTOR_ID)
    if cur_distractor is None:
        score -= 0.3
        print("Penalty: 'Wrap-up Call' (evt_121) was deleted; it must remain untouched.")
    elif init_distractor is not None and cur_distractor != init_distractor:
        score -= 0.3
        print("Penalty: 'Wrap-up Call' (evt_121) was modified; it must remain untouched.")

    score = max(0.0, min(1.0, score))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
