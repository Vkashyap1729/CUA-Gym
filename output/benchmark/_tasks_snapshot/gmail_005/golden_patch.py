"""
Golden Patch: Apply 'Travel' label to the SkyJet flight confirmation email
Task ID: gmail_005
Domain: mock_websites
Mock: gmail
Changes: email_2.labels [] -> ['l3'] (Travel). All other emails untouched.
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
# Add the 'Travel' label (l3) to email_2 (the SkyJet flight confirmation).
# Preserve email_1's ['l1'] and leave email_3 / email_4 unlabeled.
for email in state['emails']:
    if email['id'] == 'email_2':
        assert email['labels'] == [], f"Unexpected pre-existing labels: {email['labels']}"
        email['labels'] = ['l3']
        break
else:
    raise AssertionError('email_2 not found in initial state')

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
