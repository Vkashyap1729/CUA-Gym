#!/usr/bin/env python3
"""Reward for: Archive every inbox email from @newsletters.co, leave everything else.

Task-introduced change: emails whose sender is at the EXACT domain
`newsletters.co` must move from folder 'inbox' -> 'archive'. All other emails
(including the newsletters.co.uk distractor and the company.com distractor)
must remain untouched in the inbox.

Progressive scoring (exact state checks only, no LLM judge needed):
  - +1/3 for each of the three target emails correctly archived.
  - Over-action penalty: any distractor moved out of the inbox, or any target
    moved somewhere other than 'archive', reduces the score.
Initial (nothing done) -> 0.0 ; fully completed -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

# Ground-truth email IDs from the task context.
TARGETS = ["email_1", "email_2", "email_5"]      # sender @newsletters.co -> must be archived
DISTRACTORS = ["email_3", "email_4"]             # must stay in the inbox, unchanged


def _sender_domain(email_obj):
    frm = email_obj.get("from") or {}
    addr = (frm.get("email") or "").strip().lower()
    return addr.rsplit("@", 1)[-1] if "@" in addr else ""


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    current = data.get("current_state") or {}
    emails = {e.get("id"): e for e in (current.get("emails") or [])}

    score = 0.0

    # --- Reward the intended archives (exact domain match on @newsletters.co) ---
    for eid in TARGETS:
        e = emails.get(eid)
        if e is None:
            continue
        folder = (e.get("folder") or "").strip().lower()
        domain = _sender_domain(e)
        # Only credit if it's genuinely the @newsletters.co sender and now archived.
        if domain == "newsletters.co" and folder == "archive":
            score += 1.0 / 3.0

    # --- Over-action penalties: distractors must be untouched (still inbox) ---
    penalty = 0.0
    for eid in DISTRACTORS:
        e = emails.get(eid)
        if e is None:
            continue
        folder = (e.get("folder") or "").strip().lower()
        if folder != "inbox":
            # A distractor was moved (e.g. newsletters.co.uk wrongly archived,
            # or company.com touched). Penalize heavily.
            penalty += 1.0 / 3.0

    # --- Targets moved to the WRONG place (not inbox, not archive) ---
    for eid in TARGETS:
        e = emails.get(eid)
        if e is None:
            continue
        folder = (e.get("folder") or "").strip().lower()
        if folder not in ("inbox", "archive"):
            penalty += 1.0 / 6.0

    score = max(0.0, score - penalty)
    score = round(min(1.0, score), 4)

    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
