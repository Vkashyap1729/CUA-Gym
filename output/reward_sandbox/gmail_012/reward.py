"""Reward for gmail_012: triage three Finance invoice emails.

Task: star the OVERDUE invoice (email_1), move the PAID invoice (email_2) to trash,
and leave the pending invoice (email_3) exactly as-is. Distractors email_4/email_5
must remain untouched. No label or read-status changes anywhere.

Scoring (progressive, exact state checks only):
  +0.5  email_1.starred == true AND email_1.folder == 'inbox'   (star the overdue one)
  +0.5  email_2.folder == 'trash' AND email_2.starred == false  (trash the paid one)
  -0.5  per over-action: any protected email changed in a way the task did not call for
Score is floored at 0.0 and capped at 1.0.

Initial (nothing done) -> 0.0 ; fully completed -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

# Fields whose changes count as observable (over-)actions.
TRACKED_FIELDS = ["starred", "folder", "read", "important", "category", "labels"]

# For each protected email, the ONLY field change the task permits (None = must be fully unchanged).
ALLOWED_CHANGE = {
    "email_1": "starred",   # false -> true
    "email_2": "folder",    # inbox -> trash
    "email_3": None,         # pending invoice: untouched
    "email_4": None,         # distractor: untouched
    "email_5": None,         # distractor: untouched
}


def _get_go(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _by_id(emails):
    return {e.get("id"): e for e in (emails or [])}


def _field_changed(before, after, field):
    if field == "labels":
        return set(before.get("labels") or []) != set(after.get("labels") or [])
    return before.get(field) != after.get(field)


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    data = _get_go(sid)
    initial = _by_id((data.get("initial_state") or {}).get("emails"))
    current = _by_id((data.get("current_state") or {}).get("emails"))

    score = 0.0

    # --- Required action 1: star the OVERDUE invoice, keep it in the inbox ---
    e1 = current.get("email_1")
    if e1 is not None and e1.get("starred") is True and e1.get("folder") == "inbox":
        score += 0.5

    # --- Required action 2: move the PAID invoice to trash, do not star it ---
    e2 = current.get("email_2")
    if e2 is not None and e2.get("folder") == "trash" and e2.get("starred") is False:
        score += 0.5

    # --- Over-action penalties: protected emails may only change in the sanctioned way ---
    violations = 0
    for eid, allowed in ALLOWED_CHANGE.items():
        before = initial.get(eid)
        after = current.get(eid)
        if before is None:
            continue
        if after is None:
            # a protected email was permanently deleted -> over-action
            violations += 1
            continue
        for field in TRACKED_FIELDS:
            if field == allowed:
                continue
            if _field_changed(before, after, field):
                violations += 1

    # Any brand-new email (e.g. an accidental compose/reply) is also over-action.
    new_ids = set(current) - set(initial)
    violations += len(new_ids)

    score -= 0.5 * violations

    score = max(0.0, min(1.0, score))
    print("REWARD:", round(score, 1))


if __name__ == "__main__":
    main()
