"""
Golden Patch: Triage three Finance invoice emails
Task ID: gmail_012
Domain: mock_websites
Mock: gmail_mock
Changes: email_1.starred → True (stays in inbox); email_2.folder → 'trash' (starred stays False);
         email_3, email_4, email_5 untouched.
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
for email in state['emails']:
    if email['id'] == 'email_1':
        # Star the OVERDUE invoice; folder stays 'inbox'
        email['starred'] = True
    elif email['id'] == 'email_2':
        # Move the PAID invoice to trash; starred stays False
        email['folder'] = 'trash'
    # email_3 (pending), email_4, email_5 left completely untouched

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
