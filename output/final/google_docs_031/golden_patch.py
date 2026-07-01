"""
Golden Patch: Create meeting-notes doc "All-Hands 2025-06" shared with Alice and Bob as viewers
Task ID: google_docs_031
Domain: mock_websites
Mock: google_docs
Changes: adds exactly one new document titled "All-Hands 2025-06" (owner user-1)
         shared with user-2 (Alice) and user-3 (Bob) as viewers. doc-1 untouched.
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
# Add exactly one new document; do not touch doc-1.
new_doc_id = "doc-1750000000000"
state['documents'][new_doc_id] = {
    "id": new_doc_id,
    "title": "All-Hands 2025-06",
    "content": "<h1>All-Hands 2025-06</h1><p></p>",
    "ownerId": "user-1",
    "starred": False,
    "created": "2025-06-15T09:00:00Z",
    "updated": "2025-06-15T09:00:00Z",
    "sharedWith": [
        {"userId": "user-2", "permission": "viewer"},
        {"userId": "user-3", "permission": "viewer"},
    ],
    "linkSharing": {"enabled": False, "permission": "viewer"},
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
