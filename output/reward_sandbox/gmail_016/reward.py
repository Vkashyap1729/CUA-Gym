"""Reward for gmail_016.

Task: Delete the old 'Weekly deals' promo (email_1) from the inbox.
Expected end state: email_1 is trashed (folder == 'trash') or removed from the
mailbox entirely. The distractors email_2 ('Weekly deals - LAST CHANCE') and
email_3 ('Standup notes') must be left untouched.

Scoring is a pure state check (no subjective content), progressive 0.0-1.0:
  - main action (email_1 deleted/trashed): worth full credit
  - over-action penalty: each named distractor that was modified subtracts credit
Initial (not-done) state -> 0.0, fully-completed golden state -> 1.0.
"""
import json
import urllib.request

BASE_URL = 'https://cua-gym-gmail.xlang.ai'

with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

resp = urllib.request.urlopen(BASE_URL + '/go?sid=' + sid, timeout=30)
data = json.loads(resp.read().decode())

current = data.get('current_state') or {}
initial = data.get('initial_state') or {}
diff = data.get('state_diff') or {}

cur_emails = current.get('emails', []) or []
init_emails = initial.get('emails', []) or []
cur_by_id = {e.get('id'): e for e in cur_emails}
init_by_id = {e.get('id'): e for e in init_emails}
deleted_ids = set(diff.get('deletedEmails') or [])

# ---------------------------------------------------------------------------
# Main action: the plain 'Weekly deals' message (email_1) must be gone from the
# inbox -- either moved to trash or permanently removed from the mailbox.
# ---------------------------------------------------------------------------
main = 0.0
e1 = cur_by_id.get('email_1')
if e1 is None or 'email_1' in deleted_ids:
    main = 1.0
    print("email_1 permanently removed from mailbox -> done")
else:
    folder = e1.get('folder')
    if folder == 'trash':
        main = 1.0
        print("email_1 moved to trash -> done")
    elif folder in ('spam', 'archive'):
        # Out of the inbox but not the requested destination -> partial credit.
        main = 0.5
        print("email_1 moved to '%s' (out of inbox, wrong destination) -> partial" % folder)
    else:
        main = 0.0
        print("email_1 still in folder '%s' -> not done" % folder)

# ---------------------------------------------------------------------------
# Over-action penalty: the named distractors (email_2, email_3) must be
# unchanged relative to the initial state. Compare the fields a delete/organize
# action could plausibly touch.
# ---------------------------------------------------------------------------
_TRACKED = ('folder', 'read', 'starred', 'important', 'category', 'subject', 'labels')


def distractor_changed(eid):
    init_e = init_by_id.get(eid)
    cur_e = cur_by_id.get(eid)
    if init_e is None:
        return False  # not part of the initial state; nothing to protect
    if cur_e is None or eid in deleted_ids:
        return True  # distractor was deleted
    for field in _TRACKED:
        if init_e.get(field) != cur_e.get(field):
            return True
    return False


penalty = 0.0
for eid in ('email_2', 'email_3'):
    if distractor_changed(eid):
        penalty += 0.5
        print("OVER-ACTION: distractor %s was modified -> penalty" % eid)

score = max(0.0, main - penalty)
score = round(min(1.0, score), 2)

print("main=%.2f penalty=%.2f" % (main, penalty))
print("REWARD: %s" % score)
