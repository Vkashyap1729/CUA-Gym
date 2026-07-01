"""
Golden Patch: Clean up the "Archive" workspace: delete "Draft A" and "Draft B", but keep "Draft C".
Task ID: google_docs_025
Domain: mock_websites
Mock: google_docs
Changes: remove doc-1 (Draft A) and doc-2 (Draft B) from documents;
         remove comment-1 (on deleted doc-1); doc-3, doc-4 and comment-2 remain.
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
# Delete "Draft A" (doc-1) and "Draft B" (doc-2); keep "Draft C" (doc-3) and Master Index (doc-4).
for doc_id in ('doc-1', 'doc-2'):
    state['documents'].pop(doc_id, None)

# Deleting a document also removes its comments. comment-1 was on doc-1.
# comment-2 (on doc-3) remains.
state['comments'] = [c for c in state['comments'] if c['docId'] in state['documents']]

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
assert set(go2['current_state']['documents'].keys()) == {'doc-3', 'doc-4'}, \
    'documents not pruned correctly'
assert {c['id'] for c in go2['current_state']['comments']} == {'comment-2'}, \
    'comments not pruned correctly'
print('Verified: state_diff is non-empty')
