"""
Golden Patch: Empty spam — permanently delete every email in the spam folder.
Task ID: gmail_010
Domain: mock_websites
Mock: gmail
Changes: Remove email_5 and email_6 (the two spam emails) entirely from the
         emails array so they appear in state_diff.deletedEmails. Inbox emails
         (email_1, email_2, email_3) are left untouched.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-gmail.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# Permanently delete every email in the spam folder (email_5, email_6).
# "Permanently delete" = removed entirely from the emails array (NOT moved to trash).
spam_ids = {e['id'] for e in state['emails'] if e['folder'] == 'spam'}
state['emails'] = [e for e in state['emails'] if e['id'] not in spam_ids]

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid} (deleted {sorted(spam_ids)})')

# --- Verify the change registered ---
# IMPORTANT (mock reality, verified against the live server):
#   The gmail_mock server `/go` endpoint computes a GENERIC per-key state_diff
#   (vite.config.js `calculateStateDiff`). A deletion of emails shows up as
#   `state_diff.emails = {modified: [<remaining emails>]}` — the server does NOT
#   emit a top-level `deletedEmails` list (that richer diff lives only in the
#   client-side src/data/mockData.js and is never exposed over HTTP).
#   => The permanent deletion is detectable ONLY by diffing initial_state vs
#      current_state email-id sets. reward.py MUST use that id-set diff, not
#      `state_diff.deletedEmails`.
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
assert 'emails' in go2['state_diff'], f"emails not in state_diff: {go2['state_diff']}"

cur_ids = {e['id'] for e in go2['current_state']['emails']}
init_ids = {e['id'] for e in go2['initial_state']['emails']}
removed = init_ids - cur_ids
assert removed == {'email_5', 'email_6'}, f'Unexpected removed emails: {removed}'
assert not (cur_ids - init_ids), f'Unexpected new emails: {cur_ids - init_ids}'
# Inbox distractors untouched
assert {'email_1', 'email_2', 'email_3'} <= cur_ids, 'Inbox distractors were altered'
# Spam folder is now empty; trash stayed empty (permanent delete, not move-to-trash)
assert not [e for e in go2['current_state']['emails'] if e['folder'] == 'spam'], 'spam not empty'
assert not [e for e in go2['current_state']['emails'] if e['folder'] == 'trash'], 'trash not empty'
print(f'Verified: emails removed from array = {sorted(removed)}; inbox intact; spam+trash empty')
