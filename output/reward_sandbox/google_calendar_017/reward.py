#!/usr/bin/env python3
"""Reward for: Create an all-day event titled "Company Offsite" on March 27, 2026
on the Work calendar (c2).

Scores ONLY the task-introduced change: a NEW event must be appended with
title 'Company Offsite', allDay=true, calendarId=c2 (Work), spanning 2026-03-27
(start 2026-03-27T00:00, end 2026-03-28T00:00). The pre-existing 'Standup' event
(evt_080, c2) must remain untouched.

Progressive 0.0-1.0. 0.0 on the initial (not-done) state, 1.0 when fully complete.
"""

import json
import re
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _norm(s):
    """Lowercase, collapse whitespace, strip — for tolerant title compare."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _date_prefix(s):
    """Return the YYYY-MM-DD portion of an ISO datetime string, or ''."""
    m = re.match(r"\s*(\d{4}-\d{2}-\d{2})", str(s or ""))
    return m.group(1) if m else ""


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = f"{BASE_URL}/go?sid={sid}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    # ---- Over-action guard: the pre-existing Standup event must be unchanged ----
    # Match the initial Standup event (evt_080, c2, 2026-03-27 09:00-09:30).
    init_standup = None
    for e in init_events:
        if e.get("id") == "evt_080" or (
            _norm(e.get("title")) == "standup" and e.get("calendarId") == "c2"
        ):
            init_standup = e
            break

    standup_ok = True
    if init_standup is not None:
        cur_standup = None
        for e in cur_events:
            if e.get("id") == init_standup.get("id"):
                cur_standup = e
                break
        if cur_standup is None:
            standup_ok = False  # deleted
        else:
            for fld in ("title", "calendarId", "start", "end", "allDay"):
                if cur_standup.get(fld) != init_standup.get(fld):
                    standup_ok = False
                    break

    # ---- Identify the task-introduced (new) event ----
    init_ids = {e.get("id") for e in init_events}
    new_events = [e for e in cur_events if e.get("id") not in init_ids]

    # Among new events, pick the best candidate matching "Company Offsite".
    def candidate_score(e):
        s = 0.0
        if _norm(e.get("title")) == "company offsite":
            s += 0.30
        elif "company offsite" in _norm(e.get("title")):
            s += 0.20
        if e.get("allDay") is True:
            s += 0.25
        if e.get("calendarId") == "c2":
            s += 0.20
        if _date_prefix(e.get("start")) == "2026-03-27":
            s += 0.15
        # end should be the following midnight for an all-day single-day event
        if _date_prefix(e.get("end")) in ("2026-03-27", "2026-03-28"):
            s += 0.10
        return s

    best = 0.0
    if new_events:
        best = max(candidate_score(e) for e in new_events)

    score = best

    # Apply over-action penalty: if the existing Standup was tampered with, cap.
    if not standup_ok:
        score = min(score, 0.5)

    score = max(0.0, min(1.0, round(score, 2)))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
