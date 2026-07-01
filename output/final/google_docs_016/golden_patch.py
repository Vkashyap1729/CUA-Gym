"""
Golden Patch: Change the editor to viewing (read-only) mode while reviewing the "Legal Terms" document.
Task ID: google_docs_016
Domain: mock_websites
Mock: google_docs_mock
Changes: ui.viewMode "editing" -> "viewing" (document content and currentDocId unchanged).
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
# Switch the editor view mode to viewing (read-only). Touch nothing else.
state['ui']['viewMode'] = 'viewing'

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
assert go2['current_state']['ui']['viewMode'] == 'viewing', 'viewMode should be viewing after patch'
assert go2['current_state']['ui']['currentDocId'] == 'doc-1', 'currentDocId must remain doc-1'
print('Verified: state_diff is non-empty')
