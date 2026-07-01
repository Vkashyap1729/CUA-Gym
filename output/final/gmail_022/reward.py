"""Reward for gmail_022.

Task: Clean up starred items — unstar the two promotional emails (email_1, email_2),
keep the work email (email_3) starred, and mark the work email as important.
Distractor: email_4 (spam@x.com, not starred) must remain unchanged.

Scoring (progressive, exact state checks only — no LLM judge needed since every
criterion is an observable boolean state field):
  - email_1.starred == False        -> 1/3   (task-introduced change)
  - email_2.starred == False        -> 1/3   (task-introduced change)
  - email_3.important == True        -> 1/3   (task-introduced change)
Over-action penalties (zero out relevant credit):
  - email_3 must STAY starred (unstarring the work email is wrong)
  - email_4 must be completely unchanged
  - no other email may be modified

Initial state (nothing done) scores 0.0; fully-completed golden state scores 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_by_id(state):
    out = {}
    for e in (state or {}).get("emails", []) or []:
        out[e.get("id")] = e
    return out


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    cur = _emails_by_id(current)
    e1 = cur.get("email_1", {})
    e2 = cur.get("email_2", {})
    e3 = cur.get("email_3", {})

    score = 0.0

    # --- Task-introduced changes (each worth 1/3) ---
    # 1) Promotional email_1 unstarred
    if e1.get("starred") is False:
        score += 1.0 / 3.0
    # 2) Promotional email_2 unstarred
    if e2.get("starred") is False:
        score += 1.0 / 3.0
    # 3) Work email_3 marked important
    if e3.get("important") is True:
        score += 1.0 / 3.0

    # --- Over-action penalties (use state_diff so we don't assume unknown
    #     initial values like read/folder for each email) ---
    modified = diff.get("modifiedEmails", {}) or {}

    # The work email must STAY starred. Unstarring it is a direct task violation:
    # wipe out any credit earned, since the "keep it starred" requirement failed.
    if e3.get("starred") is not True:
        score = 0.0

    # For each touched email, only the intended field(s) may have changed.
    # email_1 / email_2: only 'starred' allowed. email_3: only 'important' allowed.
    allowed = {
        "email_1": {"starred"},
        "email_2": {"starred"},
        "email_3": {"important"},
    }
    for eid, changed_fields in modified.items():
        touched = set((changed_fields or {}).keys())
        if eid == "email_4":
            # Distractor must be completely unchanged.
            score = min(score, 0.3)
        elif eid in allowed:
            extra = touched - allowed[eid]
            if extra:
                # Modified a field beyond what the task asked for (e.g. moved,
                # read, relabeled) -> over-action.
                score = min(score, 0.5)
        else:
            # Any other email being modified is unexpected over-action.
            score = min(score, 0.3)

    # No new/deleted emails should occur for this task.
    if diff.get("newEmails") or diff.get("deletedEmails"):
        score = min(score, 0.3)

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    return round(score, 4)


if __name__ == "__main__":
    r = compute_reward()
    print("REWARD: " + str(r))
