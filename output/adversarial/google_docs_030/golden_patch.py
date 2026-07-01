"""
Golden Patch: Reply to Alice's comment on "Translation Strings" and resolve it
Task ID: google_docs_030
Domain: mock_websites
Mock: google_docs
Changes: comment-1 gains one reply by user-1 ("Done — updated in the latest version.")
         and comment-1.resolved becomes True.
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
for comment in state['comments']:
    if comment['id'] == 'comment-1':
        comment['replies'].append({
            'id': 'reply-1',
            'userId': 'user-1',
            'content': 'Done — updated in the latest version.',
            'created': '2025-02-19T10:15:00Z',
        })
        comment['resolved'] = True
        break

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
