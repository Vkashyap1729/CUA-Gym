"""
Golden Patch: Resolve the comment Alice left on the "Design Spec" document.
Task ID: google_docs_007
Domain: mock_websites
Mock: google_docs
Changes: comment-1 (Alice Chen, on doc-1) resolved -> True. Bob's comment-2 untouched.
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
# Resolve Alice's comment (comment-1) on the Design Spec document.
# Leave Bob's comment (comment-2) untouched.
for comment in state['comments']:
    if comment['id'] == 'comment-1':
        comment['resolved'] = True

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
cur_comments = {c['id']: c for c in go2['current_state']['comments']}
assert cur_comments['comment-1']['resolved'] is True, 'comment-1 should be resolved in golden'
assert cur_comments['comment-2']['resolved'] is False, 'comment-2 (Bob) must remain unresolved'
print('Verified: state_diff is non-empty; comment-1 resolved, comment-2 untouched')
