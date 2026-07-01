"""
Golden Patch: Make a copy of "Policy Handbook", then rename the copy to "Policy Handbook 2025".
Task ID: google_docs_028
Domain: mock_websites
Mock: google_docs
Changes: Adds exactly one new document (new ID) titled "Policy Handbook 2025" with the
         same content/owner as doc-1. Original doc-1 and doc-2 left untouched.
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
# Copy "Policy Handbook" (doc-1) -> new doc with new ID, then rename the copy
# to "Policy Handbook 2025". Same content, same owner. doc-1 itself untouched.
source = state['documents']['doc-1']
new_id = 'doc-1750000000000'
state['documents'][new_id] = {
    "id": new_id,
    "title": "Policy Handbook 2025",
    "content": source['content'],
    "ownerId": "user-1",
    "starred": False,
    "created": "2025-03-01T12:00:00Z",
    "updated": "2025-03-01T12:00:00Z",
    "sharedWith": [],
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
