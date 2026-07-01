"""
Reward for task: "Jump the calendar to today."

Task-introduced change (the ONLY thing that should change):
  - currentDate: from 2026-01-10 (calendar showing January) -> today's date.
  - view stays the same ('week').
  - events stay the same.
  - everything else (calendars, settings, user, sidebarOpen) stays the same.

What "today" means here:
  The task was generated with a fixed system 'today' of 2026-03-13, and the
  golden state jumps currentDate to exactly that date. "Today" is therefore a
  FIXED reference date, NOT the wall clock at reward time (the reward may run on
  a different calendar day than the state was authored, so datetime.now() would
  be wrong). We compare only the YYYY-MM-DD date portion of currentDate, robust
  to any time-of-day component the app attaches on navigation.

Scoring (progressive, 0.0 - 1.0):
  - 1.0  currentDate's DATE part == today (2026-03-13).
  - 0.5  currentDate moved to today's year+month (right neighborhood) wrong day.
  - 0.3  currentDate navigated off the initial date but to the wrong month.
  - 0.0  currentDate unchanged (still on the initial January date).

Over-action penalty:
  - "Jump to today" changes ONLY currentDate. If the agent also creates,
    deletes, edits, or moves an event, or switches the view, that is
    over-action and caps the score at 0.3.

  NOTE: We do NOT key over-action off the server `state_diff`. In the golden
  env, initial_setup (action "set") and golden_patch (action "set_current")
  inject the events/settings blobs through the state API independently, and
  normalization can serialize them slightly differently -> the flat state_diff
  then reports a spurious "events" (etc.) change even though the calendar
  content is logically identical. Instead we compare a SEMANTIC SIGNATURE of the
  untouched fields (the `view` string + each event's (id,title,start,end))
  directly between current and initial state. Real agent over-action changes
  that signature; authoring serialization noise does not.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

# Fixed reference dates (date portion only). "Today" is the system date the task
# was authored against; the golden state jumps currentDate to exactly this.
TODAY_DATE = "2026-03-13"
INITIAL_DATE = "2026-01-10"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _date_part(iso_str):
    """Return the YYYY-MM-DD date portion of an ISO datetime string, or None."""
    if not isinstance(iso_str, str) or len(iso_str) < 10:
        return None
    return iso_str[:10]


def _event_signature(events):
    """A normalization-tolerant signature of the events an agent could touch.

    Captures create/delete (id set + count) and edit/move (title/start/end),
    while ignoring cosmetic default-field noise from the injection endpoint.
    """
    if not isinstance(events, list):
        return None
    sig = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        sig.append(
            (
                ev.get("id"),
                ev.get("title"),
                _date_part(ev.get("start")) or ev.get("start"),
                _date_part(ev.get("end")) or ev.get("end"),
            )
        )
    return sorted(sig, key=lambda t: str(t[0]))


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_date = _date_part(current.get("currentDate"))
    init_date = _date_part(initial.get("currentDate")) or INITIAL_DATE

    if cur_date is None:
        print("currentDate missing or malformed in current_state.")
        print("REWARD: 0.0")
        return

    print(f"today (fixed reference): {TODAY_DATE}")
    print(f"currentDate now: {cur_date} (initial was {init_date})")

    # --- Over-action detection: only currentDate should change ---------------
    over_action = False

    if current.get("view") != initial.get("view"):
        over_action = True
        print(
            f"Over-action: view changed {initial.get('view')!r} -> "
            f"{current.get('view')!r} (should stay unchanged)."
        )

    cur_events = _event_signature(current.get("events"))
    init_events = _event_signature(initial.get("events"))
    if cur_events != init_events:
        over_action = True
        print(
            f"Over-action: events changed ({len(cur_events or [])} now vs "
            f"{len(init_events or [])} initially; content/id/time differs)."
        )

    # --- Score the currentDate change ----------------------------------------
    if cur_date == TODAY_DATE:
        score = 1.0
        print(f"currentDate == today ({cur_date}): full credit.")
    elif cur_date == init_date:
        score = 0.0
        print(f"currentDate unchanged ({cur_date}): not done.")
    elif cur_date[:7] == TODAY_DATE[:7]:
        score = 0.5
        print(f"currentDate in today's month ({cur_date[:7]}) but wrong day: partial.")
    else:
        score = 0.3
        print(f"currentDate moved to {cur_date} (off initial) but wrong month: partial.")

    # Apply over-action penalty: untouched fields must be intact.
    if over_action:
        score = min(score, 0.3)
        print("Score capped due to over-action on fields that should stay untouched.")

    score = max(0.0, min(1.0, round(score, 2)))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    compute_reward()
