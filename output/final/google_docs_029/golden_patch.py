"""
Golden Patch: Add a comment on the "Recipe Collection" document quoting the "Recipes" heading
Task ID: google_docs_029
Domain: mock_websites
Mock: google_docs
Changes: comments gains exactly one Comment on doc-1 by user-1,
         content "Add prep time for each recipe", quotedText "Recipes", resolved=false.
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
# Add exactly one comment on doc-1 authored by the current user (user-1),
# quoting the "Recipes" heading. Document content is untouched.
state['comments'].append({
    'id': 'comment-1740000000000',
    'docId': 'doc-1',
    'userId': 'user-1',
    'content': 'Add prep time for each recipe',
    'resolved': False,
    'created': '2025-02-18T15:00:00Z',
    'quotedText': 'Recipes',
    'replies': [],
})

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
