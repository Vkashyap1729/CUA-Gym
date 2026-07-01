"""
Golden Patch: Create a brand-new blank document titled "Weekly Standup Agenda"
Task ID: google_docs_005
Domain: mock_websites
Mock: google_docs
Changes: Adds exactly one new document (title "Weekly Standup Agenda", ownerId user-1).
         The two existing documents (doc-1, doc-2) remain untouched.
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

# --- Apply ONLY the minimal change the task requires ---
# Create one new blank document titled "Weekly Standup Agenda", owned by user-1.
new_doc_id = 'doc-1740000000000'
assert new_doc_id not in state['documents'], 'new doc id collides with existing doc'
state['documents'][new_doc_id] = {
    'id': new_doc_id,
    'title': 'Weekly Standup Agenda',
    'content': '<p></p>',  # brand-new blank document
    'ownerId': 'user-1',
    'starred': False,
    'created': '2025-02-18T12:00:00Z',
    'updated': '2025-02-18T12:00:00Z',
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
docs = go2['current_state']['documents']
assert len(docs) == 3, f'expected exactly 3 documents after patch, got {len(docs)}'
new_titles = [d['title'] for d in docs.values() if d['title'] == 'Weekly Standup Agenda']
assert len(new_titles) == 1, 'expected exactly one "Weekly Standup Agenda" document'
print('Verified: state_diff is non-empty and new document added')
