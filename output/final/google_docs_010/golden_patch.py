"""
Golden Patch: Make a copy of the "Contract Template" document.
Task ID: google_docs_010
Domain: mock_websites
Mock: google_docs
Changes: Adds one new document "Copy of Contract Template" with a new ID,
         same content/owner as doc-1. doc-1 and doc-2 untouched.
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
# Copy doc-1 ("Contract Template") into a new document with a new ID.
src = state['documents']['doc-1']
new_id = 'doc-1740000000000'
state['documents'][new_id] = {
    'id': new_id,
    'title': 'Copy of Contract Template',
    'content': src['content'],
    'ownerId': 'user-1',
    'starred': False,
    'created': '2025-02-20T12:00:00Z',
    'updated': '2025-02-20T12:00:00Z',
    'sharedWith': [],
    'linkSharing': {'enabled': False, 'permission': 'viewer'},
}

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
