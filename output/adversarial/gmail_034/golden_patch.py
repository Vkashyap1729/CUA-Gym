"""
Golden Patch: Reorganize two flagged project emails (labels + star)
Task ID: gmail_034
Domain: mock_websites
Mock: gmail
Changes:
  - email_1: labels ['l2'] -> ['l1'] (remove Personal, add Work), starred False -> True (from project lead)
  - email_2: labels ['l2'] -> ['l1'] (remove Personal, add Work), starred stays False
  - email_3 (distractor): unchanged
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
        # remove Personal (l2), add Work (l1); star (from project lead)
        email['labels'] = ['l1']
        email['starred'] = True
    elif email['id'] == 'email_2':
        # remove Personal (l2), add Work (l1); starred unchanged
        email['labels'] = ['l1']
    # email_3 (distractor): untouched

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
print('Verified: state_diff is non-empty')
