"""
Golden Patch: Recover accidentally-trashed client email to inbox (unread, starred),
then permanently delete the phishing email still in trash.
Task ID: gmail_024
Domain: mock_websites
Mock: gmail
Changes:
  - email_1: folder trash -> inbox, read True -> False, starred False -> True
  - email_2: permanently removed from emails array (appears in state_diff.deletedEmails)
  - email_3: unchanged (distractor)
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
# 1) Recover email_1: back to inbox, unread, starred
for email in state['emails']:
    if email['id'] == 'email_1':
        email['folder'] = 'inbox'
        email['read'] = False
        email['starred'] = True

# 2) Permanently delete email_2 (the phishing message)
state['emails'] = [e for e in state['emails'] if e['id'] != 'email_2']

# email_3 is left untouched.

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print(f'Verified: state_diff is non-empty')
