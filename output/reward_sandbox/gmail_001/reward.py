#!/usr/bin/env python3
"""Reward for gmail task: star the email from Alice Chen about the quarterly budget.

Scores ONLY the task-introduced change (email_1.starred: false -> true).
Purely exact state checks -- no LLM judge (the action is objective).
- 1.0  target email starred, nothing else touched
- 0.0  target email not starred (initial / not-done state)
- over-action (starring/modifying distractors, adding/deleting emails) is penalized
"""

import json
import urllib.request

BASE_URL = 'https://cua-gym-gmail.xlang.ai'


def _read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def _fetch(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _is_target(email):
    """The email from Alice Chen (alice.chen@finance.co) about the quarterly budget.

    Distinguished from her other email ('Out of office next week') by the subject
    referencing the budget -- same sender, different subject must NOT match.
    """
    frm = (email.get('from') or {}).get('email', '').lower()
    subject = (email.get('subject') or '').lower()
    return frm == 'alice.chen@finance.co' and 'budget' in subject


def compute_reward():
    sid = _read_sid()
    data = _fetch(sid)

    current = data.get('current_state') or {}
    diff = data.get('state_diff') or {}
    emails = current.get('emails') or []

    # Locate the target email by sender + subject content.
    targets = [e for e in emails if _is_target(e)]
    if not targets:
        return 0.0
    target = targets[0]
    target_id = target.get('id')

    # --- Main criterion: target must be starred ---
    if target.get('starred') is not True:
        return 0.0
    score = 1.0

    # --- Over-action penalties (distractors / structure must be untouched) ---
    modified = diff.get('modifiedEmails') or {}
    new_emails = diff.get('newEmails') or []
    deleted_emails = diff.get('deletedEmails') or []

    penalty = 0.0
    for eid, changes in modified.items():
        if eid == target_id:
            # Only the starred flag flipping is expected on the target.
            extra = [k for k in (changes or {}) if k != 'starred']
            if extra:
                penalty += 0.5
        else:
            # Any change to a distractor email is over-action.
            penalty += 0.5

    if new_emails:
        penalty += 0.5
    if deleted_emails:
        penalty += 0.5

    # Belt-and-suspenders: directly confirm no other email is starred.
    for e in emails:
        if e.get('id') != target_id and e.get('starred') is True:
            penalty += 0.5

    return max(0.0, score - penalty)


if __name__ == '__main__':
    try:
        reward = compute_reward()
    except Exception as exc:
        print('ERROR:', exc)
        reward = 0.0
    reward = round(max(0.0, min(1.0, float(reward))), 2)
    print('REWARD:', reward)
