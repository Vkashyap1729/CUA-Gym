"""Reward for: Move the "Coffee Chat" event onto my Work calendar instead of Personal.

Task-introduced change: event evt_100 ("Coffee Chat") moves from calendar c1
(Personal) to c2 (Work). Its title/start/end must stay unchanged, and the
distractor event evt_101 ("Personal Errand") must remain untouched on c1.

Scoring (progressive, 0.0-1.0):
  - Core move: evt_100.calendarId == "c2"        -> 0.6  (gate; 0 otherwise)
  - evt_100 title/start/end unchanged            -> +0.2 (penalize over-action)
  - evt_101 fully unchanged (the distractor)     -> +0.2 (penalize over-action)
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_event(events, evt_id):
    for e in events or []:
        if e.get("id") == evt_id:
            return e
    return None


def main():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    cur_100 = _find_event(cur_events, "evt_100")
    init_100 = _find_event(init_events, "evt_100")
    cur_101 = _find_event(cur_events, "evt_101")
    init_101 = _find_event(init_events, "evt_101")

    score = 0.0

    # --- Core move: evt_100 must now live on the Work calendar (c2). Gate. ---
    if cur_100 is not None and cur_100.get("calendarId") == "c2":
        score += 0.6

        # --- evt_100 identity preserved (title/start/end unchanged). ---
        if init_100 is not None:
            same_identity = (
                cur_100.get("title") == init_100.get("title")
                and cur_100.get("start") == init_100.get("start")
                and cur_100.get("end") == init_100.get("end")
            )
        else:
            # No initial reference; fall back to expected ground-truth values.
            same_identity = cur_100.get("title") == "Coffee Chat"
        if same_identity:
            score += 0.2

        # --- Distractor evt_101 must be completely untouched. ---
        if cur_101 is not None and init_101 is not None and cur_101 == init_101:
            score += 0.2

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
