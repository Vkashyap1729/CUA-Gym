#!/usr/bin/env python3
"""Reward for task gmail_030.

Task: Compose and send a NEW email to jordan@partner.com with subject
'Kickoff scheduling' asking for their availability next week.

Scoring (progressive, 0.0-1.0):
  - 0.20  a new sent email addressed to jordan@partner.com exists
  - 0.20  that email's folder == 'sent' (actually sent, not saved as draft)
  - 0.25  subject is exactly 'Kickoff scheduling'
  - 0.35  body asks for availability next week  (LLM judge, <=40% of score)

Over-action penalties (subtracted from the base score):
  - distractor emails (email_1, email_2) must be untouched
  - drafts must stay empty (a sent email is NOT a draft)
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"
TARGET = "jordan@partner.com"
EXPECTED_SUBJECT = "Kickoff scheduling"
DISTRACTOR_IDS = {"email_1", "email_2"}


def _norm(s):
    return (s or "").strip().lower()


def _recipient_emails(email):
    out = []
    for rcpt in email.get("to") or []:
        if isinstance(rcpt, dict):
            out.append(_norm(rcpt.get("email")))
        elif isinstance(rcpt, str):
            out.append(_norm(rcpt))
    return out


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state") or {}
    diff = data.get("state_diff") or {}
    emails = current.get("emails") or []
    drafts = current.get("drafts") or []

    # --- Identify the task-introduced email ---------------------------------
    # A newly composed/sent email addressed to jordan@partner.com that is NOT
    # one of the pre-existing distractor emails.
    candidates = [
        e
        for e in emails
        if e.get("id") not in DISTRACTOR_IDS and TARGET in _recipient_emails(e)
    ]

    score = 0.0
    target_email = None

    if candidates:
        # Prefer a candidate that is in the sent folder with the right subject.
        def rank(e):
            return (
                _norm(e.get("folder")) == "sent",
                _norm(e.get("subject")) == _norm(EXPECTED_SUBJECT),
            )

        target_email = sorted(candidates, key=rank, reverse=True)[0]

        # 0.20 - a new email to jordan exists
        score += 0.20

        # 0.20 - it was actually sent (folder == 'sent'), not left as a draft
        if _norm(target_email.get("folder")) == "sent":
            score += 0.20

        # 0.25 - subject matches exactly (case-insensitive, trimmed)
        if _norm(target_email.get("subject")) == _norm(EXPECTED_SUBJECT):
            score += 0.25

        # 0.35 - body content: asks for availability next week (LLM judge)
        body = target_email.get("body") or target_email.get("snippet") or ""
        if body.strip():
            # JUSTIFICATION: Whether the body genuinely asks the recipient for
            # their availability next week is a subjective wording judgement
            # that cannot be reduced to an exact string match; delegate to the
            # LLM judge. This is 0.35 (<=40%) of the total score.
            from reward_judge import call_llm_judge

            judge_score = call_llm_judge(
                task_instruction=(
                    "Compose and send an email to a partner asking for their "
                    "availability next week (e.g. to schedule a kickoff meeting)."
                ),
                success_criteria=(
                    "Score 1.0 only if the email body clearly asks the recipient "
                    "for their availability / schedule / free times for NEXT WEEK "
                    "(any phrasing that requests when they are available next week). "
                    "Score 0.0 if it does not request availability or does not "
                    "reference next week."
                ),
                state_excerpt="EMAIL SUBJECT: {}\n\nEMAIL BODY:\n{}".format(
                    target_email.get("subject") or "", body
                ),
            )
            # judge_score is a float in [0.0, 1.0]; scale into the 0.35 slice.
            score += 0.35 * max(0.0, min(1.0, float(judge_score)))

    # --- Over-action penalties ---------------------------------------------
    penalty = 0.0

    # Distractor emails must be unchanged.
    modified = diff.get("modifiedEmails") or {}
    deleted = set(diff.get("deletedEmails") or [])
    for did in DISTRACTOR_IDS:
        if did in modified or did in deleted:
            penalty += 0.25

    # Ensure both distractors are still present in the inbox, untouched.
    present_ids = {e.get("id") for e in emails}
    for did in DISTRACTOR_IDS:
        e = next((x for x in emails if x.get("id") == did), None)
        if e is None:
            penalty += 0.25
        elif _norm(e.get("folder")) not in ("inbox", ""):
            penalty += 0.25

    # Drafts must stay empty (sent email should not have been saved as a draft).
    if drafts:
        penalty += 0.25

    final = max(0.0, min(1.0, score - penalty))
    print("REWARD: {:.1f}".format(round(final, 1)))


if __name__ == "__main__":
    main()
