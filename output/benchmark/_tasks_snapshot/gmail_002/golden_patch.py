"""
Golden Patch: Open and read the message from IT Support about the password reset.
Task ID: gmail_002
Domain: mock_websites
Mock: gmail
Changes: mark email_2 (IT Support, 'Action required: reset your password') as
         read. All other emails remain unread; no folder/star/label changes.
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
# The task is to open/read the IT Support password-reset message (email_2).
# Reading an email flips emails[i].read: false -> true. Touch nothing else.
target_found = False
for email in state['emails']:
    if email['id'] == 'email_2':
        email['read'] = True
        target_found = True
        break
assert target_found, 'email_2 not found in state'

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial'
print(f'Verified: state_diff is non-empty')
