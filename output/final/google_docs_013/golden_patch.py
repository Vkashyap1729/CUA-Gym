"""
Golden Patch: Revoke Bob's access to the "Salary Bands" document entirely.
Task ID: google_docs_013
Domain: mock_websites
Mock: google_docs
Changes: Remove the user-3 (Bob) share entry from doc-1.sharedWith.
         Alice (user-2) viewer entry remains -> sharedWith ends with exactly one entry.
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
# Remove Bob (user-3) from doc-1's sharedWith; leave everything else untouched.
doc = state['documents']['doc-1']
doc['sharedWith'] = [
    entry for entry in doc['sharedWith'] if entry.get('userId') != 'user-3'
]

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
