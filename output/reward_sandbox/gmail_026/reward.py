"""Reward for gmail_026.

Task: Open and read the message with the subject 'Server maintenance window'.

Expected: the target email (email_1, from ops@company.com, subject
'Server maintenance window') transitions read:false -> read:true.
The two distractor emails (email_2 'Benefits enrollment', email_3
'Server upgrade complete') must remain unread and otherwise untouched.
No starring, moving, labeling, or deletion of any email.

Scoring (progressive, 0.0-1.0):
  +1.0  target email is now read
  Over-action penalties (subtractive):
    -0.5  each distractor that was read (should stay unread)
    -0.5  any email starred / important / moved / relabeled that wasn't so initially
    -1.0  any email deleted, or any new email created
The initial (not-done) state scores 0.0; the fully-correct state scores 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_SUBJECT = "Server maintenance window"
TARGET_FROM = "ops@company.com"


def _get(email, key, default=None):
    return email.get(key, default) if isinstance(email, dict) else default


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    initial_emails = {e.get("id"): e for e in (initial.get("emails") or []) if isinstance(e, dict)}
    current_emails = {e.get("id"): e for e in (current.get("emails") or []) if isinstance(e, dict)}

    # Identify the target email by subject + sender (fall back to subject only).
    def is_target(e):
        subj = (_get(e, "subject") or "").strip().lower()
        frm = _get(e, "from") or {}
        frm_email = (frm.get("email") if isinstance(frm, dict) else "") or ""
        return subj == TARGET_SUBJECT.lower() and frm_email.lower() == TARGET_FROM.lower()

    target_id = None
    for eid, e in current_emails.items():
        if is_target(e):
            target_id = eid
            break
    if target_id is None:
        # fall back to subject-only match
        for eid, e in current_emails.items():
            if (_get(e, "subject") or "").strip().lower() == TARGET_SUBJECT.lower():
                target_id = eid
                break

    score = 0.0

    # --- Main criterion: target is now read ---
    if target_id is not None and _get(current_emails[target_id], "read") is True:
        score += 1.0

    # --- Over-action penalties ---
    penalty = 0.0

    # Deletions or new emails are hard failures for this read-only task.
    initial_ids = set(initial_emails.keys())
    current_ids = set(current_emails.keys())
    if initial_ids - current_ids:  # deleted
        penalty += 1.0
    if current_ids - initial_ids:  # new emails created
        penalty += 1.0

    for eid, cur in current_emails.items():
        init = initial_emails.get(eid)
        if init is None:
            continue  # newly created email already penalized above

        is_tgt = eid == target_id

        # Distractors (non-target) must NOT be read if they started unread.
        if not is_tgt:
            if _get(init, "read") is False and _get(cur, "read") is True:
                penalty += 0.5

        # No starring / important / moving / relabeling for ANY email.
        if bool(_get(cur, "starred")) != bool(_get(init, "starred")):
            penalty += 0.5
        if bool(_get(cur, "important")) != bool(_get(init, "important")):
            penalty += 0.5
        if (_get(cur, "folder") or "") != (_get(init, "folder") or ""):
            penalty += 0.5
        if sorted(_get(cur, "labels") or []) != sorted(_get(init, "labels") or []):
            penalty += 0.5

    score = max(0.0, score - penalty)
    score = min(1.0, score)

    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    main()
