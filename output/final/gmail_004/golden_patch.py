"""
Golden Patch: Report the message pretending to be from my bank as spam.
Task ID: gmail_004
Domain: mock_websites
Mock: gmail
Changes: email_3 (phishing, spoofed bank domain) folder inbox -> spam.
         All other emails (incl. legitimate email_4) unchanged.
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
# Report the phishing email pretending to be from the bank as spam:
# move email_3 from inbox to spam. Touch nothing else.
for email in state['emails']:
    if email['id'] == 'email_3':
        email['folder'] = 'spam'
        break
else:
    raise AssertionError('email_3 not found in initial state')

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
print(f'Verified: state_diff is non-empty')
