"""Reward for: Update the description of "Onboarding Session" to
"Bring your laptop and ID badge."

Task-introduced change (scored):
  - evt_150 ("Onboarding Session") description must become
    "Bring your laptop and ID badge."

Over-action guard:
  - evt_151 ("Onboarding Follow-up") must keep its "TBD" description.
  - No other event may be added/removed.

Exact-text task -> deterministic state checks only (no LLM judge).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_TITLE = "Onboarding Session"
TARGET_DESC = "Bring your laptop and ID badge."

DISTRACTOR_TITLE = "Onboarding Follow-up"
DISTRACTOR_DESC = "TBD"


def _norm(s):
    return " ".join(str(s or "").split()).strip().lower()


def _find_event(events, title=None, eid=None):
    for ev in events or []:
        if eid is not None and ev.get("id") == eid:
            return ev
    for ev in events or []:
        if title is not None and _norm(ev.get("title")) == _norm(title):
            return ev
    return None


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}
    events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    score = 0.0

    # --- Primary criterion: evt_150 description updated (60%) ---
    target_ev = _find_event(events, title=TARGET_TITLE, eid="evt_150")
    if target_ev is not None:
        desc = _norm(target_ev.get("description"))
        if desc == _norm(TARGET_DESC):
            score += 0.6  # exact match
        elif ("laptop" in desc and "badge" in desc) and desc != _norm("TBD"):
            score += 0.3  # right idea, wrong wording -> partial
        # still "TBD" or empty -> 0

    # --- Distractor unchanged: evt_151 keeps "TBD" (25%) ---
    distractor_ev = _find_event(events, title=DISTRACTOR_TITLE, eid="evt_151")
    if distractor_ev is not None and _norm(distractor_ev.get("description")) == _norm(
        DISTRACTOR_DESC
    ):
        score += 0.25

    # --- No spurious add/remove of events (15%) ---
    if init_events and len(events) == len(init_events):
        init_ids = {ev.get("id") for ev in init_events}
        cur_ids = {ev.get("id") for ev in events}
        if init_ids == cur_ids:
            score += 0.15

    # Over-action gate: if the target was never correctly updated, do not let
    # the "unchanged" credits alone produce a non-trivial score on the
    # not-done state. Require the primary edit to land for full credit.
    if target_ev is None or _norm(target_ev.get("description")) != _norm(TARGET_DESC):
        # Primary edit incomplete: cap so the initial state scores 0.0.
        # On the initial state evt_150 desc == "TBD" -> primary credit is 0,
        # so total would be 0.4 from the "unchanged" parts; clamp to 0.0 unless
        # at least the partial primary credit was earned.
        if target_ev is None or _norm(target_ev.get("description")) == _norm("TBD") or not (
            "laptop" in _norm(target_ev.get("description"))
            and "badge" in _norm(target_ev.get("description"))
        ):
            score = 0.0

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 2)))


if __name__ == "__main__":
    main()
