"""Reward for: Hide the Family calendar, switch to Agenda view, jump to April 1, 2026.

Scores ONLY the three task-introduced changes:
  1. Family calendar (c3) visibility set to false  (c1 Personal & c2 Work stay visible)
  2. view changed to "agenda"
  3. currentDate jumped to 2026-04-01

Each criterion is worth 1/3 of the reward. Events array must stay unchanged.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_calendar(calendars, cal_id):
    for c in calendars or []:
        if c.get("id") == cal_id:
            return c
    return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}

    calendars = current.get("calendars") or []
    view = current.get("view")
    current_date = current.get("currentDate") or ""

    score = 0.0

    # --- Criterion 1: Family (c3) hidden, Personal (c1) & Work (c2) still visible (1/3) ---
    c1 = _find_calendar(calendars, "c1")
    c2 = _find_calendar(calendars, "c2")
    c3 = _find_calendar(calendars, "c3")
    family_hidden = bool(c3) and (c3.get("visible") is False)
    others_visible = (
        bool(c1) and c1.get("visible") is True and bool(c2) and c2.get("visible") is True
    )
    if family_hidden and others_visible:
        score += 1.0 / 3.0

    # --- Criterion 2: view == "agenda" (1/3) ---
    if view == "agenda":
        score += 1.0 / 3.0

    # --- Criterion 3: currentDate jumped to 2026-04-01 (1/3) ---
    # Accept any time-of-day on that calendar date.
    if isinstance(current_date, str) and current_date.startswith("2026-04-01"):
        score += 1.0 / 3.0

    # --- Over-action guard: events array must be unchanged from initial ---
    init_events = initial.get("events")
    cur_events = current.get("events")
    if init_events is not None and cur_events is not None and init_events != cur_events:
        score = 0.0

    score = round(max(0.0, min(1.0, score)), 4)
    print("REWARD:", score)


if __name__ == "__main__":
    main()
