"""
Golden Patch: Share "Investor Deck Notes" with Alice as a commenter and turn on link sharing set to viewer
Task ID: google_docs_024
Domain: mock_websites
Mock: google_docs
Changes: doc-1.sharedWith += {user-2, commenter}; doc-1.linkSharing.enabled = True (permission stays viewer)
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

# Share with Alice (user-2) as a commenter — no extra entries
doc['sharedWith'] = [{'userId': 'user-2', 'permission': 'commenter'}]

# Turn on link sharing, permission set to viewer
doc['linkSharing']['enabled'] = True
doc['linkSharing']['permission'] = 'viewer'

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
