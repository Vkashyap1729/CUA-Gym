"""
Golden Patch: Clean up starred items
Task ID: gmail_022
Domain: mock_websites
Mock: gmail
Changes: email_1.starred=False, email_2.starred=False, email_3.important=True (email_3.starred stays True, email_4 unchanged)
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
        email['starred'] = False          # unstar promo email
    elif email['id'] == 'email_2':
        email['starred'] = False          # unstar promo email
    elif email['id'] == 'email_3':
        email['important'] = True          # mark work email important (stays starred)
    # email_4 untouched

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
