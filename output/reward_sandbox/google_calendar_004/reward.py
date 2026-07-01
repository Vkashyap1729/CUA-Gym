"""Reward for: Rename the event titled "Team Standup" to "Daily Engineering Sync".

Scores ONLY the task-introduced change: evt_001.title -> "Daily Engineering Sync",
with every other field of evt_001 (time, calendar, guests, recurrence) preserved and
the distractor event evt_002 ("Lunch with Sarah") left untouched.

Progressive 0.0-1.0; prints 'REWARD: X.X' as the last line.
0.0 on the initial (not-done) state, 1.0 on the fully-completed state.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_TITLE = "Daily Engineering Sync"
ORIGINAL_TITLE = "Team Standup"

EVT_ID = "evt_001"
DISTRACTOR_ID = "evt_002"

# Fields of evt_001 that MUST be preserved unchanged by the rename.
PRESERVE_FIELDS = ["calendarId", "start", "end", "recurring", "allDay"]


def _norm(s):
    return " ".join(str(s or "").split()).strip().lower()


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_event(events, eid):
    for e in events or []:
        if e.get("id") == eid:
            return e
    return None


def compute_reward():
    data = _get_state()
    current = data.get("current_state") or {}
    events = current.get("events") or []

    evt = _find_event(events, EVT_ID)
    if evt is None:
        # Target event must still exist (renaming must not delete/replace it).
        return 0.0

    cur_title = _norm(evt.get("title"))

    # --- Title change: the core of the task (up to 0.7) ---
    title_score = 0.0
    if cur_title == _norm(TARGET_TITLE):
        title_score = 0.7
    elif cur_title and cur_title != _norm(ORIGINAL_TITLE):
        # Title was edited toward something other than the original, but not the
        # exact target -> partial credit (e.g. minor wording/casing differences).
        title_score = 0.4

    # Gate preservation/over-action credit on the rename actually having happened,
    # so the untouched INITIAL state scores exactly 0.0.
    if title_score == 0.0:
        return 0.0

    # --- Preservation of evt_001's other fields (up to 0.2) ---
    # Compare against the initial copy of evt_001 from state_diff / initial_state.
    initial = data.get("initial_state") or {}
    init_evt = _find_event(initial.get("events"), EVT_ID)

    preserve_score = 0.0
    if init_evt is not None:
        ok = 0
        total = len(PRESERVE_FIELDS) + 1  # +1 for guests
        for fld in PRESERVE_FIELDS:
            if evt.get(fld) == init_evt.get(fld):
                ok += 1
        # guests compared order-insensitively
        if sorted(evt.get("guests") or []) == sorted(init_evt.get("guests") or []):
            ok += 1
        preserve_score = 0.2 * (ok / total)
    else:
        # No baseline to compare; assume preserved.
        preserve_score = 0.2

    # --- Distractor untouched: evt_002 must be unchanged (up to 0.1) ---
    distractor_score = 0.1
    if init_evt is not None or initial.get("events"):
        cur_d = _find_event(events, DISTRACTOR_ID)
        init_d = _find_event(initial.get("events"), DISTRACTOR_ID)
        if init_d is not None:
            if cur_d is None:
                distractor_score = 0.0  # distractor deleted -> over-action
            elif cur_d != init_d:
                distractor_score = 0.0  # distractor modified -> over-action
        elif cur_d is None:
            distractor_score = 0.0

    score = title_score + preserve_score + distractor_score
    if score > 1.0:
        score = 1.0
    if score < 0.0:
        score = 0.0
    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as exc:
        print("ERROR computing reward:", repr(exc))
        reward = 0.0
    print("REWARD:", reward)
