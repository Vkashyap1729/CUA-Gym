"""Reward for gmail_033.

Task: Permanently delete the phishing email in Spam from security-alert@paypa1.com
(email_1). Distractors that must remain untouched:
  - email_2: spam, deals@marketing.net (legit marketing) -> stays folder 'spam'
  - email_3: inbox, security-alert@paypal.com (legit lookalike) -> stays folder 'inbox'

A permanent delete removes the email ID from `emails` entirely and lists it under
state_diff.deletedEmails. Merely moving it to trash is only partial progress.
All criteria are exact state checks (no LLM judge needed).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid", "r") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_email(emails, email_id):
    for e in emails or []:
        if e.get("id") == email_id:
            return e
    return None


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)

    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = current.get("emails", []) or []
    deleted = set(diff.get("deletedEmails", []) or [])

    email_1 = _find_email(emails, "email_1")  # the phishing email to delete
    email_2 = _find_email(emails, "email_2")  # distractor: legit marketing (stays spam)
    email_3 = _find_email(emails, "email_3")  # distractor: legit lookalike (stays inbox)

    # --- Base credit: did the target phishing email get permanently deleted? ---
    if email_1 is None and "email_1" in deleted:
        base = 1.0  # fully removed from emails array + recorded as deleted
    elif email_1 is None:
        # gone from emails but not flagged in deletedEmails -> still counts as removed
        base = 1.0
    elif (email_1.get("folder") or "") == "trash":
        base = 0.5  # moved to trash but not permanently deleted -> partial progress
    else:
        base = 0.0  # still sitting in spam (or elsewhere), task not started/done

    score = base

    # --- Over-action penalties: distractors must be untouched ---
    # email_2 must still exist and remain in 'spam'
    if email_2 is None or (email_2.get("folder") or "") != "spam":
        score *= 0.4

    # email_3 must still exist and remain in 'inbox'
    if email_3 is None or (email_3.get("folder") or "") != "inbox":
        score *= 0.4

    # No email other than the target may be deleted
    extra_deleted = deleted - {"email_1"}
    if extra_deleted:
        score *= 0.3
    # Also guard against distractors vanishing without appearing in deletedEmails
    if email_2 is None or email_3 is None:
        score *= 0.3

    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: " + str(reward))
