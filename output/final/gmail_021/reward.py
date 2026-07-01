#!/usr/bin/env python3
"""Reward for gmail_021.

Task: Save a DRAFT to alice@company.com titled 'Budget proposal' with a note
that the user will send full numbers next week — do NOT send it.

Scored (progressive, 0.0-1.0), against ONLY the task-introduced change:
  0.25  a new draft was created (drafts non-empty vs. empty initial)
  0.20  the draft is addressed to alice@company.com
  0.25  the draft subject is 'Budget proposal'
  0.20  (LLM judge, <=40%) the draft body notes full numbers come next week
  0.10  no over-action: nothing sent to 'sent', inbox email_1 untouched
"""

import json
import urllib.request

from reward_judge import call_llm_judge  # returns a float in [0.0, 1.0]

BASE_URL = "https://cua-gym-gmail.xlang.ai"

TASK_INSTRUCTION = (
    "Save a draft to alice@company.com titled 'Budget proposal' with a note that "
    "I'll send full numbers next week — don't send it yet."
)

TARGET_TO = "alice@company.com"
TARGET_SUBJECT = "budget proposal"


def _norm(s):
    return (s or "").strip().lower()


def _to_emails(to_field):
    """Extract a set of recipient email addresses from a `to` array."""
    out = set()
    if isinstance(to_field, list):
        for r in to_field:
            if isinstance(r, dict):
                out.add(_norm(r.get("email")))
            elif isinstance(r, str):
                out.add(_norm(r))
    elif isinstance(to_field, str):
        out.add(_norm(to_field))
    return out


def draft_match_score(d):
    """Rank drafts so we pick the task-introduced one (recipient weighted highest)."""
    s = 0
    if TARGET_TO in _to_emails(d.get("to")):
        s += 2
    if TARGET_SUBJECT in _norm(d.get("subject")):
        s += 1
    return s


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    drafts = current.get("drafts", []) or []
    emails = current.get("emails", []) or []

    score = 0.0

    best = max(drafts, key=draft_match_score) if drafts else None

    if best is None:
        print("No draft found in drafts array.")
        print("REWARD: 0.0")
        return

    # 0.25 -- a draft exists at all (initial has none)
    score += 0.25

    # 0.20 -- addressed to alice@company.com
    to_ok = TARGET_TO in _to_emails(best.get("to"))
    if to_ok:
        score += 0.20
    print(f"draft.to = {sorted(_to_emails(best.get('to')))} | to_ok={to_ok}")

    # 0.25 -- subject is 'Budget proposal'
    subj_ok = TARGET_SUBJECT in _norm(best.get("subject"))
    if subj_ok:
        score += 0.25
    print(f"draft.subject = {best.get('subject')!r} | subj_ok={subj_ok}")

    # 0.20 -- body notes full numbers will be sent next week (LLM judge)
    body = (best.get("body") or best.get("snippet") or "").strip()
    if body:
        # JUSTIFICATION: whether the body communicates "I'll send the full numbers
        # next week" is a paraphrase/wording check that exact string matching cannot
        # reliably do; delegated to the LLM judge (0.20 of 1.0 = 20% <= 40% cap).
        judge_score = call_llm_judge(
            TASK_INSTRUCTION,
            (
                "The draft body must communicate that the user will send the full/"
                "complete numbers (the budget figures) next week. Any clear paraphrase "
                "of 'I'll send full numbers next week' counts. Score 1.0 if the body "
                "clearly conveys this, 0.0 if it is unrelated or omits this note."
            ),
            f"Draft subject: {best.get('subject')!r}\nDraft body:\n{body}",
        )
        try:
            judge_score = max(0.0, min(1.0, float(judge_score)))
        except (TypeError, ValueError):
            judge_score = 0.0
        score += 0.20 * judge_score
        print(f"body judge_score = {judge_score}")
    else:
        print("draft.body is empty -> no body credit")

    # 0.10 -- no over-action: message not sent, pre-existing inbox email untouched
    sent_to_alice = any(
        (e.get("folder") == "sent") and (TARGET_TO in _to_emails(e.get("to")))
        for e in emails
    )
    modified = diff.get("modifiedEmails", {}) or {}
    email_1_touched = "email_1" in modified
    over_action = sent_to_alice or email_1_touched
    if not over_action:
        score += 0.10
    print(
        f"over_action={over_action} | sent_to_alice={sent_to_alice} "
        f"email_1_touched={email_1_touched}"
    )

    score = max(0.0, min(1.0, round(score, 4)))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    main()
