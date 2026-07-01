"""Reward for gmail_002: 'Open and read the message from IT Support about the password reset.'

Task-introduced change: email_2 (IT Support, 'Action required: reset your password')
goes from read=false -> read=true. Every other email must stay unchanged
(read=false, no folder/star/label changes). No new/deleted emails.

Scoring (progressive, exact-state only — no LLM judge needed for a read-status check).
The primary action is a prerequisite: with email_2 still unread (initial state) the
score is 0.0 regardless of anything else, so over-action credit cannot leak in.
  email_2.read != true              -> 0.0
  email_2.read == true, over-action -> 0.8
  email_2.read == true, clean       -> 1.0
"""

import json
import urllib.request

BASE_URL = 'https://cua-gym-gmail.xlang.ai'


def _get_state():
    with open('/tmp/task_web_sid') as f:
        sid = f.read().strip()
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    data = _get_state()
    current = data.get('current_state', {}) or {}
    diff = data.get('state_diff', {}) or {}

    emails = current.get('emails', []) or []
    by_id = {e.get('id'): e for e in emails}

    # --- Primary criterion (prerequisite): the IT Support password-reset email is read. ---
    # If it is not read, the task is not done at all -> score 0.0 (this is the initial state).
    target = by_id.get('email_2')
    target_read = bool(target and target.get('read') is True)
    if not target_read:
        print('REWARD: 0.0')
        return

    # Action performed: base credit. Over-action guard can dock the remaining 0.2.
    score = 0.8

    # --- Over-action guard (0.2): nothing else may change. ---
    # Authoritative signal is state_diff; the only allowed modification is
    # email_2.read (false -> true). Any other modified/new/deleted email is over-action.
    clean = True

    modified = diff.get('modifiedEmails', {}) or {}
    for eid, changes in modified.items():
        if eid == 'email_2':
            # email_2 may only have its read flag changed.
            if set((changes or {}).keys()) - {'read'}:
                clean = False
        else:
            clean = False

    if diff.get('newEmails'):
        clean = False
    if diff.get('deletedEmails'):
        clean = False

    # Belt-and-suspenders against a missing/partial diff: verify distractors from
    # current_state directly — every non-target inbox email must remain unread.
    for eid, e in by_id.items():
        if eid == 'email_2':
            continue
        if e.get('read') is True:
            clean = False
            break

    if clean:
        score += 0.2

    # Clamp and emit.
    score = max(0.0, min(1.0, score))
    print('REWARD: {:.1f}'.format(score))


if __name__ == '__main__':
    main()
