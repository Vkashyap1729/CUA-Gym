"""
Golden Patch: Clean up inbox — mark two unread newsletters as read and archive them.
Task ID: gmail_008
Domain: mock_websites
Mock: gmail
Changes: email_2 and email_4 → read=True, folder='archive'. Nothing else touched.
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
# The two unread newsletters (email_2, email_4): mark read + archive.
targets = {'email_2', 'email_4'}
patched = set()
for email in state['emails']:
    if email['id'] in targets:
        email['read'] = True
        email['folder'] = 'archive'
        patched.add(email['id'])

assert patched == targets, f'Expected to patch {targets}, patched {patched}'

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
