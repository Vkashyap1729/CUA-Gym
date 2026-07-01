#!/usr/bin/env python3
"""Reward for: Create a new calendar named "Side Projects" with the lavender color.

Scores ONLY the task-introduced change: a new calendar appended to `calendars`
with name 'Side Projects' and color '#7986CB' (lavender). The three pre-existing
calendars (c1 Personal, c2 Work, c3 Family) must remain unchanged.

Progressive scoring (max 1.0):
  +0.30  a new calendar (id not among the initial calendars) exists
  +0.40  that new calendar is named "Side Projects" (case/space-insensitive)
  +0.30  that new calendar's color is the lavender hex '#7986CB'
Over-action guard: if any of the three pre-existing calendars was modified
(name/color/visibility changed) or removed, the score is capped at 0.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"
LAVENDER = "#7986CB"
TARGET_NAME = "side projects"


def _norm(s):
    return str(s or "").strip().lower()


def _norm_hex(s):
    return str(s or "").strip().upper()


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_reward():
    data = _get_state()
    initial = data.get("initial_state") or {}
    current = data.get("current_state") or {}

    init_cals = initial.get("calendars") or []
    cur_cals = current.get("calendars") or []

    init_by_id = {c.get("id"): c for c in init_cals if isinstance(c, dict)}
    cur_by_id = {c.get("id"): c for c in cur_cals if isinstance(c, dict)}

    # --- Over-action guard: the three pre-existing calendars must be untouched ---
    for cid, orig in init_by_id.items():
        cur = cur_by_id.get(cid)
        if cur is None:
            print("Pre-existing calendar %s was removed -> over-action." % cid)
            return 0.0
        for field in ("name", "color", "visible"):
            if orig.get(field) != cur.get(field):
                print(
                    "Pre-existing calendar %s field '%s' changed (%r -> %r) -> over-action."
                    % (cid, field, orig.get(field), cur.get(field))
                )
                return 0.0

    # --- Identify newly-added calendar(s): ids not present in the initial state ---
    new_cals = [
        c for c in cur_cals if isinstance(c, dict) and c.get("id") not in init_by_id
    ]
    if not new_cals:
        print("No new calendar added.")
        return 0.0

    # Pick the best-matching new calendar (prefer one named "Side Projects").
    def match_score(c):
        s = 0.0
        if _norm(c.get("name")) == TARGET_NAME:
            s += 0.40
        if _norm_hex(c.get("color")) == LAVENDER:
            s += 0.30
        return s

    best = max(new_cals, key=match_score)

    score = 0.30  # a new calendar exists
    if _norm(best.get("name")) == TARGET_NAME:
        score += 0.40
    else:
        print("New calendar name is %r, expected 'Side Projects'." % best.get("name"))
    if _norm_hex(best.get("color")) == LAVENDER:
        score += 0.30
    else:
        print("New calendar color is %r, expected '%s' (lavender)." % (best.get("color"), LAVENDER))

    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("Error computing reward: %r" % e)
        reward = 0.0
    print("REWARD: %s" % reward)
