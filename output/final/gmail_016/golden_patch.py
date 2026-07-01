"""
Golden Patch: Delete the old 'Weekly deals' promo from inbox
Task ID: gmail_016
Domain: mock_websites
Mock: gmail
Changes: Move email_1 ('Weekly deals') from folder 'inbox' to 'trash'.
         email_2 and email_3 are left untouched.
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
# Move ONLY the plain 'Weekly deals' message (email_1) to trash.
for email in state['emails']:
    if email['id'] == 'email_1':
        assert email['subject'] == 'Weekly deals', \
            f"Unexpected subject for email_1: {email['subject']}"
        email['folder'] = 'trash'
        break
else:
    raise AssertionError('email_1 not found in state')

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
