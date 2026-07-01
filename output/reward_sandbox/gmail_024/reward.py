"""Reward for gmail_024.

Task: Recover the accidentally-trashed client message (email_1) back into the
inbox as an UNREAD, STARRED email, then PERMANENTLY delete the phishing message
(email_2) that is still in trash. The inbox distractor (email_3) must be left
untouched.

All criteria are exact state checks (no LLM judge needed).

Scoring (progressive, total 1.0) — every additive component is FALSE on the
initial state (folder=trash, read=true, starred=false, email_2 present), so an
untouched initial state scores exactly 0.0:
  email_1 recovered to inbox ..... 0.30
  email_1 marked unread .......... 0.20
  email_1 starred ................ 0.20
  email_2 permanently deleted .... 0.30
Over-action gate (never additive credit): the distractor email_3 must remain in
the inbox with read/starred unchanged. If it is deleted or altered, the total
score is halved.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_email(emails, eid):
    for e in emails:
        if e.get("id") == eid:
            return e
    return None


def main():
    sid = read_sid()
    data = fetch_state(sid)
    current = data.get("current_state") or {}
    state_diff = data.get("state_diff") or {}
    emails = current.get("emails") or []

    email_1 = find_email(emails, "email_1")
    email_2 = find_email(emails, "email_2")
    email_3 = find_email(emails, "email_3")

    deleted = set(state_diff.get("deletedEmails") or [])

    score = 0.0

    # --- Recover the client message (email_1) ---
    # All three checks are false on initial (trash / read=true / starred=false).
    if email_1 is not None:
        if email_1.get("folder") == "inbox":
            score += 0.30
        if email_1.get("read") is False:
            score += 0.20
        if email_1.get("starred") is True:
            score += 0.20

    # --- Permanently delete the phishing message (email_2) ---
    # It must be gone from the emails array (and should appear in deletedEmails).
    # On initial, email_2 is still present -> 0 credit.
    if email_2 is None:
        score += 0.30
    elif "email_2" in deleted:
        # Fallback: diff says deleted but array still lists it — partial credit.
        score += 0.15

    # --- Over-action gate: the distractor email_3 must be untouched. ---
    # This is already true on the initial state, so it is NOT additive credit;
    # it only penalizes when the distractor was wrongly changed.
    email_3_untouched = (
        email_3 is not None
        and email_3.get("folder") == "inbox"
        and email_3.get("read") is True
        and email_3.get("starred") is False
        and "email_3" not in deleted
    )
    if not email_3_untouched:
        score *= 0.5

    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 2)))


if __name__ == "__main__":
    main()
