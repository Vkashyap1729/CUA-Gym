"""
Golden Patch: Disable link sharing on "Confidential Memo" and remove the external collaborator
Task ID: google_docs_033
Domain: mock_websites
Mock: google_docs
Changes: documents[doc-1].linkSharing.enabled -> False; sharedWith -> [] (user-2 removed).
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
doc = state['documents']['doc-1']
# Disable link sharing (permission value left untouched; only `enabled` must be False).
doc['linkSharing']['enabled'] = False
# Remove the external collaborator so only the owner can access it.
doc['sharedWith'] = []

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
