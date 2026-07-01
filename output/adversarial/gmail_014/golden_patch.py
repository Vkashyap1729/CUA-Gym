"""
Golden Patch: Open and read the unread message from the recruiter.
Task ID: gmail_014
Domain: mock_websites
Mock: gmail
Changes: Mark email_1 (unread recruiter message) as read; leave all other
         emails and fields untouched.
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
# The task is to open and read the unread recruiter message (email_1).
# Only email_1.read flips false -> true. email_2 stays read:true,
# email_3 stays read:false. No other fields change.
for email in state['emails']:
    if email['id'] == 'email_1':
        email['read'] = True
        break

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
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print('Verified: state_diff is non-empty')
