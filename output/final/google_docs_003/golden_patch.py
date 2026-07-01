"""
Golden Patch: Delete the document called "Old Draft v1"
Task ID: google_docs_003
Domain: mock_websites
Mock: google_docs_mock
Changes: remove doc-1 from documents map; remove comment-1 (its comment) from comments array.
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
# Delete "Old Draft v1" (doc-1): remove from documents map and drop its comments.
state['documents'].pop('doc-1', None)
state['comments'] = [c for c in state['comments'] if c.get('docId') != 'doc-1']

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
assert 'doc-1' not in go2['current_state']['documents'], 'doc-1 still present in current state'
assert 'doc-2' in go2['current_state']['documents'], 'doc-2 should remain'
assert 'doc-3' in go2['current_state']['documents'], 'doc-3 should remain'
assert all(c.get('docId') != 'doc-1' for c in go2['current_state']['comments']), 'comment-1 should be removed'
assert any(c.get('id') == 'comment-2' for c in go2['current_state']['comments']), 'comment-2 should remain'
print('Verified: state_diff is non-empty')
