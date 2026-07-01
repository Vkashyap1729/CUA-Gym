"""
Golden Patch: Delete the spam comment Bob posted on the "Feedback Form" document.
Task ID: google_docs_019
Domain: mock_websites
Mock: google_docs
Changes: Remove comment-2 (Bob's spam) from the comments array; comment-1 (Alice) remains.
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
# Delete Bob's spam comment (comment-2) from the comments array.
state['comments'] = [c for c in state['comments'] if c['id'] != 'comment-2']

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
assert len(go2['current_state']['comments']) == 1, 'expected exactly 1 comment after deletion'
assert all(c['id'] != 'comment-2' for c in go2['current_state']['comments']), 'comment-2 still present'
print('Verified: state_diff is non-empty')
