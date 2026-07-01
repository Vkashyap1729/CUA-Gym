"""
Golden Patch: Switch the document list to list view instead of the grid of thumbnails.
Task ID: google_docs_004
Domain: mock_websites
Mock: google_docs_mock
Changes: ui.documentListView "grid" -> "list" (nothing else touched).
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
state['ui']['documentListView'] = 'list'

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
assert go2['current_state']['ui']['documentListView'] == 'list', 'documentListView should be list'
assert go2['initial_state']['ui']['documentListView'] == 'grid', 'initial_state must remain grid'
print('Verified: state_diff is non-empty')
