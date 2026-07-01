"""Reward for: Make the "Yoga Class" event repeat every week.

Task-introduced change: evt_040 ('Yoga Class', the weekly recurring class) must
have its `recurring` field changed from 'none' to 'weekly'.

Distractor / over-action guard: evt_041 is a one-off "Yoga Class" makeup session
on a different day and must REMAIN recurring 'none'. All other events must be
left untouched.

Scoring (progressive, exact state checks only):
  - evt_040.recurring == 'weekly'                 -> 1.0 base
  - evt_040.recurring in {daily, monthly, yearly} -> 0.3 base (touched recurrence,
                                                      wrong rule)
  - otherwise (still 'none' / missing)            -> 0.0 base
  Over-action penalty: if evt_041 was changed (its recurring is no longer 'none',
  it was deleted, or its identity fields changed) or any other event was added /
  deleted / mutated, the score is halved.

  Initial state -> 0.0 ; fully-completed golden state -> 1.0.
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


def _find_event(events, evt_id):
    for e in events or []:
        if e.get("id") == evt_id:
            return e
    return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    # ---- Primary criterion: evt_040 should now recur weekly ----
    e40 = _find_event(cur_events, "evt_040")
    if e40 is None:
        base = 0.0  # the target event was deleted/lost
    else:
        rec = e40.get("recurring", "none")
        if rec == "weekly":
            base = 1.0
        elif rec in ("daily", "monthly", "yearly"):
            base = 0.3  # recurrence was touched but set to the wrong rule
        else:
            base = 0.0  # still 'none' -> not done

    # ---- Over-action guard ----
    # evt_041 (the one-off makeup session) must stay recurring 'none' and otherwise
    # unchanged; no other event may be added, deleted, or mutated.
    over_action = False

    init_by_id = {e.get("id"): e for e in init_events}
    cur_by_id = {e.get("id"): e for e in cur_events}

    # No events added or removed.
    if set(init_by_id.keys()) != set(cur_by_id.keys()):
        over_action = True

    # Every event other than evt_040 must be byte-for-byte identical to initial;
    # evt_040 may differ ONLY in its `recurring` field.
    for eid, init_e in init_by_id.items():
        cur_e = cur_by_id.get(eid)
        if cur_e is None:
            over_action = True
            continue
        if eid == "evt_040":
            init_copy = dict(init_e)
            cur_copy = dict(cur_e)
            init_copy.pop("recurring", None)
            cur_copy.pop("recurring", None)
            if init_copy != cur_copy:
                over_action = True
        else:
            if init_e != cur_e:
                over_action = True

    # Anything outside the events array (calendars, settings, user, ...) must be
    # untouched as well.
    for key in ("user", "calendars", "settings"):
        if initial.get(key) != current.get(key):
            over_action = True

    score = base
    if over_action:
        score = round(base * 0.5, 4)

    print("evt_040.recurring =", (e40 or {}).get("recurring"))
    e41 = _find_event(cur_events, "evt_041")
    print("evt_041.recurring =", (e41 or {}).get("recurring"))
    print("over_action =", over_action)
    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    main()
