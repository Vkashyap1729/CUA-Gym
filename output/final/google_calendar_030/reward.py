"""Reward for google_calendar_030.

Task: The recurring "Weekly 1:1" (evt_200) should become a one-off:
  - recurring changed from "weekly" -> "none"
  - moved to Thursday March 19 2026 at 2:00 PM (start 14:00, end 14:30, 30-min duration kept)
  - distractor evt_201 "Skip Level" must be left untouched.

Scores ONLY the task-introduced change. Progressive 0.0-1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_event(events, evt_id):
    for e in events or []:
        if e.get("id") == evt_id:
            return e
    return None


def main():
    sid = read_sid()
    data = fetch_state(sid)
    current = data.get("current_state") or {}
    events = current.get("events") or []

    evt = find_event(events, "evt_200")  # "Weekly 1:1"
    distractor = find_event(events, "evt_201")  # "Skip Level"

    score = 0.0

    if evt is not None:
        start = str(evt.get("start") or "")
        end = str(evt.get("end") or "")
        recurring = str(evt.get("recurring") or "none")

        # --- recurrence flipped to non-recurring (0.4) ---
        if recurring == "none":
            score += 0.4

        # --- moved to the correct date: Thursday 2026-03-19 (0.2) ---
        # Stored ISO format is "YYYY-MM-DDTHH:MM:..." so a literal prefix
        # compare captures the wall-clock the UI set, free of tz conversion.
        if start.startswith("2026-03-19"):
            score += 0.2

        # --- correct start time 14:00 (2 PM) on the right day (0.2) ---
        if start.startswith("2026-03-19T14:00"):
            score += 0.2

        # --- correct end time 14:30 on the right day (duration kept) (0.2) ---
        if end.startswith("2026-03-19T14:30"):
            score += 0.2

    # --- over-action penalty: distractor evt_201 must be unchanged ---
    # Expected: c2, 2026-03-17 15:00-15:30, recurring "none", title "Skip Level".
    distractor_ok = (
        distractor is not None
        and str(distractor.get("title") or "") == "Skip Level"
        and str(distractor.get("start") or "").startswith("2026-03-17T15:00")
        and str(distractor.get("end") or "").startswith("2026-03-17T15:30")
        and str(distractor.get("recurring") or "none") == "none"
        and str(distractor.get("calendarId") or "") == "c2"
    )
    if not distractor_ok:
        # Penalize tampering with the distractor; cap well below full credit.
        score = min(score, 0.5)

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    main()
