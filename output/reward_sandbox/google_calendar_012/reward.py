"""Reward for: Add Alice and Bob as guests to the "Design Review" meeting.

Target: evt_030 'Design Review' (c2, 2026-03-19 11:00-12:00).
  EXPECTED guests -> ['alice@example.com', 'bob@example.com'].
Distractor: evt_031 'Design Review Prep' must keep an EMPTY guest list.

Scoring (progressive, 0.0-1.0):
  +0.5  alice@example.com added to evt_030.guests
  +0.5  bob@example.com   added to evt_030.guests
  Hard penalty -> 0.0 if the distractor evt_031 gained any guest (over-action).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_ID = "evt_030"
DISTRACTOR_ID = "evt_031"
REQUIRED_GUESTS = ["alice@example.com", "bob@example.com"]


def _norm(email):
    return str(email).strip().lower()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    events = current.get("events", []) or []

    by_id = {e.get("id"): e for e in events if isinstance(e, dict)}

    target = by_id.get(TARGET_ID)
    distractor = by_id.get(DISTRACTOR_ID)

    if target is None:
        print("Target event evt_030 not found in current state.")
        print("REWARD: 0.0")
        return

    target_guests = {_norm(g) for g in (target.get("guests") or []) if isinstance(g, str)}

    # Over-action guard: the similarly-named distractor must keep an empty guest list.
    if distractor is not None:
        distractor_guests = [g for g in (distractor.get("guests") or []) if isinstance(g, str)]
        if len(distractor_guests) > 0:
            print(f"Over-action: distractor evt_031 has guests {distractor_guests}; expected empty.")
            print("REWARD: 0.0")
            return

    score = 0.0
    for g in REQUIRED_GUESTS:
        if _norm(g) in target_guests:
            score += 0.5
            print(f"Found required guest on evt_030: {g}")
        else:
            print(f"Missing required guest on evt_030: {g}")

    score = round(min(score, 1.0), 1)
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
