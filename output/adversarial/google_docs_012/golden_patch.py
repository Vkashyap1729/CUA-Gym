"""
Golden Patch: Alice currently has editor rights on "Financial Model" — downgrade her to view-only.
Task ID: google_docs_012
Domain: mock_websites
Mock: google_docs
Changes: doc-1 sharedWith entry for user-2 (Alice) permission editor -> viewer; user-3 unchanged.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# Downgrade Alice (user-2) from editor to viewer on "Financial Model" (doc-1).
for entry in state['documents']['doc-1']['sharedWith']:
    if entry['userId'] == 'user-2':
        entry['permission'] = 'viewer'

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
