"""
Golden Patch: Archive every inbox email from @newsletters.co, leave everything else.
Task ID: gmail_020
Domain: mock_websites
Mock: gmail_mock
Changes: email_1, email_2, email_5 folder inbox -> archive. email_3, email_4 unchanged.
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
# Archive exactly the inbox emails whose sender domain is exactly newsletters.co.
TO_ARCHIVE = {"email_1", "email_2", "email_5"}
for email in state['emails']:
    if email['id'] in TO_ARCHIVE:
        email['folder'] = 'archive'

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
print('DONE')
