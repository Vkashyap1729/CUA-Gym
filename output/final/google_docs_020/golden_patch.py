"""
Golden Patch: Create a new document titled "Onboarding Checklist"
Task ID: google_docs_020
Domain: mock_websites
Mock: google_docs
Changes: Adds exactly one new document "Onboarding Checklist" (owner user-1) with an
         "Onboarding" heading and a paragraph "Complete all items before day one."
         doc-1 "HR Policies" is left untouched.
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
# Add exactly one new document. doc-1 is left untouched.
new_doc_id = "doc-1740000000000"
state['documents'][new_doc_id] = {
    "id": new_doc_id,
    "title": "Onboarding Checklist",
    "content": "<h1>Onboarding</h1><p>Complete all items before day one.</p>",
    "ownerId": "user-1",
    "starred": False,
    "created": "2025-02-18T14:30:00Z",
    "updated": "2025-02-18T14:30:00Z",
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
