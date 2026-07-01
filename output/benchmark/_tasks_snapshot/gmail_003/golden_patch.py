"""
Golden Patch: Move the promotional ShopMart email to trash
Task ID: gmail_003
Domain: mock_websites
Mock: gmail_mock
Changes: email_4 (ShopMart promo) folder inbox -> trash; nothing else changes.
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
# Move the ShopMart promotional email (email_4) to trash. Touch nothing else.
moved = False
for email in state['emails']:
    if email['id'] == 'email_4':
        email['folder'] = 'trash'
        moved = True
        break
assert moved, 'email_4 (ShopMart promo) not found in state'

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
cur = {e['id']: e for e in go2['current_state']['emails']}
assert cur['email_4']['folder'] == 'trash', 'email_4 should be in trash after patch'
for eid in ('email_1', 'email_2', 'email_3'):
    assert cur[eid]['folder'] == 'inbox', f'{eid} should remain in inbox'
print('Verified: state_diff is non-empty; email_4 -> trash, others unchanged')
