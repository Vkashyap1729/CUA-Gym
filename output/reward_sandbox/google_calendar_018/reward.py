import json
import urllib.request

BASE_URL = "https://cua-gym-google-calendar.xlang.ai"

TARGET_EVENT_ID = "evt_090"
TARGET_TITLE = "Client Demo"
REMOVE_EMAIL = "charlie@example.com"
KEEP_EMAILS = ["alice@example.com", "david@example.com"]


def _norm(email):
    return (email or "").strip().lower()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_events = current.get("events", []) or []
    init_events = initial.get("events", []) or []

    # Locate the target event by id (fall back to title) in current state.
    target = None
    for ev in cur_events:
        if ev.get("id") == TARGET_EVENT_ID:
            target = ev
            break
    if target is None:
        for ev in cur_events:
            if (ev.get("title") or "").strip().lower() == TARGET_TITLE.lower():
                target = ev
                break

    if target is None:
        # Event missing entirely (e.g. deleted) — that's not the requested edit.
        print("Target event 'Client Demo' (evt_090) not found in current state.")
        print("REWARD: 0.0")
        return

    guests = [_norm(g) for g in (target.get("guests", []) or [])]

    score = 0.0

    # --- Primary criterion (gate): charlie must be removed from the target. ---
    # No credit is given until this happens, so the initial (not-done) state
    # scores 0.0 even though alice/david are present.
    charlie_removed = _norm(REMOVE_EMAIL) not in guests
    keep_present = sum(1 for k in KEEP_EMAILS if _norm(k) in guests)

    if charlie_removed:
        # Base credit for the core action, plus credit for preserving the
        # two guests that must stay. Both kept -> 1.0; dropping one is penalized.
        score = 0.5 + 0.5 * (keep_present / len(KEEP_EMAILS))

    # --- Over-action guard: other events must be unchanged ---
    # Build id->event maps for initial and current; any distractor event whose
    # guest list (or other key fields) changed indicates collateral edits.
    init_by_id = {ev.get("id"): ev for ev in init_events}
    cur_by_id = {ev.get("id"): ev for ev in cur_events}

    over_action = False

    # Distractor events (everything except the target) must match the initial state.
    for ev_id, init_ev in init_by_id.items():
        if ev_id == TARGET_EVENT_ID:
            continue
        cur_ev = cur_by_id.get(ev_id)
        if cur_ev is None:
            over_action = True  # a distractor event was deleted
            break
        # Compare guest lists and core fields for unintended modification.
        init_guests = sorted(_norm(g) for g in (init_ev.get("guests", []) or []))
        cur_guests = sorted(_norm(g) for g in (cur_ev.get("guests", []) or []))
        if init_guests != cur_guests:
            over_action = True
            break
        for field in ("title", "start", "end", "calendarId"):
            if init_ev.get(field) != cur_ev.get(field):
                over_action = True
                break
        if over_action:
            break

    # Newly created events also count as over-action.
    if not over_action:
        for ev_id in cur_by_id:
            if ev_id not in init_by_id:
                over_action = True
                break

    # On the target event itself, the only allowed change is removing charlie.
    # If alice/david were dropped, the preservation score already reflects it,
    # but adding NEW guests to the target is over-action too.
    init_target = init_by_id.get(TARGET_EVENT_ID, {})
    init_target_guests = set(_norm(g) for g in (init_target.get("guests", []) or []))
    added_to_target = [g for g in guests if g not in init_target_guests]
    if added_to_target:
        over_action = True

    if over_action:
        # Cap the score so collateral changes can never reach full reward.
        score = min(score, 0.5)

    score = max(0.0, min(1.0, score))
    print("Target guests:", guests)
    print("charlie_removed:", charlie_removed, "| kept:", keep_present, "/", len(KEEP_EMAILS),
          "| over_action:", over_action)
    print("REWARD: " + str(round(score, 2)))


if __name__ == "__main__":
    main()
