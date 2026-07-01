#!/usr/bin/env python3
"""Reward for gmail_004: 'Report the message pretending to be from my bank as spam.'

Task-introduced change: email_3 (the phishing 'SecureBank Alerts' from the lookalike
domain secure-bank-verify.net) must be moved to folder 'spam'. The genuine SecureBank
email (email_4, alerts@securebank.com) and every other email must stay in 'inbox'.

Scoring is a pure exact-state check (no LLM judge needed):
  - email_3.folder == 'spam' .................... primary credit
  - email_3 moved elsewhere (not inbox/not spam) . partial credit
  - any named distractor moved / deleted ......... over-action penalty
Initial state (email_3 in inbox) → 0.0. Golden state → 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TARGET_ID = "email_3"                         # the phishing email to report as spam
DISTRACTORS = ["email_1", "email_2", "email_4"]  # must remain untouched in inbox


def _folder_of(emails, eid):
    """Return the folder of the email with id==eid, or None if absent."""
    for e in emails:
        if e.get("id") == eid:
            return e.get("folder")
    return None


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}
    emails = current.get("emails", []) or []

    # ---- Primary: phishing email moved to spam ----------------------------
    target_folder = _folder_of(emails, TARGET_ID)
    if target_folder == "spam":
        base = 1.0
    elif target_folder not in ("inbox", None):
        # acted on the right email but sent it to the wrong folder (e.g. trash)
        base = 0.3
    else:
        base = 0.0

    # ---- Over-action penalty: distractors must be unchanged in inbox ------
    violations = 0
    for eid in DISTRACTORS:
        folder = _folder_of(emails, eid)
        if folder is None:
            violations += 1          # a required email was deleted / lost
        elif folder != "inbox":
            violations += 1          # a legitimate email was wrongly moved

    # any brand-new email that was not part of the task is also over-action
    new_emails = diff.get("newEmails", []) or []
    violations += len(new_emails)

    score = max(0.0, base - 0.25 * violations)
    score = round(min(1.0, score), 2)

    print("target(email_3) folder:", target_folder)
    print("distractor violations:", violations, "new_emails:", new_emails)
    print("REWARD:", score)


if __name__ == "__main__":
    main()
